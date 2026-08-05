#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import pandas as pd
import pickle
import torch

TEST_PATH  = "building_evoage_kg_new/Store_House/EvoAge_1to1_KG_test.pt"
KG_PATH    = "building_evoage_kg_new/Store_House/EvoAge_121_12M_to_many_KG.pt"
TRAIN_OUT  = "building_evoage_kg_new/Store_House/EvoAge_121_12M_KG_train_90.pt"
VALID_OUT  = "building_evoage_kg_new/Store_House/EvoAge_121_12M_KG_valid_10.pt"
CHUNK      = 50_000_000      # rows per chunk — lower this if RAM is still tight
VALID_FRAC = 0.10
SEED       = 42
OUT_DTYPE  = None #torch.int32     # IDs almost certainly fit; halves RAM/disk. Set None to keep original.

# --- load lazily: mmap=True does NOT copy the file into RAM ---
test = torch.load(TEST_PATH, mmap=True)
kg   = torch.load(KG_PATH,  mmap=True)
N    = kg.shape[0]
print("test:", tuple(test.shape), "| kg:", tuple(kg.shape))

# --- build a bijective int64 key per triple (computed in chunks to stay RAM-light) ---
def chunked_amax(t, chunk=CHUNK):
    m = t[:chunk].to(torch.int64).amax(0)
    for s in range(chunk, t.shape[0], chunk):
        m = torch.maximum(m, t[s:s+chunk].to(torch.int64).amax(0))
    return m

col_max = torch.maximum(chunked_amax(test), chunked_amax(kg))
base_t  = int(col_max[2]) + 1
base_r  = int(col_max[1]) + 1
m_r, m_h = base_t, base_r * base_t
assert int(col_max[0])*m_h + int(col_max[1])*m_r + int(col_max[2]) < 2**63 - 1, \
    "Key overflows int64 — use the void-view fallback (see note)."

def encode(block):
    b = block.to(torch.int64)
    return b[:, 0]*m_h + b[:, 1]*m_r + b[:, 2]

# --- sort the SMALL test keys once (~0.9 GB), then stream the big KG past it ---
test_keys, _ = torch.sort(encode(test))
del test

gen = torch.Generator().manual_seed(SEED)
train_parts, valid_parts = [], []
removed = 0

for s in range(0, N, CHUNK):
    block = kg[s:s+CHUNK]                                   # only this slice enters RAM
    keys  = encode(block)
    pos   = torch.searchsorted(test_keys, keys).clamp_(max=test_keys.numel()-1)
    in_test = test_keys[pos] == keys
    removed += int(in_test.sum())

    kept = block[~in_test]
    if OUT_DTYPE is not None:
        kept = kept.to(OUT_DTYPE)

    vmask = torch.rand(kept.shape[0], generator=gen) < VALID_FRAC
    valid_parts.append(kept[vmask])
    train_parts.append(kept[~vmask])
    print(f"  processed {min(s+CHUNK, N):,}/{N:,}")

del kg, test_keys

# --- concat WITHOUT torch.cat's usual 2x memory spike ---
def concat_free(parts):
    total = sum(p.shape[0] for p in parts)
    out = torch.empty((total, 3), dtype=parts[0].dtype)
    off = 0
    while parts:
        p = parts.pop(0)
        out[off:off+p.shape[0]] = p
        off += p.shape[0]
        del p
    return out

train = concat_free(train_parts)
valid = concat_free(valid_parts)

print(f"\nremoved overlaps : {removed:,}")
print(f"train : {train.shape[0]:,}  |  valid : {valid.shape[0]:,}")
torch.save(train, TRAIN_OUT)
torch.save(valid, VALID_OUT)
print("saved.")


# In[ ]:


# Preparing files for training

import torch
import pandas as pd
from pathlib import Path

with open("building_evoage_kg_new/Store_House/node_id_mapping_EvoAge_121_12M.pkl", "rb") as f:
    df = pickle.load(f)

# clean entity names
df["Node"] = (
    df["Node"]
    .astype(str)
    .str.replace(r"[\r\n]+", " ", regex=True)
    .str.replace(r"\s+", " ", regex=True)
    .str.strip()
)

df = df.sort_values("MappedID")

df[["MappedID", "Node"]].to_csv(
    "building_evoage_kg_new/Store_House/entities_final.dict",
    sep="\t",
    index=False,
    header=False,
    encoding="utf-8"
)

print(f"Wrote {len(df)} entities")

# =========================================================
# LOAD RELATION MAPPING (.csv)
# =========================================================
rel_df = pd.read_csv("building_evoage_kg_new/Store_House/relation_id_EvoAge_EvoAge_121_12M.csv")

relations = dict(zip(rel_df["Relation"], rel_df["MappedID"]))

# =========================================================
# WRITE relation_final.dict
# =========================================================
relation_output = "building_evoage_kg_new/Store_House/relation_final.dict"

with open(relation_output, "w", encoding="utf-8") as f:
    for name, idx in sorted(relations.items(), key=lambda kv: kv[1]):
        f.write(f"{idx}\t{name}\n")

print(f"Wrote {len(relations)} lines to {relation_output}")


STORE = Path("building_evoage_kg_new/Store_House")

# Load saved splits
train = torch.load("building_evoage_kg_new/Store_House/EvoAge_121_12M_KG_train_90.pt")
valid = torch.load("building_evoage_kg_new/Store_House/EvoAge_121_12M_KG_valid_10.pt")
test  = torch.load("building_evoage_kg_new/Store_House/EvoAge_1to1_KG_test.pt")

print("Train:", train.shape)
print("Valid:", valid.shape)
print("Test :", test.shape)

def write_tsv(tensor, outfile):
    # Move to CPU if needed
    if tensor.is_cuda:
        tensor = tensor.cpu()

    pd.DataFrame(tensor.numpy()).to_csv(
        outfile,
        sep="\t",
        header=False,
        index=False
    )

print("Saving TXT files...")

write_tsv(train, 'building_evoage_kg_new/Store_House/EvoAge_121_12M_KG_train_90.txt')
del train
write_tsv(valid, 'building_evoage_kg_new/Store_House/EvoAge_121_12M_KG_valid_10.txt')
del valid
write_tsv(test,  'building_evoage_kg_new/Store_House/EvoAge_1to1_KG_test.txt')
del test

print("Done.")


# In[ ]:




