#!/usr/bin/env python
# coding: utf-8

# In[2]:


"""
═══════════════════════════════════════════════════════════════════════════════
 Biomedical-Specific KG → mapped_triples tensor
═══════════════════════════════════════════════════════════════════════════════
 Sources  : All files under Biomedical/ (Human parquets + species CSVs)
 Mappings : Pre-built node_id and relation_id from 1-to-many EvoAGE-KG
 Output   : Store_House/Biomedical_1_to_1_KG.pt  (mapped_triples [N, 3])
═══════════════════════════════════════════════════════════════════════════════
"""
import os
import glob
import warnings
import numpy as np
import pandas as pd
import torch
from tqdm import tqdm

warnings.filterwarnings('ignore')

# ── Fixed seed for reproducibility ────────────────────────────────────────────
SEED = 42
torch.manual_seed(SEED)
np.random.seed(SEED)

os.makedirs('Store_House', exist_ok=True)


# In[3]:


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — PATHS
# ═══════════════════════════════════════════════════════════════════════════════

BIOMEDICAL_BASE   = '/storage/Arushi/090526_EvoAge/kg_formation/processed_data_relation_wise_merge/Biomedical/'
STORE_HOUSE  = '/storage/Arushi/090526_EvoAge/kg_formation/final_kg_building_2/building_evoage_kg_new/Store_House'

NODE_MAP_PATH = os.path.join(STORE_HOUSE, 'node_id_mapping_EvoAge_121_12M.pkl')
REL_MAP_PATH  = os.path.join(STORE_HOUSE, 'relation_id_EvoAge_EvoAge_121_12M.csv')

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — LOAD EXISTING MAPPINGS
# ═══════════════════════════════════════════════════════════════════════════════

print("Loading pre-built mappings ...")

# Node mapping: pkl has columns ['Node', 'MappedID']
node_id_df     = pd.read_pickle(NODE_MAP_PATH)
global_mapping = dict(zip(node_id_df['Node'].astype(str), node_id_df['MappedID']))
print(f"  ✅  Nodes loaded      : {len(global_mapping):,}")

# Relation mapping: csv has columns ['Relation', 'MappedID']
rel_id_df         = pd.read_csv(REL_MAP_PATH)
relation_mapping  = dict(zip(rel_id_df['Relation'].astype(str), rel_id_df['MappedID']))
print(f"  ✅  Relations loaded  : {len(relation_mapping):,}\n")

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — COLLECT ALL FILES FROM Biomedical/
# ═══════════════════════════════════════════════════════════════════════════════

# Human parquets
human_files = sorted(glob.glob(os.path.join(BIOMEDICAL_BASE, 'Human', '**/*.parquet'), recursive=True))

# Other species CSVs — 1-to-1 orthologs ONLY
species_files = sorted([
    f for f in glob.glob(os.path.join(BIOMEDICAL_BASE, '**/*_ortho_1_to_1.csv'), recursive=True)
    if 'Human' not in f
    and '.ipynb_checkpoints' not in f
])

all_files = human_files + species_files

print(f"{'═'*60}")
print(f"  Human parquets       : {len(human_files)}")
print(f"  Species CSVs         : {len(species_files)}")
print(f"  TOTAL                : {len(all_files)}")
print(f"{'═'*60}\n")
all_files


# In[4]:


#


# In[5]:


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — HELPER
# ═══════════════════════════════════════════════════════════════════════════════

def load_file(path):
    if path.lower().endswith('.parquet'):
        return pd.read_parquet(path, columns=['head', 'tail', 'relation'])
    # case-insensitive header → usecols
    hdr = pd.read_csv(path, nrows=0)
    cols = [c for c in hdr.columns if c.lower() in {'head', 'tail', 'relation'}]
    return pd.read_csv(path, usecols=cols or None, low_memory=False)

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — CONVERT TRIPLES → MAPPED IDs
# ═══════════════════════════════════════════════════════════════════════════════

head_index_list = []
tail_index_list = []
edge_type_list  = []
unmapped_records = []

head_map_s = pd.Series(global_mapping,   dtype='int64')
tail_map_s = head_map_s
rel_map_s  = pd.Series(relation_mapping, dtype='int64')

print("Converting triples to mapped IDs ...")
for path in tqdm(all_files, desc="Triple mapping", unit="file",
                 bar_format="{l_bar}{bar:30}{r_bar}"):
    try:
        df = load_file(path)
        df.columns = df.columns.str.lower()
        if not {'head', 'tail', 'relation'}.issubset(df.columns):
            tqdm.write(f"  ⏭️  missing cols: {os.path.basename(path)}")
            continue

        df = df.dropna(subset=['head', 'tail', 'relation'])
        if df.empty:
            continue

        h = df['head'].astype(str).map(head_map_s).fillna(-1).to_numpy('int64')
        t = df['tail'].astype(str).map(tail_map_s).fillna(-1).to_numpy('int64')
        r = df['relation'].astype(str).map(rel_map_s).fillna(-1).to_numpy('int64')

        # ── collect unmapped ──────────────────────────────────────────
        mask_bad  = (h < 0) | (t < 0) | (r < 0)
        if mask_bad.any():
            bad = df[mask_bad].copy()
            bad['unmapped_head']     = h[mask_bad] < 0
            bad['unmapped_tail']     = t[mask_bad] < 0
            bad['unmapped_relation'] = r[mask_bad] < 0
            bad['source_file']       = os.path.basename(path)
            unmapped_records.append(bad)
            tqdm.write(f"  ⚠️  {mask_bad.sum()} unmapped in: {os.path.basename(path)}")

        # ── keep only fully mapped triples ────────────────────────────
        mask_good = ~mask_bad
        head_index_list.append(torch.from_numpy(h[mask_good]))
        tail_index_list.append(torch.from_numpy(t[mask_good]))
        edge_type_list.append(torch.from_numpy(r[mask_good]))
        tqdm.write(f"  ✅  {os.path.basename(path):60s}  {mask_good.sum():>8,} triples (kept)")

    except Exception as e:
        tqdm.write(f"  ❌  {os.path.basename(path)}: {e}")

# ── save unmapped audit file ──────────────────────────────────────────────────
if unmapped_records:
    unmapped_df = pd.concat(unmapped_records, ignore_index=True)
    unmapped_out = 'Store_House/unmapped_triples_Biomedical_1_to_1.csv'
    unmapped_df.to_csv(unmapped_out, index=False)
    print(f"\n  ⚠️  Total unmapped triples : {len(unmapped_df):,}  → saved to {unmapped_out}")
else:
    print("\n  ✅  No unmapped triples found")

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — CONCATENATE AND SAVE
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═'*60}")
print("  Concatenating tensors ...")

final_head  = torch.cat(head_index_list, dim=0)
final_tail  = torch.cat(tail_index_list, dim=0)
final_etype = torch.cat(edge_type_list,  dim=0)

mapped_triples = torch.stack([final_head, final_etype, final_tail], dim=1)

print(f"  mapped_triples shape : {mapped_triples.shape}")
print(f"  Total triples        : {mapped_triples.shape[0]:,}")
print(f"  Num nodes            : {len(global_mapping):,}")
print(f"  Num relations        : {len(relation_mapping):,}")

# ── remove any surviving -1 rows (safety net) ────────────────────────────────
before = mapped_triples.shape[0]
valid_mask     = (mapped_triples >= 0).all(dim=1)
mapped_triples = mapped_triples[valid_mask]
removed        = before - mapped_triples.shape[0]
if removed > 0:
    print(f"  ⚠️  Removed {removed:,} triples containing -1 (safety net)")
else:
    print(f"  ✅  All indices valid (>= 0)")

# ── dedup ─────────────────────────────────────────────────────────────────────
mt = mapped_triples
if mt.dtype != torch.int64:
    mt = mt.to(torch.int64)

H = int(mt[:, 0].max()) + 1
R = int(mt[:, 1].max()) + 1
T = int(mt[:, 2].max()) + 1

INT64_MAX = (1 << 63) - 1
fits = (H - 1) * (R * T) + (R - 1) * T + (T - 1) <= INT64_MAX

if fits:
    enc = mt[:, 0] * (R * T) + mt[:, 1] * T + mt[:, 2]
    enc = torch.unique(enc)
    tail = enc % T
    rel  = (enc // T) % R
    head = enc // (T * R)
    mapped_triples = torch.stack([head, rel, tail], dim=1)
else:
    mapped_triples = torch.unique(mapped_triples, dim=0)

print(mapped_triples.shape)

#######################################
# Save tensor
out_path = 'Store_House/Biomedical_1_to_1_KG.pt'
torch.save(mapped_triples, out_path)
print(f"\n  ✅  Saved → {out_path}")
print(f"{'═'*60}")


# In[3]:


# mapped_triples


# # SPLITING  Biomedical 1-to-1 KG

# In[1]:


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 7 — REPRODUCIBLE 80 / 10 / 10 SPLIT  (fixed seed = 42)
# ═══════════════════════════════════════════════════════════════════════════════
import os
import glob
import warnings
import numpy as np
import pandas as pd
import torch
from tqdm import tqdm

warnings.filterwarnings('ignore')

# ── Fixed seed for reproducibility ────────────────────────────────────────────
SEED = 42
torch.manual_seed(SEED)
np.random.seed(SEED)

os.makedirs('Store_House', exist_ok=True)


print(f"\n{'═'*60}")
print(f"  Splitting 80/10/10  (seed = {SEED}) ...")

Biomed_1_to_1 = torch.load('/storage/Arushi/090526_EvoAge/kg_formation/final_kg_building_2/building_biomedical_kg_new/Store_House/Biomedical_1_to_1_KG.pt')
Biomed_1_to_1

N   = Biomed_1_to_1.size(0)
print(N)

# Fixed-seed permutation — same result on any machine, any run
generator = torch.Generator()
generator.manual_seed(SEED)
perm      = torch.randperm(N, generator=generator)
shuffled  = Biomed_1_to_1[perm]

# Compute split sizes
n_train = int(N * 0.80)
n_valid = int(N * 0.10)
n_test  = N - n_train - n_valid     # remainder goes to test → ensures sum = N

train = shuffled[:n_train]
valid = shuffled[n_train : n_train + n_valid]
test  = shuffled[n_train + n_valid :]

print(f"  Train : {len(train):>12,}  ({len(train)/N*100:.1f}%)")
print(f"  Valid : {len(valid):>12,}  ({len(valid)/N*100:.1f}%)")
print(f"  Test  : {len(test):>12,}  ({len(test)/N*100:.1f}%)")

# ── Save as .pt ───────────────────────────────────────────────────────────────
torch.save(train, 'Store_House/Biomedical_1to1_KG_train_80.pt')
torch.save(valid, 'Store_House/Biomedical_1to1_KG_valid_10.pt')
torch.save(test,  'Store_House/Biomedical_1to1_KG_test_10.pt')

print(f"\n  ✅  Saved .pt  files → Store_House/train_80.pt / valid_10.pt / test_10.pt")

def write_tsv(tensor, path):
    pd.DataFrame(tensor.numpy()).to_csv(
        path, sep='\t', header=False, index=False
    )

write_tsv(train, 'Store_House/Biomedical_1to1_KG_train_80.txt')
write_tsv(valid, 'Store_House/Biomedical_1to1_KG_valid_10.txt')
write_tsv(test,  'Store_House/Biomedical_1to1_KG_test_10.txt')

print(f"  ✅  Saved .txt files → Store_House/train_80.txt / valid_10.txt / test_10.txt")

print(f"\n{'═'*60}")
print(f"  DONE")
print(f"  Total triples : {N:,}")
print(f"  Seed used     : {SEED}  ← same split every run on any machine")
print(f"{'═'*60}")


# In[1]:


#


# In[2]:


# import torch
# import pandas as pd
# from pathlib import Path

# STORE = Path("Store_House")

# # Load saved splits
# train = torch.load("Store_House/Biomedical_1to1_KG_train_80.pt")
# valid = torch.load("Store_House/Biomedical_1to1_KG_valid_10.pt")
# test  = torch.load("Store_House/Biomedical_1to1_KG_test_10.pt")

# print("Train:", train.shape)
# print("Valid:", valid.shape)
# print("Test :", test.shape)

# def write_tsv(tensor, outfile):
#     # Move to CPU if needed
#     if tensor.is_cuda:
#         tensor = tensor.cpu()

#     pd.DataFrame(tensor.numpy()).to_csv(
#         outfile,
#         sep="\t",
#         header=False,
#         index=False
#     )

# print("Saving TXT files...")

# write_tsv(train, 'Store_House/Biomedical_1to1_KG_train_80.txt')
# del train
# write_tsv(valid, 'Store_House/Biomedical_1to1_KG_valid_10.txt')
# del valid
# write_tsv(test,  'Store_House/Biomedical_1to1_KG_test_10.txt')
# del test


# print("Done.")


# In[1]:


max_step = (10 * 945427302) / 2048
max_step


# In[ ]:




