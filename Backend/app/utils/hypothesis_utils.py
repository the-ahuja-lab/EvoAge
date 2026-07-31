"""
app/utils/hypothesis_utils.py

Pure helpers + every prompt for the EvoAge hypothesis pipeline.
Nothing here holds request state or loads a model -- see hypothesis_routes_new.py
for the stateful resources (RESCAL, edge tensor, Neo4j driver).
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from collections import defaultdict
from pathlib import Path
from textwrap import dedent
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import google.generativeai as genai
import openai
from openai import OpenAI
from pydantic import BaseModel

logger = logging.getLogger("HypothesisTesting")


# =============================================================================
# RELATIONS · CANONICAL LABELS · SIGNED VARIANTS
# =============================================================================

VALID_RELATIONS_RAW = """
anatomicalentity_anatomicalentity
anatomicalentity_biologicalprocess
anatomicalentity_cellularcomponent
anatomicalentity_chemicalentity
anatomicalentity_gene
biologicalprocess_biologicalprocess
biologicalprocess_cellularcomponent
biologicalprocess_chemicalentity
biologicalprocess_gene
biologicalprocess_molecularfunction
biologicalprocess_protein
cellularcomponent_cellularcomponent
cellularcomponent_chemicalentity
cellularcomponent_gene
chemicalentity_biologicalprocess
chemicalentity_chemicalentity
chemicalentity_disease
chemicalentity_gene
chemicalentity_mutation
chemicalentity_pathway
chemicalentity_protein
chemicalentity_tissue
chemicalentity_inhibits_biologicalprocess
chemicalentity_negativelyassociatedwith_biologicalprocess
chemicalentity_noeffect_biologicalprocess
chemicalentity_notassociatedwith_biologicalprocess
chemicalentity_positivelyassociatedwith_biologicalprocess
chemicalentity_promotes_biologicalprocess
disease_anatomicalentity
disease_chemicalentity
disease_disease
disease_gene
disease_mutation
disease_pathway
disease_phenotype
gene_anatomicalentity
gene_biologicalprocess
gene_cellularcomponent
gene_chemicalentity
gene_disease
gene_gene
gene_inhibits_biologicalprocess
gene_molecularfunction
gene_mutation
gene_negativelyassociatedwith_biologicalprocess
gene_notassociatedwith_biologicalprocess
gene_pathway
gene_phenotype
gene_positivelyassociatedwith_biologicalprocess
gene_promotes_biologicalprocess
gene_protein
gene_tissue
mirna_gene
molecularfunction_biologicalprocess
molecularfunction_chemicalentity
molecularfunction_molecularfunction
molecularfunction_protein
mutation_chemicalentity
mutation_disease
mutation_gene
mutation_mutation
mutation_protein
pathway_gene
pathway_pathway
phenotype_biologicalprocess
phenotype_cellularcomponent
phenotype_chemicalentity
phenotype_disease
phenotype_gene
phenotype_molecularfunction
phenotype_phenotype
phenotype_protein
plantspecies_chemicalentity
plantspecies_disease
pmid_cellularcomponent
pmid_chemicalentity
pmid_disease
pmid_protein
pmid_tissue
protein_biologicalprocess
protein_cellularcomponent
protein_chemicalentity
protein_disease
protein_molecularfunction
protein_pathway
protein_phenotype
protein_protein
protein_tissue
species_associatedwith
"""

VALID_RELATIONS: set = {
    ln.strip().strip("'").lower()
    for ln in VALID_RELATIONS_RAW.splitlines()
    if ln.strip()
}

# Labels that ACTUALLY exist in the KG (verified against the fulltext index).
# The old map had 'anatomy'->'Anatomy' and 'plantextract'->'PlantExtract' -- neither exists.
_CANON_LABELS = {
    "anatomicalentity":  "AnatomicalEntity",
    "biologicalprocess": "BiologicalProcess",
    "cellularcomponent": "CellularComponent",
    "chemicalentity":    "ChemicalEntity",
    "disease":           "Disease",
    "gene":              "Gene",
    "mirna":             "Mirna",
    "molecularfunction": "MolecularFunction",
    "mutation":          "Mutation",
    "pathway":           "Pathway",
    "phenotype":         "Phenotype",
    "plantspecies":      "PlantSpecies",
    "pmid":              "PMID",
    "protein":           "Protein",
    "species":           "Species",
    "tissue":            "Tissue",
}
_ALLOWED_LABELS = set(_CANON_LABELS.values())


def canon_label(s: str) -> str:
    key = re.sub(r"[^A-Za-z0-9]", "", str(s)).lower()
    return _CANON_LABELS.get(key, s)


def safe_label(lbl: str) -> str:
    """Guard against Cypher label injection -- labels cannot be parameterised."""
    if lbl not in _ALLOWED_LABELS:
        raise ValueError(f"Refusing unknown label: {lbl}")
    return lbl


# Signed / causal relations are 3-part (gene_promotes_biologicalprocess).
# A type-pair alone can only build the 2-part base form, so index the signed
# variants here and emit them explicitly during triple construction.
SIGNED_VARIANTS: Dict[Tuple[str, str], List[str]] = defaultdict(list)
BASE_RELATIONS: set = set()

for _rel in VALID_RELATIONS:
    _parts = _rel.split("_")
    if len(_parts) == 2:
        BASE_RELATIONS.add(_rel)
    elif len(_parts) == 3:
        _h, _mid, _t = _parts
        SIGNED_VARIANTS[(_h, _t)].append(_rel)


OPPOSITE_SIGN = {
    "promotes":                 "inhibits",
    "inhibits":                 "promotes",
    "positivelyassociatedwith": "negativelyassociatedwith",
    "negativelyassociatedwith": "positivelyassociatedwith",
}


def rel_in_kg(tested_rel: str, kg_rel_types) -> bool:
    """base relation (2-part) -> ANY edge means 'connected'.
       signed relation (3-part) -> the KG must hold THAT SIGN, not just any edge."""
    kg_low = {str(t).lower() for t in kg_rel_types}
    if len(str(tested_rel).split("_")) == 3:
        return str(tested_rel).lower() in kg_low
    return len(kg_low) > 0


def sign_conflict(tested_rel: str, kg_rel_types) -> bool:
    """Model asserts one sign; the KG holds the OPPOSITE one and not this one.
       Strictly stronger than in_KG=False -- this is a contradiction, not a gap."""
    p = str(tested_rel).split("_")
    if len(p) != 3 or p[1].lower() not in OPPOSITE_SIGN:
        return False
    kg_low = {str(t).lower() for t in kg_rel_types}
    opp = f"{p[0]}_{OPPOSITE_SIGN[p[1].lower()]}_{p[2]}".lower()
    return (opp in kg_low) and (str(tested_rel).lower() not in kg_low)


# =============================================================================
# NEO4J PROPERTY PARSERS
# =============================================================================

def as_list(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def parse_sources(source_prop) -> List[str]:
    """'Crossbar::PrimeKG::TARKG' -> 3 independent databases."""
    dbs = set()
    for s in as_list(source_prop):
        for part in str(s).split("::"):
            if part.strip():
                dbs.add(part.strip())
    return sorted(dbs)


def kg_flags(kg_type_prop) -> Dict[str, Any]:
    """kg_type carries 'Aging' and/or 'Generalised' -- Aging is a direct relevance signal."""
    vals = {str(x).strip().lower() for x in as_list(kg_type_prop)}
    return {
        "has_aging": "aging" in vals,
        "has_generalised": ("generalised" in vals or "generalized" in vals),
        "raw": as_list(kg_type_prop),
    }


_ORTHO_RE = re.compile(r"([^\(]+)\(([^)]+)\)\s*\[([^\]]+)\]")


def parse_ortholog_info(s) -> List[Dict[str, str]]:
    """'tep-1 (Celegans) [WBGene00013969]; A2m (Mouse) [ENSMUSG...]' -> structured."""
    if not s:
        return []
    out = []
    for chunk in str(s).split(";"):
        m = _ORTHO_RE.search(chunk)
        if m:
            out.append({
                "symbol": m.group(1).strip(),
                "species": m.group(2).strip(),
                "id": m.group(3).strip(),
            })
    return out


_CLEAN_PREDICATES = {
    "associate", "positive_correlate", "negative_correlate",
    "promotes", "inhibits", "actively_involved_in",
    "positivelyassociatedwith", "negativelyassociatedwith",
    "activelyinvolvedin", "noeffect", "notassociatedwith",
}


def normalize_relation_type(rt) -> Tuple[str, str]:
    """Never drop an edge for a missing relation_type -- an edge IS evidence even when
    the mechanism is unnamed. NaN / provenance-codes -> 'associative_link'."""
    if rt is None:
        return ("associative_link", "associative")
    s = str(rt).strip()
    if s == "" or s.lower() in {"nan", "none", "null"}:
        return ("associative_link", "associative")
    low = s.lower()
    if low in _CLEAN_PREDICATES:
        return (low, "mechanistic")
    if "::" in s or re.search(r"[A-Za-z]+:[A-Za-z]+", s):    # e.g. GNBR::J::Gene:Disease
        return ("associative_link", "associative")
    return (low, "mechanistic")


def annotate_edge_meta(meta: dict) -> dict:
    label, tier = normalize_relation_type(meta.get("relation_type"))
    meta["rel_clean"], meta["rel_tier"] = label, tier
    return meta


def edge_strength(edge: dict) -> float:
    """Transparent heuristic: n_independent_sources x aging-boost."""
    return round(len(edge["sources"]) * (2.5 if edge["kg"]["has_aging"] else 1.0), 2)


def split_edges_by_sign(rel: str, edges: List[dict]) -> Tuple[List[dict], List[dict]]:
    """edge_by_pair is keyed on the ENTITY PAIR, so it holds every edge between the two
    nodes -- both signs. Provenance for a SIGNED row must come only from the edge that
    actually carries that sign; the opposite-sign edge is counter-evidence, not support.
    For a BASE (2-part) row the question is just 'are they connected?', so all edges count."""
    if len(str(rel).split("_")) != 3:
        return list(edges), []
    want = str(rel).lower()
    matching = [e for e in edges if str(e.get("type", "")).lower() == want]
    other = [e for e in edges if str(e.get("type", "")).lower() != want]
    return matching, other


# =============================================================================
# GEMINI · key rotation + fence-safe JSON
# =============================================================================

def strip_code_fences(s: str) -> str:
    s = (s or "").strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", s, flags=re.IGNORECASE)
    return m.group(1).strip() if m else s


def try_parse_json(s: str) -> Optional[Any]:
    if not s:
        return None
    s1 = strip_code_fences(s).strip()
    if not (s1.startswith("{") or s1.startswith("[")):
        return None
    try:
        return json.loads(s1)
    except Exception:
        return None


def call_gemini_json(
    system_prompt: str,
    payload_text: str,
    key_provider,
    n_keys: int,
    model_name: str,
    temperature: float = 0.0,
) -> Dict[str, Any]:
    """Temp-0 Gemini call with round-robin key rotation and fence-safe JSON parse.

    key_provider: a zero-arg callable returning the next API key.
    Returns the parsed dict, or {"_error"/"_parse_error": ...} -- never raises.
    """
    last_err, raw = None, ""
    for _ in range(max(1, n_keys)):
        key = key_provider()
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel(
                model_name,
                generation_config={
                    "temperature": temperature,
                    "response_mime_type": "application/json",
                },
            )
            resp = model.generate_content([system_prompt, payload_text])
            raw = (resp.text or "").strip()
            parsed = try_parse_json(raw)
            if parsed is None:
                return {"_parse_error": "model did not return JSON", "raw_text": raw[:2000]}
            return parsed
        except json.JSONDecodeError as e:
            return {"_parse_error": str(e), "raw_text": raw[:2000]}
        except Exception as e:
            last_err = e
            logger.warning("gemini key ...%s failed (%s); cycling", key[-4:], type(e).__name__)
            time.sleep(0.5)
            continue
    return {"_error": str(last_err)}


# =============================================================================
# LOCAL LLM (MedGemma / any OpenAI-compatible server, e.g. SGLang) -- an
# alternative to Gemini, selected at runtime via CONFIG.GEMINI.USE.
# =============================================================================

_OPENAI_CLIENTS: Dict[str, "OpenAI"] = {}


def _get_openai_client(base_url: str) -> "OpenAI":
    if base_url not in _OPENAI_CLIENTS:
        _OPENAI_CLIENTS[base_url] = OpenAI(base_url=base_url, api_key="EMPTY")
    return _OPENAI_CLIENTS[base_url]


def call_medgemma_json(
    system_prompt: str,
    payload_text: str,
    base_url: str,
    model_name: str,
    temperature: float = 0.0,
    schema: Optional[type] = None,
    max_tokens: int = 3072,
    retries: int = 3,
) -> Dict[str, Any]:
    """Same call contract as call_gemini_json: returns the parsed dict, or
    {"_error"/"_parse_error": ...} -- never raises. `schema` (a pydantic model)
    enables SGLang/vLLM-style constrained JSON decoding when supported."""
    client = _get_openai_client(base_url)
    kwargs = dict(
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": payload_text},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    if schema is not None:
        kwargs["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": schema.__name__, "schema": schema.model_json_schema()},
        }

    last_err, raw = None, ""
    for _ in range(max(1, retries)):
        try:
            resp = client.chat.completions.create(**kwargs)
            raw = strip_code_fences(resp.choices[0].message.content or "")
            # NOT try_parse_json here -- it swallows every exception internally
            # (returns None on any failure), which throws away exactly the
            # json.JSONDecodeError detail needed to tell "truncated mid-object"
            # (generation hit max_tokens before the JSON closed) apart from
            # "didn't attempt JSON at all". Calling json.loads directly keeps
            # that error live for the except clause below.
            if not (raw.startswith("{") or raw.startswith("[")):
                return {"_parse_error": "model did not return JSON", "raw_text": raw[:2000]}
            parsed = json.loads(raw)
            return parsed
        except openai.BadRequestError as e:
            # malformed request (bad schema, model rejects a param) -- retrying won't help
            return {"_error": f"400: {str(e)[:300]}"}
        except json.JSONDecodeError as e:
            # Most common cause: max_tokens cut generation off mid-object, so the
            # JSON is well-formed up to the cutoff but never closes -- that shows
            # at the TAIL, not the head, so log the end of the string plus the
            # total length (a suspiciously round number near the max_tokens cap
            # is the tell).
            return {"_parse_error": f"JSON decode failed: {e}",
                   "raw_text": raw[-3000:], "raw_text_len": len(raw)}
        except Exception as e:
            last_err = e
            logger.warning("medgemma call failed (%s); retrying", type(e).__name__)
            time.sleep(1.0)
            continue
    return {"_error": str(last_err)}


def call_llm_json(
    provider: str,
    system_prompt: str,
    payload_text: str,
    key_provider,
    n_keys: int,
    gemini_model: str,
    medgemma_base_url: str,
    medgemma_model: str,
    temperature: float = 0.0,
    schema: Optional[type] = None,
    max_tokens: int = 3072,
) -> Dict[str, Any]:
    """Dispatch to whichever LLM backend CONFIG.GEMINI.USE selects. Callers pass
    both providers' settings; only the active one is actually used. `max_tokens`
    only affects the MedGemma path -- Gemini has no output cap set here."""
    if str(provider).strip().lower() == "medgemma":
        return call_medgemma_json(system_prompt, payload_text, medgemma_base_url,
                                  medgemma_model, temperature=temperature, schema=schema,
                                  max_tokens=max_tokens)
    return call_gemini_json(system_prompt, payload_text, key_provider, n_keys,
                            gemini_model, temperature=temperature)


_ID_RE = re.compile(r'\bE\d{3,4}\b')   # E### / E#### ; won't match E2F1 or vitamin E


def eids_to_count(text: str, noun: str = "supporting triple") -> str:
    """Reader-facing safety net: turn a pure-eid parenthetical like '(E009, E014)'
    into '(2 supporting triples)'. Leaves mixed/normal text alone. Applied to every
    free-text field before it reaches the caller, regardless of which LLM backend
    is in use -- prompts say 'never mention eids in prose', but nothing guarantees
    a model actually obeys that."""
    if not text:
        return text
    def repl(m):
        inner = m.group(1)
        ids = _ID_RE.findall(inner)
        if not ids:
            return m.group(0)
        residue = re.sub(r'[\s,;/&]|and', '', _ID_RE.sub('', inner))
        if residue:
            return m.group(0)
        n = len(ids)
        return f"({n} {noun}{'' if n == 1 else 's'})"
    text = re.sub(r'\(([^()]*)\)', repl, text)
    text = _ID_RE.sub('', text)
    text = re.sub(r'\s{2,}', ' ', text)
    text = re.sub(r'\s+([,.;:])', r'\1', text)
    return text.strip()


# =============================================================================
# PROMPT · entity filter (stage 1.2)
# =============================================================================

ENTITY_FILTER_PROMPT = """You are cleaning a list of biological entities from a fuzzy knowledge-graph (Lucene) search. Remove only clear NOISE; keep everything biologically relevant to the user's hypothesis — including entities the user did not name but that are mechanistically connected.

STEP 1 — ANALYZE THE HYPOTHESIS FIRST:
Before filtering, determine what the hypothesis is fundamentally about and which entity types matter:
- Identify the core subject(s): is it about gene(s), chemical(s)/drug(s), a pathway, a disease, etc.?
- Strictly analyse which entity Types are RELEVANT to answering it. Keep entities of those types (plus their mechanistic partners). Drop entity types that don't serve the hypothesis.
- Strictly keep most relevant entities, to the hypothesis. We need to find links in KG based to those entities edges.
  Example: if the hypothesis is about a gene or a chemical, keep genes and chemicals (and their targets/regulators/effectors), and DROP phenotypes, anatomy, or other node types that aren't mechanistically needed — unless the hypothesis explicitly concerns them.

STEP 2 — APPLY KEEP / DROP:
KEEP (default when unsure):
- Every entity the user named, in its correct biological sense.
- Unnamed entities mechanistically tied to the hypothesis: targets, regulators, downstream effectors, pathway members, interactors of the named entities.
  (e.g. for a capsaicin hypothesis, keep capsaicin-responsive genes, its molecular targets, and downstream signaling.)

DROP (clear noise only):
- Wrong-type string collisions — matched the letters but biologically unrelated to how the concept is used here.
- Exact/near-exact duplicates — keep the single best, drop the rest.
- Irrelevant node types — entity types that don't serve the hypothesis (per Step 1), e.g. phenotypes for a pure gene/chemical mechanism question.
- Candidates with no plausible biological relationship to the hypothesis.

VOLUME RULE:
- If candidates are many (>20): keep only the highly relevant, drop the rest.
- If candidates are few: keep all plausibly relevant ones.
- If every candidate for a user-named concept would be dropped, keep the single best one anyway.

Return ONLY valid JSON, no markdown:
{
  "kept": [
    {"id": "<kg id>", "name": "<name>", "entityType": "<type>",
     "relevance": "named" | "mechanistically_related",
     "reason": "<short>"}
  ],
  "dropped": [
    {"id": "<kg id>", "name": "<name>", "entityType": "<type>",
     "reason": "wrong_type_collision" | "duplicate" | "irrelevant_node_type" | "no_biological_relation"}
  ]
}

RULES:
- Do NOT invent ids. Use only ids present in the candidates.

USER HYPOTHESIS:
{hypothesis}

CANDIDATES (grouped by search term):
{candidates_json}
"""


def build_entity_filter_prompt(hypothesis: str, candidates_json: str) -> str:
    return (ENTITY_FILTER_PROMPT
            .replace("{hypothesis}", hypothesis)
            .replace("{candidates_json}", candidates_json))


def enforce_keep_floor(parsed: dict, union_entities_raw: List[dict], floor: float = 0.5) -> set:
    
    total = len(union_entities_raw)
    need = int(np.ceil(total * floor))
    kept_ids = {str(k.get("id")) for k in parsed.get("kept", [])}
    if len(kept_ids) >= need:
        return kept_ids
    score_by_id = {str(e["id"]): (e.get("lucene_score") or 0.0) for e in union_entities_raw}
    for d in sorted(parsed.get("dropped", []),
                    key=lambda d: score_by_id.get(str(d.get("id")), 0.0),
                    reverse=True):
        if len(kept_ids) >= need:
            break
        kept_ids.add(str(d.get("id")))
    return kept_ids


# =============================================================================
# PROMPTS · the four evidence-view agents + judge (stage 5)
# =============================================================================


 
_COMMON = (
    "You are an EvoAge specialist evaluating a hypothesis ONLY from supplied KG evidence.\n\n"
    "Evidence types:\n"
    "- scored_in_KG: curated; strongest support\n"
    "- scored_prediction_specific: plausible prediction with specific KG support\n"
    "- prediction_hub_only: semi plausible, hub-driven prediction\n"
    "- prediction_contradicts_KG_sign: directional conflict\n"
    "- prediction_no_graph_support: least supported prediction\n\n"
    "Rules:\n"
    "1. Use no external knowledge or invented biology.\n"
    "2. Preserve triple direction and exact relation meaning.\n"
    "3. Association/annotation/path != causation, regulation, binding or mechanism.\n"
    "4. Prediction != established evidence -- a coherent, same-direction "
    "prediction is legitimate SUPPORT (see stance/verdict guidance below), but "
    "it is still a prediction, not a curated fact; keep `status` honest.\n"
    "5. Missing evidence != contradiction -- absence of an edge/prediction is a "
    "gap, not a sign that the hypothesis is wrong.\n"
    "6. Do not transfer evidence across species or contexts without explicit support.\n"
    "7. Duplicate edges count once unless provenance is independent.\n"
    "8. Judge relevance and quality, not evidence count.\n"
    "9. Cite <=5 IDs per claim, only in JSON `eids`; never put IDs in prose.\n"
    "10. `contradicts` requires explicit opposing evidence.\n"
    "11. If evidence is unavailable, say `not established`.\n"
    "12. Return valid JSON only.\n"
    "13. Evidence below is grouped into LINKS -- one group per entity-pair the "
    "hypothesis actually connects, ordered the way the hypothesis presents them. "
    "Read one LINK at a time, using only that group's rows. For every LINK, fill "
    "in `link_findings` with how many rows it has and a 1-1.5 line, evidence-"
    "grounded conclusion -- do this BEFORE forming your overall `stance`, and keep "
    "`stance` consistent with what the links actually showed.\n"
    "14. For every LINK, also state the DIRECTION the evidence points relative "
    "to the hypothesis (same_direction | opposing | none), so directional "
    "coherence across links can be assessed downstream.\n"
    "15. Every row is tagged `[score_pctl:pXX-pYY]` -- where that row's raw "
    "model score falls against the distribution of ALL ground-truth triples in "
    "the ENTIRE graph (not this hypothesis, not this relation). It answers "
    "'how strong is this score, really' independent of accept/reject. Use it "
    "ONLY to grade the strength of a PREDICTED row (rule 4) -- a prediction at "
    "p95+ is a materially stronger, more specific signal than one at p25-p50, "
    "which is close to a coin flip against the whole graph and should read as "
    "weak/generic support even if it is directionally correct. It does not "
    "change `evidence_level` or upgrade a prediction to established.\n"
)

MECH_PROMPT = _COMMON + """
ROLE: Molecular Mechanism Expert
Determine whether the evidence supports the hypothesis's causal mechanism.

Tasks:
- Split the hypothesis into essential causal steps.
- Reconstruct only paths present in the evidence.
- Separate curated, predicted and missing steps.
- Check direction, relation meaning and context.
- Do not fill missing steps with plausible biology.
- A path containing a missing or predicted-only essential edge is not an
  established mechanism.

Return:
{
  "link_findings":[
    {"link":"<EntityA <-> EntityB>","n_evidence":<int>,"conclusion":"<1-1.5 line finding>","eids":["E001"]}
  ],
  "stance":"supports|partial_support|mixed|contradicts|insufficient",
  "claims":[
    {"claim":"<mechanistic step>","status":"established|predicted|missing|conflicting","eids":["E001"]}
  ],
  "mechanism":"<short evidence-bounded path>",
  "critical_gap":"<weakest essential causal step>"
}
"""

CONS_PROMPT = _COMMON + """
ROLE: Evolutionary Conservation Expert

Determine whether the proposed relationship or mechanism is conserved across
the species represented in the evidence.

Tasks:
- Identify the species supporting each hypothesis step.
- Separate gene orthology, functional conservation, pathway conservation and
  phenotype conservation.
- Conserved genes alone do not establish a conserved mechanism.
- Require explicit orthology or cross-species evidence.
- If species or mapping information is absent, report not assessable.
- Do not infer human relevance from model-organism evidence.

Return:
{
  "link_findings":[
    {"link":"<EntityA <-> EntityB>","n_evidence":<int>,"conclusion":"<1-1.5 line finding>","eids":["E001"]}
  ],
  "stance":"supports|partial_support|mixed|contradicts|insufficient",
  "claims":[
    {"claim":"<conservation finding>","species":["<species>"],"status":"conserved|partial|species_specific|not_assessable|conflicting","eids":["E001"]}
  ],
  "conservation_summary":"<short conclusion>",
  "critical_gap":"<missing cross-species evidence>"
}
"""

INTERACTION_PROMPT = _COMMON + """
ROLE: Molecular Interaction Expert

Audit the exact relationships connecting the hypothesis entities.

Classify each relevant relationship as one of:
direct_physical | direct_regulatory | functional_association | annotation |
indirect_path | predicted | not_established

Tasks:
- Check subject, predicate, object and direction.
- Do not interpret a "binding" function node as direct compound-protein binding.
- Do not convert shared processes or intermediates into an interaction.
- Distinguish activation, inhibition, binding and generic association.
- Identify the exact interaction missing from the hypothesis chain.

Return:
{
  "link_findings":[
    {"link":"<EntityA <-> EntityB>","n_evidence":<int>,"conclusion":"<1-1.5 line finding>","eids":["E001"]}
  ],
  "stance":"supports|partial_support|mixed|contradicts|insufficient",
  "interactions":[
    {"claim":"<entity A-entity B relationship>","interaction_class":"<class>","status":"established|predicted|missing|conflicting","eids":["E001"]}
  ],
  "interaction_summary":"<short conclusion>",
  "critical_gap":"<missing or overstated interaction>"
}
"""

CRITIC_PROMPT = _COMMON + """
ROLE: Skeptical Evidence Critic (calibrated, not adversarial)

Identify ONLY problems that genuinely prevent the hypothesis from being
supported. Do not manufacture objections. If the evidence reasonably backs the
hypothesis, say so plainly -- a clean hypothesis should produce few or no
objections, and that is a valid outcome.

Raise an objection ONLY when it materially weakens the claim:
- an essential causal link has NO evidence at all (not merely predicted);
- evidence OPPOSES the hypothesis in sign or direction;
- a specific mechanistic claim (direct binding, direct regulation) is asserted
  where the evidence shows only association or an indirect path;
- a clear species/context mismatch on an essential link.

Do NOT object to, and do NOT treat as flaws:
- predicted or hub-driven evidence that points the SAME direction as the
  hypothesis -- prediction is acceptable support here, not a defect;
- missing evidence on a peripheral (non-essential) link;
- coherent convergent evidence just because it is not curated;
- normal gaps that would only be closed by further experiments.

Do not: explain the mechanism; add alternative biology; invent objections;
treat missing evidence as contradiction; propose detailed experiments.

`maximum_defensible_verdict` is the HIGHEST verdict the evidence can justify.
Be generous where the evidence is directionally coherent:
- Set it to not_supported ONLY if explicit opposing/sign-conflict evidence
  exists on an essential link.
- Set it to insufficient_evidence ONLY when an ESSENTIAL link is entirely
  absent (no edge, no prediction) -- not when it is merely predicted.
- Set it to partially_supported when essential links point the right way but at
  least one rests on predicted-only/indirect support, or a peripheral step is
  missing.
- Set it to supported when every essential link points the same direction as
  the hypothesis with no opposing evidence, EVEN IF that support is largely
  predicted or hub-only. Coherent direction is enough to defend `supported`.

Return:
{
  "link_findings":[
    {"link":"<EntityA <-> EntityB>","n_evidence":<int>,"direction":"same_direction|opposing|none","conclusion":"<1-1.5 line finding>","eids":["E001"]}
],
  "stance":"supports|partial_support|mixed|contradicts|insufficient",
  "objections":[
    {"claim":"<precise evidence problem>","severity":"critical|major|minor","eids":["E001"]}
  ],
  "unsupported_claims":["<claim not established by supplied evidence, or empty>"],
  "explicit_conflicts":["<conflict, or none>"],
  "minimum_missing_evidence":"<single most important missing relationship, or none>",
  "maximum_defensible_verdict":"supported|partially_supported|insufficient_evidence|not_supported"
}
"""

JUDGE_PROMPT = """You are the Chief Scientific Reviewer for EvoAge. Your default posture is
skeptical: a hypothesis earns a verdict, it is not granted one for being coherent.

Four independent experts have each scanned the SAME evidence, one LINK
(entity-pair) at a time, in the order the hypothesis presents them:
1. Molecular Mechanism
2. Evolutionary Conservation
3. Molecular Interaction
4. Skeptical Evidence Critic

Each expert's `link_findings` gives, per link: how many evidence rows exist,
the DIRECTION the evidence points relative to the hypothesis
(same_direction | opposing | none), and a short evidence-grounded conclusion.
Your job is to walk the SAME links, cross-check the four experts per link, and
synthesize ONE final verdict -- not average their stances.

## What decides the verdict vs. what you may reason about
- The VERDICT is decided by the supplied evidence ONLY. You may not create,
  assume, or repair a link the evidence does not contain.
- You MAY use your own biological knowledge to INTERPRET what the evidence
  shows -- e.g. to recognize that "response to heat", "protein folding" and
  "response to unfolded protein" are facets of one proteostasis program, and so
  point the same direction. Interpretation may clarify what a link means; it may
  NEVER substitute for a missing link, and it may NEVER raise a verdict on its
  own. If removing your outside knowledge would lower the verdict, the verdict
  is too high.

## Evidence tiers -- read these off `evidence_level`, do not guess
- CURATED = an essential link is backed by an in-KG edge (evidence_level
  `scored_in_KG` or `in_KG_unscored`): a real, source-attributed relationship.
- PREDICTED = the link exists only as a model prediction (evidence_level
  `scored_prediction_specific`, `prediction_hub_only`, or
  `prediction_no_graph_support`): the model's guess, not a recorded fact.
A directionally consistent PREDICTED link is weak, suggestive support. It is
NOT equivalent to a curated edge, and no amount of predicted-only agreement
across links upgrades it to curated-strength.

## The specificity test (apply BEFORE choosing a verdict)
For the central claim, ask: "If I replaced the named compound/gene with an
arbitrary, unrelated one of the same entity type, would this same evidence
pattern still appear?" The model predicts generic (chemical -> process) edges
for many chemicals; a directionally-correct PREDICTED edge that any random
chemical would also receive carries almost no evidential weight for THIS
compound. If the support for an essential link is prediction-only and of a kind
the model would plausibly emit for an arbitrary entity, treat that link as
effectively unsupported for verdict purposes, and say so in `caveats_and_gaps`.

Each row carries `[score_pctl:pXX-pYY]` -- where its raw score sits against
EVERY ground-truth triple in the whole graph, not just this hypothesis. Use it
as a quantitative anchor for the test above, on PREDICTED links only (it says
nothing about CURATED links, which are already established regardless of
score):
- p90+ (especially p95/p99): the model is genuinely distinguishing this
  specific pair, not emitting a generic edge -- treat this as passing the
  specificity test, and it can support `strong support` even without curated backing
  on that link.
- p75-p90: some signal above the model's generic default, but not clearly
  distinguishing -- this PASSES the specificity test only partially; it can
  carry an essential link at most to `partial_support`, never to `strong support` on
  its own, and say so in `caveats_and_gaps` if it is doing the load-bearing
  work for that link.
- p50-p75: unremarkable against the whole graph -- treat as the model's
  default behaviour for this entity type, not distinguishing evidence.
- below p50: the score is weaker than an average ground-truth triple --
  this essentially FAILS the specificity test; name it explicitly in
  `caveats_and_gaps` and do not let it carry an essential link past
  `weak_support`.
This never upgrades a PREDICTED link to CURATED, and never substitutes for a
missing or opposing essential link -- it only calibrates how much weight a
prediction that IS present deserves.

## Directional coherence
Lay out every essential link with its DIRECTION across the four experts. A link
is "essential" if the hypothesis's central claim cannot hold without it (the
link between the two central entities, or the link to the outcome/phenotype).
Coherent same-direction evidence is necessary for support but NOT sufficient on
its own -- coherence tells you the links do not contradict each other; it does
not tell you the evidence is strong. An essential link with ZERO evidence, or
with OPPOSING (sign/direction) evidence, breaks coherence and caps the verdict
regardless of the other links.

## Verdict levels (use exactly one)

strong_support
Every essential link points the same direction as the hypothesis, no essential
link is opposing or at zero evidence, AND at least one essential link -- the
central mechanistic link between the two core entities -- is CURATED (in-KG).
Directional coherence built entirely on PREDICTED links can NEVER reach
strong_support, however clean it looks.

support
Essential links point the same direction and the central claim has some curated
grounding, but at least one essential link is predicted-only, missing, or
disputed between experts. Also the ceiling for a hypothesis whose essential
links are directionally coherent but where curated support is partial. Name the
link that needs confirmatory experiments.

partial_support
Essential links are mostly same-direction but MORE THAN ONE is predicted-only,
missing, or disputed, and curated grounding is sparse. The story is plausible
but rests largely on prediction.

weak_support
Directionally consistent but THIN and entirely or almost entirely PREDICTED:
the central links are prediction-only (especially if they would survive the
specificity test above being swapped for an arbitrary entity), with little or no
curated evidence anywhere on the essential path. A hypothesis that is coherent
but supported only by generic, non-specific predictions belongs HERE, not in
support -- this is the correct home for "the model likes this shape for any
compound."

no_support
At least one essential link has ZERO evidence across every expert, OR an
essential link's evidence OPPOSES the hypothesis (sign/direction conflict) with
nothing offsetting it.

## Decision procedure (follow in order)
1. List essential links + direction + tier (CURATED/PREDICTED) + specificity.
2. Any essential link opposing or at zero evidence? -> no_support. Stop.
3. Is the central mechanistic link CURATED? If NO -> the ceiling is
   weak_support (if essential links are prediction-only/non-specific) or
   support (only if there is meaningful curated evidence elsewhere on the path);
   strong_support is unavailable. 
4. If the central link IS curated and all essential links are same-direction
   with no zero/opposing link -> strong_support.
5. Otherwise choose support / partial_support by how much of the essential path
   is curated vs predicted.

## Writing the answer
Graduate-level scientific discussion. The 'answer' should:
- summarize the overall EvoAge evidence in 2-3 lines
- state whether the essential links converge on one biological direction, and
  name that program if they do
- state plainly, for the central link, whether the support is CURATED or
  PREDICTED-ONLY, and whether it would survive the specificity test
- justify the verdict by naming which link(s) drove it, their direction, and
  their tier
- label any use of your own biological knowledge as interpretation, not evidence
- avoid inventing unsupported links or filling missing edges

`supporting_evidence` and `caveats_and_gaps` are NOT optional restatements of
`answer` -- they are what the caller actually displays to the reader as
discrete bullet points, separately from `answer`. Every verdict, including
no_support and weak_support, has at least one of each:
- `supporting_evidence`: 1-3 points, each grounded in a specific link/eid --
  for a low verdict this is what little there IS (e.g. "the predicted link
  points the right direction, though only as a generic prediction").
- `caveats_and_gaps`: 1-3 entries -- the essential link(s) that are missing,
  predicted-only, or fail the specificity test; NEVER leave this empty, an
  empty list here is only correct if literally nothing is uncertain.
Fill these BEFORE `direction_check`/`link_summary` -- those two are your own
working notes for the analysis above, not part of what the reader sees; if
you are running low on room, it is `direction_check`/`link_summary` that may
be abbreviated, never `supporting_evidence` or `caveats_and_gaps`.

Return ONLY valid JSON:
{
  "verdict":"strong_support|support|partial_support|weak_support|no_support",
  "answer":"<approximately 200-250 word scientific assessment>",
  "supporting_evidence":[
    {"point":"<biological conclusion>","eids":["E001"]}
  ],
  "caveats_and_gaps":["<remaining uncertainty -- required, see above>"],
  "expert_disagreements":["<important disagreement between experts, if any>"],
  "direction_check":{
    "essential_links":["<EntityA <-> EntityB>"],
    "all_same_direction":<true|false>,
    "central_link_is_curated":<true|false>,
    "central_link_survives_specificity_test":<true|false>,
    "biological_program":"<the unifying program if links converge, else null>"
  },
  "link_summary":[
    {"link":"<EntityA <-> EntityB>","direction":"same_direction|opposing|none","tier":"curated|predicted","assessment":"<1 line: what the link's evidence shows>","eids":["E001"]}
  ]
}
"""


# =============================================================================
# SCHEMAS · guided JSON decoding (used by the local/MedGemma path only -- Gemini
# ignores these and relies on prompt instructions + response_mime_type, exactly
# as before)
# =============================================================================

class LinkFinding(BaseModel):
    link: str
    n_evidence: int = 0
    direction: str = ""
    conclusion: str = ""
    eids: List[str] = []

class ClaimItem(BaseModel):
    claim: str
    status: str
    eids: List[str] = []

class ConservationClaim(BaseModel):
    claim: str
    species: List[str] = []
    status: str
    eids: List[str] = []

class InteractionItem(BaseModel):
    claim: str
    interaction_class: str
    status: str
    eids: List[str] = []

class ObjectionItem(BaseModel):
    claim: str
    severity: str
    eids: List[str] = []

class MechOut(BaseModel):
    link_findings: List[LinkFinding] = []
    stance: str
    claims: List[ClaimItem] = []
    mechanism: str = ""
    critical_gap: str = ""

class ConsOut(BaseModel):
    link_findings: List[LinkFinding] = []
    stance: str
    claims: List[ConservationClaim] = []
    conservation_summary: str = ""
    critical_gap: str = ""

class InteractionOut(BaseModel):
    link_findings: List[LinkFinding] = []
    stance: str
    interactions: List[InteractionItem] = []
    interaction_summary: str = ""
    critical_gap: str = ""

class CriticOut(BaseModel):
    link_findings: List[LinkFinding] = []
    stance: str
    objections: List[ObjectionItem] = []
    unsupported_claims: List[str] = []
    explicit_conflicts: List[str] = []
    minimum_missing_evidence: str = ""
    maximum_defensible_verdict: str = ""

class SupportingEvidenceItem(BaseModel):
    point: str
    eids: List[str] = []

class LinkSummaryItem(BaseModel):
    link: str
    direction: str = ""
    tier: str = ""
    assessment: str = ""
    eids: List[str] = []

class DirectionCheck(BaseModel):
    essential_links: List[str] = []
    all_same_direction: bool = False
    central_link_is_curated: bool = False
    central_link_survives_specificity_test: bool = False
    biological_program: Optional[str] = None

class JudgeOut(BaseModel):
    verdict: str
    answer: str
    supporting_evidence: List[SupportingEvidenceItem] = []
    caveats_and_gaps: List[str] = []
    expert_disagreements: List[str] = []
    direction_check: Optional[DirectionCheck] = None
    link_summary: List[LinkSummaryItem] = []


AGENT_SPECS = [
    ("mechanism",    MECH_PROMPT,        MechOut),
    ("conservation", CONS_PROMPT,        ConsOut),
    ("interaction",  INTERACTION_PROMPT, InteractionOut),
    ("critic",       CRITIC_PROMPT,      CriticOut),
]


# =============================================================================
# SAVE
# =============================================================================

def _json_default(o):
    try:
        if isinstance(o, (np.integer, np.floating)):
            return o.item()
        if isinstance(o, np.ndarray):
            return o.tolist()
    except Exception:
        pass
    if isinstance(o, set):
        return sorted(o)
    return str(o)


def save_response_obj(response_obj, folder, filename: str = "response_obj.json") -> Path:
    folder_path = Path(folder)
    folder_path.mkdir(parents=True, exist_ok=True)
    out_path = folder_path / filename
    tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(response_obj, f, ensure_ascii=False, indent=2, default=_json_default)
    os.replace(tmp_path, out_path)
    return out_path


__all__ = [
    "VALID_RELATIONS", "SIGNED_VARIANTS", "BASE_RELATIONS", "OPPOSITE_SIGN",
    "canon_label", "safe_label", "rel_in_kg", "sign_conflict",
    "as_list", "parse_sources", "kg_flags", "parse_ortholog_info",
    "normalize_relation_type", "annotate_edge_meta", "edge_strength", "split_edges_by_sign",
    "strip_code_fences", "try_parse_json", "call_gemini_json",
    "call_medgemma_json", "call_llm_json", "eids_to_count",
    "build_entity_filter_prompt", "enforce_keep_floor",
    "MECH_PROMPT", "CONS_PROMPT", "INTERACTION_PROMPT", "CRITIC_PROMPT", "JUDGE_PROMPT",
    "AGENT_SPECS",
    "LinkFinding", "ClaimItem", "ConservationClaim", "InteractionItem", "ObjectionItem",
    "MechOut", "ConsOut", "InteractionOut", "CriticOut",
    "SupportingEvidenceItem", "LinkSummaryItem", "DirectionCheck", "JudgeOut",
    "save_response_obj",
]