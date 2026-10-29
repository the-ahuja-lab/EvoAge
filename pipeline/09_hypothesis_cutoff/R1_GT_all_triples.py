#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dump ALL GT triples of every relation from the KG tensor into per-relation
DGL-KE list files (head/rel/tail) + a TSV. Feed the .list files to your
prediction/scoring script to get per-triple scores for cutoff building.
"""
import os
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import torch
from tqdm import tqdm

# ============================= CONFIG =============================
KG_TENSOR_PT = "/path/to/EvoAge/kg_formation/final_kg_building_3/building_evoage_kg_new/Store_House/EvoAge_121_12M_KG_train_90.pt"

MAPPING_PKL   = "/path/to/EvoAge/kg_formation/final_kg_building_3/building_evoage_kg_new/Store_House/node_id_mapping_EvoAge_121_12M.pkl"
REL_DICT_PATH = "/path/to/EvoAge/kg_formation/final_kg_building_3/building_evoage_kg_new/Store_House/relation_final.dict"

OUT_DIR = "/path/to/cutoff/output/relation_samples_ALLGT"     # one subfolder per relation

# None = write EVERY GT triple of every relation.
MAX_GT_PER_REL = None

# Excluded from the whole cutoff pipeline: its name does not follow the
# <headtype>_<tailtype> convention, R2 cannot resolve node-type pools for it,
# so it never gets a Random set and can never be paired for Youden. Dumping it
# only burns 2.3 GB of .list files. Keep GT and Random at 88 relations.
SKIP_RELATIONS = {"Species_AssociatedWith"}
# =================================================================


# ---- load id -> node-name and id -> relation-name maps ----
Mapping = pd.read_pickle(MAPPING_PKL)
id2node = dict(zip(Mapping["MappedID"], Mapping["Node"]))

id2relname_original: Dict[int, str] = {}
with open(REL_DICT_PATH, "r") as f:
    for line in f:
        rid, rname = line.strip().split("\t")
        id2relname_original[int(rid)] = rname
# relation-name -> id (drives the per-relation loop)
edge_mapping = {v: k for k, v in id2relname_original.items()}


def write_triple_files(triples: torch.Tensor, out_base: Path, rel_id: int):
    """Write TSV (head, rel, tail) + DGL-KE *_head.list / *_rel.list / *_tail.list.
    Heads/tails are mapped back to original Node names; relation is the
    original-case name from relation_final.dict."""
    triples = triples.detach().cpu().long()

    heads = [id2node.get(int(h), str(h)) for h in triples[:, 0].tolist()]
    tails = [id2node.get(int(t), str(t)) for t in triples[:, 2].tolist()]
    rels  = [id2relname_original[rel_id]] * triples.shape[0]

    # TSV
    tsv_path = out_base.with_suffix(".tsv")
    pd.DataFrame({"head": heads, "rel": rels, "tail": tails}).to_csv(
        tsv_path, sep="\t", index=False)

    # list files (one token per line, aligned row-for-row)
    head_f = out_base.parent / f"{out_base.stem}_head.list"
    rel_f  = out_base.parent / f"{out_base.stem}_rel.list"
    tail_f = out_base.parent / f"{out_base.stem}_tail.list"

    head_f.write_text("\n".join(map(str, heads)) + "\n")
    rel_f.write_text("\n".join(rels) + "\n")
    tail_f.write_text("\n".join(map(str, tails)) + "\n")

    return str(tsv_path), str(head_f), str(rel_f), str(tail_f)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    FULLKG = torch.load(KG_TENSOR_PT)
    if not isinstance(FULLKG, torch.Tensor) or FULLKG.ndim != 2 or FULLKG.shape[1] != 3:
        raise ValueError("FULLKG must be a 2D tensor [N,3] (h,r,t)")
    print(f"Loaded KG: {FULLKG.shape[0]:,} triples, "
          f"{len(edge_mapping)} relations in dict")

    manifest = []

    pbar = tqdm(edge_mapping.items(), total=len(edge_mapping),
                desc="relations", unit="rel")
    for rel_name, rel_id in pbar:
        pbar.set_postfix_str(rel_name[:40])

        if rel_name in SKIP_RELATIONS:
            tqdm.write(f"  skip {rel_name} — in SKIP_RELATIONS")
            continue

        mask = (FULLKG[:, 1] == rel_id)
        triples_rel = FULLKG[mask]
        n_rel = triples_rel.shape[0]

        if n_rel == 0:
            tqdm.write(f"  skip {rel_name} (r={rel_id}) — no GT triples")
            continue

        # take ALL, unless this relation is bigger than the optional cap
        if MAX_GT_PER_REL is None or n_rel <= MAX_GT_PER_REL:
            gt = triples_rel
            k = n_rel
            note = "ALL"
        else:
            # NOTE: capping keeps the FIRST MAX_GT_PER_REL rows in tensor order
            # (no shuffle -> deterministic). If the tensor is sorted by head/source
            # this subset is not representative; switch to a strided or explicit
            # selection if that matters for the capped giants.
            gt = triples_rel[:MAX_GT_PER_REL]
            k = MAX_GT_PER_REL
            note = f"capped from {n_rel:,}"

        rel_dir = Path(OUT_DIR) / rel_name
        rel_dir.mkdir(parents=True, exist_ok=True)
        gt_base = rel_dir / f"{rel_name}_GT"

        tsv, hf, rf, tf = write_triple_files(gt, gt_base, rel_id)
        tqdm.write(f"  ✔ {rel_name} (r={rel_id}): wrote {k:,} GT triples ({note})")

        manifest.append({
            "relation": rel_name, "rel_id": rel_id,
            "gt_available": n_rel, "gt_written": k,
            "gt_head_list": hf, "gt_rel_list": rf, "gt_tail_list": tf,
            "gt_tsv": tsv,
        })

    if manifest:
        mpath = Path(OUT_DIR) / "gt_manifest.csv"
        pd.DataFrame(manifest).sort_values("gt_available", ascending=False)\
          .to_csv(mpath, index=False)
        print(f"\n✅ Done. {len(manifest)} relations. Manifest -> {mpath}")


if __name__ == "__main__":
    main()
