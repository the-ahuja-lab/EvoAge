# 7. Building Final KG Tensors & Train/Valid/Test Splitting

This section covers the last stage before training: converting the split, ortholog-mapped CSV/Parquet files ([KG Construction](kg-construction.md)) into integer-encoded PyTorch tensors, and creating leakage-free train/valid/test splits across **four KG variants** — Aging (1-to-1), Biomedical (1-to-1), EvoAge (1-to-1), and EvoAge (121+12M).

The single most important structural decision in this stage is the **global node and relation mapping**: it is built **once**, from the largest KG (EvoAge 121+12M), and every other KG variant — Aging, Biomedical, EvoAge 1-to-1 — reuses that exact same mapping rather than building its own. This is what makes the four KG variants directly comparable.

---

## **7.1 Build Order (Critical — Do Not Reorder)**

The scripts must run in this exact order, because each later step depends on an artifact produced by an earlier one:

```
1. EvoAge_1_to_1_1_to_M.py   ← Builds the GLOBAL node_id + relation_id mapping
                                 (from the EvoAge 121+12M file set — the largest)
                              ← Produces:
                                  Store_House/node_id_mapping_EvoAge_121_12M.pkl
                                  Store_House/relation_id_EvoAge_EvoAge_121_12M.csv
                              ← Builds EvoAge_121_12M_to_many_KG.pt
                                 (deferred — actually run AFTER step 2, see §7.5)

2. EvoAge_1_to_1.py          ← Reuses the global mapping from step 1
                              ← Builds EvoAge_1_to_1_KG.pt
                              ← Splits into EvoAge_1to1_KG_test (= AB_test, see §7.4)
                                 + train_90 / valid_10

3. Aging_1_to_1.py           ← Reuses the SAME global mapping
                              ← Builds Aging_specific_1_to_1_KG.pt
                              ← Splits 80/10/10 → train_80 / valid_10 / test_10

4. Biomedical_1_to_1.py      ← Reuses the SAME global mapping
                              ← Builds Biomedical_1_to_1_KG.pt
                              ← Splits 80/10/10 → train_80 / valid_10 / test_10

   [Steps 3 + 4 must complete before re-entering EvoAge_1_to_1.py's splitting
    section, because that section needs Aging_specific_1to1_KG_test_10.pt and
    Biomedical_1to1_KG_test_10.pt as inputs — see §7.4]

5. Aging_121_12M.py          ← Reuses the SAME global mapping
                              ← Builds Aging_specific_121_12M_KG.pt
                              ← Removes the Aging 1-to-1 test set from it, then
                                90/10 splits the remainder → train_90 / valid_10

6. Biomedical_121_12M.py     ← Reuses the SAME global mapping
                              ← Builds Biomedical_121_12M_KG.pt (same pattern as #5)

7. (back to) EvoAge_1_to_1_1_to_M.py's later cells
                              ← Builds EvoAge_121_12M_to_many_KG.pt
                              ← Removes EvoAge_1to1_KG_test from it, then
                                90/10 splits the remainder → train_90 / valid_10
```

---

## **7.2 Building the Global Node & Relation Mapping**

**Script**: `EvoAge_1_to_1_1_to_M.py` (Section: "BUILD NODE MAPPING of EvoAge 121+12M")

The mapping is built from the **complete EvoAge 121+12M file set** — Human files plus all five species' `*_ortho_1_to_one2one_plus_one2many.csv` files plus six species-connection parquet files.

### **Why a custom parallel builder instead of `pd.unique()` on everything at once**

Some of these files are 25GB+. The builder is deliberately engineered for this scale:

```python
BATCH_ROWS = 2_000_000   # rows per streamed batch
N_JOBS     = 8           # parallel workers across files

def file_unique_nodes(idx, path, cache_dir=None):
    """Read ONLY head & tail columns, streaming in batches, dedup per-batch."""
    seen = set()
    if path.lower().endswith('.parquet'):
        pf = pq.ParquetFile(path)
        for batch in pf.iter_batches(columns=['head', 'tail'], batch_size=BATCH_ROWS):
            d = batch.to_pandas()
            seen.update(pd.unique(d['head'].astype(str)))
            seen.update(pd.unique(d['tail'].astype(str)))
    else:
        for chunk in pd.read_csv(path, usecols=['head', 'tail'], dtype=str,
                                 chunksize=BATCH_ROWS, low_memory=False):
            seen.update(pd.unique(chunk['head'].astype(str)))
            seen.update(pd.unique(chunk['tail'].astype(str)))

    arr = np.fromiter(seen, dtype=object, count=len(seen))
    arr.sort()   # sorted output matches np.union1d's behavior — reproducible IDs
    return idx, arr
```

Four optimizations stacked together:

1. **Column projection** — only `head`/`tail` are read.
2. **Streaming/chunked** — no file is ever held whole in RAM.
3. **Parallel across files** — `ProcessPoolExecutor` runs `file_unique_nodes` concurrently.
4. **Deterministic ID assignment** — Phase 2 replays files in original list order, making the resulting mapping exactly reproducible.

```python
def build_global_mapping(all_files, n_jobs=8, cache_dir=None):
    # Phase 1: parallel per-file unique extraction
    with ProcessPoolExecutor(max_workers=n_jobs) as ex:
        futs = [ex.submit(file_unique_nodes, i, p, cache_dir) for i, p in enumerate(all_files)]
        results = [None] * len(all_files)
        for fut in as_completed(futs):
            i, payload = fut.result()
            results[i] = payload

    # Phase 2: sequential, ORDER-PRESERVING id assignment
    global_mapping = {}
    n = 0
    for payload in results:           # original order
        arr = np.load(payload, allow_pickle=True) if isinstance(payload, str) else payload
        for name in arr:
            if name not in global_mapping:
                global_mapping[name] = n
                n += 1
    return global_mapping
```

### **Saved artifacts**

```python
node_id_df.to_pickle('Store_House/node_id_mapping_EvoAge_121_12M.pkl')        # ['Node', 'MappedID']
rel_id_df.to_csv('Store_House/relation_id_EvoAge_EvoAge_121_12M.csv')         # ['Relation', 'MappedID']
```

Every other script loads these files and never rebuilds them.

---

## **7.3 The Shared Triple-Mapping Pattern**

Every KG-variant script converts its CSV/Parquet files into an integer tensor using the **same four-part pattern**:

### **Part 1 — Collect the right file set**

Each variant pulls from a different combination:

| Variant | Human source | Species source pattern |
|---|---|---|
| Aging (1-to-1) | `Aging_specific/Human/**/*.parquet` | `Aging_specific/**/*_ortho_1_to_1.csv` |
| Aging (121+12M) | `Aging_specific/Human/**/*.parquet` | `Aging_specific/**/*1_to_one2one_plus_one2many.csv` |
| Biomedical (1-to-1) | `Biomedical/Human/**/*.parquet` | `Biomedical/**/*_ortho_1_to_1.csv` |
| Biomedical (121+12M) | `Biomedical/Human/**/*.parquet` | `Biomedical/**/*ortho_1_to_one2one_plus_one2many.csv` |
| EvoAge (1-to-1) | `generalised/**/*.csv` + `*.parquet` (excl. `OTHER_SPECIES`) | `OTHER_SPECIES/<Species>/**/*_ortho_1_to_1.csv` **+ 6 species-connection parquet files** |
| EvoAge (121+12M) | same human files | `**/*1_to_one2one_plus_one2many.csv` **+ 6 species-connection parquet files** |

### **Part 2 — Vectorized ID lookup via `pd.Series.map`**

```python
head_map_s = pd.Series(global_mapping,   dtype='int64')
tail_map_s = head_map_s
rel_map_s  = pd.Series(relation_mapping, dtype='int64')

h = df['head'].astype(str).map(head_map_s).fillna(-1).to_numpy('int64')
t = df['tail'].astype(str).map(tail_map_s).fillna(-1).to_numpy('int64')
r = df['relation'].astype(str).map(rel_map_s).fillna(-1).to_numpy('int64')
```

### **Part 3 — Unmapped-row auditing (not silent dropping)**

```python
mask_bad = (h < 0) | (t < 0) | (r < 0)
if mask_bad.any():
    bad = df[mask_bad].copy()
    bad['unmapped_head']     = h[mask_bad] < 0
    bad['unmapped_tail']     = t[mask_bad] < 0
    bad['unmapped_relation'] = r[mask_bad] < 0
    bad['source_file']       = os.path.basename(path)
    unmapped_records.append(bad)

mask_good = ~mask_bad
head_index_list.append(torch.from_numpy(h[mask_good]))
tail_index_list.append(torch.from_numpy(t[mask_good]))
edge_type_list.append(torch.from_numpy(r[mask_good]))
```

### **Part 4 — Concatenate, dedup via bijective integer encoding, save**

```python
mapped_triples = torch.stack([
    torch.cat(head_index_list, dim=0),
    torch.cat(edge_type_list,  dim=0),
    torch.cat(tail_index_list, dim=0),
], dim=1)
```

**Deduplication** uses bijective packing:

```python
H, R, T = int(mt[:, 0].max()) + 1, int(mt[:, 1].max()) + 1, int(mt[:, 2].max()) + 1
INT64_MAX = (1 << 63) - 1

fits = (H - 1) * (R * T) + (R - 1) * T + (T - 1) <= INT64_MAX

if fits:
    enc  = mt[:, 0] * (R * T) + mt[:, 1] * T + mt[:, 2]
    enc  = torch.unique(enc)
    tail = enc % T
    rel  = (enc // T) % R
    head = enc // (T * R)
    mapped_triples = torch.stack([head, rel, tail], dim=1)
else:
    mapped_triples = torch.unique(mapped_triples, dim=0)
```

---

## **7.4 Train/Valid/Test Splitting — Three Different Strategies**

### **7.4.1 Aging (1-to-1) and Biomedical (1-to-1) — independent 80/10/10**

```python
SEED = 42
generator = torch.Generator()
generator.manual_seed(SEED)
perm     = torch.randperm(N, generator=generator)
shuffled = mapped_triples[perm]

n_train = int(N * 0.80)
n_valid = int(N * 0.10)
n_test  = N - n_train - n_valid

train, valid, test = shuffled[:n_train], shuffled[n_train:n_train+n_valid], shuffled[n_train+n_valid:]
```

### **7.4.2 EvoAge (1-to-1) — AB_test construction, then leakage-free 90/10**

1. **Combines** Aging and Biomedical 1-to-1 test sets into a single **AB_test**
2. **Removes** AB_test triples from EvoAge 1-to-1 KG
3. **Splits** the remainder 90/10 into train/valid
4. **AB_test** itself becomes the EvoAge test set

```python
AB_test = torch.cat([aging_test, biomedical_test], dim=0)
# dedup
AB_enc = encode(AB_test)
sort_idx = AB_enc.argsort()
AB_sorted_enc, AB_sorted_triples = AB_enc[sort_idx], AB_test[sort_idx]
unique_mask = torch.ones_like(AB_sorted_enc, dtype=torch.bool)
unique_mask[1:] = AB_sorted_enc[1:] != AB_sorted_enc[:-1]
AB_test_unique = AB_sorted_triples[unique_mask]
```

Subtract via binary search (`searchsorted`):

```python
CHUNK = 50_000_000
ab_sorted, _ = torch.sort(encode(AB_test_unique))

keep_parts, test_parts = [], []
for s in range(0, N_full, CHUNK):
    block = evoage_full[s:s+CHUNK]
    keys  = encode(block)
    pos   = torch.searchsorted(ab_sorted, keys).clamp_(max=ab_sorted.numel() - 1)
    in_ab = ab_sorted[pos] == keys
    test_parts.append(block[in_ab])
    keep_parts.append(block[~in_ab])

remaining   = concat_free(keep_parts)
evoage_test = concat_free(test_parts)
```

The remaining pool is split 90/10:

```python
generator = torch.Generator().manual_seed(SEED)
perm      = torch.randperm(N_remaining, generator=generator)
shuffled  = remaining[perm]

n_train = int(N_remaining * 0.90)
train, valid = shuffled[:n_train], shuffled[n_train:]
```

### **7.4.3 Aging (121+12M) and Biomedical (121+12M) — remove-1to1-test, then 90/10**

The 1-to-1 test set is removed from the 121+12M tensor, and the remainder is split 90/10 into train/valid (the 1-to-1 test set functions as the test set).

```python
test_1to1  = torch.load('Store_House/Aging_specific_1to1_KG_test_10.pt')
kg_1tomany = torch.load('Store_House/Aging_specific_121_12M_KG.pt')

test_set = set(map(tuple, test_1to1.tolist()))
mask = [tuple(triple.tolist()) not in test_set for triple in kg_1tomany]
kg_filtered = kg_1tomany[mask]

train_idx, valid_idx = train_test_split(
    list(range(len(kg_filtered))), test_size=0.10, random_state=42, shuffle=True)
train_90, valid_10 = kg_filtered[train_idx], kg_filtered[valid_idx]
```

### **7.4.4 EvoAge (121+12M) — remove EvoAge-1to1-test, then 90/10**

Same removal pattern, but using binary search at scale:

```python
test_keys, _ = torch.sort(encode(test))

train_parts, valid_parts = [], []
gen = torch.Generator().manual_seed(SEED)
for s in range(0, N, CHUNK):
    block = kg[s:s+CHUNK]
    keys  = encode(block)
    pos     = torch.searchsorted(test_keys, keys).clamp_(max=test_keys.numel()-1)
    in_test = test_keys[pos] == keys
    kept    = block[~in_test]

    vmask = torch.rand(kept.shape[0], generator=gen) < 0.10
    valid_parts.append(kept[vmask])
    train_parts.append(kept[~vmask])
```

---

## **7.5 Test-Set Lineage Summary**

The four KG variants' test sets form a strict lineage:

```
Aging (1-to-1) test_10        ──┐
                                 ├──► AB_test (deduped union) ──► EvoAge (1-to-1) test
Biomedical (1-to-1) test_10   ──┘                                       │
                                                                           │ (reused as-is)
        Aging (1-to-1) test_10  ──► removed from Aging (121+12M)        │
        Biomedical (1-to-1) test_10  ──► removed from Biomedical (121+12M)
                                                                           ▼
                                                           EvoAge (1-to-1) test
                                                                   ──► removed from EvoAge (121+12M)
```

This guarantees **any triple that is test data for Aging or Biomedical in any ortholog variant is also test data for EvoAge.**

---

## **7.6 Output Inventory (Store_House/)**

| File | Variant | Content |
|---|---|---|
| `node_id_mapping_EvoAge_121_12M.pkl` | global | Node string → integer ID |
| `relation_id_EvoAge_EvoAge_121_12M.csv` | global | Relation string → integer ID |
| `Aging_specific_1_to_1_KG.pt` | Aging 1-to-1 | Full deduped tensor |
| `Aging_specific_1to1_KG_train_80.pt` / `_valid_10.pt` / `_test_10.pt` | Aging 1-to-1 | 80/10/10 split |
| `Aging_specific_121_12M_KG.pt` | Aging 121+12M | Full deduped tensor |
| `Aging_specific_121_12M_KG_train_90.pt` / `_valid_10.pt` | Aging 121+12M | 90/10 split (test = Aging 1-to-1 test) |
| `Biomedical_1_to_1_KG.pt` | Biomedical 1-to-1 | Full deduped tensor |
| `Biomedical_1to1_KG_train_80.pt` / `_valid_10.pt` / `_test_10.pt` | Biomedical 1-to-1 | 80/10/10 split |
| `Biomedical_121_12M_KG.pt` | Biomedical 121+12M | Full deduped tensor |
| `Biomedical_121_12M_KG_train_90.pt` / `_valid_10.pt` | Biomedical 121+12M | 90/10 split (test = Biomedical 1-to-1 test) |
| `EvoAge_1_to_1_KG.pt` | EvoAge 1-to-1 | Full deduped tensor |
| `EvoAge_1to1_KG_train_90.pt` / `_valid_10.pt` / `_test.pt` | EvoAge 1-to-1 | test = AB_test; 90/10 of remainder |
| `EvoAge_121_12M_to_many_KG.pt` | EvoAge 121+12M | Full deduped tensor |
| `EvoAge_121_12M_KG_train_90.pt` / `_valid_10.pt` | EvoAge 121+12M | 90/10 split (test = EvoAge 1-to-1 test) |
| `entities_final.dict` | global | `MappedID \t Node` |
| `relation_final.dict` | global | `MappedID \t Relation` |

Every tensor twin is also written as a TSV file for training pipelines.

---

## **Next Steps**

1. ✅ **All four KG variants built and split?** → Proceed to DGL-KE / PyKEEN model training.
2. **Re-running with a 6th species?** → Rebuild the global mapping first.
3. **Auditing for test-set leakage?** → Verify using searchsorted membership check.
