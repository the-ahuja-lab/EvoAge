import pandas as pd
import uuid
import os
import time
import logging
from pathlib import Path

from app.utils.environment import CONFIG
from fastapi import APIRouter, HTTPException, Query
from app.utils.constants import check_rev_rel, Ntype_split

# DGL-KE imports
from dglke.utils import load_model_config, load_raw_triplet_data
from dglke.models.infer import ScoreInfer
from app.utils.model_manager import LazyKGEManager



logger = logging.getLogger("LinkPrediction")
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


def predict_tails_dglke(tail_type, k=10, head_list_path=None, rel_list_path=None):
    """
    k                 : number of top predictions to return
    head_list_path    : path to your head.list file
    rel_list_path     : path to your rel.list file

    Returns:
      results : list of (head_str, rel_str, tail_str, score)
      elapsed : total time in seconds for loading and inference
    """

    tail_type = (tail_type or "").strip().lower()
    if not tail_type:
        raise RuntimeError("tail_type must be a non-empty string")
    
    logger.info(
        "predict_tails called: k=%s, head_list_path=%s, rel_list_path=%s",
        k, head_list_path, rel_list_path
    )
    start_time = time.time()
    
    # 2) load this call’s head & rel
    head_ids, rel_ids, tail_ids, user_tail_id, id2ent, id2rel = load_raw_triplet_data(
        head_f=head_list_path,
        rel_f=rel_list_path,
        tail_f=None,
        emap_f=ENT_DICT_PATH,
        rmap_f=REL_DICT_PATH,
        tail_type=tail_type
    )
    logger.info("Loaded %d heads and %d relations and %d tails in %.3f seconds", len(head_ids), len(rel_ids), len(tail_ids), (time.time() - start_time))

    # 3) run inference
    logger.info("Running infer.topK(exec_mode='batch_head', k=%d)", k)
    # raw_results = infer.topK(
    #     head=head_ids,
    #     rel=rel_ids,
    #     tail=tail_ids,
    #     exec_mode="batch_head",
    #     k=k
    # )
    with MODEL.session() as infer:
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

def predict_heads_dglke(head_type, k=10, tail_list_path=None, rel_list_path=None):
    """
    k                 : number of top predictions to return
    tail_list_path    : path to your tail.list file
    rel_list_path     : path to your rel.list file

    Returns:
      results : list of (head_str, rel_str, tail_str, score)
      elapsed : total time in seconds for loading and inference
    """
    head_type = (head_type or "").strip().lower()
    if not head_type:
        raise RuntimeError("head_type must be a non-empty string")

    logger.info(
        "predict_tails called: k=%s, tail_list_path=%s, rel_list_path=%s",
        k, tail_list_path, rel_list_path
    )
    start_time = time.time()

    # 2) load this call’s head & rel
    head_ids, rel_ids, tail_ids, user_tail_id, id2ent, id2rel = load_raw_triplet_data(
        head_f=None,
        rel_f=rel_list_path,
        tail_f=tail_list_path,
        emap_f=ENT_DICT_PATH,
        rmap_f=REL_DICT_PATH,
        head_type=head_type,
        tail_type = None
    )

    logger.info("Loaded %d tails and %d relations in %.3f seconds", len(tail_ids), len(rel_ids), (time.time() - start_time))

    # 3) run inference
    logger.info("Running infer.topK(exec_mode='batch_tail', k=%d)", k)
    # raw_results = infer.topK(
    #     head=head_ids,
    #     rel=rel_ids,
    #     tail=tail_ids,
    #     exec_mode="batch_tail",
    #     k=k
    # )
    with MODEL.session() as infer:
        raw_results = infer.topK(
            head=head_ids,
            rel=rel_ids,
            tail=tail_ids,
            exec_mode="batch_tail",
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
    tail_type: str,
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
    head_ids, rel_ids, tail_ids, user_tail_id, id2ent, id2rel = load_raw_triplet_data(
        head_f=head_list_path,
        rel_f=rel_list_path,
        tail_f=None,
        user_tail_f=user_set_tail_list_path,
        emap_f=ENT_DICT_PATH,
        rmap_f=REL_DICT_PATH,
        tail_type=tail_type,
    )
    logger.info("Loaded %d heads, %d relations, and %d user_set_tails in %.3f seconds", len(head_ids), len(rel_ids), len(user_tail_id), (time.time() - start_time))

    logger.info("Running infer.get_rank_score(exec_mode='batch_head')")
    # get_rank_score expects lists of length 1 for head_ids, rel_ids, tail_ids
    # rank, user_score, max_score = infer.get_rank_score(
    #     head=head_ids,
    #     rel=rel_ids,
    #     user_set_tail=tail_ids,
    #     exec_mode="batch_head",
    # )
    with MODEL.session() as infer:
        rank, user_score, max_score = infer.get_rank_score(
            head=head_ids,
            rel=rel_ids,
            tail=tail_ids,
            user_set_tail=user_tail_id,
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

# Load the mappings for the entities and relations
try:
    node_mappings = pd.read_pickle(NODE_MAPPINGS_PATH)
except FileNotFoundError:
    raise Exception(
        f"Node mappings file not found. Please ensure {NODE_MAPPINGS_PATH} exists in the app/data directory.",
    )
except Exception as e:
    raise Exception(f"Error loading node mappings: {e!s}")

MODEL = LazyKGEManager(
    score_infer_cls=ScoreInfer,
    device=DEVICE,
    config=config,
    model_path=MODEL_PATH,
    sfunc=SFUNC,
    idle_seconds=1800,   # 30 minutes
    max_inflight=1      # start with 1; raise carefully if memory allows
)


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
    tail_file = os.path.join(INPUT_DIR, f"tail{unique_id}.list")
    rel_file = os.path.join(INPUT_DIR, f"rel_{unique_id}.list")
    try:
        head_input = str(head).strip()
        mapped = None
        if head_input.isdigit():
            mapped = node_mappings.loc[node_mappings["MappedID"] == int(head_input)]
        elif mapped is None or mapped.empty:
            mapped = node_mappings.loc[node_mappings["Node"] == head_input]

        if mapped.empty:
            raise HTTPException(status_code=404, detail=f"No head found for '{head}'")
        
        head_str = mapped["Node"].iat[0]          
        head = int(mapped["MappedID"].iat[0]) 
        head_type = mapped["Node_type"].iat[0].lower()

        # Normalize relation
        rel_norm = relation.lower()
        if rel_norm in check_rev_rel:
            rel_norm = check_rev_rel[rel_norm]
        Ntype_split_array = Ntype_split.get(rel_norm, [])

        # Default values in case of missing parts
        rel_head_type = None
        tail_head_type = None

        if len(Ntype_split_array) == 2:
            rel_head_type = Ntype_split_array[0]
            tail_head_type = Ntype_split_array[1]
        else:
            raise HTTPException(status_code=400,
                                detail=f"This relation doesn't exist in Evo-Age, relation: {rel_norm}")

        logger.info(f"predict_tails called: Head: {head_str}; Head: {head}; Relation: {rel_norm}")

        if (head_type == rel_head_type):
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
                tail_type=tail_head_type
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
                head_entity=str(head),
                relation=relation_return,
                predictions=predictions,
            )
        
        elif (head_type == tail_head_type):
            # write head and relation files
            with open(tail_file, "w") as tf:
                tf.write(head_str + "\n")
            with open(rel_file, "w") as rf:
                rf.write(rel_norm + "\n")

            # Direct inference
            results, elapsed = predict_heads_dglke(
                k=top_k_predictions,
                tail_list_path=tail_file,
                rel_list_path=rel_file,
                head_type=rel_head_type
            )
        
            if not results:
                raise HTTPException(status_code=404, detail="No predictions returned")

            # Build predictions list
            predictions = [
                PredictionResult(tail_entity=head, score=score)
                for head, _, _, score in results
            ]

            # Use original head ID in response, and the relation string from model output if available
            relation_return = results[0][1] if results else rel_norm

            return PredictionResponse(
                head_entity=str(head),
                relation=Ntype_split_array[1]+"_"+Ntype_split_array[0],
                predictions=predictions,
            )
        
        else:
            raise HTTPException(status_code=400,
                                detail=f"Entity type mismatch for relation '{relation}'.")

    except Exception as e:
        logger.error("Error in predict_tail: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e!s}")
    finally:
        for p in (head_file, rel_file, tail_file):
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
        head_input = str(head).strip()
        mapped_head = None
        if head_input.isdigit():
            mapped_head = node_mappings.loc[node_mappings["MappedID"] == int(head_input)]
        elif mapped_head is None or mapped_head.empty:
            mapped_head = node_mappings.loc[node_mappings["Node"] == head_input]
        
        if mapped_head.empty:
            raise HTTPException(status_code=404, detail=f"No head found for ID {head}")

        head_str = mapped_head["Node"].iat[0]          
        head = str(mapped_head["MappedID"].iat[0])
        head_node_type = mapped_head["Node_type"].iat[0].lower()

        # map head ID → string
        tail_input = str(tail).strip()
        mapped_tail = None
        if tail_input.isdigit():
            mapped_tail = node_mappings.loc[node_mappings["MappedID"] == int(tail_input)]
        elif mapped_tail is None or mapped_tail.empty:
            mapped_tail = node_mappings.loc[node_mappings["Node"] == tail_input]
        
        if mapped_tail.empty:
            raise HTTPException(status_code=404, detail=f"No head found for ID {tail}")

        tail_str = mapped_tail["Node"].iat[0]
        tail = str(mapped_tail["MappedID"].iat[0])
        tail_node_type = mapped_tail["Node_type"].iat[0].lower()

        # normalize relation
        rel_norm = relation.lower()
        if rel_norm in check_rev_rel:
            rel_norm = check_rev_rel[rel_norm]
        Ntype_split_array = Ntype_split.get(rel_norm, [])

        # Default values in case of missing parts
        rel_head_type = None
        rel_tail_type = None

        if len(Ntype_split_array) == 2:
            rel_head_type = Ntype_split_array[0]
            rel_tail_type = Ntype_split_array[1]
        else:
            raise HTTPException(status_code=400, detail=f"This relation doesn't exist in Evo-Age, relation: {rel_norm}")

        logger.info(f"Head Node Type: {head_node_type}; Head Type: {rel_head_type}; Tail Node Type: {tail_node_type}; Tail Type: {rel_tail_type}")
        
        if (head_node_type == rel_head_type and tail_node_type == rel_tail_type):
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
                tail_type = tail_node_type
            )

            return PredictionRankResponse(
                head_entity=head,
                relation=relation,
                tail_entity=tail,
                rank=rank,
                score=score,
                max_score=max_score
            )
        elif (head_node_type == rel_tail_type and tail_node_type == rel_head_type):
            # write out the three .list files
            with open(head_file, "w") as hf:
                hf.write(tail_str + "\n")
            with open(rel_file, "w") as rf:
                rf.write(rel_norm + "\n")
            with open(tail_file, "w") as tf:
                tf.write(head_str + "\n")

            # get rank, score, max_score
            rank, score, max_score, elapsed = predict_rank_dglke(
                head_list_path=head_file,
                rel_list_path=rel_file,
                user_set_tail_list_path=tail_file,
                tail_type = head_node_type
            )

            return PredictionRankResponse(
                head_entity=head,
                relation=relation,
                tail_entity=tail,
                rank=rank,
                score=score,
                max_score=max_score
            )
        raise HTTPException(
            status_code=400,
            detail=(
                f"Entity type mismatch for relation '{relation}'."
                # "Expected '{ht}->{tt}', got '{hnode}->{tnode}'"
            )
            # .format(
            #     rel=relation,
            #     ht=rel_head_type_expected, tt=tail_type_expected,
            #     hnode=head_node_type, tnode=tail_node_type
            # ),
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
    
@router.post("/unload_model")
def unload_model():
    unloaded = MODEL.unload_now()
    return {"unloaded": unloaded, "stats": MODEL.stats()}

@router.get("/model_stats")
def model_stats():
    return MODEL.stats()