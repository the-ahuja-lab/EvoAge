import pandas as pd
import uuid
import os
import time
import logging
from pathlib import Path

os.environ["CUDA_LAUNCH_BLOCKING"] = "0"

from app.utils.environment import CONFIG
from fastapi import APIRouter, HTTPException, Query

# DGL-KE imports
from dglke.utils import load_model_config, load_raw_triplet_data
from dglke.models.infer import ScoreInfer



logger = logging.getLogger("main_server_kge")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

from app.utils.schema import (
    PredictionRankResponse,
    PredictionResponse,
    PredictionResult,
)

router = APIRouter()

# DGL configuration paths from .env
NODE_MAPPINGS_PATH = CONFIG.DGLCONFIG.NODE_MAPPINGS_PATH
MODEL_PATH         = CONFIG.DGLCONFIG.MODEL_PATH
ENT_DICT_PATH      = CONFIG.DGLCONFIG.ENT_DICT_PATH
REL_DICT_PATH      = CONFIG.DGLCONFIG.REL_DICT_PATH
INPUT_DIR          = CONFIG.DGLCONFIG.DGLKE_INPUT_DIR
DUMMY_HEAD         = CONFIG.DGLCONFIG.DGLKE_DUMMY_HEAD_LIST
DUMMY_REL          = CONFIG.DGLCONFIG.DGLKE_DUMMY_REL_LIST

DEVICE             = CONFIG.DGLCONFIG.DGLKE_DEVICE
SFUNC              = CONFIG.DGLCONFIG.DGLKE_SFUNC

# validate once, fail with clear messages
def _as_path(value, name: str) -> Path:
    if value is None or (isinstance(value, str) and value.strip() == ""):
        raise RuntimeError(f"{name} is not set (empty/None).")
    try:
        return value if isinstance(value, Path) else Path(value)
    except TypeError:
        raise RuntimeError(f"{name} must be path-like, got {type(value).__name__}.")
    
# Normalize everything to Path objects
MODEL_PATH        = _as_path(MODEL_PATH, "MODEL_PATH")
ENT_DICT_PATH     = _as_path(ENT_DICT_PATH, "ENT_DICT_PATH")
REL_DICT_PATH     = _as_path(REL_DICT_PATH, "REL_DICT_PATH")
NODE_MAPPINGS_PATH= _as_path(NODE_MAPPINGS_PATH, "NODE_MAPPINGS_PATH")
DUMMY_HEAD        = _as_path(DUMMY_HEAD, "DUMMY_HEAD")        # <-- only keep as Path if it’s a file path
DUMMY_REL         = _as_path(DUMMY_REL, "DUMMY_REL")          # <-- only keep as Path if it’s a file path

# validate once, fail with clear messages
errors = []

# MODEL_PATH must exist and be a directory
if not MODEL_PATH.exists():
    errors.append(f"MODEL_PATH missing: {MODEL_PATH}")
elif not MODEL_PATH.is_dir():
    errors.append(f"MODEL_PATH not a directory: {MODEL_PATH}")

cfg = MODEL_PATH / "config.json"
if not cfg.is_file():
    errors.append(f"Missing config.json at {cfg}")

for name, p in [
    ("ENT_DICT_PATH", ENT_DICT_PATH),
    ("REL_DICT_PATH", REL_DICT_PATH),
    ("NODE_MAPPINGS_PATH", NODE_MAPPINGS_PATH),
    ("DUMMY_HEAD", DUMMY_HEAD),
    ("DUMMY_REL", DUMMY_REL),
]:
    if not p.is_file():
        errors.append(f"{name} not a file: {p}")

if errors:
    raise FileNotFoundError(" | ".join(errors))


def predict_tails_dglke(k=10, head_list_path=None, rel_list_path=None):
    """
    k                 : number of top predictions to return
    head_list_path    : path to your head.list file
    rel_list_path     : path to your rel.list file

    Returns:
      results : list of (head_str, rel_str, tail_str, score)
      elapsed : total time in seconds for loading and inference
    """
    logger.info(
        "predict_tails called: k=%s, head_list_path=%s, rel_list_path=%s",
        k, head_list_path, rel_list_path
    )
    start_time = time.time()

    # 2) load this call’s head & rel
    head_ids, rel_ids, tail_ids, id2ent, id2rel = load_raw_triplet_data(
        head_f=head_list_path,
        rel_f=rel_list_path,
        tail_f=None,
        emap_f=ENT_DICT_PATH,
        rmap_f=REL_DICT_PATH
    )
    logger.info("Loaded %d heads and %d relations in %.3f seconds", len(head_ids), len(rel_ids), (time.time() - start_time))

    # 3) run inference
    logger.info("Running infer.topK(exec_mode='batch_head', k=%d)", k)
    raw_results = infer.topK(
        head=head_ids,
        rel=rel_ids,
        tail=tail_ids,
        exec_mode="batch_head",
        k=k
    )

    # 4) map back to strings
    output = [
        (id2ent[h], id2rel[r], id2ent[t], float(s))
        for h_arr, r_arr, t_arr, s_arr in raw_results
        for h, r, t, s in zip(h_arr, r_arr, t_arr, s_arr)
    ]

    elapsed = time.time() - start_time
    logger.info("Inference completed in %.3f seconds, returning %d results", elapsed, len(output))
    return output, elapsed

def predict_rank_dglke(
    head_list_path: str,
    rel_list_path: str,
    user_set_tail_list_path: str,
):
    """
    Load the single head, single rel, and single target tail from the given files,
    call infer.get_rank_score(..., exec_mode='batch_head'), and return
    (rank, score, max_score, elapsed_seconds).
    """
    logger.info(
        "predict_rank_dglke called: head_list_path=%s, rel_list_path=%s, user_set_tail_list_path=%s",
        head_list_path, rel_list_path, user_set_tail_list_path
    )
    start_time = time.time()
    head_ids, rel_ids, tail_ids, id2ent, id2rel = load_raw_triplet_data(
        head_f=head_list_path,
        rel_f=rel_list_path,
        tail_f=user_set_tail_list_path,
        emap_f=ENT_DICT_PATH,
        rmap_f=REL_DICT_PATH,
    )
    logger.info("Loaded %d heads, %d relations, and %d user_set_tails in %.3f seconds", len(head_ids), len(rel_ids), len(tail_ids), (time.time() - start_time))

    logger.info("Running infer.get_rank_score(exec_mode='batch_head')")
    # get_rank_score expects lists of length 1 for head_ids, rel_ids, tail_ids
    rank, user_score, max_score = infer.get_rank_score(
        head=head_ids,
        rel=rel_ids,
        user_set_tail=tail_ids,
        exec_mode="batch_head",
    )
    elapsed = time.time() - start_time
    logger.info("Cal. completed in %.3f seconds", elapsed)
    return rank, user_score, max_score, elapsed

# ─── LOAD THE CONFIG & MODEL ONCE ─────────────────────────────────────────
config_json = os.path.join(MODEL_PATH, "config.json")
# Attempt to load config
try:
    logger.info("Loading DGL-KE model configuration from %s", config_json)
    config = load_model_config(config_json)
except Exception as e:
    raise RuntimeError(f"Failed to load model config: {e!s}")

try:
    logger.info(f"Initializing ScoreInfer on device {DEVICE}")
    infer = ScoreInfer(
        device=DEVICE,
        config=config,
        model_path=MODEL_PATH,
        sfunc=SFUNC
    )
    logger.info("Starting model.load_model() (this may take a while)")
    infer.load_model()
except Exception as e:
        logger.warning("Loading on GPU failed: %s", str(e))
        raise RuntimeError(f"Cannot initialize inference model: {e!s}")

logger.info("Inference service starting up… warming up DGL-KE model on GPU")
try:
    # One tiny predict call to force the first GPU / JIT warm‑up
    dummy_head = DUMMY_HEAD
    dummy_rel = DUMMY_REL

    _ , _ = predict_tails_dglke(k=1,
        head_list_path=dummy_head,
        rel_list_path=dummy_rel)

    logger.info("Model warm‑up complete; ready to receive requests")
except Exception as e:
    logger.error("Model warm‑up failed: %s", str(e), exc_info=True)
    raise HTTPException(status_code=404, detail=f"Model warm‑up failed: {str(e)}")

logger.info("Model successfully loaded into GPU memory")

# Load the mappings for the entities and relations
try:
    node_mappings = pd.read_pickle(NODE_MAPPINGS_PATH)
except FileNotFoundError:
    raise Exception(
        f"Node mappings file not found. Please ensure {NODE_MAPPINGS_PATH} exists in the app/data directory.",
    )
except Exception as e:
    raise Exception(f"Error loading node mappings: {e!s}")


@router.get(
    "/predict_tail",
    tags=["KGE Predictions"],
    response_model=PredictionResponse,
    description="Predict the top K tail entities given head and relation via embedded DGL-KE model",
    summary="Get top-K tail predictions for a given head and relation",
    operation_id="predict_tail",
)
def predict_tail(
    head: str = Query(..., description="model_id for the head entity"),
    relation: str = Query(..., description="Relation for the prediction"),
    top_k_predictions: int = Query(10, description="Number of top predictions to return"),
):  
    os.makedirs(INPUT_DIR, exist_ok=True)

    unique_id = uuid.uuid4().hex
    head_file = os.path.join(INPUT_DIR, f"head_{unique_id}.list")
    rel_file = os.path.join(INPUT_DIR, f"rel_{unique_id}.list")
    try:
        # Map ID → node name
        mapped = node_mappings.loc[node_mappings["MappedID"] == int(head)]
        if mapped.empty:
            raise HTTPException(status_code=404, detail=f"No head found for ID {head}")
        head_str = mapped["Node"].iat[0]

        # Normalize relation
        rel_norm = relation.lower()

        # write head and relation files
        with open(head_file, "w") as hf:
            hf.write(head_str + "\n")
        with open(rel_file, "w") as rf:
            rf.write(rel_norm + "\n")

        # Direct inference
        results, elapsed = predict_tails_dglke(
            k=top_k_predictions,
            head_list_path=head_file,
            rel_list_path=rel_file,
        )
        if not results:
            raise HTTPException(status_code=404, detail="No predictions returned")

        # Build predictions list
        predictions = [
            PredictionResult(tail_entity=tail, score=score)
            for _, _, tail, score in results
        ]

        # Use original head ID in response, and the relation string from model output if available
        relation_return = results[0][1] if results else rel_norm

        return PredictionResponse(
            head_entity=head,
            relation=relation_return,
            predictions=predictions,
        )

    except Exception as e:
        logger.error("Error in predict_tail: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e!s}")
    finally:
        for p in (head_file, rel_file):
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass

    
@router.get(
    "/get_prediction_rank",
    tags=["KGE Predictions"],
    description="Get the rank and score of a specific tail entity for a given head and relation, along with the maximum score.",
    summary="Retrieve prediction rank and score for a given tail entity",
    response_description="Returns the rank, score, and maximum score of the prediction",
    operation_id="get_prediction_rank",
    response_model=PredictionRankResponse,
)
async def get_prediction_rank(
    head: str = Query(..., description="model_id for head entity for the prediction"),
    relation: str = Query(..., description="Relation for the prediction"),
    tail: str = Query(
        ...,
        description="model_id for tail entity to check for its rank",
    ),
):
    """Returns the rank, score of the given tail entity, and the maximum score among predictions."""
    os.makedirs(INPUT_DIR, exist_ok=True)

    unique_id = uuid.uuid4().hex
    head_file = os.path.join(INPUT_DIR, f"head_{unique_id}.list")
    rel_file  = os.path.join(INPUT_DIR, f"rel_{unique_id}.list")
    tail_file = os.path.join(INPUT_DIR, f"tail_{unique_id}.list")

    try:
        # map head ID → string
        mapped = node_mappings.loc[node_mappings["MappedID"] == int(head)]
        if mapped.empty:
            raise HTTPException(status_code=404, detail=f"No head found for ID {head}")
        head_str = mapped["Node"].iat[0]

        # map tail ID → string
        mapped_t = node_mappings.loc[node_mappings["MappedID"] == int(tail)]
        if mapped_t.empty:
            raise HTTPException(status_code=404, detail=f"No tail found for ID {tail}")
        tail_str = mapped_t["Node"].iat[0]

        # normalize relation
        rel_norm = relation.lower()

        # write out the three .list files
        with open(head_file, "w") as hf:
            hf.write(head_str + "\n")
        with open(rel_file, "w") as rf:
            rf.write(rel_norm + "\n")
        with open(tail_file, "w") as tf:
            tf.write(tail_str + "\n")

        # get rank, score, max_score
        rank, score, max_score, elapsed = predict_rank_dglke(
            head_list_path=head_file,
            rel_list_path=rel_file,
            user_set_tail_list_path=tail_file,
        )

        return PredictionRankResponse(
            head_entity=head,
            relation=relation,
            tail_entity=tail,
            rank=rank,
            score=score,
            max_score=max_score
        )
        
    except Exception as e:
        logger.error("Error in get_prediction_rank: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Rank prediction failed: {e!s}")
    finally:
        for p in (head_file, rel_file, tail_file):
            try:
                if os.path.exists(p):
                    os.remove(p)
            except OSError:
                pass
    
