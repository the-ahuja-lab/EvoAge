#!/usr/bin/env python3
import os
import json
import sys
import numpy as np
import pandas as pd

import os, subprocess, sys

# ───── Your configuration ───────────────────────────────────────────────────────
# Paths (adjust to your environment)
head_list     = "head.list"
rel_list      = "relation.list"
tail_file     = "tail.list"
output_file   = "Triple_score.tsv"
score_func    = "logsigmoid"  # "none" for raw score
gpu_id        = "0"

model_path     = "../../2-DGL_Training/model_output/rotatE/RotatE_wikimedia_128Dim_emb"
entity_mfile   = "../../2-DGL_Training/Training_files/entities_final.dict"
rel_mfile      = "../../2-DGL_Training/Training_files/relation_final.dict"

# gpu_id         = "0"
# score_func     = "logsigmoid"
# ────────────────────────────────────────────────────────────────────────────────

# sanity checks
for f in (head_list, rel_list, tail_file, entity_mfile, rel_mfile):
    if not os.path.exists(f):
        print(f"ERROR: file not found → {f}", file=sys.stderr)
        sys.exit(1)

# prepare head_all.list
with open(head_list) as gf:
    genes = [g.strip() for g in gf if g.strip()]
with open("head_all.list", "w") as hf:
    hf.write("\n".join(genes) + "\n")

# build the exact command you used
cmd = [
    "dglke_predict",
    "--model_path", model_path,
    "--format", "h_r_t",
    "--data_files", "head_all.list", rel_list, tail_file,
    "--raw_data",
    "--entity_mfile", entity_mfile,
    "--rel_mfile", rel_mfile,
    "--exec_mode",   "batch_head",
    "--gpu", gpu_id,
    "--score_func", score_func,
    "--output", output_file,
]

print("Running prediction across all heads…")
print(">", " ".join(cmd))
# <<< here’s the change: run via shell so PATH is applied >>>
ret = subprocess.run(" ".join(cmd), shell=True)

if ret.returncode == 0:
    print(f"\n✅ Done! All scores written to {output_file}")
else:
    print(f"\n❌ dglke_predict exited with code {ret.returncode}", file=sys.stderr)
    sys.exit(ret.returncode)
