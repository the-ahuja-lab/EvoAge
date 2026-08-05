import logging
import os
import unicodedata
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv
from kani import AIParam, ai_function
from kani_utils.base_kanis import StreamlitKani
from requests.exceptions import HTTPError, RequestException
from typing_extensions import Annotated

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

MAX_ENTITIES = 10       # cap on extracted hypothesis terms
PER_TYPE_LIMIT = 5      # SBE hits kept per entity type per term -- sent to the backend
MAX_HYPOTHESIS_CHARS = 600

logger = logging.getLogger(__name__)


# =====================================================================
# Term normalisation -- mirrors the backend's normalize()
# Keeps agent-side and API-side handling of Greek letters in agreement.
# =====================================================================

GREEK = {
    "α": "alpha", "β": "beta", "γ": "gamma", "δ": "delta", "ε": "epsilon",
    "ζ": "zeta", "η": "eta", "θ": "theta", "ι": "iota", "κ": "kappa",
    "λ": "lambda", "μ": "mu", "ν": "nu", "ξ": "xi", "ο": "omicron",
    "π": "pi", "ρ": "rho", "σ": "sigma", "ς": "sigma", "τ": "tau",
    "υ": "upsilon", "φ": "phi", "χ": "chi", "ψ": "psi", "ω": "omega",
}
GREEK.update({k.upper(): v for k, v in list(GREEK.items())})

_DASHES = dict.fromkeys(map(ord, "\u2010\u2011\u2012\u2013\u2014\u2015\u2212"), "-")
_APOS = dict.fromkeys(map(ord, "\u2018\u2019\u02bc'"), None)


def normalize_term(term: str) -> str:
    """b-secretase normalisation: 'β-secretase' -> 'beta-secretase'."""
    term = unicodedata.normalize("NFKC", term)
    term = term.translate(_DASHES).translate(_APOS)
    return "".join(GREEK.get(ch, ch) for ch in term).strip()


def dedupe_entities_preserve_order(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Case-insensitive, Greek-normalised dedupe on `mention`. Keeps first
    occurrence's mention text and order, but UNIONS `types` across duplicates --
    if the model called BACE1 out twice with different type guesses, both are
    worth keeping rather than picking one arbitrarily."""
    seen: Dict[str, int] = {}
    out: List[Dict[str, Any]] = []
    for it in items:
        mention = str(it.get("mention", "")).strip()
        key = normalize_term(mention).lower()
        if not key:
            continue
        types = [t.strip() for t in (it.get("types") or [])
                if isinstance(t, str) and t.strip()]
        if key in seen:
            existing_types = out[seen[key]]["types"]
            for t in types:
                if t not in existing_types:
                    existing_types.append(t)
            continue
        seen[key] = len(out)
        out.append({"mention": mention, "types": types})
    return out


class HypoEvoKgAgent(StreamlitKani):
    """
    EvoAge hypothesis agent.

    Contract:
      - the LLM maps user phrasing to KG ontology names during extraction,
      - every mapped term is verified against Neo4j before the pipeline runs,
      - the mapping is SHOWN to the user (a wrong map must never be silent),
      - numeric results from the backend are rendered, never re-derived.
    """

    def __init__(self, *args, **kwargs):
        kwargs["system_prompt"] = SYSTEM_PROMPT
        super().__init__(*args, **kwargs)

        self.greeting = GREETING_HTML
        self.description = "Queries the EvoAge knowledge graph."
        self.avatar = "\U0001F9EC"
        self.user_avatar = "\U0001F464"
        self.name = "EvoAge Assistant"
        self.api_base = API_BASE_URL

        # Retrieval-coverage telemetry. Grep UNRESOLVED-TERM / PARTIAL-COVERAGE
        # across a batch of hypotheses to build the synonym-ingest backlog and
        # to report a real coverage number.
        self.resolution_log: List[Dict[str, Any]] = []

    # -----------------------------------------------------------------
    # HTTP helpers (not @ai_function -- Optional is safe here)
    # -----------------------------------------------------------------

    def api_call(self, endpoint: str, timeout: int = 600, **kwargs) -> Any:
        url = f"{self.api_base}/{endpoint}"
        logger.info(f"[GET] {url} params={kwargs}")
        response = requests.get(url, params=kwargs, timeout=timeout)
        response.raise_for_status()
        return response.json()

    def api_post(self, endpoint: str, json: Optional[dict] = None,
                 timeout: int = 120) -> Any:
        url = f"{self.api_base}/{endpoint}"
        logger.info(f"[POST] {url}")
        response = requests.post(url, json=json, timeout=timeout)
        response.raise_for_status()
        return response.json()

    # -----------------------------------------------------------------
    # Internal resolution (not @ai_function)
    # -----------------------------------------------------------------

    def _resolve(self, term: str):
        """
        Check a term against the KG. Returns (buckets, term) or ([], None).
        A 404 means "no such node" -- that is information, not an error.
        """
        try:
            resp = self.api_call("search_biological_entities", targetTerm=term)
        except HTTPError as e:
            status = e.response.status_code if e.response is not None else None
            if status != 404:
                logger.error(f"search_biological_entities HTTP {status} for '{term}'")
            resp = None
        except RequestException as e:
            logger.error(f"search_biological_entities network error '{term}': {e}")
            resp = None

        if resp:
            self.resolution_log.append({"term": term, "resolved": True})
            return resp, term

        self.resolution_log.append({"term": term, "resolved": False})
        # Grep this. Every unresolved term is a synonym gap in the KG,
        # and nothing downstream can recover it.
        logger.warning(f"UNRESOLVED-TERM '{term}'")
        return [], None

    # -----------------------------------------------------------------
    # Tools
    # -----------------------------------------------------------------

    @ai_function
    def search_biological_entities(
        self,
        targetTerm: Annotated[
            str,
            AIParam(desc="The name or id of the biological entity to search for."),
        ],
    ) -> List[dict]:
        """
        Search biological entities (Gene, Protein, Disease, ChemicalEntity,
        Phenotype, Tissue, AnatomicalEntity, BiologicalProcess, MolecularFunction,
        CellularComponent, Pathway, Mirna, Mutation, PMID, Species, PlantSpecies)
        by name or id.

        Returns up to 5 matches per entity type. Returns an EMPTY LIST if the term
        matches nothing -- an empty result is information, not an error.
        """
        buckets, _ = self._resolve(targetTerm)
        return buckets or []

    @ai_function
    def run_hypothesis_from_text(
        self,
        extracted_entities: Annotated[
            List[dict],
            AIParam(
                desc="Biological entities from the hypothesis, ALREADY MAPPED to "
                     "the names used in the EvoAge knowledge graph -- official "
                     "gene symbols (APP, BACE1), Gene Ontology term names "
                     "(amyloid-beta formation, postsynaptic density), ontology "
                     "disease names (Alzheimer disease). Each item is "
                     "{'mention': <mapped KG name>, 'types': [<1-2 EvoAge entity "
                     "types>]} -- 'types' is what KIND of thing the hypothesis means "
                     "by this mention (e.g. BACE1 discussed as an enzyme -> "
                     "['Gene','Protein']), chosen from: Gene, Protein, Disease, "
                     "ChemicalEntity, Phenotype, Tissue, AnatomicalEntity, "
                     "BiologicalProcess, MolecularFunction, CellularComponent, "
                     "Pathway, Mirna, Mutation, PMID, Species, PlantSpecies. Max 10 "
                     "items, order preserved. mention is names only -- never "
                     "ontology IDs."
            ),
        ],
        hypothesis: Annotated[
            str,
            AIParam(desc="The full original hypothesis text, verbatim. REQUIRED -- "
                         "the swarm agents reason directly against this text; an "
                         "empty hypothesis makes every agent's verdict meaningless."),
        ],
    ) -> dict:
        """
        THIS IS THE ONLY WAY to run the hypothesis pipeline. You cannot POST to
        the backend yourself.

        Verifies each mapped mention against the knowledge graph, sends the ones
        that resolve to /hypothesis/run_hypothesis_pipeline, and returns the
        backend's results plus a coverage report.

        This function does NOT extract or map entities itself -- pass them in.
        """
        try:
            mentions = dedupe_entities_preserve_order([
                e for e in (extracted_entities or [])
                if isinstance(e, dict) and isinstance(e.get("mention"), str)
                and e["mention"].strip()
            ])[:MAX_ENTITIES]

            if not mentions:
                return {"error": "No entities were extracted from the hypothesis."}

            if not hypothesis or not hypothesis.strip():
                # Belt-and-suspenders: the parameter is now required, but if the LLM
                # still calls this with an empty string, fail loudly rather than let
                # the swarm silently reason against no hypothesis text at all.
                return {"error": "hypothesis was empty. Re-call with the full "
                                 "original hypothesis text -- it is required."}

            if len(hypothesis) > MAX_HYPOTHESIS_CHARS:
                return {
                    "error": f"Hypothesis exceeds the {MAX_HYPOTHESIS_CHARS}-character "
                             f"limit ({len(hypothesis)} chars). Please shorten it."
                }

            # --- verify every mapped mention against the KG
            resolved_mentions: List[Dict[str, Any]] = []
            coverage: List[Dict[str, Any]] = []

            for m in mentions:
                buckets, matched = self._resolve(m["mention"])
                coverage.append({
                    "term": m["mention"],
                    "resolved": bool(buckets),
                    "entity_types": [b.get("entityType") for b in buckets],
                })
                if matched:
                    resolved_mentions.append({"mention": matched, "types": m["types"]})

            if not resolved_mentions:
                return {
                    "error": "None of the extracted entities could be matched to "
                             "nodes in EvoAge. The mapping to knowledge-graph "
                             "terminology may have been incorrect.",
                    "coverage": coverage,
                }

            n_res, n_tot = len(resolved_mentions), len(mentions)
            if n_res < n_tot:
                unresolved = [c["term"] for c in coverage if not c["resolved"]]
                logger.warning(
                    f"PARTIAL-COVERAGE {n_res}/{n_tot} resolved; unresolved={unresolved}"
                )

            # --- backend contract: {hypothesis, entities_input}
            payload = {
                "hypothesis": hypothesis,
                "entities_input": resolved_mentions,
                "per_type_limit": PER_TYPE_LIMIT,
            }
            resp = self.api_post(
                "hypothesis/run_hypothesis_pipeline", json=payload, timeout=1200
            )

            terms_sent = [m["mention"] for m in resolved_mentions]
            out = {
                "summary": self._summarise(resp, coverage),
                "formatted_answer": resp.get("formatted_answer", ""),
                "verdict": resp.get("verdict"),
                "statistical_overview": resp.get("statistical_overview", {}),
                "run_id": resp.get("run_id"),
                "terms_sent": terms_sent,
                "coverage": coverage,
                "coverage_note": (
                    None if n_res == n_tot else
                    f"{n_tot - n_res} of {n_tot} mapped entities did not match any "
                    f"EvoAge node and were excluded. Results reflect only the "
                    f"{n_res} that resolved."
                ),
            }
            if hypothesis:
                out["hypothesis"] = hypothesis
            return out

        except HTTPError as e:
            status = e.response.status_code if e.response is not None else "?"
            logger.error(f"run_hypothesis_from_text HTTP {status}: {e}")
            return {"error": f"The hypothesis backend returned HTTP {status}."}
        except RequestException as e:
            logger.error(f"run_hypothesis_from_text network error: {e}")
            return {"error": "Could not reach the hypothesis backend. Hypotheses can "
                             "take 2-3 minutes to compute -- it may have timed out."}
        except Exception as e:
            logger.exception("run_hypothesis_from_text failed")
            return {"error": f"Failed to run hypothesis pipeline: {e}"}

    # -----------------------------------------------------------------
    # Summary rendering (never re-derives backend numbers)
    # -----------------------------------------------------------------

    def _summarise(self, resp: dict, coverage: List[dict]) -> str:
        """User-facing summary. The backend's formatted_answer is already
        plain-text, eid-free, and includes the triple-count stats -- this only
        prepends a coverage note when some entities didn't resolve. Never
        rewritten or re-derived."""
        formatted = str(resp.get("formatted_answer", "")).strip()

        n_res = sum(1 for c in coverage if c["resolved"])
        n_tot = len(coverage)
        cov = (f"{n_res} of {n_tot} mapped entities resolved to EvoAge nodes.\n\n"
               if n_res < n_tot else "")

        if not formatted:
            return f"{cov}The hypothesis pipeline did not return a verdict."

        return f"{cov}{formatted}"


# =====================================================================
# System prompt
# =====================================================================

SYSTEM_PROMPT = """
You are the EvoAge Assistant, an AI chatbot for the EvoAge knowledge graph and
hypothesis testing. EvoAge contains Gene, Protein, Disease, ChemicalEntity,
Phenotype, Tissue, AnatomicalEntity, BiologicalProcess, MolecularFunction,
CellularComponent, Pathway, Mirna, Mutation, PMID, Species and PlantSpecies.

Each entity has an internal "model_id". NEVER show model_id to the user.

## Relationships in EvoAge

AnatomicalEntity: ANATOMICALENTITY_ANATOMICALENTITY, ANATOMICALENTITY_BIOLOGICALPROCESS,
ANATOMICALENTITY_CELLULARCOMPONENT, ANATOMICALENTITY_CHEMICALENTITY, ANATOMICALENTITY_GENE

BiologicalProcess: BIOLOGICALPROCESS_BIOLOGICALPROCESS, BIOLOGICALPROCESS_CELLULARCOMPONENT,
BIOLOGICALPROCESS_CHEMICALENTITY, BIOLOGICALPROCESS_GENE, BIOLOGICALPROCESS_MOLECULARFUNCTION,
BIOLOGICALPROCESS_PROTEIN

CellularComponent: CELLULARCOMPONENT_CELLULARCOMPONENT, CELLULARCOMPONENT_CHEMICALENTITY,
CELLULARCOMPONENT_GENE

ChemicalEntity: CHEMICALENTITY_BIOLOGICALPROCESS, CHEMICALENTITY_CHEMICALENTITY,
CHEMICALENTITY_DISEASE, CHEMICALENTITY_GENE, CHEMICALENTITY_MUTATION, CHEMICALENTITY_PATHWAY,
CHEMICALENTITY_PROTEIN, CHEMICALENTITY_TISSUE, CHEMICALENTITY_INHIBITS_BIOLOGICALPROCESS,
CHEMICALENTITY_PROMOTES_BIOLOGICALPROCESS,
CHEMICALENTITY_POSITIVELYASSOCIATEDWITH_BIOLOGICALPROCESS,
CHEMICALENTITY_NEGATIVELYASSOCIATEDWITH_BIOLOGICALPROCESS,
CHEMICALENTITY_NOTASSOCIATEDWITH_BIOLOGICALPROCESS, CHEMICALENTITY_NOEFFECT_BIOLOGICALPROCESS

Disease: DISEASE_ANATOMICALENTITY, DISEASE_CHEMICALENTITY, DISEASE_DISEASE, DISEASE_GENE,
DISEASE_MUTATION, DISEASE_PATHWAY, DISEASE_PHENOTYPE

Gene: GENE_ANATOMICALENTITY, GENE_BIOLOGICALPROCESS, GENE_CELLULARCOMPONENT,
GENE_CHEMICALENTITY, GENE_DISEASE, GENE_GENE, GENE_MOLECULARFUNCTION, GENE_MUTATION,
GENE_PATHWAY, GENE_PHENOTYPE, GENE_PROTEIN, GENE_TISSUE, GENE_INHIBITS_BIOLOGICALPROCESS,
GENE_PROMOTES_BIOLOGICALPROCESS, GENE_NOEFFECT_BIOLOGICALPROCESS,
GENE_POSITIVELYASSOCIATEDWITH_BIOLOGICALPROCESS,
GENE_NEGATIVELYASSOCIATEDWITH_BIOLOGICALPROCESS, GENE_NOTASSOCIATEDWITH_BIOLOGICALPROCESS

Mirna: MIRNA_GENE

MolecularFunction: MOLECULARFUNCTION_BIOLOGICALPROCESS, MOLECULARFUNCTION_CHEMICALENTITY,
MOLECULARFUNCTION_MOLECULARFUNCTION, MOLECULARFUNCTION_PROTEIN

Mutation: MUTATION_CHEMICALENTITY, MUTATION_DISEASE, MUTATION_GENE, MUTATION_MUTATION,
MUTATION_PROTEIN

Pathway: PATHWAY_GENE, PATHWAY_PATHWAY

Phenotype: PHENOTYPE_BIOLOGICALPROCESS, PHENOTYPE_CELLULARCOMPONENT, PHENOTYPE_CHEMICALENTITY,
PHENOTYPE_DISEASE, PHENOTYPE_GENE, PHENOTYPE_MOLECULARFUNCTION, PHENOTYPE_PHENOTYPE,
PHENOTYPE_PROTEIN

PlantSpecies: PLANTSPECIES_CHEMICALENTITY, PLANTSPECIES_DISEASE

PMID: PMID_CELLULARCOMPONENT, PMID_CHEMICALENTITY, PMID_DISEASE, PMID_PROTEIN, PMID_TISSUE

Protein: PROTEIN_BIOLOGICALPROCESS, PROTEIN_CELLULARCOMPONENT, PROTEIN_CHEMICALENTITY,
PROTEIN_DISEASE, PROTEIN_MOLECULARFUNCTION, PROTEIN_PATHWAY, PROTEIN_PHENOTYPE,
PROTEIN_PROTEIN, PROTEIN_TISSUE

Species: Species_AssociatedWith

## ROUTING -- decide first, then act

Read the user's message and pick exactly ONE path.

PATH A -- HYPOTHESIS. The message proposes or asserts a causal, mechanistic, or
relational biomedical claim connecting TWO OR MORE concepts -- trigger on the
SHAPE of the claim, not just a cue word. All of these are PATH A:
  "I hypothesize...", "I propose...", "I suspect...", "Could X cause Y...",
  "Is there evidence that...", "X may influence/affect/regulate/promote/inhibit
  Y through/via Z...", "X is involved in Y...", "X plays a role in Y...".
If answering the message requires relating multiple entities through a proposed
mechanism or effect, it is PATH A -- even with no cue word at all. Both sample
questions in the greeting card are PATH A.

PATH B -- LOOKUP. The user asks about ONE entity in isolation ("What is BACE1?",
"Tell me about spermine") or wants fuzzy matching against a single concept
("What diseases relate to lung?"), with no proposed relationship to anything
else. Call search_biological_entities, then offer a tail-prediction or get_entity_relationship follow-up.

When unsure between A and B: if the message names more than one entity AND
proposes how they connect, that's PATH A. Never run both paths for one message.

## Hypothesis testing (PATH A)

Call run_hypothesis_from_text. This is the ONLY way to run the pipeline -- you
cannot POST to the backend yourself.

### Step 1 -- extract, map to knowledge-graph names, AND type each mention

Pull the biological entities from the hypothesis. Then, for each one, emit the
name it is stored under in the knowledge graph -- NOT the user's casual phrasing.
EvoAge stores ontology terms, not prose. Send the MAPPED names.

Also decide, from reading the hypothesis, what KIND of thing each mention is --
its `types`, 1-2 values from: Gene, Protein, Disease, ChemicalEntity, Phenotype,
Tissue, AnatomicalEntity, BiologicalProcess, MolecularFunction, CellularComponent,
Pathway, Mirna, Mutation, PMID, Species, PlantSpecies. This is your own reading of
the hypothesis's intent, not a guess at what search will return -- e.g. BACE1
discussed as an enzyme is ['Gene','Protein']; if you aren't sure, list the 2 most
plausible types rather than just one, or leave `types` empty if truly unsure.

Mapping rules:
  - Genes / proteins -> full name, if not available then official symbol; types: ['Gene','Protein']
      "amyloid precursor protein"    ->  amyloid precursor protein or APP
      "beta-secretase enzyme"        ->  beta-secretase or BACE1
      "AMP-activated protein kinase" ->  AMP-activated protein kinase or PRKAA1
  - Biological processes -> Gene Ontology term names; types: ['BiologicalProcess']
      "amyloidogenic processing"     ->  amyloid-beta formation
      "APP cleavage"                 ->  amyloid precursor protein catabolic process
      "life-span extension"          ->  determination of adult lifespan
  - Cellular components -> Gene Ontology component names; types: ['CellularComponent']
      "synaptic compartment"         ->  synapse
      "postsynaptic regions"         ->  postsynaptic density
      "endocytic regions"            ->  endosome
  - Diseases -> ontology form, no possessive; types: ['Disease','Phenotype']
      "Alzheimer's disease"          ->  Alzheimer disease
  - Chemicals / drugs -> the standard compound name; types: ['ChemicalEntity']
      "lithocholic acid"             ->  lithocholic acid

### Worked example

Hypothesis:
  "BACE1, a key beta-secretase enzyme involved in amyloid precursor protein
   cleavage, may exhibit altered localization from postsynaptic to perisynaptic
   and endocytic regions in Alzheimer's disease, reflecting synaptic
   compartment-specific dysregulation of amyloidogenic processing."

extracted_entities:
  [{'mention': 'beta-secretase',               'types': ['Gene', 'Protein']},
   {'mention': 'amyloid precursor protein',    'types': ['Gene', 'Protein']},
   {'mention': 'Alzheimer disease',            'types': ['Disease', 'Phenotype']},
   {'mention': 'postsynaptic density',         'types': ['CellularComponent']},
   {'mention': 'endosome',                     'types': ['CellularComponent']},
   {'mention': 'amyloid-beta formation',       'types': ['BiologicalProcess']}]

Note that "BACE1" collapsed into "beta-secretase" (same entity -- keep it ONCE),
and "synaptic compartment" / "amyloidogenic processing" became their GO names.

### Rules

  - Maximum 10 entities. Preserve the order they appear in the hypothesis.
  - Case-insensitive dedupe AFTER mapping. If two spans map to the same KG name,
    keep it once (union their types if they differed).
  - mention is names only. NEVER emit ontology IDs (no GO:0001234, no MONDO:0004975).
  - NEVER extract an entity that is not present in the hypothesis text.
  - If you cannot confidently map a phrase to a KG name, pass the user's ORIGINAL
    wording unchanged rather than guessing. A term that fails to resolve is
    reported honestly; a wrong guess silently changes the user's claim.

### Step 2 -- report
show user the exact run id at the top bot in small test(non highlighted).
Directly show the user the verdict text you received (response.formatted_answer),
in its structured format, exactly as received -- do not rewrite, condense, or
paraphrase it.

At the end, show the stats: total triples analysed, how many became ground truth
(bucket_1_known_and_supported -- already curated in the graph), and how many were
novel (bucket_2_novel_predicted -- predicted by the model, not yet in the graph).
""".strip()


GREETING_HTML = """
        <style>

            html, body {
                margin: 0 !important;
                padding: 0 !important;
                overflow: hidden;
            }
            [data-testid="stHeader"] {{ display: none !important; }}
            .block-container {
                max-width: 100% !important;
                margin: 0 auto;
                padding-top: 1.5rem;
            }

            .evo-hypo-box {
                position: sticky;
                top: 0;
                background: rgba(255, 255, 255, 0.65);
                backdrop-filter: blur(14px) saturate(150%);
                -webkit-backdrop-filter: blur(14px) saturate(150%);

                border-radius: 22px;
                padding: 1.8rem 2rem;
                margin: 0rem 2rem 9rem;

                animation: fadeIn 1s ease-out;

                border: 1.4px solid rgba(190, 210, 255, 0.35);
                box-shadow:
                    0 10px 28px rgba(0, 0, 0, 0.08),
                    inset 0 0 16px rgba(180, 200, 255, 0.15);

                position: relative;
                overflow: hidden;
                display: flex;
                flex-direction: column;
                align-items: center;
            }

            .evo-hypo-box::before {
                content: "";
                position: absolute;
                inset: 0;
                border-radius: 22px;
                padding: 2px;
                background: linear-gradient(
                    120deg,
                    rgba(140,180,255,0.45),
                    rgba(255,255,255,0.15),
                    rgba(110,160,255,0.45)
                );
                mask:
                    linear-gradient(#fff 0 0) content-box,
                    linear-gradient(#fff 0 0);
                mask-composite: exclude;
                animation: borderGlow 6s linear infinite;
            }

            @keyframes borderGlow {
                0% { background-position: 0% 50%; }
                50% { background-position: 100% 50%; }
                100% { background-position: 0% 50%; }
            }

            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(-10px); }
                to { opacity: 1; transform: translateY(0); }
            }

            @keyframes dnaGlow {
                0% { filter: drop-shadow(0 0 0px rgba(93,165,255,0.4)); }
                50% { filter: drop-shadow(0 0 12px rgba(93,165,255,0.9)); }
                100% { filter: drop-shadow(0 0 0px rgba(93,165,255,0.4)); }
            }

            @keyframes emojiSpin {
                0% { transform: rotate(0deg) scale(1); }
                40% { transform: rotate(14deg) scale(1.12); }
                100% { transform: rotate(0deg) scale(1); }
            }

            .evo-hypo-title-inline {
                font-size: 2.4rem;
                font-weight: 800;
                text-align: center;
                color: #1a2b47;
                margin-bottom: 0.4rem;
                display: flex;
                justify-content: center;
                align-items: center;
                gap: 0.55rem;
            }

            .evo-dna-emoji-inline {
                font-size: 2.4rem;
                animation: dnaGlow 2.8s infinite ease-in-out;
                cursor: pointer;
                transition: 0.3s ease;
                display: inline-block;
            }

            .evo-dna-emoji-inline:hover {
                animation: emojiSpin 0.7s ease-in-out, dnaGlow 2.8s infinite ease-in-out;
            }

            .evo-hypo-subtext {
                font-size: 1rem;
                text-align: center;
                color: #3d4b5c;
                line-height: 1.45;
                margin-bottom: 1.2rem;
                max-width: 850px;
                margin-left: auto;
                margin-right: auto;
            }

            .evo-divider {
                width: 80%;
                height: 1px;
                margin: 0.4rem auto 1.2rem;
                background: linear-gradient(to right, transparent, #a0c8ff, transparent);
                opacity: 0.55;
            }

            .sample-title {
                font-size: 1.25rem;
                text-align: center;
                color: #1a2b47;
                font-weight: 700;
                margin-bottom: 0.6rem;
            }

            .hypo-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
                gap: 1rem;
                margin-bottom: 1.2rem;
            }

            .hypo-card {
                background: rgba(255,255,255,0.75);
                border-radius: 16px;
                padding: 1rem;
                box-shadow: 0 4px 12px rgba(0,0,0,0.08);
                border: 1px solid rgba(200,220,255,0.4);
                backdrop-filter: blur(8px);
                transition: 0.25s ease;
            }

            .hypo-card:hover {
                transform: translateY(-3px);
                box-shadow: 0 6px 18px rgba(0,0,0,0.12);
                background: rgba(250,250,255,0.85);
            }

            .hypo-card p {
                font-size: 0.9rem;
                color: #4a5664;
                line-height: 1.45;
            }

            .hypo-note {
                text-align: center;
                font-weight: 600;
                color: #1565c0;
                font-size: 0.95rem;
            }

        </style>

        <div class="evo-hypo-box">
            <h1 class="evo-hypo-title-inline">
                <span class="evo-dna-emoji-inline">&#129516;</span>
                Test Your Hypothesis
            </h1>
            <p class="evo-hypo-subtext">
                Submit your biological hypothesis, and EvoAge will analyze it against
                scientific knowledge to give you an evidence-based assessment.
            </p>
            <h3 class="sample-title">&#128204; Sample Questions You Can Ask</h3>
            <div class="hypo-grid">
                <div class="hypo-card">
                    <p><b>Hypothesis:</b>
                    "Spermine, a polyamine involved in metabolism and neuroprotection,
                    may influence Hyperkinesis through neurotransmitter and
                    oxidative-stress pathways."</p>
                </div>
                <div class="hypo-card">
                    <p><b>I hypothesize</b> that administration of lithocholic acid (LCA),
                    a calorie-restriction metabolite, promotes health- and lifespan
                    extension by activating AMPK and mimicking CR benefits.</p>
                </div>
            </div>
            <div class="evo-divider"></div>
            <p class="hypo-note">
                Note: Maximum input length is 600 characters.<br>
                <i><u>Each hypothesis may take 2-3 minutes to compute.</i></u>
            </p>
            <div style="margin-top:0.6rem; text-align:center; max-width:760px;">
            <p style="
                font-size:0.82rem;
                color:#35507a;
                line-height:1.35;
                background:rgba(230,238,255,0.6);
                padding:0.45rem 0.8rem;
                border-radius:12px;
                display:inline-block;
                border:1px solid rgba(150,180,240,0.35);
                backdrop-filter:blur(6px);
            ">
                <strong>&#128161; Tip:</strong> For best results, start hypothesis prompts with
                <em>"I hypothesize..."</em> or <em>"My hypothesis..."</em>.
            </p>
            </div>
        </div>
        """