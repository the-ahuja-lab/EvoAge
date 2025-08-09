import pandas as pd
import uuid
import os
os.environ["CUDA_LAUNCH_BLOCKING"] = "0"
from fastapi import APIRouter, HTTPException, Query
import time

# DGL-KE imports
from dglke.utils import load_model_config, load_raw_triplet_data
from dglke.models.infer import ScoreInfer

import logging

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

# ─── CONFIG (adjust paths if needed) ───────────────────────────────────────────
NODE_MAPPINGS_PATH = "/home/pushpendrag/ankiss/DGL_EvoKG_model/EvoKG/node_id_HYCDZM_SPECIES_KG.pkl"
MODEL_PATH = "/home/pushpendrag/ankiss/DGL_EvoKG_model/EvoKG/RotatE_wikimedia_64_emb/"
ENT_DICT_PATH = "/home/pushpendrag/ankiss/DGL_EvoKG_model/EvoKG/entities_FullEvoKG.dict"
REL_DICT_PATH = "/home/pushpendrag/ankiss/DGL_EvoKG_model/EvoKG/relation_FullEvoKG.dict"


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
if not os.path.isfile(config_json):
    raise FileNotFoundError(f"Config file not found at {config_json}")
if not os.path.isdir(MODEL_PATH):
    raise FileNotFoundError(f"Model directory not found at {MODEL_PATH}")

# Attempt to load config
try:
    logger.info("Loading DGL-KE model configuration from %s", config_json)
    config = load_model_config(config_json)
except Exception as e:
    raise RuntimeError(f"Failed to load model config: {e!s}")

try:
    logger.info("Initializing ScoreInfer on device 0")
    infer = ScoreInfer(
        device=0,
        config=config,
        model_path=MODEL_PATH,
        sfunc="logsigmoid"
    )
    logger.info("Starting model.load_model() (this may take a while)")
    infer.load_model()
except Exception as e:
        logger.warning("Loading on GPU failed: %s", str(e))
        raise RuntimeError(f"Cannot initialize inference model: {e!s}")

logger.info("Inference service starting up… warming up DGL-KE model on GPU")
try:
    # one tiny predict call to force the first GPU / JIT warm‑up
    dummy_head = "/home/pushpendrag/ankiss/neo4j-fastapi/app/DGL-microservice/model/inputs/head.list"
    dummy_rel  = "/home/pushpendrag/ankiss/neo4j-fastapi/app/DGL-microservice/model/inputs/rel.list"

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

edge_mapping = {
    "phenotype_chemicalentity": 0,
    "chemicalentity_phenotype": 0,
    "mutation_disease": 1,  # reverse relation exists with different ID (40)
    "molecularfunction_chemicalentity": 2,
    "chemicalentity_molecularfunction": 2,
    "disease_anatomy": 3,
    "anatomy_disease": 3,
    "chemicalentity_disease": 4,  # reverse relation exists with different ID (39)
    "disease_disease": 5,
    "biologicalprocess_gene": 6,  # reverse relation exists with different ID (46)
    "protein_protein": 7,
    "gene_phenotype": 8,  # reverse relation exists with different ID (25)
    "protein_disease": 9,
    "disease_protein": 9,
    "anatomy_gene": 10,  # reverse relation exists with different ID (36)
    "chemicalentity_biologicalprocess": 11,  # reverse relation exists with different ID (57)
    "disease_gene": 12,  # reverse relation exists with different ID (16)
    "gene_cellularcomponent": 13,  # reverse relation exists with different ID (15)
    "chemicalentity_chemicalentity": 14,
    "cellularcomponent_gene": 15,
    "gene_disease": 16,
    "protein_cellularcomponent": 17,
    "cellularcomponent_protein": 17,
    "protein_phenotype": 18,
    "phenotype_protein": 18,
    "mutation_protein": 19,
    "protein_mutation": 19,
    "chemicalentity_gene": 20,  # reverse relation exists with different ID (41)
    "chemicalentity_tissue": 21,
    "tissue_chemicalentity": 21,
    "chemicalentity_protein": 22,
    "protein_chemicalentity": 22,
    "biologicalprocess_biologicalprocess": 23,
    "phenotype_phenotype": 24,
    "phenotype_gene": 25,
    "chemicalentity_inhibits_biologicalprocess": 26,
    "biologicalprocess_inhibits_chemicalentity": 26,  # Assuming "inhibits" stays in middle
    "gene_inhibits_biologicalprocess": 27,
    "biologicalprocess_inhibits_gene": 27,  # Assuming "inhibits" stays in middle
    "protein_biologicalprocess": 28,
    "biologicalprocess_protein": 28,
    "gene_promotes_biologicalprocess": 29,
    "biologicalprocess_promotes_gene": 29,  # Assuming "promotes" stays in middle
    "gene_molecularfunction": 30,
    "molecularfunction_gene": 30,
    "gene_pathway": 31,  # reverse relation exists with different ID (38)
    "chemicalentity_pathway": 32,
    "pathway_chemicalentity": 32,
    "gene_tissue": 33,
    "tissue_gene": 33,
    "disease_phenotype": 34,  # reverse relation exists with different ID (37)
    "chemicalentity_mutation": 35,
    "mutation_chemicalentity": 35,
    "gene_anatomy": 36,
    "phenotype_disease": 37,
    "pathway_gene": 38,
    "disease_chemicalentity": 39,
    "disease_mutation": 40,
    "gene_chemicalentity": 41,
    "protein_pathway": 42,
    "pathway_protein": 42,
    "gene_protein": 43,
    "protein_gene": 43,
    "gene_noeffect_biologicalprocess": 44,
    "biologicalprocess_noeffect_gene": 44,  # Assuming "noeffect" stays in middle
    "chemicalentity_promotes_biologicalprocess": 45,
    "biologicalprocess_promotes_chemicalentity": 45,  # Assuming "promotes" stays in middle
    "gene_biologicalprocess": 46,
    "protein_molecularfunction": 47,
    "molecularfunction_protein": 47,
    "mutation_gene": 48,  # reverse relation exists with different ID (51)
    "gene_gene": 49,
    "molecularfunction_molecularfunction": 50,
    "gene_mutation": 51,
    "molecularfunction_biologicalprocess": 52,
    "biologicalprocess_molecularfunction": 52,
    "protein_tissue": 53,
    "tissue_protein": 53,
    "cellularcomponent_cellularcomponent": 54,
    "pathway_pathway": 55,
    "anatomy_anatomy": 56,
    "biologicalprocess_chemicalentity": 57,
    "plantextract_chemicalentity": 58,
    "chemicalentity_plantextract": 58,
    "plantextract_disease": 59,
    "disease_plantextract": 59,
    "pmid_cellularcomponent": 60,
    "cellularcomponent_pmid": 60,
    "pmid_chemicalentity": 61,
    "chemicalentity_pmid": 61,
    "pmid_disease": 62,
    "disease_pmid": 62,
    "pmid_protein": 63,
    "protein_pmid": 63,
    "pmid_tissue": 64,
    "tissue_pmid": 64,
    "species_associatedwith_nodes": 65,
    "nodes_associatedwith_species": 65,  # Assuming "associatedwith" stays in middle
}

def get_EdgeID(edge: str) -> int:
    return edge_mapping[edge.lower()]


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
    input_dir = "/home/pushpendrag/ankiss/neo4j-fastapi/app/DGL-microservice/input"
    os.makedirs(input_dir, exist_ok=True)

    unique_id = uuid.uuid4().hex
    head_file = os.path.join(input_dir, f"head_{unique_id}.list")
    rel_file = os.path.join(input_dir, f"rel_{unique_id}.list")
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
    input_dir = "/home/pushpendrag/ankiss/neo4j-fastapi/app/DGL-microservice/input"
    os.makedirs(input_dir, exist_ok=True)

    unique_id = uuid.uuid4().hex
    head_file = os.path.join(input_dir, f"head_{unique_id}.list")
    rel_file  = os.path.join(input_dir, f"rel_{unique_id}.list")
    tail_file = os.path.join(input_dir, f"tail_{unique_id}.list")

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
    
