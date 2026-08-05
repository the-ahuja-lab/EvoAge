"""
app/routers/hypothesis_routes.py

Full EvoAge hypothesis pipeline:
  search -> LLM entity filter -> signed triples -> RESCAL score -> collapse signs
         -> sign-aware KG check -> 6 buckets -> evidence -> 4-agent swarm -> judge

STATE DISCIPLINE (the thing that makes this different from the notebook):
  * LOADED ONCE, at first use, shared across requests:
        RESCAL model, edge tensor + degree array, entity/relation dicts, Neo4j driver
  * BUILT PER REQUEST, never global:
        union_entities, type_index, buckets, edge_by_pair, adj, A_Q, records
  In the notebook these were all module globals. Making them globals here would
  cross-contaminate concurrent hypotheses.
"""

from __future__ import annotations

import csv
import json
import logging
import os
import re
import time
import uuid
from collections import Counter, defaultdict
from datetime import datetime
from itertools import cycle
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple
from neo4j import GraphDatabase

import numpy as np
import pandas as pd
import requests
from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel
from scipy.sparse import csr_matrix

from dglke.models.infer import ScoreInfer
from dglke.utils import load_model_config, load_raw_triplet_data
from app import model_routes
from app.utils.environment import CONFIG
from app.utils.hypothesis_utils import (
    AGENT_SPECS, JUDGE_PROMPT, JudgeOut, SIGNED_VARIANTS, VALID_RELATIONS,
    annotate_edge_meta, build_entity_filter_prompt, call_llm_json, canon_label,
    edge_strength, eids_to_count, enforce_keep_floor, kg_flags, parse_ortholog_info,
    parse_sources, rel_in_kg, safe_label, sign_conflict, split_edges_by_sign,
)

router = APIRouter(prefix="/hypothesis", tags=["Hypothesis"])
logger = logging.getLogger("HypothesisTesting")


class EntityMention(BaseModel):
    """One entity as extracted by the frontend from the hypothesis text, in the
    order it appears there. `types` is the frontend's guess at which KG label(s)
    this mention could resolve to (e.g. ["Gene","Protein"] for a gene symbol) --
    used to hard-filter search results down to plausible-type candidates before
    anything reaches the LLM relevance filter. Leave `types` empty for "no
    constraint, keep every type the search returns" (old behaviour)."""
    mention: str
    types: List[str] = []


# =============================================================================
# CONFIG
# =============================================================================

MODEL_PATH               = Path(CONFIG.DGLCONFIG.MODEL_PATH)
ENT_DICT_PATH            = Path(CONFIG.DGLCONFIG.ENT_DICT_PATH)
REL_DICT_PATH            = Path(CONFIG.DGLCONFIG.REL_DICT_PATH)
HYPOTHESIS_ENT_DICT_PATH = Path(CONFIG.HYPOTHESIS.HYPOTHESIS_ENT_DICT_PATH)
CUTOFF_FILE              = Path(CONFIG.HYPOTHESIS.CUTOFF_FILE_NAME)
GLOBAL_SCORE_PERCENTILES_FILE = Path(CONFIG.HYPOTHESIS.GLOBAL_SCORE_PERCENTILES_FILE)
INPUT_DIR_HYPOTHESIS     = Path(CONFIG.HYPOTHESIS.INPUT_DIR_HYPOTHESIS)
EDGE_TENSOR_PATH         = Path(CONFIG.HYPOTHESIS.EDGE_TENSOR_PATH)
OUTPUT_DIR               = Path(CONFIG.HYPOTHESIS.HYPOTHESIS_TRIPLE_OUTPUT_DIR)

API_BASE            = CONFIG.HYPOTHESIS.API_BASE
DEFAULT_ENTITY_PROP = CONFIG.HYPOTHESIS.DEFAULT_ENTITY_PROP
SEARCH_URL = f"{API_BASE}/search_biological_entities"

NEO4J_URI  = CONFIG.NEO4J.URI
NEO4J_AUTH = (CONFIG.NEO4J.USERNAME, CONFIG.NEO4J.PASSWORD)

DEVICE = CONFIG.DGLCONFIG.DGLKE_DEVICE
SFUNC  = CONFIG.DGLCONFIG.DGLKE_SFUNC

GEMINI_MODEL = CONFIG.GEMINI.GEMINI_MODEL
ALL_KEYS = [k.strip() for k in CONFIG.GEMINI.GEMINI_API_KEY.split(",") if k.strip()]
_KEY_CYCLE = cycle(ALL_KEYS)
_KEY_LOCK = Lock()

# LLM backend switch -- CONFIG.GEMINI.USE = "gemini" (default) or "medgemma".
# Set USE=medgemma in .env to route filter/agent/judge calls.
LLM_PROVIDER = CONFIG.GEMINI.USE
MEDGEMMA_BASE_URL = CONFIG.GEMINI.MEDGEMMA_BASE_URL
MEDGEMMA_MODEL = CONFIG.GEMINI.MEDGEMMA_MODEL
logger.info("LLM backend for hypothesis pipeline: %s", LLM_PROVIDER)

# Adamic-Adar connector window.
# aa_sum alone rewards raw count; mean_aa alone rewards singletons.
# AA summed over connectors in the degree window balances both.
MIN_CONN_DEG = 3      # below this = dangling/artifact node
HUB_CONN_DEG = 500    # above this = hub bridge ("both connect to cancer") = not specific
assert MIN_CONN_DEG >= 2, "AA weight is 1/log(d); d=1 -> log(1)=0 -> inf"

INPUT_DIR_HYPOTHESIS.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# One subfolder per run (response/triples/evidence together) + one running CSV
# across every run, so stats/figures across all tested hypotheses are one file away.
RUNS_DIR = OUTPUT_DIR / "runs"
RUNS_DIR.mkdir(parents=True, exist_ok=True)
STATS_CSV_PATH = OUTPUT_DIR / "hypothesis_run_stats.csv"


def get_next_key() -> str:
    with _KEY_LOCK:
        return next(_KEY_CYCLE)


def _gemini(system_prompt: str, payload: str, temperature: float = 0.0,
           schema: Optional[type] = None, max_tokens: int = 3072) -> Dict[str, Any]:
    """Dispatches to Gemini or MedGemma per CONFIG.GEMINI.USE."""
    return call_llm_json(
        provider=LLM_PROVIDER,
        system_prompt=system_prompt, payload_text=payload,
        key_provider=get_next_key, n_keys=len(ALL_KEYS),
        gemini_model=GEMINI_MODEL,
        medgemma_base_url=MEDGEMMA_BASE_URL, medgemma_model=MEDGEMMA_MODEL,
        temperature=temperature, schema=schema, max_tokens=max_tokens,
    )



# =============================================================================
# HEAVY RESOURCES -- loaded once, shared, never rebuilt per request
# =============================================================================

_DRIVER = None
_GRAPH: Optional[Dict[str, Any]] = None      # heads/tails/rels/deg/N_nodes + dicts
_GRAPH_LOCK = Lock()


def _get_infer() -> ScoreInfer:
    """Reuse model_routes' ScoreInfer instead of loading a second copy.

    Same MODEL_PATH/DEVICE/SFUNC (CONFIG.DGLCONFIG.*) as model_routes.py, which
    already loads and warms this exact model at server startup (module import
    time -- see the "Inference service starting up" log). Loading it again here
    would double GPU memory and repeat the ~5 minute cold-start on the first
    hypothesis request despite the model already being warm. main.py imports
    model_routes before hypothesis_routes, so `model_routes.infer` is guaranteed
    to exist and be warmed up by the time this is called.
    """
    return model_routes.infer


def _get_driver():
    global _DRIVER
    if _DRIVER is None:
        _DRIVER = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
        _DRIVER.verify_connectivity()
        logger.info("Neo4j connected")
    return _DRIVER


def run_cypher(query: str, **params) -> List[dict]:
    with _get_driver().session() as s:
        return [r.data() for r in s.run(query, **params)]


def _load_dict(path) -> Tuple[Dict[str, int], Dict[int, str]]:
    s2i, i2s = {}, {}
    with open(path) as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 2:
                continue
            a, b = parts[0], parts[1]
            if a.isdigit():
                idx, nm = int(a), b
            elif b.isdigit():
                idx, nm = int(b), a
            else:
                continue
            s2i[nm] = idx
            i2s[idx] = nm
    return s2i, i2s


def _get_graph() -> Dict[str, Any]:
    """Edge tensor + global degree + entity/relation dicts.

    This is the expensive one (~1B edges). Loaded exactly once behind a lock, then
    shared read-only by every request. Loading it per-request would be the whole
    3-minute latency.
    """
    global _GRAPH
    if _GRAPH is not None:
        return _GRAPH
    with _GRAPH_LOCK:
        if _GRAPH is not None:
            return _GRAPH

        import torch
        t0 = time.time()

        ent_s2i, ent_i2s = _load_dict(HYPOTHESIS_ENT_DICT_PATH)
        rel_s2i, rel_i2s = _load_dict(REL_DICT_PATH)

        T = torch.load(str(EDGE_TENSOR_PATH), map_location="cpu")
        if isinstance(T, dict):
            T = T.get("edge_index") or next(iter(T.values()))
        T = torch.as_tensor(T)
        if T.shape[0] in (2, 3) and T.shape[0] < T.shape[1]:
            heads = T[0].numpy().astype(np.int64)
            tails = T[-1].numpy().astype(np.int64)
            rels = T[1].numpy().astype(np.int64) if T.shape[0] == 3 else None
        else:
            heads = T[:, 0].numpy().astype(np.int64)
            tails = T[:, -1].numpy().astype(np.int64)
            rels = T[:, 1].numpy().astype(np.int64) if T.shape[1] == 3 else None
        del T

        n_nodes = int(max(heads.max(), tails.max())) + 1
        deg = np.zeros(n_nodes, dtype=np.int64)
        np.add.at(deg, heads, 1)
        np.add.at(deg, tails, 1)

        _GRAPH = {
            "heads": heads, "tails": tails, "rels": rels, "deg": deg,
            "n_nodes": n_nodes, "n_edges": len(heads),
            "ent_s2i": ent_s2i, "ent_i2s": ent_i2s,
            "rel_s2i": rel_s2i, "rel_i2s": rel_i2s,
            "species_rel": rel_s2i.get("species_associatedwith"),
        }
        logger.info("edge tensor loaded: %s edges, %s nodes (%.1fs)",
                    f"{len(heads):,}", f"{n_nodes:,}", time.time() - t0)
    return _GRAPH


# =============================================================================
# 1.1 · ENTITY SEARCH
# =============================================================================

def _call_search_once(q: str, timeout: int = 60):
    try:
        r = requests.get(SEARCH_URL, params={"targetTerm": q}, timeout=timeout)
        if r.status_code == 200:
            return r.json(), None
        return None, f"HTTP {r.status_code}: {r.text[:180]}"
    except Exception as e:
        return None, f"Request error: {e}"


def _norm_type(t: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", str(t or "")).lower()


def _flatten_top_k_per_type(grouped, k: int = 5, allowed_types: Optional[set] = None):
    """`allowed_types`, if given, is a set of normalised type keys (see _norm_type)
    -- any bucket whose entityType doesn't normalise into that set is skipped
    entirely, before its hits are even looked at. None means no constraint."""
    flat, counts = [], {}
    for bucket in grouped or []:
        etype = bucket.get("entityType") or "Entity"
        if allowed_types is not None and _norm_type(etype) not in allowed_types:
            continue
        hits = (bucket.get("topEntities") or [])[:k]
        counts[etype] = len(hits)
        for hit in hits:
            props = hit.get("properties") or {}
            srcid = str(props.get("id") or "").strip()
            if not srcid:
                continue            # cannot score without a dict id
            flat.append({
                "id": srcid,
                "model_id": str(props.get("model_id") or "").strip(),
                "entityType": etype,
                "name": props.get("name") or props.get("iupac_name") or "",
                "lucene_score": hit.get("lucene_score"),
                "source": props.get("node_id_is") or props.get("source") or "search_api",
            })
    return flat, counts


def _candidates_for(term: str, max_out: int = 8) -> List[str]:
    """Fallback query variants if the exact term misses."""
    cand, t = [], (term or "").strip()
    if not t:
        return []
    cand.append(t)
    cand += re.findall(r"\(([^)]+)\)", t)
    toks = re.findall(r"[A-Za-z0-9]+", t)
    if len(toks) >= 2:
        cand.append(" ".join(sorted(toks, key=len, reverse=True)[:2]))
    if toks:
        cand.append(max(toks, key=len))
        cand += toks
    out, seen = [], set()
    for c in cand:
        c = c.strip()
        if c and c.lower() not in seen:
            seen.add(c.lower())
            out.append(c)
    return out[:max_out]


def _search_terms(mentions: List[Dict[str, Any]], k: int = 5) -> Dict[str, Any]:
    """`mentions` = [{"mention": str, "types": [str]}, ...], already in hypothesis
    order (dict insertion order below preserves it for _collect_union_entities'
    term_order tagging).

    Each mention's `types`, if given, hard-filters which SBE type-buckets are
    kept for that mention -- a deterministic pass ahead of the LLM relevance
    filter (which still has to reason about biological relevance, but no longer
    has to also catch wrong-type string collisions). Fails OPEN per mention: if
    the declared types match nothing the search actually returned, that's a
    frontend-NER miss, not proof the entity is irrelevant -- fall back to the
    unfiltered results rather than silently losing a named entity.
    """
    out: Dict[str, Any] = {}
    for m in mentions:
        term = str(m.get("mention", "")).strip()
        if not term:
            continue
        allowed = {_norm_type(t) for t in (m.get("types") or [])} or None

        attempts = _candidates_for(term)
        success, used, last_err = None, None, None
        for q in attempts:
            resp, err = _call_search_once(q)
            if resp is not None:
                success, used = resp, q
                break
            last_err = err

        if success is None:
            logger.warning("UNRESOLVED-TERM '%s' (tried %s)", term, attempts)
            out[term] = {"error": last_err or "no match", "attempted": attempts}
            continue

        flat, counts = _flatten_top_k_per_type(success, k=k, allowed_types=allowed)
        if allowed is not None and not flat:
            logger.warning("'%s': declared types %s matched no search results -- "
                           "falling back to unfiltered candidates for this mention",
                           term, sorted(allowed))
            flat, counts = _flatten_top_k_per_type(success, k=k)

        out[term] = {"used_term": used, "per_type_counts": counts, "entities": flat,
                     "declared_types": sorted(allowed) if allowed else []}
    return out


# =============================================================================
# 1.2 · LLM ENTITY FILTER  (fails OPEN -- keeps everything on error)
# =============================================================================

def _group_candidates_by_term(results):
    return {
        term: [
            {"id": e.get("id"), "name": e.get("name", ""),
             "entityType": e.get("entityType", ""), "lucene_score": e.get("lucene_score")}
            for e in (payload.get("entities", []) if isinstance(payload, dict) else [])
        ]
        for term, payload in results.items()
    }


def filter_entities_llm(hypothesis: str, results: dict, union_raw: List[dict]) -> dict:
    prompt = build_entity_filter_prompt(
        hypothesis, json.dumps(_group_candidates_by_term(results), indent=2))

    logger.info("entity_filter: payload %d chars (%d raw candidates)",
               len(prompt), len(union_raw))
    # 60 candidates x ~4-5 fields each (id/name/entityType/relevance-or-reason) can
    # easily need more than the 3072-token default -- confirmed by a truncated
    # "reason" string in a real failure log. No schema is used here (see the
    # remaining TODO on adding one), so there's no guided-decoding floor to lean on.
    parsed = _gemini("", prompt, temperature=0.0, max_tokens=8192)

    if "_error" in parsed or "_parse_error" in parsed:
        logger.warning("entity filter failed -- keeping all %d candidates unfiltered",
                       len(union_raw))
        _log_agent_failure("entity_filter", parsed)
        return {"kept": [], "dropped": [], "kept_union_entities": union_raw,
                "filter_failed": True}

    kept_ids = enforce_keep_floor(parsed, union_raw, floor=0.5)
    return {
        "kept": parsed.get("kept", []),
        "dropped": parsed.get("dropped", []),
        "kept_union_entities": [e for e in union_raw if str(e["id"]) in kept_ids],
        "filter_failed": False,
    }


# =============================================================================
# 1.3 · UNION + ALL-PAIRS TRIPLES (base + SIGNED variants)
# =============================================================================

def _collect_union_entities(results) -> List[Dict[str, Any]]:
    """`results` is keyed by mention, in the SAME order `entities_input` was passed
    in by the caller (dict insertion order, built by _search_terms iterating
    `mentions`). That order mirrors how the entities appear in the hypothesis
    text, so it's tagged onto each entity here as `term_order` -- the only place
    this information is still available; every later stage (triples, buckets,
    records) carries ids only, so ordering-by-hypothesis-position has to be
    captured now or it's lost."""
    all_ents = []
    for term_order, payload in enumerate(results.values()):
        ents = payload.get("entities", []) if isinstance(payload, dict) else []
        for e in ents:
            mid = str(e.get("model_id") or e.get("id") or "").strip()
            ety = str(e.get("entityType") or "").strip()
            if not mid or not ety:
                continue
            all_ents.append({
                "id": str(e.get("id") or mid),
                "model_id": mid,
                "entityType": ety,
                "entityType_norm": re.sub(r"[^A-Za-z0-9]", "", ety).lower(),
                "name": e.get("name") or "",
                "lucene_score": e.get("lucene_score"),
                "term_order": term_order,
            })
    seen, uniq = set(), []
    for e in all_ents:
        key = (e["model_id"], e["entityType_norm"])
        if key not in seen:
            # first occurrence wins -- earliest term the entity was found under.
            seen.add(key)
            uniq.append(e)
    return uniq


def _make_all_triples_strict(entities) -> List[Dict[str, Any]]:
    """All-with-all pairs. For each valid type-pair emit the BASE relation AND every
    signed variant, so RESCAL can score direction, not just connection. O(n^2)."""
    prelim = []
    for h in entities:
        for t in entities:
            h_type, t_type = h["entityType"], t["entityType"]
            h_norm = re.sub(r"[^A-Za-z0-9]", "", h_type).lower()
            t_norm = re.sub(r"[^A-Za-z0-9]", "", t_type).lower()

            if (h["id"] == t["id"]) and (h_norm == t_norm):
                continue

            rels_to_emit = []
            base_rel = f"{h_norm}_{t_norm}"
            if base_rel in VALID_RELATIONS:
                rels_to_emit.append((base_rel, ""))
            for signed in SIGNED_VARIANTS.get((h_norm, t_norm), []):
                rels_to_emit.append((signed, signed.split("_")[1]))

            for rel_lower, predicate in rels_to_emit:
                prelim.append({
                    "head_id": h["id"], "head_model_id": h.get("model_id"),
                    "head_type": h_type, "head_name": h.get("name", ""),
                    "relation": rel_lower,
                    "relation_camel": f"{h_type}_{t_type}",
                    "predicate": predicate,
                    "is_signed": bool(predicate),
                    "tail_type": t_type, "tail_id": t["id"],
                    "tail_model_id": t.get("model_id"), "tail_name": t.get("name", ""),
                })

    # undirected dedupe, PER PREDICATE (so promotes/inhibits don't collapse into one)
    seen, uniq = set(), []
    for tr in prelim:
        hkey = (tr["head_type"].lower(), str(tr["head_id"]))
        tkey = (tr["tail_type"].lower(), str(tr["tail_id"]))
        ukey = (tuple(sorted([hkey, tkey])), tr["predicate"])
        if ukey in seen:
            continue
        seen.add(ukey)
        uniq.append(tr)
    return uniq


# =============================================================================
# 2 · RESCAL SCORING + SIGN COLLAPSE
# =============================================================================

def _score_triples_to_df(head_f, rel_f, tail_f) -> pd.DataFrame:
    infer = _get_infer()
    head_ids, rel_ids, tail_ids, _, id2ent, id2rel = load_raw_triplet_data(
        head_f=head_f, rel_f=rel_f, tail_f=tail_f, user_tail_f=None,
        emap_f=str(HYPOTHESIS_ENT_DICT_PATH), rmap_f=str(REL_DICT_PATH),
        head_type=None, tail_type=None)

    raw = infer.topK_no_sort(head=head_ids, rel=rel_ids, tail=tail_ids,
                             exec_mode="triplet_wise")
    recs = [(int(h), int(r), int(t), float(s))
            for h_a, r_a, t_a, s_a in raw
            for h, r, t, s in zip(h_a, r_a, t_a, s_a)]
    df_ids = pd.DataFrame(recs, columns=["head_id", "rel_id", "tail_id", "score"])

    def _safe(tbl, idx, kind):
        if isinstance(tbl, dict):
            if int(idx) not in tbl:
                raise RuntimeError(f"{kind} id {idx} not in mapping")
            return tbl[int(idx)]
        i = int(idx)
        if not (0 <= i < len(tbl)):
            raise RuntimeError(f"{kind} id {i} out of range")
        return tbl[i]

    df = df_ids.assign(
        head=df_ids["head_id"].map(lambda x: _safe(id2ent, x, "entity")),
        rel=df_ids["rel_id"].map(lambda x: _safe(id2rel, x, "relation")),
        tail=df_ids["tail_id"].map(lambda x: _safe(id2ent, x, "entity")))
    return df[["head", "rel", "tail", "score"]]


_CUTOFF_DF: Optional[pd.DataFrame] = None


def _load_cutoff_df() -> pd.DataFrame:
    global _CUTOFF_DF
    if _CUTOFF_DF is None:
        df = pd.read_csv(CUTOFF_FILE)
        if "relation" not in df.columns or "cutoff_youdenJ" not in df.columns:
            raise RuntimeError("Cutoff file must have columns: relation, cutoff_youdenJ")
        _CUTOFF_DF = df[["relation", "cutoff_youdenJ"]].rename(
            columns={"cutoff_youdenJ": "cutoff"})
    return _CUTOFF_DF


# =============================================================================
# GLOBAL SCORE PERCENTILES -- where a triple's raw RESCAL score sits against the
# distribution of ALL ground-truth triples in the graph (GLOBAL_SCORE_PERCENTILES_FILE,
# a single summary row: p0..p100). Distinct from CUTOFF_FILE, which is a per-relation
# accept/reject threshold -- this is a graph-wide "how strong is this score,
# really" signal, independent of relation and independent of accept/reject.
# =============================================================================

_PERCENTILE_COLS = ["p0", "p1", "p5", "p10", "p25", "p50", "p75", "p90", "p95", "p99", "p100"]

_GLOBAL_PCTS: Optional[List[Tuple[str, float]]] = None


def _load_global_percentiles() -> List[Tuple[str, float]]:
    global _GLOBAL_PCTS
    if _GLOBAL_PCTS is None:
        df = pd.read_csv(GLOBAL_SCORE_PERCENTILES_FILE)
        missing = [c for c in _PERCENTILE_COLS if c not in df.columns]
        if missing:
            raise RuntimeError(f"GLOBAL_SCORE_PERCENTILES_FILE missing columns: {missing}")
        row = df.iloc[0]
        # ascending by score value -- logsigmoid scores are <= 0, so p100 (closest
        # to 0) is the STRONGEST bracket and p0 (most negative) the weakest.
        _GLOBAL_PCTS = [(c, float(row[c])) for c in _PERCENTILE_COLS]
    return _GLOBAL_PCTS


def score_percentile_label(score) -> str:
    """Bracket a raw model score against the GLOBAL ground-truth score
    distribution, e.g. 'p90-p95' -- stronger than 90% of every curated triple
    in the graph, weaker than 95% of them. 'NA' if score isn't a number."""
    try:
        s = float(score)
    except (TypeError, ValueError):
        return "NA"
    pcts = _load_global_percentiles()
    if s <= pcts[0][1]:
        return f"<={pcts[0][0]}"
    for (lo_name, _lo_val), (hi_name, hi_val) in zip(pcts, pcts[1:]):
        if s <= hi_val:
            return f"{lo_name}-{hi_name}"
    return f">={pcts[-1][0]}"


def _enrich_with_scores(triples) -> List[Dict[str, Any]]:
    if not triples:
        return []
    uid = uuid.uuid4().hex
    head_f = INPUT_DIR_HYPOTHESIS / f"head_{uid}.list"
    rel_f = INPUT_DIR_HYPOTHESIS / f"rel_{uid}.list"
    tail_f = INPUT_DIR_HYPOTHESIS / f"tail_{uid}.list"
    try:
        with open(head_f, "w") as hf, open(rel_f, "w") as rf, open(tail_f, "w") as tf:
            for t in triples:
                h = str(t.get("head_id", "")).strip()
                r = str(t.get("relation", "")).strip()
                tl = str(t.get("tail_id", "")).strip()
                if not (h and r and tl):
                    continue
                hf.write(h + "\n")
                rf.write(r + "\n")
                tf.write(tl + "\n")

        scored = _score_triples_to_df(str(head_f), str(rel_f), str(tail_f))
        out = (scored.merge(_load_cutoff_df(), left_on="rel", right_on="relation", how="left")
                     .drop(columns=["relation"]))
        out["decision"] = (out["score"] >= out["cutoff"]).map(
            lambda b: "ACCEPT" if b else "REJECT")

        names = {(t["head_id"], t["relation"], t["tail_id"]):
                 (t.get("head_name", ""), t.get("tail_name", "")) for t in triples}
        rows = []
        for r in out.to_dict(orient="records"):
            hn, tn = names.get((str(r["head"]), str(r["rel"]), str(r["tail"])), ("", ""))
            r["head_name"], r["tail_name"] = hn, tn
            rows.append(r)
        return rows
    finally:
        for p in (head_f, rel_f, tail_f):
            try:
                if p.exists():
                    p.unlink()
            except OSError:
                pass


def collapse_signed_variants(scored_rows):
    """Per entity pair:
       - the BASE relation (2-part) passes through as its own row  -> 'are they connected?'
       - among SIGNED variants (3-part) keep only the highest-scoring -> 'which direction?'
       Both survive. `variant_scores` records what the model thought of each sign."""
    groups = defaultdict(list)
    for r in scored_rows:
        groups[tuple(sorted([str(r["head"]), str(r["tail"])]))].append(r)

    kept, log = [], []
    for key, variants in groups.items():
        base_rows = [v for v in variants if len(str(v["rel"]).split("_")) == 2]
        signed_rows = [v for v in variants if len(str(v["rel"]).split("_")) == 3]

        kept.extend(base_rows)

        if signed_rows:
            best = dict(max(signed_rows, key=lambda x: float(x["score"])))
            best["n_variants_considered"] = len(signed_rows)
            best["variant_scores"] = {v["rel"]: round(float(v["score"]), 4)
                                      for v in signed_rows}
            kept.append(best)
            if len(signed_rows) > 1:
                log.append({"pair": list(key), "winner": best["rel"],
                            "variant_scores": best["variant_scores"]})
    return kept, log


# =============================================================================
# 3 · SIGN-AWARE in-KG CHECK  (direct cypher, pair-deduped)
# =============================================================================

def _safe_prop(prop: str) -> str:
    """Guard against Cypher injection -- property names cannot be parameterised."""
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", str(prop)):
        raise ValueError(f"Refusing unsafe property name: {prop}")
    return str(prop)


def _check_relationships(triples, prop: str = DEFAULT_ENTITY_PROP):
    """Sign-aware in-KG check, asked of Neo4j directly.

    Byte-identical question to GET /check_relationship (which the chatbot still
    uses for a single A-B lookup) -- same Cypher, both bound by the `id` index --
    but asked in-process over ONE reused session instead of over HTTP.

    The pipeline used to fan out one HTTP GET per pair back into our OWN uvicorn.
    That endpoint is `async def` wrapped around the BLOCKING neo4j driver, so each
    request held the event loop for its entire query; a few hundred of them
    serialised onto a single thread and blew the 20s client timeout. That is why a
    300-pair hypothesis came back as a wall of 6_CHECK_FAILED while a 65-triple
    one passed clean -- the cliff was the timeout, never Neo4j, which answers each
    of these pairs in ~2-4ms. Removing the HTTP hop removes the only thing that
    could time out, so this stays correct at 10 pairs and at 300.

    Kept as one query per pair on purpose: batching them into a single UNWIND
    measured ~2000x SLOWER (93s for 41 pairs vs 172ms), because the planner will
    not use the `id` index for a property compared against an UNWIND row.

    Returns {(head_id, tail_id, "headlabel_taillabel"): {kg_rel_types, check_failed}}.
    """
    # The check takes no relation param, so every relation variant between the same
    # two nodes asks the identical question. Collapse to unique pairs first.
    unique_pairs = {}
    for t in triples:
        ht, tt = canon_label(t["head_type"]), canon_label(t["tail_type"])
        key = (str(t["head_id"]), str(t["tail_id"]), f"{ht}_{tt}".lower())
        if key not in unique_pairs:
            unique_pairs[key] = (ht, tt, str(t["head_id"]), str(t["tail_id"]))

    logger.info("KG check: %d triples -> %d unique pairs", len(triples), len(unique_pairs))

    p = _safe_prop(prop)
    out = {key: {"kg_rel_types": [], "check_failed": False} for key in unique_pairs}
    t0 = time.time()

    # One session for the whole sweep -- per-pair sessions would add a round trip
    # of setup to every check for no benefit.
    with _get_driver().session() as sess:
        for key, (ht, tt, h_id, t_id) in unique_pairs.items():
            try:
                q = f"""
                MATCH (e1:`{safe_label(ht)}`)-[r]-(e2:`{safe_label(tt)}`)
                WHERE e1.`{p}` = $h AND e2.`{p}` = $t
                RETURN collect(DISTINCT type(r)) AS rel_types
                """
                rows = [r.data() for r in sess.run(q, h=h_id, t=t_id)]
            except Exception as e:
                # Fail-closed BUT FLAGGED. An empty list from a failed query looks
                # identical to "no edge exists" -> would fabricate a novel finding.
                # Never let that happen silently.
                logger.warning("KG check failed for %s/%s %s-%s (%s): %s",
                               ht, tt, h_id, t_id, type(e).__name__, e)
                out[key]["check_failed"] = True
                continue

            # collect() always yields exactly one row -- an empty list when there
            # is no edge, which is a genuine "no edge", not a failure.
            types = (rows[0].get("rel_types") if rows else []) or []
            out[key]["kg_rel_types"] = [str(x) for x in types if x]

    logger.info("KG check: %d pairs resolved in %.2fs", len(unique_pairs), time.time() - t0)
    return out


def _bucket_name(r: dict) -> str:
    # A sign conflict is a CONTRADICTION, not a gap. Without this branch,
    # (in_KG=False, ACCEPT) lands in bucket 2 and a prediction that directly opposes a
    # curated edge gets reported as a "novel discovery".
    if r.get("kg_sign_conflict"):
        return "5_SIGN_CONFLICT"
    if r.get("check_failed"):
        return "6_CHECK_FAILED"

    inkg = bool(r.get("in_KG", False))
    acc = str(r.get("decision", "")).upper() == "ACCEPT"
    if inkg and acc:
        return "1_inKG_true_ACCEPT"
    if (not inkg) and acc:
        return "2_inKG_false_ACCEPT"
    if (not inkg) and (not acc):
        return "3_inKG_false_REJECT"
    return "4_inKG_true_REJECT"


BUCKET_KEYS = ["1_inKG_true_ACCEPT", "2_inKG_false_ACCEPT", "3_inKG_false_REJECT",
               "4_inKG_true_REJECT", "5_SIGN_CONFLICT", "6_CHECK_FAILED"]


def attach_kg_state(rows_collapsed, triples):
    """Returns (buckets, type_index, counts). Both are PER-REQUEST -- never global."""
    type_index = {}
    for t in triples:
        type_index[(str(t["head_id"]), str(t["relation"]), str(t["tail_id"]))] = (
            canon_label(t["head_type"]), canon_label(t["tail_type"]))

    kg_map = _check_relationships(triples)

    n_failed = sum(1 for v in kg_map.values() if v.get("check_failed"))
    if n_failed:
        logger.warning("%d KG checks failed (cypher) -- flagged, excluded from novel",
                       n_failed)

    for r in rows_collapsed:
        h, rel, t = str(r["head"]), str(r["rel"]), str(r["tail"])
        ht, tt = type_index.get((h, rel, t), (None, None))
        if ht is None:
            r.update({"in_KG": False, "kg_rel_type": None, "kg_rel_types": [],
                      "kg_any_edge": False, "kg_sign_conflict": False,
                      "check_failed": False})
            continue

        info = kg_map.get((h, t, f"{ht}_{tt}".lower()),
                          {"kg_rel_types": [], "check_failed": True})
        kg_types = info.get("kg_rel_types", [])

        r["kg_rel_types"] = kg_types
        r["check_failed"] = bool(info.get("check_failed", False))
        r["kg_any_edge"] = bool(kg_types)
        r["in_KG"] = rel_in_kg(rel, kg_types)
        r["kg_sign_conflict"] = sign_conflict(rel, kg_types)
        r["kg_rel_type"] = (rel if (r["in_KG"] and len(rel.split("_")) == 3)
                            else (kg_types[0] if kg_types else None))

    buckets = {k: [] for k in BUCKET_KEYS}
    for r in rows_collapsed:
        buckets[_bucket_name(r)].append(r)

    # logsigmoid scores are <= 0, so closest-to-zero == highest confidence.
    # A missing score would sort to the TOP under abs(); push it last instead.
    for k in buckets:
        buckets[k].sort(key=lambda x: abs(float(x["score"]))
                        if x.get("score") is not None else float("inf"))

    counts = {k: len(v) for k, v in buckets.items()}
    counts["total"] = len(rows_collapsed)
    return buckets, type_index, counts


# =============================================================================
# 4 · EVIDENCE
# =============================================================================

def build_subgraph(union_entities) -> Dict[str, Any]:
    """Resolve hypothesis nodes + the induced subgraph among them. One indexed query
    per label, then one bounded edge query. No hub traversal."""
    label_to_ids = defaultdict(set)
    for e in union_entities:
        label_to_ids[canon_label(e["entityType"])].add(str(e["id"]))

    node_props = {}
    for lbl, ids in label_to_ids.items():
        lbl = safe_label(lbl)
        q = f"""
        MATCH (x:`{lbl}`) WHERE x.id IN $ids
        RETURN x.id AS id, elementId(x) AS eid, x.name AS name,
               x.node_species AS species, x.ortholog_info AS ortholog_info
        """
        for r in run_cypher(q, ids=list(ids)):
            node_props[(lbl, r["id"])] = {
                "eid": r["eid"], "name": r["name"], "species": r["species"],
                "ortholog": parse_ortholog_info(r["ortholog_info"]),
            }

    all_eids = [v["eid"] for v in node_props.values()]
    subgraph_edges = run_cypher("""
    MATCH (a)-[r]-(b)
    WHERE elementId(a) IN $eids AND elementId(b) IN $eids
      AND elementId(a) < elementId(b)
    RETURN a.id AS a_id, b.id AS b_id, type(r) AS rtype,
           r.relation_type AS relation_type, r.source AS source, r.kg_type AS kg_type
    """, eids=all_eids) if all_eids else []

    edge_by_pair = defaultdict(list)
    adj = defaultdict(list)
    for e in subgraph_edges:
        a, b = str(e["a_id"]), str(e["b_id"])
        meta = {
            "relation_type": e["relation_type"], "type": e["rtype"],
            "sources": parse_sources(e["source"]), "kg": kg_flags(e["kg_type"]),
            "a_id": e["a_id"], "b_id": e["b_id"],
        }
        edge_by_pair[tuple(sorted([a, b]))].append(meta)
        adj[a].append((b, meta))
        adj[b].append((a, meta))

    logger.info("resolved %d hypothesis nodes; %d direct edges among them",
                len(all_eids), len(subgraph_edges))

    return {
        "node_props": node_props,
        "edge_by_pair": edge_by_pair,
        "adj": adj,
        "id_to_name": {str(e["id"]): (e.get("name") or str(e["id"]))
                       for e in union_entities},
    }


def _conservation_for(ht, h_id, tt, t_id, node_props):
    cons = {}
    for lbl, nid in [(ht, h_id), (tt, t_id)]:
        if lbl == "Gene":
            props = node_props.get((lbl, nid), {})
            cons[nid] = {
                "species_conserved": [o["species"] for o in props.get("ortholog", [])],
                "orthologs": props.get("ortholog", []),
            }
    return cons


def build_evidence(row, ctx) -> dict:
    """Bucket 1 / 4 -- provenance is free, straight off the edge."""
    h_id, t_id = str(row["head"]), str(row["tail"])
    ht, tt = ctx["type_index"].get((h_id, str(row["rel"]), t_id), (None, None))

    all_edges = ctx["edge_by_pair"].get(tuple(sorted([h_id, t_id])), [])
    for e in all_edges:
        e["strength"] = edge_strength(e)

    # only the sign-matching edges back THIS claim
    edges, other_sign_edges = split_edges_by_sign(row["rel"], all_edges)

    return {
        "head": h_id, "head_name": row.get("head_name", ""), "head_label": ht,
        "rel": row["rel"],
        "tail": t_id, "tail_name": row.get("tail_name", ""), "tail_label": tt,
        "score": row["score"], "cutoff": row.get("cutoff"),
        "decision": row["decision"], "in_KG": row["in_KG"],

        "kg_any_edge": row.get("kg_any_edge", False),
        "kg_sign_conflict": row.get("kg_sign_conflict", False),
        "kg_rel_types": row.get("kg_rel_types", []),
        "kg_rel_type": row.get("kg_rel_type"),
        "variant_scores": row.get("variant_scores"),

        "direct_edges": edges,
        "n_direct_edges": len(edges),
        "max_edge_strength": max([e["strength"] for e in edges], default=0.0),
        "aging_supported": any(e["kg"]["has_aging"] for e in edges),

        "other_sign_edges": other_sign_edges,
        "n_other_sign_edges": len(other_sign_edges),

        "conservation": _conservation_for(ht, h_id, tt, t_id, ctx["node_props"]),
    }


def find_paths_inmemory(src, dst, adj, id_to_name, max_len=3, max_paths=15, min_len=2):
    """Simple paths src->dst over the hypothesis-only subgraph (tens of nodes, instant).

    min_len=2 matters now that the in-KG check is sign-aware. A bucket-2 row can be a
    SIGN CONFLICT -- the pair has a direct edge, just the opposite sign. That edge would
    come back as a length-1 'connecting path' and read as circumstantial SUPPORT for the
    claim it actually contradicts."""
    results = []

    def _name(i):
        return id_to_name.get(i, i)

    def dfs(node, path_nodes, path_edges):
        if len(results) >= max_paths or len(path_edges) > max_len:
            return
        if node == dst and len(path_edges) >= min_len:
            results.append({"nodes": list(path_nodes),
                            "node_names": [_name(n) for n in path_nodes],
                            "edges": list(path_edges), "length": len(path_edges)})
            return
        if node == dst and path_edges:      # direct edge: not a path, don't walk through
            return
        for nbr, meta in adj.get(node, []):
            if nbr in path_nodes:
                continue
            path_nodes.append(nbr)
            path_edges.append(meta)
            dfs(nbr, path_nodes, path_edges)
            path_nodes.pop()
            path_edges.pop()

    dfs(src, [src], [])
    results.sort(key=lambda p: p["length"])
    return results[:max_paths]


def shared_neighbours_inmemory(src, dst, adj, id_to_name):
    ns = {n for n, _ in adj.get(src, [])}
    nd = {n for n, _ in adj.get(dst, [])}
    out = []
    for s in (ns & nd) - {src, dst}:
        aging = any(m["kg"]["has_aging"] for nbr, m in adj.get(s, []) if nbr in (src, dst))
        out.append({"id": s, "name": id_to_name.get(s, s), "aging_bridge": aging})
    return out


def build_evidence_bucket2(row, ctx) -> dict:
    """Bucket 2 -- no edge exists, so build a CIRCUMSTANTIAL case."""
    h_id, t_id = str(row["head"]), str(row["tail"])
    ht, tt = ctx["type_index"].get((h_id, str(row["rel"]), t_id), (None, None))

    margin = None
    if row.get("cutoff") is not None:
        try:
            margin = round(float(row["score"]) - float(row["cutoff"]), 4)
        except Exception:
            pass

    paths = find_paths_inmemory(h_id, t_id, ctx["adj"], ctx["id_to_name"])
    for p in paths:
        for meta in p["edges"]:
            annotate_edge_meta(meta)
        p["all_mechanistic"] = all(m["rel_tier"] == "mechanistic" for m in p["edges"])

    # DIRECT edges between the pair. In bucket 2 these are never the tested relation
    # (that is what put the row here) -- they are edges of a DIFFERENT type, and when
    # that type is the opposite sign they are counter-evidence, not support.
    direct = ctx["edge_by_pair"].get(tuple(sorted([h_id, t_id])), [])
    for de in direct:
        annotate_edge_meta(de)
        de["strength"] = edge_strength(de)
    contradicting = direct if row.get("kg_sign_conflict") else []

    return {
        "head": h_id, "head_name": row.get("head_name", ""), "head_label": ht,
        "rel": row["rel"],
        "tail": t_id, "tail_name": row.get("tail_name", ""), "tail_label": tt,
        "score": row["score"], "cutoff": row.get("cutoff"), "margin": margin,
        "decision": row["decision"], "in_KG": row["in_KG"],

        "kg_any_edge": row.get("kg_any_edge", False),
        "kg_sign_conflict": row.get("kg_sign_conflict", False),
        "kg_rel_types": row.get("kg_rel_types", []),
        "kg_rel_type": row.get("kg_rel_type"),
        "variant_scores": row.get("variant_scores"),

        "connecting_paths": paths,
        "n_paths": len(paths),
        "shared_neighbours": shared_neighbours_inmemory(
            h_id, t_id, ctx["adj"], ctx["id_to_name"]),

        "other_relation_edges": direct,
        "n_other_relation_edges": len(direct),
        "contradicting_edges": contradicting,
        "n_contradicting_edges": len(contradicting),

        "conservation": _conservation_for(ht, h_id, tt, t_id, ctx["node_props"]),
        "path_source": "inmemory",
    }


def score_connectors_sparse(evidence_bucket2):
    """Shared neighbours over the FULL KG via sparse matmul, weighted by Adamic-Adar.

    Neo4j traversal does not scale on this graph's hubs -- this replaces it. A_Q is
    built per request from the shared, read-only edge arrays."""
    if not evidence_bucket2:
        return

    G = _get_graph()
    heads, tails, rels, deg = G["heads"], G["tails"], G["rels"], G["deg"]
    n_nodes, ent_s2i, ent_i2s = G["n_nodes"], G["ent_s2i"], G["ent_i2s"]

    b2_ids = sorted({e["head"] for e in evidence_bucket2} |
                    {e["tail"] for e in evidence_bucket2})
    q_int, q_local, unmapped = [], {}, []
    for sid in b2_ids:
        idx = ent_s2i.get(sid)
        if idx is None:
            unmapped.append(sid)
            continue
        q_local[sid] = len(q_int)
        q_int.append(idx)
    q_int = np.array(q_int, dtype=np.int64)

    if len(q_int) == 0:
        for e in evidence_bucket2:
            e["path_source"] = "unmapped"
        return

    # O(1) membership test instead of np.isin
    local_of = np.full(n_nodes, -1, dtype=np.int64)
    local_of[q_int] = np.arange(len(q_int), dtype=np.int64)
    lh, lt = local_of[heads], local_of[tails]

    species_rel = G["species_rel"]
    ok = (rels != species_rel) if (species_rel is not None and rels is not None) \
        else np.ones(len(heads), dtype=bool)

    m_h = (lh >= 0) & ok
    m_t = (lt >= 0) & ok
    sp_rows = np.concatenate([lh[m_h], lt[m_t]])
    sp_cols = np.concatenate([tails[m_h], heads[m_t]])

    A_Q = csr_matrix((np.ones(len(sp_rows), dtype=np.float32), (sp_rows, sp_cols)),
                     shape=(len(q_int), n_nodes))
    A_Q.sum_duplicates()
    A_Q.data[:] = 1.0

    def _neigh(li):
        return A_Q.indices[A_Q.indptr[li]:A_Q.indptr[li + 1]]

    def _score(li, lj):
        common = np.intersect1d(_neigh(li), _neigh(lj), assume_unique=False)
        # An endpoint must never count as its own bridge. Bucket 2 now contains
        # SIGN_CONFLICT rows (head and tail directly adjacent) -- exactly where such
        # an artifact would inflate the score.
        common = common[(common != q_int[li]) & (common != q_int[lj])]
        if len(common) == 0:
            return None
        d = deg[common].astype(np.float64)
        keep = (d >= MIN_CONN_DEG) & (d <= HUB_CONN_DEG)
        spec_common, spec_d = common[keep], d[keep]
        aa = float((1.0 / np.log(spec_d)).sum()) if len(spec_d) else 0.0
        order = np.argsort(spec_d) if len(spec_d) else []
        return {
            "connectors_scored": [{"id": ent_i2s.get(int(spec_common[k]),
                                                     str(spec_common[k])),
                                   "degree": int(spec_d[k])} for k in order][:25],
            "aa_specific": round(aa, 4),
            "n_specific_connectors": int(len(spec_d)),
            "n_total_connectors": int(len(common)),
            "n_hub_connectors": int((d > HUB_CONN_DEG).sum()),
            "n_dangling_connectors": int((d < MIN_CONN_DEG).sum()),
        }

    def _jaccard(li, lj):
        a, b = set(_neigh(li).tolist()), set(_neigh(lj).tolist())
        return len(a & b) / max(len(a | b), 1)

    for e in evidence_bucket2:
        e["n_shared_neighbours"] = len(e.get("shared_neighbours", []))
        if e["head"] not in q_local or e["tail"] not in q_local:
            e["path_source"] = "unmapped"
            continue
        li, lj = q_local[e["head"]], q_local[e["tail"]]

        r = _score(li, lj)
        if r:
            e.update(r)

        if e.get("n_paths", 0) > 0:
            e["path_source"] = "inmemory"          # explicit paths through hypothesis entities
        elif r:
            e["path_source"] = "sparse_intersect"  # no path; shared neighbours from full KG
        else:
            e["path_source"] = "none"

        # near-duplicate entities (isomers, paralogs) share almost all neighbours --
        # they score high but are not novel findings. Flag, don't silently drop.
        j = _jaccard(li, lj)
        e["neighbour_jaccard"] = round(j, 3)
        e["likely_duplicate"] = j > 0.7


# =============================================================================
# 5 · EVIDENCE RECORDS + FOUR DECORRELATED VIEWS + SWARM
# =============================================================================

def make_records(buckets, evidence_bucket1, evidence_bucket2, ctx) -> List[dict]:
    recs: List[dict] = []

    def add(e, bucket, stance):
        eid = f"E{len(recs)+1:03d}"

        # for bucket 1/4, build_evidence() returns only SIGN-MATCHING edges, so these
        # sources back THIS relation, not merely "some edge between the pair".
        srcs = sorted({s for de in e.get("direct_edges", [])
                       for s in de.get("sources", [])})
        n_src = max((len(de.get("sources", [])) for de in e.get("direct_edges", [])),
                    default=0)
        n_edges = e.get("n_direct_edges", len(e.get("direct_edges", [])))

        strength = e.get("max_edge_strength")
        aa_spec = e.get("aa_specific")
        n_spec = e.get("n_specific_connectors")

        conflict = bool(e.get("kg_sign_conflict", False))
        contra = e.get("contradicting_edges", []) or e.get("other_sign_edges", []) or []
        contra_src = sorted({s for de in contra for s in de.get("sources", [])})
        n_contra_src = max((len(de.get("sources", [])) for de in contra), default=0)

        # honest tag of how much graph evidence exists -- NOT a validity ladder
        if conflict:
            # the graph is not silent here: it holds the OPPOSITE direction. Must be
            # checked FIRST, or this lands in prediction_no_graph_support ("no signal"),
            # which is the exact inverse of the truth.
            level = "prediction_contradicts_KG_sign"
        elif bucket.startswith("1") or bucket.startswith("4"):
            # gate on n_edges, NOT on `strength is not None`: max_edge_strength defaults
            # to 0.0, so that test never fires and a signed row with no sign-matching edge
            # would still be sold to the agents as curated, source-backed.
            level = "scored_in_KG" if n_edges > 0 else "in_KG_unscored"
        elif aa_spec and n_spec and n_spec >= 1:
            level = "scored_prediction_specific"
        elif e.get("n_total_connectors", 0) > 0 or e.get("n_paths", 0) > 0:
            level = "prediction_hub_only"
        else:
            level = "prediction_no_graph_support"

        if conflict and stance == "model_predicts_not_in_KG":
            stance = "model_contradicts_KG_sign"     # not a gap -- a disagreement

        recs.append({
            "eid": eid, "bucket": bucket, "stance": stance, "evidence_level": level,
            "head": e.get("head_name") or e.get("head"),
            "tail": e.get("tail_name") or e.get("tail"),
            "head_id": e.get("head"), "tail_id": e.get("tail"),
            "rel": e.get("rel"),
            "score": round(float(e.get("score", 0)), 4), "margin": e.get("margin"),
            # where this score sits against ALL ground-truth triples in the graph
            # (GLOBAL_SCORE_PERCENTILES_FILE) -- independent of relation, independent
            # of the accept/reject cutoff. Applies to every bucket alike (1/2/4/5);
            # a bucket-2/4 PREDICTED score in the p95+ bracket is a materially
            # stronger signal than one sitting at the p50 median.
            "score_percentile": score_percentile_label(e.get("score", 0)),
            "in_KG": e.get("in_KG"),

            "kg_any_edge": e.get("kg_any_edge", False),
            "kg_sign_conflict": conflict,
            "kg_rel_types": e.get("kg_rel_types", []),
            "contradicting_edges": contra,
            "n_contradicting_edges": len(contra),
            "contradicting_sources": contra_src,
            "n_contradicting_sources": n_contra_src,

            "variant_scores": e.get("variant_scores"),

            "direct_edges": e.get("direct_edges", []),
            "n_direct_edges": n_edges,
            "strength": strength, "n_sources_max": n_src, "sources": srcs,
            "aging": e.get("aging_supported", False),

            "connectors": e.get("connectors_scored", []),
            "aa_specific": aa_spec,
            "n_specific_connectors": n_spec,
            "n_hub_connectors": e.get("n_hub_connectors"),
            "n_total_connectors": e.get("n_total_connectors"),
            "n_paths": e.get("n_paths", 0),
            "path_source": e.get("path_source"),
            "likely_duplicate": e.get("likely_duplicate", False),

            "conservation": e.get("conservation", {}),
            "conserved_in": sorted({s for c in e.get("conservation", {}).values()
                                    for s in c.get("species_conserved", [])}),
        })

    for e in evidence_bucket1:
        add(e, "1_inKG_ACCEPT", "KG_and_model_agree")
    for e in evidence_bucket2:
        add(e, "2_pred_ACCEPT", "model_predicts_not_in_KG")
    for r in buckets.get("4_inKG_true_REJECT", []):
        add(build_evidence(r, ctx), "4_inKG_REJECT", "KG_yes_model_no")
    for r in buckets.get("5_SIGN_CONFLICT", []):
        add(build_evidence_bucket2(r, ctx), "5_SIGN_CONFLICT", "model_contradicts_KG_sign")

    return recs


def enrich_connector_names(records) -> Dict[str, Tuple[str, str]]:
    """One small Neo4j fetch -- NOT per-pair traversal."""
    conn_ids = sorted({c["id"] for r in records for c in r["connectors"]})
    conn_name = {}
    if not conn_ids:
        return conn_name
    try:
        for r in run_cypher(
            "MATCH (m) WHERE m.id IN $ids RETURN m.id AS id, m.name AS name, "
            "labels(m) AS lbls", ids=conn_ids
        ):
            conn_name[r["id"]] = (r["name"] or r["id"],
                                  (r["lbls"][0] if r["lbls"] else "?"))
    except Exception as ex:
        logger.warning("connector enrichment skipped: %s", ex)
    return conn_name


def _hop_key(rec: dict, entity_order_map: Dict[str, int]) -> Tuple[int, int]:
    ho = entity_order_map.get(str(rec.get("head_id")), 10_000)
    to = entity_order_map.get(str(rec.get("tail_id")), 10_000)
    return (ho, to) if ho <= to else (to, ho)


def group_records_by_hop(records: List[dict],
                         entity_order_map: Dict[str, int]) -> List[Tuple[str, List[dict]]]:
    """Group evidence rows by entity-pair ("link"), ordered the way the hypothesis
    presents them -- earliest-appearing entity first, and among ties, the pair
    whose two entities are closest together in the hypothesis (adjacent hops,
    e.g. "A interacts with B") before pairs further apart (e.g. "A ... disease").
    This is purely a VIEW-ordering concern: `records`/eids are untouched, so
    nothing downstream (csv stats, saved run files) needs to change."""
    groups: Dict[Tuple[int, int], Dict[str, Any]] = {}
    order: List[Tuple[int, int]] = []
    for r in records:
        key = _hop_key(r, entity_order_map)
        if key not in groups:
            groups[key] = {"records": [], "label": None}
            order.append(key)
        groups[key]["records"].append(r)
        if groups[key]["label"] is None:
            ho = entity_order_map.get(str(r.get("head_id")), 10_000)
            to = entity_order_map.get(str(r.get("tail_id")), 10_000)
            first, second = (r["head"], r["tail"]) if ho <= to else (r["tail"], r["head"])
            groups[key]["label"] = f"{first} <-> {second}"

    order.sort(key=lambda k: (k[0], k[1] - k[0], k[1]))
    return [(groups[k]["label"], groups[k]["records"]) for k in order]


def build_grouped_view(records: List[dict], entity_order_map: Dict[str, int], viewfn) -> str:
    """Same content as a flat viewfn join, just organised into LINK blocks in
    hypothesis order -- so the agent reads evidence for one entity-pair at a
    time instead of a bucket-quality-ordered stream with no relation to the
    hypothesis's actual chain of claims."""
    blocks = []
    for i, (label, group) in enumerate(group_records_by_hop(records, entity_order_map), 1):
        n = len(group)
        body = "\n".join(viewfn(r) for r in group)
        blocks.append(f"=== LINK {i}: {label} ({n} evidence row{'s' if n != 1 else ''}) ===\n"
                      f"{body if body else '(no evidence rows for this link)'}")
    return "\n\n".join(blocks)


def make_views(records, conn_name):
    def _cname(cid):
        n = conn_name.get(cid)
        return f"{n[0]} ({n[1]})" if n else str(cid)

    def _prefix(r):
        # shared by all four views -- score_pctl is where this triple's raw score
        # sits against ALL ground-truth triples in the graph (see
        # score_percentile_label), independent of relation and of accept/reject.
        return f"{r['eid']} [{r['evidence_level']}] [score_pctl:{r.get('score_percentile', 'NA')}]"

    def view_mechanism(r):
        parts = [f"edge:{de.get('relation_type')}" for de in r["direct_edges"]]

        # the curated edge carrying the OPPOSITE sign. The direction agent is exactly
        # the one that must see this: same pair, same biology, contrary direction.
        if r.get("kg_sign_conflict"):
            parts.append(f"KG_HOLDS_OPPOSITE:{r.get('kg_rel_types')}")
            for de in r.get("contradicting_edges", [])[:3]:
                parts.append(f"opposing_edge:{de.get('relation_type')}")

        if r.get("variant_scores"):
            best = max(r["variant_scores"], key=r["variant_scores"].get)
            bp = str(best).split("_")
            sign = bp[1] if len(bp) == 3 else best
            vs = sorted(r["variant_scores"].values(), reverse=True)
            gap = round(vs[0] - vs[1], 4) if len(vs) > 1 else None
            parts.append(f"model_favours:{sign}"
                         + (f" (margin_over_next:{gap})" if gap is not None else ""))

        if r["connectors"]:
            parts.append("bridges:[" + ", ".join(_cname(c["id"])
                                                 for c in r["connectors"][:6]) + "]")

        detail = "; ".join(parts) if parts else "NO_MECHANISTIC_DETAIL_FOUND"
        return (f"{_prefix(r)} {r['head']} --{r['rel']}--> "
                f"{r['tail']} | {detail}")

    def view_conservation(r):
        # deliberately sign-blind: orthology speaks to whether the biology is conserved,
        # never to the direction of effect. Leaking the conflict here would correlate
        # this view with mechanism/skeptic and defeat the point of separate views.
        return (f"{_prefix(r)} {r['head']} --{r['rel']}--> "
                f"{r['tail']} | conserved_in:{r['conserved_in'] or 'none/NA'}")

    def view_provenance(r):
        if r.get("kg_sign_conflict"):
            return (f"{_prefix(r)} {r['head']} --{r['rel']}--> "
                    f"{r['tail']} | CONTRADICTED_BY_KG holds:{r.get('kg_rel_types')} "
                    f"opposing_n_sources:{r.get('n_contradicting_sources', 0)} "
                    f"opposing_sources:{r.get('contradicting_sources', [])[:6]} "
                    f"model_score:{r['score']} "
                    f"aa_specific:{r['aa_specific'] if r['aa_specific'] is not None else 'none'} "
                    f"conserved:{r['conserved_in'] or 'NA'}")

        if r["evidence_level"].startswith("scored_in_KG") or \
                r["evidence_level"] == "in_KG_unscored":
            st = r["strength"] if r.get("n_direct_edges", 0) > 0 else "NO_MATCHING_EDGE"
            return (f"{_prefix(r)} {r['head']} --{r['rel']}--> "
                    f"{r['tail']} | IN_KG strength:{st} n_sources:{r['n_sources_max']} "
                    f"sources:{r['sources'][:6]} aging:{r['aging']} "
                    f"model_score:{r['score']} conserved:{r['conserved_in'] or 'NA'}")

        aa = r["aa_specific"] if r["aa_specific"] is not None else "none"
        return (f"{_prefix(r)} {r['head']} --{r['rel']}--> "
                f"{r['tail']} | PREDICTED aa_specific:{aa} "
                f"n_specific_conn:{r['n_specific_connectors'] or 0} "
                f"n_hub_conn:{r['n_hub_connectors'] or 0} model_score:{r['score']}")

    def view_skeptic(r):
        flags = []
        if r.get("kg_sign_conflict"):
            flags.append(f"MODEL_PREDICTS_OPPOSITE_SIGN_TO_KG(holds:{r.get('kg_rel_types')},"
                         f"opposing_n_sources:{r.get('n_contradicting_sources', 0)})")
        if r["in_KG"] and r.get("n_direct_edges", 0) == 0:
            flags.append("IN_KG_BUT_NO_MATCHING_EDGE")
        vs = r.get("variant_scores") or {}
        if len(vs) > 1:
            s = sorted(vs.values(), reverse=True)
            if (s[0] - s[1]) < 0.05:
                flags.append(f"SIGN_CALL_IS_A_COIN_FLIP(margin:{round(s[0]-s[1], 4)})")
        if r["likely_duplicate"]:
            flags.append("NEAR_DUPLICATE_ENTITIES")
        if r["evidence_level"] == "prediction_no_graph_support":
            flags.append("NO_GRAPH_SUPPORT")
        if r["evidence_level"] == "prediction_hub_only":
            flags.append("BROAD_SUPPORT_ONLY")
        if r["in_KG"] and r["n_sources_max"] <= 1:
            flags.append("SINGLE_SOURCE_EDGE")
        if r["stance"] == "KG_yes_model_no":
            flags.append("MODEL_REJECTS_KG_EDGE")
        return (f"{_prefix(r)} {r['head']} --{r['rel']}--> "
                f"{r['tail']} | flags:{flags or ['none']}")

    return {
        "mechanism": view_mechanism,
        "conservation": view_conservation,
        # agent roster renamed provenance->interaction, skeptic->critic; reusing
        # the same underlying view content (rich per-edge stats / red-flags) --
        # only the AGENT_SPECS keys and prompts changed, not what's shown here.
        "interaction": view_provenance,
        "critic": view_skeptic,
    }


def _log_agent_failure(name: str, result: dict) -> None:
    if "_parse_error" in result:
        raw = result.get("raw_text", "")
        # log the TAIL, not the head -- a truncated-by-max_tokens JSON object is
        # well-formed up to the cutoff, so the head is uninformative; the cutoff
        # itself only shows in the last chars. raw_text_len (present since the
        # medgemma path stores the tail slice, not the whole string) flags a
        # token-cap truncation directly if it lands suspiciously close to the
        # max_tokens value passed for that call.
        logger.warning("  %s: parse error (%s); raw_text_len=%s; end of raw model output: %.1000s",
                       name, result["_parse_error"], result.get("raw_text_len", len(raw)), raw[-1000:])
    else:
        logger.warning("  %s: call error: %s", name, result.get("_error"))


def _merge_agent_results(results: List[dict]) -> dict:
    """Schema-agnostic merge of N successful chunk results into one finding.
    List fields (key_points, caveats, objections, ... -- whatever the agent's
    schema has) are concatenated. 'stance' is kept only if every chunk agreed;
    otherwise 'mixed' -- an honest signal that the evidence didn't converge
    cleanly once split, rather than arbitrarily picking one chunk's opinion."""
    all_keys = set()
    for r in results:
        all_keys.update(r.keys())

    merged: Dict[str, Any] = {}
    for key in all_keys:
        values = [r.get(key) for r in results if key in r]
        if key == "stance":
            stances = [v for v in values if v]
            merged[key] = stances[0] if len(set(stances)) == 1 else "mixed"
        elif all(isinstance(v, list) for v in values):
            combined = []
            for v in values:
                combined.extend(v)
            merged[key] = combined
        else:
            merged[key] = next((v for v in values if v), values[0] if values else None)
    return merged


def _run_agent_split(name: str, prompt: str, schema, hypothesis: str,
                     records: List[dict], viewfn, entity_order_map: Dict[str, int],
                     n_chunks: int = 3) -> dict:
    """Retry a failed agent with its evidence split into smaller chunks -- each
    chunk is a separate call with the SAME prompt, only a slice of the evidence.
    Mitigates truncation/parse failures on large evidence payloads. A chunk that
    also fails is dropped (logged), not fatal; only failing on every chunk is.
    Each chunk still gets the LINK grouping/ordering, just over a subset of rows."""
    n_chunks = max(1, min(n_chunks, len(records)))
    chunk_size = -(-len(records) // n_chunks)  # ceiling division, no extra import
    chunks = [records[i:i + chunk_size] for i in range(0, len(records), chunk_size)]

    chunk_results = []
    for i, chunk in enumerate(chunks):
        chunk_view = build_grouped_view(chunk, entity_order_map, viewfn)
        chunk_payload = (f"HYPOTHESIS:\n{hypothesis}\n\n"
                         f"EVIDENCE ({name} view, PART {i + 1}/{len(chunks)} -- "
                         f"only some evidence records, not all):\n{chunk_view}")
        logger.info("%s agent chunk %d/%d: payload %d chars (%d records)",
                   name, i + 1, len(chunks), len(chunk_payload), len(chunk))
        r = _gemini(prompt, chunk_payload, schema=schema)
        if "_error" in r or "_parse_error" in r:
            logger.warning("%s agent chunk %d/%d also failed:", name, i + 1, len(chunks))
            _log_agent_failure(name, r)
            continue
        logger.info("%s agent chunk %d/%d succeeded", name, i + 1, len(chunks))
        chunk_results.append(r)

    if not chunk_results:
        logger.warning("%s agent failed on every chunk -- giving up", name)
        return {"_error": f"{name} failed on full evidence and on every split chunk"}

    return _merge_agent_results(chunk_results)


def run_swarm(hypothesis: str, records: List[dict], conn_name,
             entity_order_map: Dict[str, int]) -> Tuple[dict, dict]:
    views = make_views(records, conn_name)

    findings = {}
    for name, prompt, schema in AGENT_SPECS:
        view_text = build_grouped_view(records, entity_order_map, views[name])
        payload = f"HYPOTHESIS:\n{hypothesis}\n\nEVIDENCE ({name} view):\n{view_text}"
        logger.info("%s agent: payload %d chars (%d records)", name, len(payload), len(records))
        result = _gemini(prompt, payload, schema=schema)

        if "_error" in result or "_parse_error" in result:
            logger.warning("%s agent failed on full evidence (%d records):", name, len(records))
            _log_agent_failure(name, result)
            logger.warning("retrying %s with evidence split into 3 chunks", name)
            result = _run_agent_split(name, prompt, schema, hypothesis, records, views[name],
                                      entity_order_map)

        findings[name] = result

    failed = [n for n, f in findings.items() if "_error" in f or "_parse_error" in f]
    if failed:
        logger.warning("agents failed even after split-retry: %s -- verdict is unreliable", failed)

    # drop failed agents before the judge sees them -- one bad/malformed agent
    # output shouldn't poison the judge's input with an "_error" entry it has no
    # instructions for handling.
    clean_findings = {n: f for n, f in findings.items() if n not in failed}

    judge_payload = (f"HYPOTHESIS:\n{hypothesis}\n\n"
                     f"EXPERT FINDINGS:\n{json.dumps(clean_findings, indent=2, default=str)}\n\n"
                     f"EVIDENCE INDEX:\n"
                     f"{build_grouped_view(records, entity_order_map, views['interaction'])}")
    logger.info("judge: payload %d chars (%d clean findings, %d records)",
               len(judge_payload), len(clean_findings), len(records))
    # The judge's Return schema is the richest of any call in the swarm (verdict,
    # a ~200-word answer, supporting_evidence, caveats_and_gaps,
    # expert_disagreements, direction_check, one link_summary entry PER LINK) --
    # on a hypothesis with many links this routinely needs more than the
    # 3072-token default, and MedGemma/vLLM silently truncates generation at the
    # token cap rather than erroring. Two failure modes from the same root
    # cause: full truncation -> unterminated JSON -> parse failure (handled
    # below); or, under schema-guided decoding, the model stays within budget by
    # emitting valid-but-empty trailing arrays -- which is why the prompt above
    # now puts supporting_evidence/caveats_and_gaps BEFORE the audit-only
    # direction_check/link_summary fields, so they're filled first regardless of
    # whether the budget runs out. Only affects the MedGemma path; Gemini
    # ignores max_tokens.
    verdict = _gemini(JUDGE_PROMPT, judge_payload, schema=JudgeOut, max_tokens=8192)
    if "_error" in verdict or "_parse_error" in verdict:
        logger.warning("judge call failed:")
        _log_agent_failure("judge", verdict)
    return verdict, findings


def append_run_stats_csv(run_id, hypothesis, terms, per_type_limit,
                         results, union_raw, union_entities, filt,
                         triples, rows_collapsed, counts) -> dict:
    """One row per run, appended to STATS_CSV_PATH -- mirrors the notebook's 3.6
    RUN SUMMARY cell so the same downstream stats/figures work unchanged."""
    n_terms_unresolved = sum(
        1 for v in results.values()
        if isinstance(v, dict) and (v.get("error") or not v.get("entities")))
    n_triples_signed = sum(1 for t in triples if t.get("is_signed"))

    b = {k: int(counts.get(k, 0)) for k in BUCKET_KEYS}
    n_accept = b["1_inKG_true_ACCEPT"] + b["2_inKG_false_ACCEPT"]
    n_reject = b["3_inKG_false_REJECT"] + b["4_inKG_true_REJECT"]

    row = {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "hypothesis": hypothesis.strip().replace("\n", " "),
        "per_type_limit": per_type_limit,

        "n_input_terms": len(terms),
        "n_terms_unresolved": n_terms_unresolved,
        "n_kg_entities_raw": len(union_raw),
        "n_kg_entities_filtered": len(union_entities),
        "n_filter_dropped": len(filt.get("dropped", [])),

        "n_triples_raw": len(triples),
        "n_triples_signed": n_triples_signed,
        "n_rows_collapsed": len(rows_collapsed),

        "b1_inKG_ACCEPT": b["1_inKG_true_ACCEPT"],
        "b2_novel_ACCEPT": b["2_inKG_false_ACCEPT"],
        "b3_inKG_false_REJECT": b["3_inKG_false_REJECT"],
        "b4_inKG_true_REJECT": b["4_inKG_true_REJECT"],
        "b5_sign_conflict": b["5_SIGN_CONFLICT"],
        "b6_check_failed": b["6_CHECK_FAILED"],
        "n_accept_total": n_accept,
        "n_reject_total": n_reject,
    }

    write_header = not STATS_CSV_PATH.exists()
    with open(STATS_CSV_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(row.keys()))
        if write_header:
            w.writeheader()
        w.writerow(row)
    return row


def format_verdict_text(verdict: dict, stats: dict, run_id: str) -> str:
    """Plain-text rendering of the verdict for the API caller -- resolved evidence
    TEXT only, never a bare eid. eids stay in the saved run files, not here.
    run_id is printed first, unconditionally, so it's never dependent on the
    caller (frontend LLM, batch script, ...) remembering to surface the separate
    `run_id` JSON field itself."""
    lines = [
        f"RUN ID: {run_id}",
        f"VERDICT: {verdict.get('verdict', '?')}",
        "",
        "THE BIG PICTURE: STATISTICAL OVERVIEW",
        f"  Entities analysed: {stats['total_entities_used']}",
        f"  Triples analysed: {stats['total_triples_analyzed']} total",
        f"    - Known & Accepted (confirmed):          {stats['bucket_1_known_and_supported']}",
        f"    - New & Accepted (predicted):            {stats['bucket_2_novel_predicted']}",
        f"    - New & Rejected (filtered out):         {stats['bucket_3_not_in_kg_rejected']}",
        f"    - Known & Rejected (model disagrees):    {stats['bucket_4_known_but_model_dissents']}",
        "",
        "ANSWER:",
        f" {eids_to_count(verdict.get('answer', ''))}",
        "",
        "SUPPORTING EVIDENCE:",
    ]
    for p in verdict.get("supporting_evidence", []):
        lines.append(f"  * {eids_to_count(p.get('point', ''))}")
        for e in p.get("evidence", []):
            lines.append(f"      - {e.get('text', '')}")

    lines += ["", "CAVEATS / GAPS:"]
    for c in verdict.get("caveats_and_gaps", []):
        lines.append(f"  * {eids_to_count(c)}")

    lines += ["", "EXPERT DISAGREEMENTS:"]
    disagreements = verdict.get("expert_disagreements", [])
    if disagreements:
        for d in disagreements:
            lines.append(f"  * {eids_to_count(d)}")
    else:
        lines.append("  (none)")

    return "\n".join(lines)


# =============================================================================
# ROUTE
# =============================================================================

@router.post("/run_hypothesis_pipeline",
             summary="Search -> filter -> signed triples -> score -> evidence -> swarm")
def run_hypothesis_pipeline(
    hypothesis: str = Body(..., embed=True, description="User Hypothesis"),
    entities_input: List[EntityMention] = Body(
        ..., embed=True,
        description="[{'mention':'BACE1','types':['Gene','Protein']}, ...] -- entities "
                    "as extracted from the hypothesis, IN THE ORDER they appear there. "
                    "`types` hard-filters which KG label(s) each mention may resolve to; "
                    "pass [] for a mention to keep every type the search returns."),
    per_type_limit: int = Body(5, embed=True,
                               description="SBE hits kept per entity type per term"),
) -> Dict[str, Any]:

    mentions = [{"mention": e.mention.strip(), "types": e.types}
               for e in entities_input if e.mention and e.mention.strip()]
    if not mentions:
        raise HTTPException(status_code=400, detail="No entity mentions provided.")
    terms = [m["mention"] for m in mentions]   # mention strings, hypothesis order
    if not hypothesis or not hypothesis.strip():
        # Every swarm agent + judge prompt starts with "HYPOTHESIS:\n{hypothesis}".
        # A blank hypothesis doesn't error anywhere downstream -- it just makes
        # every verdict meaningless. Reject it here instead of silently proceeding,
        # regardless of which caller (frontend, Swagger, script) sends it.
        raise HTTPException(status_code=400, detail="hypothesis must not be empty.")

    run_id = uuid.uuid4().hex
    t_start = time.time()
    timings: Dict[str, float] = {}

    def _t(label, fn, *a, **kw):
        t0 = time.time()
        out = fn(*a, **kw)
        timings[label] = round(time.time() - t0, 2)
        return out

    logger.info("[%s] hypothesis: %s | mentions: %s", run_id[:8], hypothesis[:120], mentions)

    # ---- 1. search (seed mentions only -- no LLM expansion), type-constrained per mention
    try:
        results = _t("search", _search_terms, mentions, per_type_limit)
    except Exception as e:
        logger.exception("search failed")
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")

    unresolved = [t for t, v in results.items()
                  if isinstance(v, dict) and v.get("error")]
    union_raw = _collect_union_entities(results)
    if not union_raw:
        raise HTTPException(
            status_code=404,
            detail="No entities from this hypothesis could be resolved to EvoAge nodes.")

    # ---- 2. LLM entity filter (fails open)
    filt = _t("entity_filter", filter_entities_llm, hypothesis, results, union_raw)
    union_entities = filt["kept_union_entities"]
    logger.info("[%s] union: %d raw -> %d filtered (kept %d, dropped %d)",
                run_id[:8], len(union_raw), len(union_entities),
                len(filt["kept"]), len(filt["dropped"]))

    # id -> position of the term (in hypothesis/frontend order) that surfaced this
    # entity. Drives the swarm's LINK grouping/ordering later -- see run_swarm.
    entity_order_map = {str(e["id"]): e.get("term_order", 10_000) for e in union_entities}

    # ---- 3. triples + score + collapse
    triples = _t("build_triples", _make_all_triples_strict, union_entities)
    if not triples:
        raise HTTPException(status_code=422,
                            detail="No valid relation type-pairs among the resolved entities.")

    try:
        scored_rows = _t("score_rescal", _enrich_with_scores, triples)
    except Exception as e:
        logger.exception("scoring failed")
        raise HTTPException(status_code=500, detail=f"Scoring failed: {e}")

    rows_collapsed, collapse_log = _t("collapse_signs", collapse_signed_variants, scored_rows)

    # ---- 4. sign-aware KG check + buckets
    buckets, type_index, counts = _t("kg_check", attach_kg_state, rows_collapsed, triples)
    logger.info("[%s] buckets: %s", run_id[:8], counts)

    # ---- 5. evidence
    sg = _t("subgraph", build_subgraph, union_entities)
    ctx = {**sg, "type_index": type_index}

    evidence_b1 = [build_evidence(r, ctx) for r in buckets["1_inKG_true_ACCEPT"]]
    evidence_b1.sort(key=lambda e: (e["aging_supported"], e["max_edge_strength"]),
                     reverse=True)

    evidence_b2 = [build_evidence_bucket2(r, ctx) for r in buckets["2_inKG_false_ACCEPT"]]
    _t("sparse_connectors", score_connectors_sparse, evidence_b2)

    # a bucket-1 row asserting a sign but with NO sign-matching edge means the Neo4j
    # type(r) names and the relation dict have drifted -- the agents would be told
    # "curated + source-backed" about nothing.
    orphan = [e for e in evidence_b1
              if len(e["rel"].split("_")) == 3 and e["n_direct_edges"] == 0]
    if orphan:
        logger.warning("[%s] %d signed bucket-1 rows have NO sign-matching edge "
                       "(Neo4j type(r) vs relation dict naming drift?)",
                       run_id[:8], len(orphan))

    records = make_records(buckets, evidence_b1, evidence_b2, ctx)
    conn_name = _t("connector_names", enrich_connector_names, records)

    # attach resolved name/label onto each connector -- callers otherwise only see
    # the raw Neo4j id. Falls back to the id itself when no name is on the node.
    for r in records:
        for c in r["connectors"]:
            resolved = conn_name.get(c["id"])
            c["name"] = resolved[0] if resolved else c["id"]
            c["label"] = resolved[1] if resolved else "?"
    logger.info("[%s] records: %d | levels: %s", run_id[:8], len(records),
                dict(Counter(r["evidence_level"] for r in records)))

    # ---- 6. swarm + judge
    verdict, findings = _t("swarm", run_swarm, hypothesis, records, conn_name, entity_order_map)

    if "_error" in verdict or "_parse_error" in verdict:
        # Everything up to here (search, filter, triples, RESCAL scoring, evidence,
        # all 4 agent findings) already succeeded -- only the final judge synthesis
        # call failed. Raising here used to throw all of that away and hand the
        # caller nothing but a bare 503. Return a real (flagged) response instead,
        # so run_id/stats/agent findings are still usable, and the run is still
        # saved below like any other run.
        logger.warning("[%s] judge call failed: %s", run_id[:8],
                       verdict.get("_error") or verdict.get("_parse_error"))
        verdict = {
            "verdict": "unknown",
            "answer": "The judge model failed to synthesize a final verdict for this "
                     "run. This is a technical failure, not a scientific conclusion -- "
                     "the evidence pipeline itself completed successfully; only the "
                     "final synthesis step did not. Look up this run_id in the saved "
                     "run files for the raw per-agent findings.",
            "supporting_evidence": [],
            "caveats_and_gaps": ["Judge synthesis failed -- see run_id above."],
            "expert_disagreements": [],
        }

    eid_map = {r["eid"]: r for r in records}

    def _eid_text(eid):
        r = eid_map.get(eid)
        return (f"{r['head']} -> {r['rel'].replace('_', ' ')} -> {r['tail']}"
                if r else eid)

    # resolve cited eids to readable biology so the frontend never shows a bare "E007"
    for p in verdict.get("supporting_evidence", []):
        p["evidence"] = [{"eid": e, "text": _eid_text(e)} for e in p.get("eids", [])[:5]]

    timings["total"] = round(time.time() - t_start, 2)
    logger.info("[%s] done in %.1fs -- %s", run_id[:8], timings["total"], timings)

    # everything -- this is what gets saved to disk, NOT what the caller gets back.
    full_data = {
        "run_id": run_id,
        "hypothesis": hypothesis,
        "terms": terms,
        "entities_input": mentions,
        "unresolved_terms": unresolved,

        "verdict": verdict,
        "agent_findings": findings,
        "agent_stances": {n: f.get("stance", "?") for n, f in findings.items()},

        "entityUnionCount": len(union_entities),
        "entityUnionCountRaw": len(union_raw),
        "tripleCount": len(triples),
        "collapsedRowCount": len(rows_collapsed),
        "categoryCounts": counts,

        "entity_filter": {
            "kept": filt["kept"],
            "dropped": filt["dropped"],
            "failed": filt.get("filter_failed", False),
        },
        "collapse_log": collapse_log[:20],
        "records": records,
        "timings": timings,
    }

    try:
        run_dir = RUNS_DIR / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        with open(run_dir / "response.json", "w", encoding="utf-8") as f:
            json.dump(full_data, f, indent=2, default=str)
        pd.DataFrame(rows_collapsed).to_csv(run_dir / "triples.csv", index=False)

        # the evidence pool actually fed to the swarm, plus what each agent/judge
        # said -- a self-contained audit file, not buried inside the full response.
        with open(run_dir / "evidence_records.json", "w", encoding="utf-8") as f:
            json.dump({
                "run_id": run_id, "hypothesis": hypothesis,
                "records": records, "agent_findings": findings, "verdict": verdict,
            }, f, indent=2, default=str)

        append_run_stats_csv(run_id, hypothesis, terms, per_type_limit,
                             results, union_raw, union_entities, filt,
                             triples, rows_collapsed, counts)
    except Exception:
        logger.exception("failed saving hypothesis outputs")

    # what the caller (frontend) actually gets -- verdict + confidence + a plain-
    # text answer (NO eids anywhere, resolved evidence text only) + the full
    # triage breakdown (all 4 buckets, including bucket 3 -- not in KG, model
    # also rejects -- which never reaches the swarm but is still part of the
    # honest count of what was analyzed). agent_findings and the raw eid-bearing
    # verdict are NOT returned here -- they are still saved in full in
    # run_dir/evidence_records.json for anyone who needs to audit a specific run.
    b1 = counts.get("1_inKG_true_ACCEPT", 0)
    b2 = counts.get("2_inKG_false_ACCEPT", 0)
    b3 = counts.get("3_inKG_false_REJECT", 0)
    b4 = counts.get("4_inKG_true_REJECT", 0)
    statistical_overview = {
        "total_entities_used": len(union_entities),
        "total_triples_analyzed": b1 + b2 + b3 + b4,
        "bucket_1_known_and_supported": b1,
        "bucket_2_novel_predicted": b2,
        "bucket_3_not_in_kg_rejected": b3,
        "bucket_4_known_but_model_dissents": b4,
    }
    return {
        "run_id": run_id,
        "hypothesis": hypothesis,
        "statistical_overview": statistical_overview,
        "verdict": verdict.get("verdict"),
        "formatted_answer": format_verdict_text(verdict, statistical_overview, run_id),
    }