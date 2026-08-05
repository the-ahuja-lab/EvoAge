#!/usr/bin/env python
# coding: utf-8

# In[1]:


#


# In[1]:


"""
═══════════════════════════════════════════════════════════════════════════════
 EvoAge 1-to-MANY KG — Build edge tensors + 80/10/10 reproducible split
═══════════════════════════════════════════════════════════════════════════════
 - Uses EXISTING node mapping: node_id_EvoAge_1_to_many.pkl  (no rebuild)
 - Uses EXISTING relation mapping: relation_id_EvoAge_1_to_many.pkl
 - Builds mapped_triples tensor [N, 3] → (head_id, relation_id, tail_id)
 - Splits 80/10/10 with fixed seed for full reproducibility
 - Saves train/valid/test as .txt AND .pt
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

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — FILE PATHS  (same order as KG building script)
# ═══════════════════════════════════════════════════════════════════════════════

GENERALISED  = '/storage/Arushi/090526_EvoAge/kg_formation/processed_data_relation_wise_merge/generalised'
SPECIES_ROOT = os.path.join(GENERALISED, 'OTHER_SPECIES')

# ── Human files ───────────────────────────────────────────────────────────────
human_files = (
    glob.glob(os.path.join(GENERALISED, '**/*.csv'),     recursive=True) +
    glob.glob(os.path.join(GENERALISED, '**/*.parquet'), recursive=True)
)
human_files = sorted([
    f for f in human_files
    if 'OTHER_SPECIES'       not in f
    and '.ipynb_checkpoints' not in f
    and not os.path.basename(f).startswith('_')
    and not os.path.basename(f).endswith('.bak')
])

# ── Other species 1-to-1 files ────────────────────────────────────────────────
yeast_files = sorted([
    f for f in glob.glob(os.path.join(SPECIES_ROOT, 'Yeast',      '**/*_ortho_1_to_1.csv'), recursive=True)
    if '.ipynb_checkpoints' not in f
])
print(len(yeast_files))
celegans_files = sorted([
    f for f in glob.glob(os.path.join(SPECIES_ROOT, 'Celegans',   '**/*_ortho_1_to_1.csv'), recursive=True)
    if '.ipynb_checkpoints' not in f
])
print(len(celegans_files))
drosophila_files = sorted([
    f for f in glob.glob(os.path.join(SPECIES_ROOT, 'Drosophila', '**/*_ortho_1_to_1.csv'), recursive=True)
    if '.ipynb_checkpoints' not in f
])
print(len(drosophila_files))
zebrafish_files = sorted([
    f for f in glob.glob(os.path.join(SPECIES_ROOT, 'Zebrafish',  '**/*_ortho_1_to_1.csv'), recursive=True)
    if '.ipynb_checkpoints' not in f
])
print(len(zebrafish_files))
mouse_files = sorted([
    f for f in glob.glob(os.path.join(SPECIES_ROOT, 'Mouse',      '**/*_ortho_1_to_1.csv'), recursive=True)
    if '.ipynb_checkpoints' not in f
])
print(len(mouse_files))
# ── Species connection — use 1_to_1_ortholog folder ───────────────────────────
SPECIES_CONN = '/storage/Arushi/090526_EvoAge/kg_formation/processed_data_relation_wise_merge/making_species_assocaitedwithconnection/1_to_1_ortholog'

species_conn_files = [
    os.path.join(SPECIES_CONN, 'Homo_sapiens.parquet'),
    os.path.join(SPECIES_CONN, 'Saccharomyces_cerevisiae.parquet'),
    os.path.join(SPECIES_CONN, 'Caenorhabditis_elegans.parquet'),
    os.path.join(SPECIES_CONN, 'Drosophila_melanogaster.parquet'),
    os.path.join(SPECIES_CONN, 'Danio_rerio.parquet'),
    os.path.join(SPECIES_CONN, 'Mus_musculus.parquet'),
]

# ── All files combined ────────────────────────────────────────────────────────
all_files = (
    human_files      +
    yeast_files      +
    celegans_files   +
    drosophila_files +
    zebrafish_files  +
    mouse_files      +
    species_conn_files
)
all_files


# In[2]:


len(all_files)
# len(human_files)


# In[3]:


print(f"{'═'*60}")
print(f"  Human files          : {len(human_files)}")
print(f"  Yeast 1-to-1      : {len(yeast_files)}")
print(f"  C.elegans 1-to-1  : {len(celegans_files)}")
print(f"  Drosophila 1-to-1 : {len(drosophila_files)}")
print(f"  Zebrafish 1-to-1  : {len(zebrafish_files)}")
print(f"  Mouse 1-to-1      : {len(mouse_files)}")
print(f"  Species conn files   : {len(species_conn_files)}")
print(f"  TOTAL                : {len(all_files)}")
print(f"{'═'*60}\n")


# In[ ]:





# In[4]:


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — LOAD EXISTING MAPPINGS  (no rebuild)
# ═══════════════════════════════════════════════════════════════════════════════

print("Loading existing node and relation mappings ...")

node_id_df   = pd.read_pickle('Store_House/node_id_mapping_EvoAge_121_12M.pkl')
relation_df  = pd.read_csv('Store_House/relation_id_EvoAge_EvoAge_121_12M.csv')

global_mapping   = dict(zip(node_id_df['Node'].astype(str),     node_id_df['MappedID']))
relation_mapping = dict(zip(relation_df['Relation'].astype(str), relation_df['MappedID']))

print(f"  ✅  Nodes loaded     : {len(global_mapping):,}")
print(f"  ✅  Relations loaded : {len(relation_mapping):,}\n")


# In[5]:


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — HELPER: load file
# ═══════════════════════════════════════════════════════════════════════════════

def load_file(path):
    if path.lower().endswith('.parquet'):
        return pd.read_parquet(path)
    return pd.read_csv(path, low_memory=False)

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — CONVERT TRIPLES → MAPPED IDs
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
    unmapped_out = 'Store_House/unmapped_triples_EvoAge_1_to_1.csv'
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
##############################################################


# Save full KG tensor
torch.save(mapped_triples, 'Store_House/EvoAge_1_to_1_KG.pt')
print(f"  ✅  Full KG saved → Store_House/EvoAge_1_to_1_KG.pt")


# In[7]:


mapped_triples


# In[6]:


mapped_triples


# # Splitting

# In[9]:


get_ipython().system('ls /storage/Arushi/090526_EvoAge/kg_formation/')


# In[2]:


"""
═══════════════════════════════════════════════════════════════════════════════
 EvoAge 1-to-1 KG — Smart 80/10/10 Split  [SCALE-SAFE VERSION]
═══════════════════════════════════════════════════════════════════════════════
 
   - Replaced tensor_to_set() with encode → sort → searchsorted
   - Never converts to Python sets or lists (avoids OOM on 1.24B rows)
   - All operations stay in PyTorch / int64
   - Added MAX_ID safety check before encoding
   - Added explicit del + gc.collect() after large intermediates
   - Added torch.save checkpoints after each major step
   - Added post-save reload verification (shape check)
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import gc
import torch
import numpy as np

SEED = 42
torch.manual_seed(SEED)
np.random.seed(SEED)

# ═══════════════════════════════════════════════════════════════════════════════
# PATHS
# ═══════════════════════════════════════════════════════════════════════════════

BASE = '/storage/Arushi/090526_EvoAge/kg_formation/final_kg_building_2/'

AGING_TEST      = os.path.join(BASE, 'building_aging_kg_new/Store_House/Aging_specific_1to1_KG_test_10.pt')
BIOMEDICAL_TEST = os.path.join(BASE, 'building_biomedical_kg_new/Store_House/Biomedical_1to1_KG_test_10.pt')
EVOAGE_FULL     = os.path.join(BASE, 'building_evoage_kg_new/Store_House/EvoAge_1_to_1_KG.pt')

OUT_DIR = os.path.join(BASE, 'building_evoage_kg_new/Store_House')
os.makedirs(OUT_DIR, exist_ok=True)

TRAIN_OUT = os.path.join(OUT_DIR, 'EvoAge_1to1_KG_train_80.pt')
VALID_OUT = os.path.join(OUT_DIR, 'EvoAge_1to1_KG_valid_10.pt')
TEST_OUT  = os.path.join(OUT_DIR, 'EvoAge_1to1_KG_test_10.pt')

# ═══════════════════════════════════════════════════════════════════════════════
# HELPER — encode (h, r, t) → single int64 for vectorized lookup
# ═══════════════════════════════════════════════════════════════════════════════

def make_encoder(triples_list):
    """
    Compute a safe MAX multiplier from actual max IDs across all tensors.
    Checks that encoding won't overflow int64.
    """
    global_max = max(t.max().item() for t in triples_list)
    MAX_ID = int(global_max) + 1

    # int64 max = 9,223,372,036,854,775,807
    # We need MAX_ID^2 < int64_max for encoding h*MAX^2 + r*MAX + t
    import math
    int64_max = 2**63 - 1
    if MAX_ID ** 2 > int64_max:
        raise OverflowError(
            f"MAX_ID={MAX_ID:,} → MAX_ID^2={MAX_ID**2:,} overflows int64!\n"
            f"Your entity IDs are too large for this encoding scheme.\n"
            f"Use a smaller multiplier or hash-based approach."
        )

    print(f"  MAX_ID across all tensors : {MAX_ID:>15,}")
    print(f"  Encoding multiplier       : {MAX_ID:>15,}  (safe, no int64 overflow)")

    def encode(t):
        """(N, 3) int64 tensor → (N,) int64 encoded"""
        M = torch.tensor(MAX_ID, dtype=torch.int64)
        return t[:, 0] * M * M + t[:, 1] * M + t[:, 2]

    return encode, MAX_ID


def subtract_encoded(full_enc, sub_enc):
    """
    Given encoded full and encoded subtract tensors,
    return boolean mask: True where full_enc[i] is NOT in sub_enc.
    Uses sort + searchsorted — O(N log M), no Python objects.
    """
    sub_sorted, _ = sub_enc.sort()
    # searchsorted finds where each full value would be inserted
    idx = torch.searchsorted(sub_sorted, full_enc)
    idx = idx.clamp(max=sub_sorted.shape[0] - 1)
    # If the value at that position equals full_enc → it's in sub → mask=False
    in_sub = (sub_sorted[idx] == full_enc)
    return ~in_sub   # True = keep (NOT in subtract set)


def verify_save(path, expected_shape):
    """Reload saved file and confirm shape matches."""
    loaded = torch.load(path)
    assert loaded.shape == expected_shape, (
        f"VERIFY FAILED: {path}\n"
        f"  Expected {expected_shape}, got {tuple(loaded.shape)}"
    )
    print(f"  ✓ Verified: {os.path.basename(path)}  shape={tuple(loaded.shape)}")
    del loaded


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 1 — Load all tensors
# ═══════════════════════════════════════════════════════════════════════════════

print(f"{'═'*65}")
print("  STEP 1 — Loading tensors")
print(f"{'═'*65}")

aging_test      = torch.load(AGING_TEST)
biomedical_test = torch.load(BIOMEDICAL_TEST)
evoage_full     = torch.load(EVOAGE_FULL)

# Enforce int64 throughout — never let dtypes silently mismatch
assert aging_test.dtype      == torch.int64, "aging_test must be int64"
assert biomedical_test.dtype == torch.int64, "biomedical_test must be int64"
assert evoage_full.dtype     == torch.int64, "evoage_full must be int64"
assert aging_test.shape[1]      == 3, "Expected (N, 3) triples"
assert biomedical_test.shape[1] == 3, "Expected (N, 3) triples"
assert evoage_full.shape[1]     == 3, "Expected (N, 3) triples"

print(f"  Aging 1-to-1 test set     : {aging_test.shape[0]:>15,} triples  shape={tuple(aging_test.shape)}")
print(f"  Biomedical 1-to-1 test set: {biomedical_test.shape[0]:>15,} triples  shape={tuple(biomedical_test.shape)}")
print(f"  EvoAge 1-to-1 full KG     : {evoage_full.shape[0]:>15,} triples  shape={tuple(evoage_full.shape)}")

N_full = evoage_full.shape[0]

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 1b — Safety check: MAX_ID for encoding
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═'*65}")
print("  STEP 1b — Checking max entity/relation IDs for safe encoding")
print(f"{'═'*65}")

encode, MAX_ID = make_encoder([aging_test, biomedical_test, evoage_full])

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 2 — Combine Aging + Biomedical test → AB_test (deduped)
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═'*65}")
print("  STEP 2 — Combining Aging test + Biomedical test → AB_test")
print(f"{'═'*65}")

AB_test = torch.cat([aging_test, biomedical_test], dim=0)
n_before_dedup = AB_test.shape[0]

# Free originals — no longer needed separately
del aging_test, biomedical_test
gc.collect()

# Deduplicate via encode → unique → decode is NOT needed;
# torch.unique on encoded scalars is much faster than torch.unique(dim=0) on (N,3)
AB_enc = encode(AB_test)
AB_enc_unique = torch.unique(AB_enc)   # unique encoded values

# We need the actual triples, not just encodings.
# Strategy: sort AB_test by encoding, then pick unique positions.
sort_idx = AB_enc.argsort()
AB_sorted_enc = AB_enc[sort_idx]
AB_sorted_triples = AB_test[sort_idx]

# unique_consecutive on sorted → get first occurrence of each unique value
unique_mask = torch.ones(AB_sorted_enc.shape[0], dtype=torch.bool)
unique_mask[1:] = AB_sorted_enc[1:] != AB_sorted_enc[:-1]

AB_test_unique = AB_sorted_triples[unique_mask].contiguous()

del AB_test, AB_enc, AB_enc_unique, sort_idx, AB_sorted_enc, AB_sorted_triples, unique_mask
gc.collect()

n_after_dedup = AB_test_unique.shape[0]
print(f"  Combined (before dedup)   : {n_before_dedup:>15,}")
print(f"  Combined (after dedup)    : {n_after_dedup:>15,}")
print(f"  Duplicates removed        : {n_before_dedup - n_after_dedup:>15,}")


# In[3]:


##


# In[4]:


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 3 — Subtract AB_test from EvoAge (CHUNKED).  Kept → train/valid.  Removed → TEST.
# ═══════════════════════════════════════════════════════════════════════════════
print(f"\n{'═'*65}")
print("  STEP 3 — Subtracting AB_test from EvoAge (chunked, RAM-safe)")
print(f"{'═'*65}")

CHUNK = 50_000_000   # rows per slice; lower if RAM still tight

# Sort the SMALL AB keys ONCE (~0.9 GB), then stream EvoAge past it.
ab_sorted, _ = torch.sort(encode(AB_test_unique))
M_ab = ab_sorted.numel()

keep_parts, test_parts = [], []
found_in_evoage = 0

for s in range(0, N_full, CHUNK):
    block = evoage_full[s:s+CHUNK]                       # only this slice in RAM
    keys  = encode(block)
    pos   = torch.searchsorted(ab_sorted, keys).clamp_(max=M_ab - 1)
    in_ab = ab_sorted[pos] == keys                       # True = matches an AB test triple

    found_in_evoage += int(in_ab.sum())
    test_parts.append(block[in_ab].contiguous())         # removed rows → TEST
    keep_parts.append(block[~in_ab].contiguous())        # kept rows → train/valid
    print(f"    processed {min(s+CHUNK, N_full):,}/{N_full:,}")

del ab_sorted
gc.collect()

not_in_evoage = n_after_dedup - found_in_evoage

print(f"  EvoAge full KG            : {N_full:>15,}")
print(f"  AB_test (deduped)         : {n_after_dedup:>15,}")
print(f"  AB found in EvoAge → TEST : {found_in_evoage:>15,}")
print(f"  AB NOT in EvoAge (dropped): {not_in_evoage:>15,}")

# --- concat without torch.cat's 2x spike (pops as it goes) ---
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

remaining   = concat_free(keep_parts)    # → train + valid
evoage_test = concat_free(test_parts)     # → test set

del evoage_full, AB_test_unique
gc.collect()

print(f"  Remaining (train+valid)   : {remaining.shape[0]:>15,}")
print(f"  Test set size             : {evoage_test.shape[0]:>15,}")


# In[5]:


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 4 — Shuffle the remaining triples (fixed seed)
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═'*65}")
print(f"  STEP 4 — Shuffling remaining triples (seed={SEED})")
print(f"{'═'*65}")

N_remaining = remaining.shape[0]
generator   = torch.Generator()
generator.manual_seed(SEED)
perm        = torch.randperm(N_remaining, generator=generator)
shuffled    = remaining[perm].contiguous()

del remaining, perm
gc.collect()

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 5 — 90 / 10 split of the remaining (leakage-free) pool
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═'*65}")
print("  STEP 5 — Splitting remaining 90/10 → train/valid")
print(f"{'═'*65}")

n_train = int(N_remaining * 0.90)
train   = shuffled[:n_train].contiguous()
valid   = shuffled[n_train:].contiguous()

del shuffled
gc.collect()

print(f"  Train : {len(train):>15,}  ({len(train)/N_remaining*100:.1f}% of remaining)")
print(f"  Valid : {len(valid):>15,}  ({len(valid)/N_remaining*100:.1f}% of remaining)")
print(f"  Test  : {len(evoage_test):>15,}  (AB triples held out)")

total = len(train) + len(valid) + len(evoage_test)
print(f"  Sum check : {total:,}  (should = N_full = {N_full:,})")
assert total == N_full, (
    f"SPLIT SUM MISMATCH: {total:,} ≠ {N_full:,}\n"
    "train + valid + test must equal the full EvoAge KG."
)

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 6 — Save + verify
# ═══════════════════════════════════════════════════════════════════════════════

TRAIN_OUT = os.path.join(OUT_DIR, 'EvoAge_1to1_KG_train_90.pt')
VALID_OUT = os.path.join(OUT_DIR, 'EvoAge_1to1_KG_valid_10.pt')
TEST_OUT  = os.path.join(OUT_DIR, 'EvoAge_1to1_KG_test.pt')

print(f"\n{'═'*65}")
print("  STEP 6 — Saving + verifying")
print(f"{'═'*65}")

torch.save(train,       TRAIN_OUT)
torch.save(valid,       VALID_OUT)
torch.save(evoage_test, TEST_OUT)

verify_save(TRAIN_OUT, tuple(train.shape))
verify_save(VALID_OUT, tuple(valid.shape))
verify_save(TEST_OUT,  tuple(evoage_test.shape))

print(f"\n{'═'*65}")
print("  ✓ ALL DONE — train/valid/test saved and verified")
print(f"{'═'*65}")


# In[7]:


get_ipython().system('ls Store_House')


# In[ ]:





# In[ ]:





# In[ ]:





# In[8]:


import torch
import pandas as pd
from pathlib import Path

STORE = Path("Store_House")

# Load saved splits
train = torch.load("Store_House/EvoAge_1to1_KG_train_90.pt")
valid = torch.load("Store_House/EvoAge_1to1_KG_valid_10.pt")

print("Train:", train.shape)
print("Valid:", valid.shape)

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

write_tsv(train, 'Store_House/EvoAge_1to1_KG_train_90.txt')
del train
write_tsv(valid, 'Store_House/EvoAge_1to1_KG_valid_10.txt')
del valid


print("Done.")


# In[9]:


max_step = (10 * 1000744942) / 2048
max_step


# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:




