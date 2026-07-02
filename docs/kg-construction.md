# 6. KG Construction — Splitting into Aging-Specific & Biomedical

> 📂 **Source Code & Notebooks:** [pipeline/05_kg_construction](../pipeline/05_kg_construction/)


By this point in the pipeline, every relation has been merged across sources ([Relation Processing](relation-processing.md)) and every non-human species has been ortholog-mapped to human gene symbols in two variants, 121 and 121+12M ([Ortholog Mapping](ortholog-mapping.md)). The **full EvoKG is now ready** — one complete, ortholog-resolved knowledge graph spanning Human plus five model organisms.

This section covers the final structural split: dividing the full EvoKG into two KG variants, **Aging_specific** and **Biomedical**, based on the `kg_type` tag that was assigned during relation-wise merging ([Relation Processing Step 2](relation-processing.md#step-2--load-each-source-with-three-tag-columns)).

---

## **6.1 Why Split Into Two KG Variants**

Every triple's `kg_type` value was set when it was loaded from its source during relation-wise merging — aging-specific sources (HALD, AgeAnno, GenAge, DrugAge, AgeAnnoMO, AgingAtlas, etc.) got `'Aging'`; general biomedical sources (DRKG, PharmKG, TARKG, Monarch, Hetionet, Harmonizome, etc.) got `'Generalised'`. After dedup, a triple that appeared in *both* kinds of sources carries `kg_type = 'Aging::Generalised'`.

Splitting on this tag produces:

- **Aging_specific KG** — every triple tagged `Aging` (including the `Aging::Generalised` overlap rows) — a focused subgraph for aging-biology-specific hypothesis testing
- **Biomedical KG** — every triple tagged `Generalised` (including the `Aging::Generalised` overlap rows again) — the broader biomedical context

Note the overlap rows deliberately appear in **both** outputs — this isn't a bug, it's the intended behavior (see `classify()` below). A triple that's both aging-relevant and part of general biomedical knowledge should be usable in either KG variant.

---

## **6.2 The Shared Classification Logic**

All three split scripts — one for Human, two for the other five species (one per ortholog variant) — use the **exact same** `classify()` function:

```python
def classify(val):
    """
    Returns (is_aging, is_biomedical).
      'aging'              → aging only
      'generalised'        → biomedical only
      'aging::generalised' → BOTH
      blank / other        → biomedical (default)
    """
    s = str(val).strip().lower()
    is_aging      = 'aging' in s
    is_biomedical = ('generalised' in s) or (s == '') or (not is_aging)
    return is_aging, is_biomedical
```

Three design choices worth calling out:

1. **Substring match, not exact match** — `'aging' in s` catches both `'aging'` and `'aging::generalised'` in one check.
2. **Biomedical is the default bucket** — if `kg_type` is blank, unrecognized, or anything that isn't clearly `'aging'`-only, the row falls into Biomedical. This means **Biomedical is the larger, catch-all KG**, and Aging is the precise, opt-in subset.
3. **Overlap rows go to both** — a row tagged `'aging::generalised'` sets both `is_aging` and `is_biomedical` to `True`, so it gets written to both output trees.

A helper finds the `kg_type` column case-insensitively:

```python
KG_COL = 'kg_type'

def find_kg_col(df):
    match = [c for c in df.columns if c.lower() == KG_COL]
    return match[0] if match else None
```

If no `kg_type` column is found at all, the file is skipped (logged as `'no kg_type'`).

---

## **6.3 Run 1 — Splitting the Human KG**

**Script**: `Run1_split_kg_by_type_human.py`

This processes every relation-wise merged file under `generalised/` (explicitly **excluding** `OTHER_SPECIES/`, since that's handled by Run2/Run3 separately):

```python
ROOT     = '/storage/Arushi/090526_EvoAge/kg_formation/processed_data_relation_wise_merge'
SRC_BASE = os.path.join(ROOT, 'generalised')
AGING_BASE = os.path.join(ROOT, 'Aging_specific', 'Human')
BIOMEDICAL_BASE = os.path.join(ROOT, 'Biomedical', 'Human')

all_files = (
    glob.glob(os.path.join(SRC_BASE, '**/*.csv'),     recursive=True) +
    glob.glob(os.path.join(SRC_BASE, '**/*.parquet'), recursive=True)
)
all_files = [
    f for f in all_files
    if 'OTHER_SPECIES' not in f
    and '.ipynb_checkpoints' not in f
    and not os.path.basename(f).startswith('_')   # skip _KG_TYPE_CHECK.csv etc.
]
```

### **Key difference from the other-species scripts: output format**

Run1 is the only one of the three that **converts CSV → Parquet on output**, regardless of input format:

```python
def save_parquet(df, rel_path, base_dir):
    """Mirror rel_path under base_dir but force a .parquet extension."""
    rel_parquet = os.path.splitext(rel_path)[0] + '.parquet'
    out_path = os.path.join(base_dir, rel_parquet)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    df.to_parquet(out_path, index=False)
    return out_path
```

This matches the project convention that final KG-stage outputs are saved as `.parquet` (faster reads, smaller footprint) even though intermediate relation-wise merge files stayed as `.csv`.

### **Output structure**

```
Aging_specific/Human/<relation_subfolder>/<relation_file>.parquet
Biomedical/Human/<relation_subfolder>/<relation_file>.parquet
```

The relative path under `generalised/` (e.g. `GENE_DISEASE/ALL_GENE_DISEASE.csv`) is preserved on both sides.

### **Log output**

`Human_KG_SPLIT_LOG.csv` — records split stats.

---

## **6.4 Run 2 — Splitting Other-Species KG (121 variant)**

**Script**: `Run2_split_1to1_kg_by_type_otherspecies.py`

Scope is the **121** (1-to-1 ortholog) files produced in [Ortholog Mapping 1-to-1 Only](ortholog-mapping.md#541-1-to-1-only-121) — specifically files matching `*_ortho_1_to_1.csv`:

```python
SPECIES_ROOT = os.path.join(ROOT, 'generalised', 'OTHER_SPECIES')
AGING_BASE   = os.path.join(ROOT, 'Aging_specific')
BIOMED_BASE  = os.path.join(ROOT, 'Biomedical')

SPECIES = {
    'Celegans': 'Celegans', 'Drosophila': 'Drosophila',
    'Mouse': 'Mouse', 'Yeast': 'Yeast', 'Zebrafish': 'Zebrafish',
}

for species, folder in SPECIES.items():
    species_dir = os.path.join(SPECIES_ROOT, folder)
    files = sorted([
        f for f in glob.glob(os.path.join(species_dir, '**/*_ortho_1_to_1.csv'), recursive=True)
        if '.ipynb_checkpoints' not in f
    ])
    # ... same split + save logic as Run1, but output stays .csv ...
```

### **Output structure**

```
Aging_specific/
├── Human/<relation>/<file>.parquet
├── Celegans/<relation>/<file>_ortho_1_to_1.csv
├── Drosophila/<relation>/<file>_ortho_1_to_1.csv
├── Mouse/<relation>/<file>_ortho_1_to_1.csv
├── Yeast/<relation>/<file>_ortho_1_to_1.csv
└── Zebrafish/<relation>/<file>_ortho_1_to_1.csv
```

### **Log output**

`_OTHER_SPECIES_KG_SPLIT_LOG_1to1.csv`

---

## **6.5 Run 3 — Splitting Other-Species KG (121+12M variant)**

**Script**: `Run3_split_12M_121_comb_kg_by_type_otherspecies.py`

Identical structure to Run2, but scoped to the **121+12M** files from [Ortholog Mapping 1-to-1 Plus 1-to-Many](ortholog-mapping.md#543-1-to-1-plus-1-to-many-12112m) — files matching `*_ortho_1_to_one2one_plus_one2many.csv`:

```python
files = sorted([
    f for f in glob.glob(
        os.path.join(species_dir, '**/*_ortho_1_to_one2one_plus_one2many.csv'),
        recursive=True
    )
    if '.ipynb_checkpoints' not in f
])
```

### **Log output**

`_OTHER_SPECIES_KG_SPLIT_LOG.csv`

---

## **6.6 Resulting Directory Structure**

After Run1 + Run2 + Run3 all complete, the full split produces:

```
processed_data_relation_wise_merge/
├── generalised/                          # pre-split, relation-wise merged (input)
│   ├── <relation_subfolder>/...          # Human relations
│   └── OTHER_SPECIES/<Species>/...       # Per-species relations (both ortho variants)
│
├── Aging_specific/
│   ├── Human/<relation>/<file>.parquet                          # from Run1
│   ├── Celegans/<relation>/<file>_ortho_1_to_1.csv               # from Run2 (121)
│   ├── Celegans/<relation>/<file>_ortho_1_to_one2one_plus_one2many.csv  # from Run3 (121+12M)
│   └── ...                                                       # other species
│
├── Biomedical/
│   ├── Human/<relation>/<file>.parquet
│   ├── Celegans/<relation>/<file>_ortho_1_to_1.csv
│   ├── Celegans/<relation>/<file>_ortho_1_to_one2one_plus_one2many.csv
│   └── ...
```

---

## **Next Steps**

1. ✅ **Aging_specific and Biomedical splits complete?** → Move to [Tensors & Splitting](kg-tensors-and-splitting.md)
2. **Auditing split correctness?** → Cross-check log CSV files.
3. **Adding a 6th species?** → Add to `SPECIES` dict in Run2 and Run3.
