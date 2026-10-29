#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FAST per-relation RANDOM (negative) triple generator using FULL node-type pools.

Negatives for a relation are sampled from ALL nodes of the correct type
(from the per-type parquet files), NOT just entities seen in that relation's GT.
This gives the strongest, most informative negatives (a valid gene that never
had this edge is still a valid negative tail).

Per relation:
  head type = FIRST underscore-token of relation name
  tail type = LAST  underscore-token of relation name
  (Species_associated_with is skipped by request.)

Speed: everything vectorized on GPU. Each candidate (h,t) -> single int64 key
h * NUM_NODES + t; positives of that relation are turned into a sorted key set;
torch.isin rejects them in bulk. No per-triple Python loop.

Parquet node ids are already in the SAME id space as the KG tensor (no mapping
needed for the pools). Output list files still map ids -> node NAMES via the pkl.
"""
import os
import glob
import re
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd
import torch
from tqdm import tqdm

# ============================= CONFIG =============================
KG_TENSOR_PT = "/path/to/EvoAge/kg_formation/final_kg_building_3/building_evoage_kg_new/Store_House/EvoAge_121_12M_KG_train_90.pt"
MAPPING_PKL   = "/path/to/EvoAge/kg_formation/final_kg_building_3/building_evoage_kg_new/Store_House/node_id_mapping_EvoAge_121_12M.pkl"
REL_DICT_PATH = "/path/to/EvoAge/kg_formation/final_kg_building_3/building_evoage_kg_new/Store_House/relation_final.dict"

# folder containing EvoAge_121_12M_<type>_nodes.parquet (+ chemical_with_names.parquet)
NODES_PARQUET_DIR = "/path/to/EvoAge/kg_formation/final_kg_building_3/building_evoage_kg_new/Stats/EvoAge_121_12M_NODES"

OUT_DIR = "/path/to/cutoff/output/relation_samples_ALLRANDOM"

SKIP_RELATIONS = {"Species_AssociatedWith"}   # exact dict spelling; the old
# "Species_associated_with" never matched, so the skip silently never fired
# (it was excluded only as a side effect of type-pool resolution failing).

MAX_NEG_PER_REL = None          # None = match GT count per relation
SEED = 42
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
OVERSAMPLE = 4
MAX_ROUNDS = 200
# hard cap on candidates sampled per round (keeps GPU temporaries bounded
# regardless of how big the relation is). 8M int64 ~ 64 MB per tensor.
MAX_BATCH = 8_000_000
# chunk size for membership tests so torch.isin never builds a giant temporary
ISIN_CHUNK = 2_000_000
# above this target, stream negatives to CPU each round instead of keeping the
# whole `collected` set on GPU (avoids GPU OOM on the giant PMID relations).
# self-dedup is skipped during sampling (collisions are negligible when the
# pool product >> target) and done once at the end on CPU.
STREAM_THRESHOLD = 20_000_000
# =================================================================

torch.manual_seed(SEED)
g = torch.Generator(device=DEVICE).manual_seed(SEED)


# ---------- id -> name map ----------
Mapping = pd.read_pickle(MAPPING_PKL)
id2node = dict(zip(Mapping["MappedID"], Mapping["Node"]))

# ---------- id -> relation-name ----------
id2relname_original: Dict[int, str] = {}
with open(REL_DICT_PATH, "r") as f:
    for line in f:
        rid, rname = line.strip().split("\t")
        id2relname_original[int(rid)] = rname
edge_mapping = {v: k for k, v in id2relname_original.items()}


# ---------- load per-type node pools from parquet ----------
# Map a canonical lowercase type name -> torch LongTensor of node ids (on DEVICE).
def load_type_pools() -> Dict[str, torch.Tensor]:
    pools: Dict[str, torch.Tensor] = {}
    pattern = os.path.join(NODES_PARQUET_DIR, "EvoAge_121_12M_*_nodes.parquet")
    for path in glob.glob(pattern):
        base = os.path.basename(path)
        # EvoAge_121_12M_<type>_nodes.parquet -> <type>
        m = re.match(r"EvoAge_121_12M_(.+)_nodes\.parquet$", base)
        if not m:
            continue
        type_key = m.group(1).lower()          # e.g. 'anatomicalentity'
        df = pd.read_parquet(path)
        # take the single id column (first column) regardless of its name
        idcol = df.columns[0]
        ids = torch.as_tensor(df[idcol].to_numpy(), dtype=torch.long)
        pools[type_key] = ids
        tqdm.write(f"  pool {type_key:<22} {ids.numel():>12,} nodes  ({idcol})")
    return pools


def isin_sorted(query: torch.Tensor, ref_sorted: torch.Tensor,
                chunk: int = ISIN_CHUNK):
    """Memory-flat membership test: is each element of `query` present in the
    SORTED, UNIQUE tensor `ref_sorted`? Uses searchsorted (O(log n) per query,
    tiny allocations) instead of torch.isin, which explodes when `ref` is huge
    (e.g. hundreds of millions of positive keys for PMID relations).
    Chunked over the query side so peak memory stays flat regardless of size."""
    n = query.numel()
    if n == 0:
        return torch.empty(0, dtype=torch.bool, device=query.device)
    out = torch.empty(n, dtype=torch.bool, device=query.device)
    for i in range(0, n, chunk):
        q = query[i:i + chunk]
        pos = torch.searchsorted(ref_sorted, q)
        pos = pos.clamp_(max=ref_sorted.numel() - 1)
        out[i:i + chunk] = ref_sorted[pos] == q
    return out


def resolve_types(rel_name: str, pool_keys):
    """head = first token, tail = last token, matched (lowercased) to a pool key."""
    toks = rel_name.split("_")
    head_tok, tail_tok = toks[0].lower(), toks[-1].lower()
    head_key = head_tok if head_tok in pool_keys else None
    tail_key = tail_tok if tail_tok in pool_keys else None
    return head_key, tail_key


def write_triple_files(h_ids, t_ids, out_base: Path, rel_id: int):
    heads = [id2node.get(int(h), str(h)) for h in h_ids.tolist()]
    tails = [id2node.get(int(t), str(t)) for t in t_ids.tolist()]
    rels  = [id2relname_original[rel_id]] * len(heads)
    (out_base.parent / f"{out_base.stem}_head.list").write_text("\n".join(heads) + "\n")
    (out_base.parent / f"{out_base.stem}_rel.list").write_text("\n".join(rels) + "\n")
    (out_base.parent / f"{out_base.stem}_tail.list").write_text("\n".join(tails) + "\n")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    print(f"Device: {DEVICE}")

    print("Loading node-type pools:")
    pools_cpu = load_type_pools()
    pool_keys = set(pools_cpu.keys())

    FULLKG = torch.load(KG_TENSOR_PT)
    FULLKG = FULLKG.detach().cpu().long()
    print(f"Loaded KG: {FULLKG.shape[0]:,} triples, {len(edge_mapping)} relations")
    rel_col = FULLKG[:, 1]

    manifest = []
    pbar = tqdm(edge_mapping.items(), total=len(edge_mapping),
                desc="relations", unit="rel")

    for rel_name, rel_id in pbar:
        pbar.set_postfix_str(rel_name[:40])

        if rel_name in SKIP_RELATIONS:
            tqdm.write(f"  skip {rel_name} — in SKIP_RELATIONS")
            continue

        rel_pos = FULLKG[rel_col == rel_id]
        n_rel = rel_pos.shape[0]
        if n_rel == 0:
            tqdm.write(f"  skip {rel_name} (r={rel_id}) — no GT triples")
            continue

        head_key, tail_key = resolve_types(rel_name, pool_keys)
        if head_key is None or tail_key is None:
            tqdm.write(f"  ⚠ {rel_name}: cannot resolve types "
                       f"(head={head_key}, tail={tail_key}) — skipped")
            continue

        head_pool = pools_cpu[head_key].to(DEVICE)
        tail_pool = pools_cpu[tail_key].to(DEVICE)
        Hn, Tn = head_pool.numel(), tail_pool.numel()

        needed = n_rel if (MAX_NEG_PER_REL is None or n_rel <= MAX_NEG_PER_REL) else MAX_NEG_PER_REL
        max_possible = Hn * Tn - n_rel
        if max_possible <= 0:
            tqdm.write(f"  ⚠ {rel_name}: pool product too small — skipped")
            continue
        target = min(needed, max_possible)

        # sorted pools -> map real ids to pool index for compact keys
        h_sorted, _ = torch.sort(head_pool)
        t_sorted, _ = torch.sort(tail_pool)

        # positives: only those whose head/tail actually lie in the pools
        ph = rel_pos[:, 0].to(DEVICE)
        pt = rel_pos[:, 2].to(DEVICE)
        h_in = torch.isin(ph, h_sorted)
        t_in = torch.isin(pt, t_sorted)
        keep = h_in & t_in
        ph, pt = ph[keep], pt[keep]
        stream_mode = target > STREAM_THRESHOLD

        # For huge relations, build the positive-key set on CPU to avoid the
        # GPU memory spike from unique() over hundreds of millions of positives.
        pk_device = "cpu" if stream_mode else DEVICE
        pos_hidx = torch.searchsorted(h_sorted, ph).to(pk_device)
        pos_tidx = torch.searchsorted(t_sorted, pt).to(pk_device)
        pos_keys = torch.unique(pos_hidx.to(torch.int64) * Tn + pos_tidx.to(torch.int64))
        del pos_hidx, pos_tidx
        if DEVICE == "cuda":
            torch.cuda.empty_cache()

        if not stream_mode:
            # ---- small/medium: accumulate on GPU with exact self-dedup ----
            collected = torch.empty(0, dtype=torch.int64, device=DEVICE)
            rounds = 0
            while collected.numel() < target and rounds < MAX_ROUNDS:
                still = target - collected.numel()
                bsz = min(int(still * OVERSAMPLE) + 1024, max_possible + 1024, MAX_BATCH)
                hi = torch.randint(0, Hn, (bsz,), device=DEVICE, generator=g)
                ti = torch.randint(0, Tn, (bsz,), device=DEVICE, generator=g)
                keys = hi.to(torch.int64) * Tn + ti.to(torch.int64)
                del hi, ti
                keys = keys[~isin_sorted(keys, pos_keys)]
                keys = torch.unique(keys)
                if collected.numel():
                    keys = keys[~isin_sorted(keys, collected)]
                collected = torch.unique(torch.cat([collected, keys]))  # stays sorted
                del keys
                rounds += 1
            collected = collected[:target]
            got_keys_cpu = collected.cpu()
            del collected
        else:
            # ---- huge (PMID-scale): stream each round to CPU, no GPU collected ----
            # collisions negligible since pool product (Hn*Tn) >> target; we
            # over-collect a little then dedup once on CPU at the end.
            buffers = []
            have = 0
            rounds = 0
            while have < target and rounds < MAX_ROUNDS:
                still = target - have
                bsz = min(int(still * OVERSAMPLE) + 1024, MAX_BATCH)
                hi = torch.randint(0, Hn, (bsz,), device=DEVICE, generator=g)
                ti = torch.randint(0, Tn, (bsz,), device=DEVICE, generator=g)
                keys = (hi.to(torch.int64) * Tn + ti.to(torch.int64)).cpu()
                del hi, ti
                if DEVICE == "cuda":
                    torch.cuda.empty_cache()
                keys = keys[~isin_sorted(keys, pos_keys)]   # both on CPU, flat mem
                keys = torch.unique(keys)          # in-batch dedup only
                buffers.append(keys)
                have += keys.numel()
                del keys
                rounds += 1
            allk = torch.cat(buffers)
            del buffers
            allk = torch.unique(allk)              # final cross-round dedup (CPU)
            got_keys_cpu = allk[:target]
            del allk

        got = got_keys_cpu.numel()
        if got < needed:
            tqdm.write(f"  ⚠ {rel_name}: wanted {needed:,}, produced {got:,} "
                       f"(round cap / sparse space)")

        out_h = h_sorted.cpu()[got_keys_cpu // Tn].numpy()
        out_t = t_sorted.cpu()[got_keys_cpu %  Tn].numpy()

        rel_dir = Path(OUT_DIR) / rel_name
        rel_dir.mkdir(parents=True, exist_ok=True)
        write_triple_files(torch.as_tensor(out_h), torch.as_tensor(out_t),
                           rel_dir / f"{rel_name}_RAND", rel_id)

        tqdm.write(f"  ✔ {rel_name} (r={rel_id}): {got:,} random "
                   f"(GT={n_rel:,}, head={head_key}[{Hn:,}] tail={tail_key}[{Tn:,}], {rounds}r)")

        manifest.append({
            "relation": rel_name, "rel_id": rel_id,
            "head_type": head_key, "tail_type": tail_key,
            "head_pool": Hn, "tail_pool": Tn,
            "gt_count": n_rel, "rand_written": got,
            "rand_head_list": str(rel_dir / f"{rel_name}_RAND_head.list"),
            "rand_rel_list":  str(rel_dir / f"{rel_name}_RAND_rel.list"),
            "rand_tail_list": str(rel_dir / f"{rel_name}_RAND_tail.list"),
        })

        # release this relation's GPU memory before the next one
        del head_pool, tail_pool, h_sorted, t_sorted
        del ph, pt, pos_keys, got_keys_cpu
        if DEVICE == "cuda":
            torch.cuda.empty_cache()

    if manifest:
        mpath = Path(OUT_DIR) / "rand_manifest.csv"
        pd.DataFrame(manifest).sort_values("gt_count", ascending=False)\
          .to_csv(mpath, index=False)
        print(f"\n✅ Done. {len(manifest)} relations. Manifest -> {mpath}")


if __name__ == "__main__":
    main()
