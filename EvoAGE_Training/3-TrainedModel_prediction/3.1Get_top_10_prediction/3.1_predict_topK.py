#!/usr/bin/env python3
import os
from dglke.utils import load_model_config, load_raw_triplet_data
from dglke.models.infer import ScoreInfer

# ─── CONFIGURE THESE PATHS ──────────────────────────────────────────────────────
MODEL_PATH    = "../2-DGL_Training/model_output/rotatE/RotatE_wikimedia_128Dim_emb"
ENT_DICT_PATH = "../2-DGL_Training/Training_files/entities_final.dict"
REL_DICT_PATH = "../2-DGL_Training/Training_files/relation_final.dict"
HEAD_LIST     = "head.list"
REL_LIST      = "relation.list"
TOPK          = 10

# ─── 1) LOAD THE CONFIG & MODEL ────────────────────────────────────────────
config = load_model_config(os.path.join(MODEL_PATH, "config.json"))
infer = ScoreInfer(
    device=0,                 # GPU 0 (or -1 for CPU)
    config=config,
    model_path=MODEL_PATH,
    sfunc="logsigmoid"        # same as --score_func logsigmoid
)
infer.load_model()

# ─── 2) READ YOUR HEAD & RELATION STRINGS → INT IDs + FULL TAIL LIST ───────
# ─── Now map your head & rel strings → IDs and get the full tail list ───────
head_ids, rel_ids, tail_ids, id2ent, id2rel = load_raw_triplet_data(
    head_f=HEAD_LIST,
    rel_f=REL_LIST,
    tail_f=None,        # `None` → use every entity as a candidate
    emap_f=ENT_DICT_PATH,
    rmap_f=REL_DICT_PATH
)

# ─── Run batch_head inference ───────────────────────────────────────────────
results = infer.topK(
    head=head_ids,
    rel=rel_ids,
    tail=tail_ids,
    exec_mode="batch_head",
    k=10
)

# ─── Print them out ─────────────────────────────────────────────────────────
print("src\trel\tdst\tscore")
for h_arr, r_arr, t_arr, s_arr in results:
    for h, r, t, s in zip(h_arr, r_arr, t_arr, s_arr):
        print(f"{id2ent[h]}\t{id2rel[r]}\t{id2ent[t]}\t{s:.6f}")
