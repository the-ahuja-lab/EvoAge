#!/usr/bin/env python
# coding: utf-8

# In[1]:


"""
═══════════════════════════════════════════════════════════════════════════════
 EvoAge KG — 1-to-MANY ortholog graph → mapped_triples tensor
═══════════════════════════════════════════════════════════════════════════════
 Sources:
   1. Human files     : all relation folders under generalised/ (csv + parquet)
   2. Other species   : *_ortho_1_to_1_plus_1_to_many.csv files for each species
   3. Species nodes   : per-species Species_AssociatedWith parquet files
 Output:
   → node_id_EvoAge_1_to_1_1_to_many.pkl   (global node string → integer mapping)
   → EvoAge_1_to__1_1_to_many.pt         (mapped_triples tensor [N, 3])
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import glob
import warnings
import numpy as np
import pandas as pd
import torch
from functools import reduce
from tqdm import tqdm
import pyarrow.parquet as pq
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm.auto import tqdm

warnings.filterwarnings('ignore')

os.makedirs('building_evoage_kg_new/Store_House', exist_ok=True)


# In[2]:


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — FILE PATHS
# ═══════════════════════════════════════════════════════════════════════════════

GENERALISED  = '/storage/Arushi/090526_EvoAge/kg_formation/processed_data_relation_wise_merge/generalised/'
SPECIES_ROOT = os.path.join(GENERALISED, 'OTHER_SPECIES')

# ── Species connection folder ───────────────────────────
SPECIES_CONN_1_to_1_1_to_M = '/storage/Arushi/090526_EvoAge/kg_formation/processed_data_relation_wise_merge/making_species_assocaitedwithconnection/one2one_plus_one2many_ortholog/'

# ── Human files (all CSVs/parquets under generalised, skip OTHER_SPECIES) ─────
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
print(len(human_files))
human_files

# ── Yeast 1-to-many files ─────────────────────────────────────────────────────
yeast_files_1_to_1_1_to_many = sorted([
    f for f in glob.glob(os.path.join(SPECIES_ROOT, 'Yeast', '**/*1_to_one2one_plus_one2many.csv'), recursive=True)
    if '.ipynb_checkpoints' not in f
])
yeast_files_1_to_1_1_to_many

# ── C. elegans 1-to-many files ────────────────────────────────────────────────
celegans_files_1_to_1_1_to_many = sorted([
    f for f in glob.glob(os.path.join(SPECIES_ROOT, 'Celegans', '**/*1_to_one2one_plus_one2many.csv'), recursive=True)
    if '.ipynb_checkpoints' not in f
])
celegans_files_1_to_1_1_to_many

# ── Drosophila 1-to-many files ────────────────────────────────────────────────
drosophila_files_1_to_1_1_to_many = sorted([
    f for f in glob.glob(os.path.join(SPECIES_ROOT, 'Drosophila', '**/*1_to_one2one_plus_one2many.csv'), recursive=True)
    if '.ipynb_checkpoints' not in f
])
drosophila_files_1_to_1_1_to_many

# ── Zebrafish 1-to-many files ─────────────────────────────────────────────────
zebrafish_files_1_to_1_1_to_many = sorted([
    f for f in glob.glob(os.path.join(SPECIES_ROOT, 'Zebrafish', '**/*1_to_one2one_plus_one2many.csv'), recursive=True)
    if '.ipynb_checkpoints' not in f
])
zebrafish_files_1_to_1_1_to_many

# ── Mouse 1-to-many files ─────────────────────────────────────────────────────
mouse_files_1_to_1_1_to_many = sorted([
    f for f in glob.glob(os.path.join(SPECIES_ROOT, 'Mouse', '**/*1_to_one2one_plus_one2many.csv'), recursive=True)
    if '.ipynb_checkpoints' not in f
])
mouse_files_1_to_1_1_to_many


species_conn_files_1_to_1_1_to_many = [
    # ── Species connection parquet files (one per species 1 to many ) ────────────────────────
    os.path.join(SPECIES_CONN_1_to_1_1_to_M, 'Homo_sapiens.parquet'),
    os.path.join(SPECIES_CONN_1_to_1_1_to_M, 'Saccharomyces_cerevisiae.parquet'),
    os.path.join(SPECIES_CONN_1_to_1_1_to_M, 'Caenorhabditis_elegans.parquet'),
    os.path.join(SPECIES_CONN_1_to_1_1_to_M, 'Drosophila_melanogaster.parquet'),
    os.path.join(SPECIES_CONN_1_to_1_1_to_M, 'Danio_rerio.parquet'),
    os.path.join(SPECIES_CONN_1_to_1_1_to_M, 'Mus_musculus.parquet'),
]

# ── All files combined ────────────────────────────────────────────────────────
all_files = (
    human_files + 

    yeast_files_1_to_1_1_to_many      +
    celegans_files_1_to_1_1_to_many   +
    drosophila_files_1_to_1_1_to_many +
    zebrafish_files_1_to_1_1_to_many  +
    mouse_files_1_to_1_1_to_many      +
    species_conn_files_1_to_1_1_to_many 
)
print(len(all_files))
all_files


# In[3]:


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — HELPER: load file
# ═══════════════════════════════════════════════════════════════════════════════

def load_file(path):
    if path.lower().endswith('.parquet'):
        return pd.read_parquet(path)
    return pd.read_csv(path, low_memory=False)


# In[4]:


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — BUILD NODE MAPPING of EvoAge 121+12M
# ═══════════════════════════════════════════════════════════════════════════════
"""
Optimized global node-id mapping builder for EvoAge_1_to_many.

Key optimizations vs. the original:
  1. COLUMN PROJECTION  -> read ONLY `head` & `tail`. For Parquet this skips
     reading the other ~10 columns entirely (huge win on the 25 GB files).
  2. STREAMING / CHUNKED -> never hold a whole 25 GB file in RAM; dedup each
     batch first so the per-file set only ever grows by *new* nodes.
  3. PARALLEL across files -> the heavy I/O + uniquing is embarrassingly parallel.
  4. EXACT-SAME IDs       -> Phase 2 replays files in original order, assigning
     ids to new nodes in sorted-within-file order. This reproduces the original
     mapping byte-for-byte (np.union1d returns sorted), so downstream tensors
     that already use this mapping stay valid.

Assumption: `head`/`tail` are string node identifiers (so str-cast is identity).
"""


BATCH_ROWS = 2_000_000   # rows per streamed batch; lower this if a worker OOMs
N_JOBS     = 8           # tune to (RAM / size of largest file's unique-node set)


HEAD, TAIL = 'head', 'tail'   # literal column names; values are read untouched


def _has_head_tail(available_cols):
    """True only if columns literally named 'head' and 'tail' are present."""
    return (HEAD in set(available_cols)) and (TAIL in set(available_cols))


def file_unique_nodes(idx, path, cache_dir=None):
    """
    Return (idx, sorted np.ndarray[str] of unique head+tail nodes) for one file,
    reading ONLY head & tail and streaming in batches. Returns (idx, None) if the
    file has no head/tail columns or is empty.

    If cache_dir is given, the array is spilled to <cache_dir>/<idx>.npy and the
    path is returned instead of the array (memory-safe for billion-scale runs).
    """
    seen = set()
    try:
        if path.lower().endswith('.parquet'):
            pf = pq.ParquetFile(path)
            if not _has_head_tail(pf.schema_arrow.names):
                return idx, None
            for batch in pf.iter_batches(columns=[HEAD, TAIL], batch_size=BATCH_ROWS):
                d = batch.to_pandas()
                # dedup *within the batch* first -> only push new-ish strings to set
                seen.update(pd.unique(d[HEAD].astype(str)))
                seen.update(pd.unique(d[TAIL].astype(str)))
        else:
            if not _has_head_tail(pd.read_csv(path, nrows=0).columns):
                return idx, None
            for chunk in pd.read_csv(path, usecols=[HEAD, TAIL], dtype=str,
                                     chunksize=BATCH_ROWS, low_memory=False):
                seen.update(pd.unique(chunk[HEAD].astype(str)))
                seen.update(pd.unique(chunk[TAIL].astype(str)))
    except Exception as e:
        print(f"  ❌  Mapping error {os.path.basename(path)}: {e}")
        return idx, None

    if not seen:
        return idx, None

    arr = np.fromiter(seen, dtype=object, count=len(seen))
    arr.sort()   # matches np.union1d's sorted output -> identical id assignment

    if cache_dir is not None:
        out = os.path.join(cache_dir, f"{idx}.npy")
        np.save(out, arr, allow_pickle=True)
        return idx, out
    return idx, arr


def build_global_mapping(all_files, n_jobs=N_JOBS, cache_dir=None):
    """Parallel Phase 1 (per-file uniques) + ordered Phase 2 (id assignment)."""
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)

    print("Phase 1: extracting per-file unique nodes (parallel) ...")
    results = [None] * len(all_files)
    with ProcessPoolExecutor(max_workers=n_jobs) as ex:
        futs = [ex.submit(file_unique_nodes, i, p, cache_dir)
                for i, p in enumerate(all_files)]
        for fut in tqdm(as_completed(futs), total=len(futs),
                        desc="Node mapping", unit="file"):
            i, payload = fut.result()
            results[i] = payload

    print("Phase 2: assigning ids in original file order ...")
    global_mapping = {}
    n = 0
    for payload in results:                       # original file order preserved
        if payload is None:
            continue
        arr = np.load(payload, allow_pickle=True) if isinstance(payload, str) else payload
        for name in arr:                          # sorted within file
            if name not in global_mapping:
                global_mapping[name] = n
                n += 1
    return global_mapping


if __name__ == "__main__":
    # all_files = [...]  # your existing list of 185 paths
    global_mapping = build_global_mapping(all_files, n_jobs=N_JOBS)
    print(f"\n  ✅  Total unique nodes: {len(global_mapping):,}\n")

    node_id_df = pd.DataFrame({
        'Node':     list(global_mapping.keys()),
        'MappedID': list(global_mapping.values()),
    })
node_id_df


# In[ ]:


node_id_df.to_pickle('building_evoage_kg_new/Store_House/node_id_mapping_EvoAge_121_12M.pkl')
print("Node mapping saved → building_evoage_kg_new/Store_House/node_id_mapping_EvoAge_121_12M.pkl")


# In[ ]:


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — RELATION MAPPING
# ═══════════════════════════════════════════════════════════════════════════════

RELATION   = 'relation'   # literal column name; values read untouched
BATCH_ROWS = 2_000_000
N_JOBS     = 8


def file_unique_relations(idx, path, cache_dir=None):
    """
    Return (idx, np.ndarray[str] of unique relations in FIRST-APPEARANCE order)
    for one file, reading ONLY the `relation` column and streaming in batches.
    Nulls are dropped. Returns (idx, None) if there's no `relation` column / no data.

    If cache_dir is given, spills to <cache_dir>/<idx>.npy and returns the path.
    """
    seen = {}   # dict preserves insertion order -> ordered set
    try:
        if path.lower().endswith('.parquet'):
            pf = pq.ParquetFile(path)
            if RELATION not in set(pf.schema_arrow.names):
                return idx, None
            for batch in pf.iter_batches(columns=[RELATION], batch_size=BATCH_ROWS):
                s = batch.to_pandas()[RELATION].dropna().astype(str)
                for r in pd.unique(s):          # first-appearance order within batch
                    if r not in seen:
                        seen[r] = None
        else:
            if RELATION not in set(pd.read_csv(path, nrows=0).columns):
                return idx, None
            for chunk in pd.read_csv(path, usecols=[RELATION], dtype=str,
                                     chunksize=BATCH_ROWS, low_memory=False):
                s = chunk[RELATION].dropna().astype(str)
                for r in pd.unique(s):
                    if r not in seen:
                        seen[r] = None
    except Exception as e:
        print(f"  ❌  Relation error {os.path.basename(path)}: {e}")
        return idx, None

    if not seen:
        return idx, None

    arr = np.array(list(seen.keys()), dtype=object)   # first-appearance order
    if cache_dir is not None:
        out = os.path.join(cache_dir, f"rel_{idx}.npy")
        np.save(out, arr, allow_pickle=True)
        return idx, out
    return idx, arr


def build_relation_mapping(all_files, n_jobs=N_JOBS, cache_dir=None):
    """Parallel Phase 1 (per-file relations) + ordered Phase 2 (id assignment)."""
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)

    print("Phase 1: extracting per-file relations (parallel) ...")
    results = [None] * len(all_files)
    with ProcessPoolExecutor(max_workers=n_jobs) as ex:
        futs = [ex.submit(file_unique_relations, i, p, cache_dir)
                for i, p in enumerate(all_files)]
        for fut in tqdm(as_completed(futs), total=len(futs),
                        desc="Relation mapping", unit="file"):
            i, payload = fut.result()
            results[i] = payload

    print("Phase 2: assigning ids in original file order ...")
    relation_mapping = {}
    n = 0
    for payload in results:                       # original file order
        if payload is None:
            continue
        arr = np.load(payload, allow_pickle=True) if isinstance(payload, str) else payload
        for rel in arr:                           # first-appearance order
            if rel not in relation_mapping:
                relation_mapping[rel] = n
                n += 1
    return relation_mapping


if __name__ == "__main__":
    # all_files = [...]  # your existing list of paths
    relation_mapping = build_relation_mapping(all_files, n_jobs=N_JOBS)
    print(f"\n  ✅  Total unique relations: {len(relation_mapping):,}")
    print(relation_mapping)


# In[ ]:


# Save relation mapping
rel_id_df = pd.DataFrame({
    'Relation': list(relation_mapping.keys()),
    'MappedID': list(relation_mapping.values()),
})

rel_id_df.to_csv('building_evoage_kg_new/Store_House/relation_id_EvoAge_EvoAge_121_12M.csv', index=False)
print(f"  Relation mapping saved → building_evoage_kg_new/Store_House/relation_id_EvoAge_1_to_many.pkl\n")
rel_id_df


# In[ ]:


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — CONVERT TRIPLES TO MAPPED IDs → BUILD TENSOR
# ═══════════════════════════════════════════════════════════════════════════════
def load_file(path):
    if path.lower().endswith('.parquet'):
        return pd.read_parquet(path, columns=['head', 'tail', 'relation'])
    # case-insensitive header → usecols
    hdr = pd.read_csv(path, nrows=0)
    cols = [c for c in hdr.columns if c.lower() in {'head', 'tail', 'relation'}]
    return pd.read_csv(path, usecols=cols or None, low_memory=False)

head_index_list = []
tail_index_list = []
edge_type_list  = []

# Convert mapping dicts to pandas Series ONCE (outside the loop).
# .map(Series) is C-speed; .map(dict) per-element is not as fast for big frames.
head_map_s = pd.Series(global_mapping,   dtype='int64')
tail_map_s = head_map_s                       # same node mapping for both sides
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

        # Vectorised lookup: astype(str) → map(Series) → unmapped become NaN → -1 → int64
        h = df['head'].astype(str).map(head_map_s).fillna(-1).to_numpy('int64')
        t = df['tail'].astype(str).map(tail_map_s).fillna(-1).to_numpy('int64')
        r = df['relation'].astype(str).map(rel_map_s).fillna(-1).to_numpy('int64')

        head_ids   = torch.from_numpy(h)
        tail_ids   = torch.from_numpy(t)
        edge_types = torch.from_numpy(r)

        if (h < 0).any() or (t < 0).any() or (r < 0).any():
            tqdm.write(f"  ⚠️  unmapped values in: {os.path.basename(path)}")

        head_index_list.append(head_ids)
        tail_index_list.append(tail_ids)
        edge_type_list.append(edge_types)
        tqdm.write(f"  ✅  {os.path.basename(path):60s}  {len(df):>8,} triples")

    except Exception as e:
        tqdm.write(f"  ❌  {os.path.basename(path)}: {e}")


# In[ ]:


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

# Validity check
if torch.all(mapped_triples >= 0):
    print("  ✅  All indices valid (>= 0)")
else:
    neg = (mapped_triples < 0).sum().item()
    print(f"  ⚠️  {neg} invalid indices found (value = -1)")


# In[ ]:


print(mapped_triples.shape)

mt = mapped_triples
if mt.dtype != torch.int64:
    mt = mt.to(torch.int64)

# per-column ranges define a bijective, order-preserving packing
H = int(mt[:, 0].max()) + 1
R = int(mt[:, 1].max()) + 1
T = int(mt[:, 2].max()) + 1

INT64_MAX = (1 << 63) - 1
fits = (H - 1) * (R * T) + (R - 1) * T + (T - 1) <= INT64_MAX   # Python big-ints → safe check

if fits:
    enc = mt[:, 0] * (R * T) + mt[:, 1] * T + mt[:, 2]   # [N] int64
    enc = torch.unique(enc)                              # sorted 1-D unique — the fast path
    tail = enc % T
    rel  = (enc // T) % R
    head = enc // (T * R)
    mapped_triples = torch.stack([head, rel, tail], dim=1)
else:
    mapped_triples = torch.unique(mapped_triples, dim=0)  # ranges too big to pack — fall back

print(mapped_triples.shape)
mapped_triples

# Save
torch.save(mapped_triples, 'building_evoage_kg_new/Store_House/EvoAge_121_12M_to_many_KG.pt')
print(f"\n  ✅  Saved → building_evoage_kg_new/Store_House/EvoAge_1_to_many_KG.pt")
print(f"{'═'*60}")


# In[ ]:


# Splitting EvoAge

