# ---- hypothesis_routes.py ----
from fastapi import APIRouter, HTTPException, Body
import google.generativeai as genai
from typing import Any, Dict, List, Tuple, Optional
import logging, re, os, io, json, uuid
import uuid
import pandas as pd
import requests
import asyncio
from pathlib import Path
from openai import OpenAI
import httpx

# DGL-KE imports
from dglke.models.infer import ScoreInfer
from dglke.utils import load_model_config, load_raw_triplet_data

from app.utils.constants import build_hypothesis_system_prompt
from app.utils.hypothesis_utils import save_response_obj, genai_response_to_payload
from app.utils.environment import CONFIG

# Router
router = APIRouter(prefix="/hypothesis", tags=["Hypothesis"])

# OpenAI Configuration
# client = OpenAI(api_key=CONFIG.OPENAI.OPENAI_API_KEY) 

# Gemini Configuration
genai.configure(api_key=CONFIG.GEMINI.GEMINI_API_KEY) 

logger = logging.getLogger("HypothesisTesting")

# =========================
# CONFIGURATION
# =========================

# DGL + Hypothesis configuration paths from .env
MODEL_PATH         = CONFIG.DGLCONFIG.MODEL_PATH
ENT_DICT_PATH      = CONFIG.DGLCONFIG.ENT_DICT_PATH
REL_DICT_PATH      = CONFIG.DGLCONFIG.REL_DICT_PATH

CUTOFF_FILE              = CONFIG.HYPOTHESIS.CUTOFF_FILE_NAME
INPUT_DIR_HYPOTHESIS     = CONFIG.HYPOTHESIS.INPUT_DIR_HYPOTHESIS
API_BASE                 = CONFIG.HYPOTHESIS.API_BASE
DEFAULT_ENTITY_PROP      = CONFIG.HYPOTHESIS.DEFAULT_ENTITY_PROP
HYPOTHESIS_ENT_DICT_PATH = CONFIG.HYPOTHESIS.HYPOTHESIS_ENT_DICT_PATH

DEVICE             = CONFIG.DGLCONFIG.DGLKE_DEVICE
SFUNC              = CONFIG.DGLCONFIG.DGLKE_SFUNC

# Validate once, fail with clear messages
def _as_path(value, name: str) -> Path:
    if value is None or (isinstance(value, str) and value.strip() == ""):
        raise RuntimeError(f"{name} is not set (empty/None).")
    try:
        return value if isinstance(value, Path) else Path(value)
    except TypeError:
        raise RuntimeError(f"{name} must be path-like, got {type(value).__name__}.")
    
# Normalize everything to Path objects
MODEL_PATH                  = _as_path(MODEL_PATH, "MODEL_PATH")
ENT_DICT_PATH               = _as_path(ENT_DICT_PATH, "ENT_DICT_PATH")
REL_DICT_PATH               = _as_path(REL_DICT_PATH, "REL_DICT_PATH")
CUTOFF_FILE                 = _as_path(CUTOFF_FILE, "CUTOFF_FILE")
INPUT_DIR_HYPOTHESIS        = _as_path(INPUT_DIR_HYPOTHESIS, "INPUT_DIR_HYPOTHESIS")
HYPOTHESIS_ENT_DICT_PATH    = _as_path(HYPOTHESIS_ENT_DICT_PATH, "HYPOTHESIS_ENT_DICT_PATH")

# Validate once, fail with clear messages
errors = []

# MODEL_PATH must exist and be a directory
if not MODEL_PATH.exists():
    errors.append(f"MODEL_PATH missing: {MODEL_PATH}")
if not MODEL_PATH.is_dir():
    errors.append(f"MODEL_PATH not a directory: {MODEL_PATH}")
if not INPUT_DIR_HYPOTHESIS.exists():
    errors.append(f"INPUT_DIR_HYPOTHESIS missing: {INPUT_DIR_HYPOTHESIS}") 
if not INPUT_DIR_HYPOTHESIS.is_dir():
    errors.append(f"INPUT_DIR_HYPOTHESIS not a directory: {INPUT_DIR_HYPOTHESIS}")

cfg = MODEL_PATH / "config.json"
if not cfg.is_file():
    errors.append(f"Missing config.json at {cfg}")

for name, p in [
    ("ENT_DICT_PATH", ENT_DICT_PATH),
    ("REL_DICT_PATH", REL_DICT_PATH),
    ("CUTOFF_FILE", CUTOFF_FILE),
    ("HYPOTHESIS_ENT_DICT_PATH", HYPOTHESIS_ENT_DICT_PATH),
]:
    if not p.is_file():
        errors.append(f"{name} not a file: {p}")

if errors:
    raise FileNotFoundError(" | ".join(errors))


SEARCH_URL = f"{API_BASE}/search_biological_entities"

CHECK_URL = f"{API_BASE}/check_relationship"

# =========================
# VALID RELATIONS
# =========================
VALID_RELATIONS_RAW = """
phenotype_chemicalentity'
mutation_disease'
molecularfunction_chemicalentity'
disease_anatomy'
chemicalentity_disease'
disease_disease'
biologicalprocess_gene'
protein_protein'
gene_phenotype'
protein_disease'
anatomy_gene'
chemicalentity_biologicalprocess'
disease_gene'
gene_cellularcomponent'
chemicalentity_chemicalentity'
cellularcomponent_gene'
gene_disease'
protein_cellularcomponent'
protein_phenotype'
mutation_protein'
chemicalentity_gene'
chemicalentity_tissue'
chemicalentity_protein'
biologicalprocess_biologicalprocess'
phenotype_phenotype'
phenotype_gene'
protein_biologicalprocess'
gene_molecularfunction'
gene_pathway'
chemicalentity_pathway'
gene_tissue'
disease_phenotype'
chemicalentity_mutation'
gene_anatomy'
phenotype_disease'
pathway_gene'
disease_chemicalentity'
disease_mutation'
gene_chemicalentity'
protein_pathway'
gene_protein'
gene_biologicalprocess'
protein_molecularfunction'
mutation_gene'
gene_gene'
molecularfunction_molecularfunction'
gene_mutation'
molecularfunction_biologicalprocess'
protein_tissue'
cellularcomponent_cellularcomponent'
pathway_pathway'
anatomy_anatomy'
biologicalprocess_chemicalentity'
plantextract_chemicalentity'
plantextract_disease'
pmid_cellularcomponent'
pmid_chemicalentity'
pmid_disease'
pmid_protein'
pmid_tissue'
"""
VALID_RELATIONS: set[str] = {
    ln.strip().strip("'").lower()
    for ln in VALID_RELATIONS_RAW.splitlines()
    if ln.strip()
}


# =========================
# Relation Check VIA HTTP API
# =========================
# Map normalized keys -> canonical Neo4j labels
_CANON_LABELS = {
    "gene": "Gene",
    "protein": "Protein",
    "chemicalentity": "ChemicalEntity",
    "biologicalprocess": "BiologicalProcess",
    "molecularfunction": "MolecularFunction",
    "cellularcomponent": "CellularComponent",
    "disease": "Disease",
    "phenotype": "Phenotype",
    "tissue": "Tissue",
    "anatomy": "Anatomy",
    "mutation": "Mutation",
    "pathway": "Pathway",
    "pmid": "PMID",
    "plantextract": "PlantExtract",
}

def _canon_label(s: str) -> str:
    key = re.sub(r"[^A-Za-z0-9]", "", str(s)).lower()
    return _CANON_LABELS.get(key, s)  # fall back to original if unknown

async def _check_one_relationship(ac: httpx.AsyncClient,
                                  head_type: str, head_id: str,
                                  tail_type: str, tail_id: str,
                                  prop: str = DEFAULT_ENTITY_PROP,
                                  timeout: float = 20.0) -> tuple[tuple[str, str, str], dict]:
    """
    Returns:
      key = (head_id, tail_id, f"{head_type}_{tail_type}".lower())
      val = {"in_KG": bool, "kg_rel_type": Optional[str]}
    """
    # params = {
    #     "entity1_type": head_type,
    #     "entity1_property_name": prop,
    #     "entity1_property_value": str(head_id),
    #     "entity2_type": tail_type,
    #     "entity2_property_name": prop,
    #     "entity2_property_value": str(tail_id),
    # }
    ht = _canon_label(head_type)
    tt = _canon_label(tail_type)

    params = {
        "entity1_type": ht,
        "entity1_property_name": prop,
        "entity1_property_value": str(head_id),
        "entity2_type": tt,
        "entity2_property_name": prop,
        "entity2_property_value": str(tail_id),
    }

    # keys for the kg_map should align with your lowercase 'rel'
    key = (str(head_id), str(tail_id), f"{ht}_{tt}".lower())


    try:
        r = await ac.get(CHECK_URL, params=params, timeout=timeout)
        if r.status_code == 200:
            data = r.json() or {}
            return (
                (str(head_id), str(tail_id), f"{ht}_{tt}".lower()),
                {"in_KG": bool(data.get("exists", False)),
                 "kg_rel_type": data.get("relationship_type")}
            )
        else:
            # On HTTP error, mark as not in KG (fail-closed)
            return (
                (str(head_id), str(tail_id), f"{ht}_{tt}".lower()),
                {"in_KG": False, "kg_rel_type": None}
            )
    except Exception:
        return (
            (str(head_id), str(tail_id), f"{ht}_{tt}".lower()),
            {"in_KG": False, "kg_rel_type": None}
        )

async def _check_relationships_async(triples: list[dict],
                                     max_concurrency: int = 50) -> dict[tuple[str, str, str], dict]:
    """
    triples: list of dicts as produced by _make_all_triples_strict(...)
             (needs: head_id, head_type, tail_id, tail_type)
    Returns:
      mapping[(head_id, tail_id, relation_label_lower)] -> {"in_KG": bool, "kg_rel_type": Optional[str]}
    """
    limiter = asyncio.Semaphore(max_concurrency)
    async with httpx.AsyncClient() as ac:
        async def _task(t: dict):
            async with limiter:
                return await _check_one_relationship(
                    ac,
                    head_type=t["head_type"], head_id=t["head_id"],
                    tail_type=t["tail_type"], tail_id=t["tail_id"]
                )
        results = await asyncio.gather(*[_task(t) for t in triples])
    return dict(results)

def _check_relationships(triples: list[dict], max_concurrency: int = 50) -> dict[tuple[str, str, str], dict]:
    """
    Synchronous wrapper you can call from your sync route.
    """
    try:
        return asyncio.run(_check_relationships_async(triples, max_concurrency=max_concurrency))
    except RuntimeError:
        # If we're already inside an event loop (rare in FastAPI sync path), create a new one
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_check_relationships_async(triples, max_concurrency=max_concurrency))
        finally:
            loop.close()

# =========================
# SEARCH VIA HTTP API
# =========================
def _call_search_once(q: str, timeout: int = 60):
    try:
        r = requests.get(SEARCH_URL, params={"targetTerm": q}, timeout=timeout)
        if r.status_code == 200:
            return r.json(), None
        return None, f"HTTP {r.status_code}: {r.text[:180]}"
    except Exception as e:
        return None, f"Request error: {e}"

def _flatten_top_k_per_type(grouped, k=5):
    """
    Keep both ids:
    - id       -> external dict id (MUST be used in .list files)
    - model_id -> internal id (optional bookkeeping)
    """
    flat, counts = [], {}
    for bucket in grouped or []:
        etype = bucket.get("entityType") or "Entity"
        hits  = (bucket.get("topEntities") or [])[:k]
        counts[etype] = len(hits)
        for hit in hits:
            props = hit.get("properties") or {}
            srcid = str(props.get("id") or "").strip()          # <-- REQUIRED
            mid   = str(props.get("model_id") or "").strip()     # optional

            if not srcid:
                # cannot score without a dict id that exists in entities.dict
                continue

            flat.append({
                "id": srcid,                 # <-- write THIS to head/tail lists
                "model_id": mid,             # keep if you want (not used for scoring)
                "entityType": etype,
                "name": props.get("name") or props.get("iupac_name") or "",
                "lucene_score": hit.get("lucene_score"),
                "source": props.get("node_id_is") or props.get("source") or "search_api",
            })
    return flat, counts

def _candidates_for(term: str, max_out: int = 8) -> List[str]:
    """Domain-agnostic fallbacks: raw, acronym-in-parens, longest tokens, etc."""
    cand, t = [], (term or "").strip()
    if not t:
        return []
    cand.append(t)
    # acronyms in parentheses
    cand += re.findall(r"\(([^)]+)\)", t)
    # basic token variants
    toks = [w for w in re.findall(r"[A-Za-z0-9]+", t)]
    if len(toks) >= 2:
        cand.append(" ".join(sorted(toks, key=len, reverse=True)[:2]))
    if toks:
        cand.append(max(toks, key=len))
        cand += toks
    # dedup case-insensitively
    out, seen = [], set()
    for c in cand:
        c = c.strip()
        if c and c.lower() not in seen:
            seen.add(c.lower()); out.append(c)
    return out[:max_out]

def _search_top10_for_terms_http(terms: List[str], k: int = 2) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for term in terms:
        attempts = _candidates_for(term)  # or [term] if you want single-shot
        success, used, last_err = None, None, None
        for q in attempts:
            resp, err = _call_search_once(q)
            if resp is not None:
                success = resp; used = q
                break
            last_err = err
        if success is not None:
            flat, counts = _flatten_top_k_per_type(success, k=k)
            out[term] = {
                "used_term": used,
                "per_type_counts": counts,
                "entities": flat,
            }
        else:
            out[term] = {"error": last_err or "no match", "attempted": attempts}
    return out

# =========================
# Entities → triples
# =========================
def _collect_union_entities(results_top10: Dict[str, Any]) -> List[Dict[str, Any]]:
    """De-dup by (model_id, normalized type)."""
    all_ents: List[Dict[str, Any]] = []
    for payload in results_top10.values():
        ents = payload.get("entities", []) if isinstance(payload, dict) else []
        for e in ents:
            mid = str(e.get("model_id") or e.get("id") or "").strip()
            ety = str(e.get("entityType") or "").strip()
            if not mid or not ety: 
                continue
            all_ents.append({
                "id": str(e.get("id") or mid),  # display/source id
                "model_id": mid,                 # <-- scoring id
                "entityType": ety,
                "entityType_norm": re.sub(r"[^A-Za-z0-9]", "", ety).lower(),
                "name": e.get("name") or "",
            })
    seen, uniq = set(), []
    for e in all_ents:
        key = (e["model_id"], e["entityType_norm"])
        if key not in seen:
            seen.add(key); uniq.append(e)
    return uniq

def _make_all_triples_strict(entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Build all-with-all triples, keep only if relation in VALID_RELATIONS,
    and drop undirected duplicates.
    """
    prelim: List[Dict[str, Any]] = []

    for h in entities:
        for t in entities:
            h_type = h["entityType"]                 # CamelCase (e.g., "Gene")
            t_type = t["entityType"]                 # CamelCase
            h_type_norm = re.sub(r"[^A-Za-z0-9]", "", h_type).lower()
            t_type_norm = re.sub(r"[^A-Za-z0-9]", "", t_type).lower()

            # same node+type -> skip
            if (h["id"] == t["id"]) and (h_type_norm == t_type_norm):
                continue

            rel_camel = f"{h_type}_{t_type}".strip()    # for Neo4j checks
            rel_lower = rel_camel.lower()               # for scoring (.list)

            if rel_lower not in VALID_RELATIONS:
                continue

            prelim.append({
                "head_id":        h["id"],
                "head_model_id":  h.get("model_id"),
                "head_type":      h_type,               # CamelCase
                "head_name":      h.get("name", ""),

                "relation":       rel_lower,            # <-- used in rel.list (lowercase)
                "relation_camel": rel_camel,            # <-- used for /check_relationship

                "tail_type":      t_type,               # CamelCase
                "tail_id":        t["id"],
                "tail_model_id":  t.get("model_id"),
                "tail_name":      t.get("name", ""),
            })

    # undirected de-dup (case-insensitive)
    seen_pairs, uniq = set(), []
    for tr in prelim:
        hkey = (tr["head_type"].lower(), str(tr["head_id"]))
        tkey = (tr["tail_type"].lower(), str(tr["tail_id"]))
        ukey = tuple(sorted([hkey, tkey]))
        if ukey in seen_pairs:
            continue
        seen_pairs.add(ukey)
        uniq.append(tr)
    return uniq

# =========================
# Scoring (YOUR WORKING HELPERS)
# =========================
_INFER: Optional[ScoreInfer] = None

def _get_infer() -> ScoreInfer:
    global _INFER
    if _INFER is None:
        cfg = load_model_config(os.path.join(MODEL_PATH, "config.json"))
        _INFER = ScoreInfer(
            device=DEVICE if DEVICE >= 0 else "cpu",
            config=cfg,
            model_path=MODEL_PATH,
            sfunc=SFUNC,
        )
        _INFER.load_model()
    return _INFER

def _score_triples_to_df(head_list_path=None, rel_list_path=None, tail_list_path=None) -> pd.DataFrame:
    infer = _get_infer()
    head_ids, rel_ids, tail_ids, _, id2ent, id2rel = load_raw_triplet_data(
        head_f=head_list_path,
        rel_f=rel_list_path,
        tail_f=tail_list_path,
        user_tail_f=None,
        emap_f=HYPOTHESIS_ENT_DICT_PATH,
        rmap_f=REL_DICT_PATH,
        head_type=None,
        tail_type=None,
    )

    raw = infer.topK_no_sort(head=head_ids, rel=rel_ids, tail=tail_ids, exec_mode="triplet_wise")

    rows = []
    for h_arr, r_arr, t_arr, s_arr in raw:
        for h, r, t, s in zip(h_arr, r_arr, t_arr, s_arr):
            rows.append((int(h), int(r), int(t), float(s)))
    df_ids = pd.DataFrame(rows, columns=["head_id", "rel_id", "tail_id", "score"])

    # Map back to strings
    def _safe(tbl, idx, kind):
        if isinstance(tbl, dict):
            if int(idx) not in tbl:
                raise RuntimeError(f"{kind} id {idx} not in mapping")
            return tbl[int(idx)]
        i = int(idx)
        if not (0 <= i < len(tbl)):
            raise RuntimeError(f"{kind} id {i} out of range 0..{len(tbl)-1}")
        return tbl[i]

    df = df_ids.assign(
        head=df_ids["head_id"].map(lambda x: _safe(id2ent, x, "entity")),
        rel=df_ids["rel_id"].map(lambda x: _safe(id2rel, x, "relation")),
        tail=df_ids["tail_id"].map(lambda x: _safe(id2ent, x, "entity")),
    )
    return df[["head", "rel", "tail", "score"]]

def _load_cutoff_df(path: str = CUTOFF_FILE) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "relation" not in df.columns or "cutoff_youdenJ" not in df.columns:
        raise RuntimeError("Cutoff file must have columns: relation, cutoff_youdenJ")
    return df[["relation", "cutoff_youdenJ"]].rename(columns={"cutoff_youdenJ": "cutoff"})

def _enrich_with_scores(triples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not triples:
        return []

    os.makedirs(INPUT_DIR_HYPOTHESIS, exist_ok=True)

    unique_id = uuid.uuid4().hex
    head_file = os.path.join(INPUT_DIR_HYPOTHESIS, f"head_{unique_id}.list")
    rel_file  = os.path.join(INPUT_DIR_HYPOTHESIS, f"rel_{unique_id}.list")
    tail_file = os.path.join(INPUT_DIR_HYPOTHESIS, f"tail_{unique_id}.list")
    
    # heads, rels, tails = [], [], []

    try:
        # Write one line per item; convert to str and strip whitespace
        with open(head_file, "w") as hf, open(rel_file, "w") as rf, open(tail_file, "w") as tf:
            for t in triples:
                head_str = str(t.get("head_id", "")).strip()
                rel_str  = str(t.get("relation", "")).strip()
                tail_str = str(t.get("tail_id", "")).strip()

                # Skip incomplete rows; change to `raise` if you want hard failure
                if not head_str or not rel_str or not tail_str:
                    continue

                hf.write(head_str + "\n")
                rf.write(rel_str + "\n")
                tf.write(tail_str + "\n")

                # Keep in-memory lists for the existing scorer
                # heads.append(head_str)
                # rels.append(rel_str)
                # tails.append(tail_str)

        # === Your existing scoring & enrichment ===
        scored = _score_triples_to_df(head_file, rel_file, tail_file)
        cutoff = _load_cutoff_df()
        out = scored.merge(cutoff, left_on="rel", right_on="relation", how="left") \
                    .drop(columns=["relation"])
        out["decision"] = (out["score"] >= out["cutoff"]).map(lambda b: "ACCEPT" if b else "REJECT")

        triple_key = {
            (t["head_id"], t["relation"], t["tail_id"]): (t.get("head_name", ""), t.get("tail_name", ""))
            for t in triples
        }

        rows = []
        for r in out.to_dict(orient="records"):
            key = (str(r["head"]), str(r["rel"]), str(r["tail"]))
            hname, tname = triple_key.get(key, ("", ""))
            r["head_name"] = hname
            r["tail_name"] = tname
            rows.append(r)

        return rows

    except Exception:
        # Optional: add logging here if you have a logger
        # logger.exception("Failed to enrich triples with scores")
        raise

    finally:
        # Best-effort cleanup of temp files
        for p in (head_file, rel_file, tail_file):
            try:
                if p and os.path.exists(p):
                    os.remove(p)
            except OSError:
                pass

def _category_counts(rows: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    1. in_KG = True,  decision = ACCEPT
    2. in_KG = False, decision = ACCEPT
    3. in_KG = False, decision = REJECT
    4. in_KG = True,  decision = REJECT
    """
    counts = {
        "1_inKG_true_ACCEPT": 0,
        "2_inKG_false_ACCEPT": 0,
        "3_inKG_false_REJECT": 0,
        "4_inKG_true_REJECT": 0,
    }
    for r in rows:
        inkg = bool(r.get("in_KG", False))
        dec  = "ACCEPT" if str(r.get("decision", "")).upper() == "ACCEPT" else "REJECT"
        if inkg and dec == "ACCEPT":
            counts["1_inKG_true_ACCEPT"] += 1
        elif (not inkg) and dec == "ACCEPT":
            counts["2_inKG_false_ACCEPT"] += 1
        elif (not inkg) and dec == "REJECT":
            counts["3_inKG_false_REJECT"] += 1
        else:  # inkg and REJECT
            counts["4_inKG_true_REJECT"] += 1
    counts["total_rows"] = len(rows)
    return counts

def _bucket_name(r: Dict[str, Any]) -> str:
    inkg = bool(r.get("in_KG", False))
    dec  = "ACCEPT" if str(r.get("decision", "")).upper() == "ACCEPT" else "REJECT"
    if inkg and dec == "ACCEPT":
        return "1_inKG_true_ACCEPT"
    if (not inkg) and dec == "ACCEPT":
        return "2_inKG_false_ACCEPT"
    if (not inkg) and dec == "REJECT":
        return "3_inKG_false_REJECT"
    return "4_inKG_true_REJECT"

def _categorized_rows_sorted(rows: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    buckets = {
        "1_inKG_true_ACCEPT": [],
        "2_inKG_false_ACCEPT": [],
        "3_inKG_false_REJECT": [],
        "4_inKG_true_REJECT": [],
    }
    for r in rows:
        buckets[_bucket_name(r)].append(r)
    # sort each bucket by closeness to zero (|score| ASC)
    for k in buckets:
        buckets[k].sort(key=lambda x: abs(float(x.get("score", 0.0))))
    return buckets


# =========================
# PUBLIC ROUTE
# =========================
@router.post("/run_hypothesis_pipeline", summary="Search via HTTP API, build triples, score, decide")
def run_hypothesis_pipeline(
    hypothesis: str = Body(..., embed=True, description="User Hypothesis"),
    terms: List[str] = Body(..., embed=True, description="['Lithocholic acid','Caloric restriction',...]"),
    per_type_limit: int = 10,
) -> Dict[str, Any]:
    logger.info(f"Hypothesis: {hypothesis}\
                Terms:{terms}")
    if not terms:
        raise HTTPException(status_code=400, detail="No terms provided.")
    
    # 1) Search via HTTP
    try:
        results_top10 = _search_top10_for_terms_http(terms, k=per_type_limit)
    except Exception as e:
        logger.exception("HTTP search failed.")
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")

    # 2) Union → 3) Triples
    union_entities = _collect_union_entities(results_top10)
    triples = _make_all_triples_strict(union_entities)

    # # 4) Score + cutoff + decision
    # try:
    #     rows = _enrich_with_scores(triples)
    # except Exception as e:
    #     logger.exception("Scoring failed.")
    #     raise HTTPException(status_code=500, detail=f"Scoring failed: {e}")
    try:
        rows = _enrich_with_scores(triples)
    except Exception as e:
        logger.exception("Scoring failed.")
        raise HTTPException(status_code=500, detail=f"Scoring failed: {e}")

    # 5) Check if each (head, tail) already exists in KG (parallel HTTP calls)
    # Build a quick index from (head, rel, tail) -> (head_type, tail_type)
    type_index: dict[tuple[str, str, str], tuple[str, str]] = {}
    for t in triples:
        key = (str(t["head_id"]), str(t["relation"]), str(t["tail_id"]))  # relation is lowercase
        # store canonical CamelCase for Neo4j
        type_index[key] = (_canon_label(t["head_type"]), _canon_label(t["tail_type"]))


    # Fire off relationship checks
    kg_map = _check_relationships(triples, max_concurrency=60)
    # kg_map key: (head_id, tail_id, f"{head_type}_{tail_type}".lower())
    # value: {"in_KG": bool, "kg_rel_type": Optional[str]}

    # Attach in_KG / kg_rel_type back onto each scored row
    for r in rows:
        h, rel, t = str(r["head"]), str(r["rel"]), str(r["tail"])
        # fetch the types for this triple
        ht, tt = type_index.get((h, rel, t), (None, None))
        if ht is None or tt is None:
            r["in_KG"] = False
            r["kg_rel_type"] = None
            continue

        lookup_key = (h, t, f"{ht}_{tt}".lower())
        info = kg_map.get(lookup_key, {"in_KG": False, "kg_rel_type": None})
        r["in_KG"] = bool(info.get("in_KG", False))
        r["kg_rel_type"] = info.get("kg_rel_type")
        # category_counts = _category_counts(rows)
        # categorized_rows = _categorized_rows_sorted(rows)
    # compute once, AFTER the loop
    category_counts  = _category_counts(rows)
    categorized_rows = _categorized_rows_sorted(rows)  # sorted by |score| asc
    categorized_rows.pop("3_inKG_false_REJECT", None)  # hide the heavy bucket
    
    response_obj = {
        "terms": terms,
        "per_type_limit": per_type_limit,
        "entityUnionCount": len(union_entities),
        "tripleCount": len(triples),
        "categoryCounts": category_counts,    # includes bucket 3
        "categorizedRows": categorized_rows,  # only buckets 1,2,4
    }

    # ----------------------------- To Save JSON ----------------------------------------
    save_response_obj(response_obj, "/storage/Arushi/EvoAge-backend/DGL-EvoKG/HypothesisTesting/JSONResult", f"response_obj.json")

    # ------------------------------ Google Vertex SDK Implementation -----------------------

    try:
        with open("/storage/Arushi/EvoAge-backend/DGL-EvoKG/HypothesisTesting/JSONResult/response_obj.json", "r") as f:
            json_data = f.read()
        model = genai.GenerativeModel(CONFIG.GEMINI.GEMINI_MODEL)
        # Send JSON + prompt together
        response = model.generate_content([build_hypothesis_system_prompt(hypothesis), json_data])
    except Exception as e:
        # Log and re-raise (or convert to your API's error)
        logger.exception("Gemini generate_content failed: %s", e)
        raise
    finally:
        try:
            if os.path.exists("/storage/Arushi/EvoAge-backend/DGL-EvoKG/HypothesisTesting/JSONResult/response_obj.json"):
                os.remove("/storage/Arushi/EvoAge-backend/DGL-EvoKG/HypothesisTesting/JSONResult/response_obj.json")
        except OSError:
            pass
    payload = genai_response_to_payload(response)
    return payload['response']

    # ------------------------------ OpenAI Implementation -----------------------

    # # 6) Upload the ENTIRE JSON to OpenAI Files and get a JSON verdict back
    # try:
    #     uploaded = _upload_json_for_file_search(client, response_obj)  # instead of _upload_json_as_file
    #     response = _ask_llm_with_file_search(client, hypothesis, uploaded, model=CONFIG.OPENAI.OPENAI_MODEL)

    # except Exception as e:
    #     raise HTTPException(status_code=502, detail=f"LLM analysis failed: {e}")
    
    # # 7) Return JUST the LLM's JSON to FE
    # if response["parsed"] is not None:
    #     # You got structured data
    #     data = response["parsed"]
    # else:
    #     # Fall back to the model's narrative text
    #     text = response["raw_text"]
    # return {"llm_response": text}

    # def ask_openai_with_inline_json(hypothesis: str, json_path: str, model: str, api_key: str) -> dict:
    #     """
    #     Reads JSON from disk and sends it inline to an OpenAI model together with your system prompt.
    #     Returns a dict: {"response": <dict or {"raw_text": str}>}
    #     """
    #     client = OpenAI(api_key=api_key)

    #     with open(json_path, "r", encoding="utf-8") as f:
    #         json_text = f.read()

    #     system_prompt = build_hypothesis_system_prompt(hypothesis)

    #     try:
    #         resp = client.chat.completions.create(
    #             model=model,
    #             # If your chosen model supports JSON mode, keep this.
    #             # If not, remove this line.
    #             response_format={"type": "json_object"},
    #             messages=[
    #                 {"role": "system", "content": system_prompt},
    #                 {
    #                     "role": "user",
    #                     "content": (
    #                         "Use the following JSON as context. "
    #                         "Respond ONLY with a single valid JSON object.\n\n"
    #                         "```json\n" + json_text + "\n```"
    #                     ),
    #                 },
    #             ],
    #         )
    #     except Exception as e:
    #         logger.exception("OpenAI chat.completions failed: %s", e)
    #         raise

    #     raw_text = resp.choices[0].message.content if resp.choices else ""

    #     try:
    #         parsed = json.loads(raw_text)
    #         return {"response": parsed}
    #     except Exception:
    #         return {"response": {"raw_text": raw_text}}
        
    #     # ------------------------------ OpenAI inline JSON Implementation -----------------------
    # json_file = "/storage/Arushi/EvoAge-backend/Hypothesis-Data/response_obj.json"
    # try:
    #     payload = ask_openai_with_inline_json(
    #         hypothesis=hypothesis,
    #         json_path=json_file,
    #         model=CONFIG.OPENAI.OPENAI_MODEL,
    #         api_key=CONFIG.OPENAI.OPENAI_API_KEY,
    #     )
    # except Exception as e:
    #     logger.exception("OpenAI generate_content failed: %s", e)
    #     raise
    # finally:
    #     try:
    #         if os.path.exists(json_file):
    #             os.remove(json_file)
    #     except OSError:
    #         pass

    # # Always return a dict with 'response'
    # resp = payload.get("response", {})
    # if isinstance(resp, dict):
    #     return resp
    # else:
    #     print('Else_executed')
    #     # defensive fallback
    #     return {"raw_text": str(resp)}
