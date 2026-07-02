# 4. Relation-Wise Merging

> 📂 **Source Code & Notebooks:** [pipeline/03_relation_merge](../pipeline/03_relation_merge/)


After per-source preprocessing ([Preprocessing](preprocessing.md)) produces relation-typed CSVs from each of the 48+ data sources, the next step is to **merge across sources, one relation type at a time**. Each relation type (Gene_Disease, Gene_BiologicalProcess, Chemical_Gene, etc.) gets its own notebook that pulls in every source contributing to that relation, harmonizes columns, deduplicates, and writes a single canonical CSV.

This section documents the standard pattern shared by all ~70+ notebooks in `kg_formation/processed_data_relation_wise_merge/`.

---

## **4.1 Why Merge Relation-by-Relation**

The 48+ sources are heterogeneous in coverage — DRKG, PharmKG, TARKG all contribute Gene–Disease edges; AgeAnno and HALD add aging-specific Gene–Disease edges; Harmonizome contributes a handful of Gene–Disease ML-derived associations; MonarchKG brings in MONDO-identified Gene–Disease edges. The same is true for every other relation type: each is partially covered by 3–10 different sources, with **different ID conventions, different column names, and significant row-level overlap** between sources.

Merging relation-by-relation (rather than concatenating everything globally and splitting later) makes three things tractable:

1. **Per-relation ID reconciliation** — Gene–Disease tails arrive as DOID in some sources, MONDO in others, MESH in others; each relation has its own reconciliation cascade
2. **Per-relation kg_type assignment** — within Gene–Disease, HALD and AgeAnno are tagged `Aging`, while DRKG/PharmKG/TARKG/Monarch/Harmonizome are tagged `Generalised` — this labeling drives the eventual Aging-KG vs Biomedical-KG split ([KG Construction](kg-construction.md))
3. **Cross-source provenance tracking** — when the same `(head, relation, tail)` triple appears in multiple sources, the dedup step preserves all source names joined with `::` rather than collapsing them away

---

## **4.2 Standard Merge Pattern**

Every relation-wise merge notebook follows the same 10-step structure:

| Step | Section in notebook | What it does |
|---|---|---|
| 0 | Configuration | `BASE_DIR`, `PROC_DIR`, `OUT_PATH`, `REQUIRED_COLS` |
| 1 | Build Lookup Dictionaries | Load NCBI gene + DO/MeSH/MedGen disease dicts for repair/fill-in |
| 2 | Load KG Sources | One cell per source: load → lowercase columns → assign `kg_type`, `kg_source`, `species` |
| 3 | Check Duplicate Columns | Audit each loaded DF for accidentally duplicated column names |
| 4 | Align Schemas & Concatenate | Add missing columns, restrict to `CONCAT_COLS`, `pd.concat` |
| 5 | Standardise Fixed-Value Columns | Normalize `head_id_is`/`tail_id_is` across sources (`DO_ID`/`DOID_ID` → `DOID`, etc.) |
| 6 | Repair Missing Names | Backfill `head_detail_name` via synonym map + NCBI symbol lookup |
| 7 | Deduplicate | `groupby([head, relation, tail])` + `merge_sources('::'.join)` aggregation |
| 8 | QC — NaN Check | True-NaN + string-`'NAN'` audit on the deduped frame |
| 9 | Drop Unresolvable, Add Schema Columns | Drop rows still missing names; restrict to `REQUIRED_COLS` |
| 10 | Save Output | Write CSV to the relation-specific subfolder under `generalised/` |

### **Worked example: Gene–Disease merge**

**Notebook**: `processed_data_relation_wise_merge/generalised/Relation_Wise_Gene_Disease.ipynb`
**Sources merged**: Monarch, DRKG, PharmKG, TARKG, Harmonizome, HALD, AgeAnno
**Output**: `processed_data_relation_wise_merge/generalised/GENE_DISEASE/ALL_GENE_DISEASE.csv`

The standard config block every notebook opens with:

```python
import os
import pandas as pd
import numpy as np

BASE_DIR = '/storage/Arushi/090526_EvoAge/kg_formation/'
PROC_DIR = BASE_DIR + 'processed_data/'
DB_DIR   = BASE_DIR + 'data_collection/databases_for_mapping/'

OUT_PATH = BASE_DIR + 'processed_data_relation_wise_merge/generalised/GENE_DISEASE/ALL_GENE_DISEASE.csv'

REQUIRED_COLS = [
    'head', 'relation', 'tail',
    'head_type', 'relation_type', 'tail_type',
    'kg_source',
    'head_id_is', 'tail_id_is',
    'head_detail_name', 'tail_detail_name',
    'kg_type', 'species',
]
```

`BASE_DIR` is defined once; all other paths are concatenations off it (no f-strings, no hardcoded `/storage/...` repeats), matching the project's path convention.

---

## **4.3 Step-by-Step Logic**

### **Step 1 — Build lookup dictionaries**

The merge step needs richer lookup tables than per-source preprocessing, because here we're **filling in gaps and reconciling formats across sources** rather than resolving from scratch. For a Gene–Disease merge:

```python
# Gene side — NCBI Symbol/Description + exploded synonym map
NCBI_ALL_GENE = pd.read_csv(DB_DIR + 'ncbi/Homo_sapiens.gene_info', sep='\t')
NCBI_ALL_Symb_Desc_dict = dict(zip(NCBI_ALL_GENE['Symbol'], NCBI_ALL_GENE['description']))

NCBI_ALL_GENE_Syn_Dict = dict(zip(NCBI_ALL_GENE['Synonyms'], NCBI_ALL_GENE['Symbol']))
exploded_dict_NCBI_ALL_GENE_Syn_Dict = {}
for k, v in NCBI_ALL_GENE_Syn_Dict.items():
    for alias in k.split('|'):
        exploded_dict_NCBI_ALL_GENE_Syn_Dict[alias.strip()] = v

# Disease side — DO labels/IDs
DO_All_File = pd.read_csv(DB_DIR + 'DO/All_DO_ref_files.csv')
DOID_disname_dict = dict(zip(DO_All_File['id'], DO_All_File['label']))

# Disease side — MONDO → MESH (MedGen) for Monarch's MONDO tails
MedGen = pd.read_csv(DB_DIR + 'MESH/MeSH/MedGenIDMappings.txt', sep='\t')
MONDO_2_MESH = MedGen[MedGen['source_id'].str.contains('MONDO', na=False)]
MONDO_2_MESH_dict = dict(zip(MONDO_2_MESH['source_id'], MONDO_2_MESH['#CUI_or_CN_id']))

# Disease side — MESH ID → name (combined + supplementary + BioGrakn-derived rest)
MESH_dict      = dict(zip(MESH['ID'], MESH['Name']))
Mesh_supp_dict = dict(zip(Mesh_supp['ID'], Mesh_supp['Name']))
rest_mesh_dict = dict(zip(rest_mesh['Tail'], rest_mesh['diseaseName']))
MedGen_CUID_Source_ID_name_dict = dict(zip(MedGen['#CUI_or_CN_id'], MedGen['pref_name']))
```

The **MONDO → MESH map** is the critical reconciler here — Monarch arrives with MONDO IDs, and unless they're remapped to MESH, the Monarch contribution stays disconnected from the DRKG/PharmKG/TARKG rows that use DOID/MESH.

### **Step 2 — Load each source with three tag columns**

Every source DataFrame gets the same three tag columns appended at load time, regardless of relation type:

```python
df = pd.read_csv(PROC_DIR + 'PharmKG/PharmKG_Gene_Disease.csv')
df.columns = df.columns.str.lower()          # always lowercase

df['kg_source'] = 'PharmKG'                   # source name (drives provenance)
df['kg_type']   = 'Generalised'               # 'Generalised' or 'Aging'
df['species']   = 'Homo species'              # uniform for human pipeline
```

`kg_type` is what distinguishes the eventual KG variants — aging sources (HALD, AgeAnno, GenAge, DrugAge, AgeAnnoMO, AgingAtlas, etc.) get `'Aging'`; general biomedical sources (DRKG, PharmKG, TARKG, Monarch, Hetionet, Harmonizome, GPKG, etc.) get `'Generalised'`.

For Monarch specifically, the MONDO→MESH remap happens inline:

```python
Monarch['tail'] = Monarch['tail'].map(MONDO_2_MESH_dict).fillna(Monarch['tail'])
Monarch = Monarch[~Monarch['tail'].astype(str).str.startswith('MONDO')]   # drop unmapped MONDO
Monarch['tail_id_is'] = np.where(
    Monarch['tail'].isna(), None,
    np.where(Monarch['tail'].astype(str).str.startswith('DOID'), 'DOID', 'MESH')
)
```

For Harmonizome, an extra row-level pattern filter removes rows that don't match a recognized disease-ID shape:

```python
pattern = r'^(DOID:\d+|C\d+|D\d+)$'
harmonizome = harmonizome[harmonizome['head'].astype(str).str.match(pattern, na=False)]
```

### **Step 3 — Duplicate-column audit**

Before concatenation, every DataFrame is checked for accidentally duplicated column names (which `pd.concat` would silently misalign):

```python
SOURCE_DFS = [
    ('Monarch_Gene_Disease', Monarch_Gene_Disease),
    ('DRKG_Gene_Disease',    DRKG_Gene_Disease),
    ('PharmKG_Gene_Disease', PharmKG_Gene_Disease),
    ('TARKG_Gene_Disease',   TARKG_Gene_Disease),
    ('harmonizome',          harmonizome),
    ('hald',                 hald),
    ('AgeAnno',              AgeAnno),
]

for name, df in SOURCE_DFS:
    dupes = df.columns[df.columns.duplicated(keep=False)].unique().tolist()
    if dupes:
        print(f"[{name}] duplicate columns: {dupes}")
    else:
        print(f"[{name}] ✓ no duplicates")
```

### **Step 4 — Align schemas and concatenate**

Each source gets restricted to the **same column set in the same order**, with missing columns filled as `pd.NA` so concatenation is clean:

```python
CONCAT_COLS = [
    'head', 'relation', 'tail',
    'head_type', 'relation_type', 'tail_type',
    'kg_source', 'head_id_is', 'tail_id_is',
    'head_detail_name', 'tail_detail_name',
    'kg_type', 'species',
]

df_list = []
for name, df in SOURCE_DFS:
    tmp = df.loc[:, ~df.columns.duplicated()].copy()
    for col in CONCAT_COLS:
        if col not in tmp.columns:
            tmp[col] = pd.NA
    df_list.append(tmp[CONCAT_COLS])

final_df = pd.concat(df_list, ignore_index=True)
```

### **Step 5 — Standardize ID-system tags**

Sources tag the same ID system with slightly different strings (`DO_ID`, `DOID_ID`, `DOID`, `MESH`, `MESH_ID`, etc.). These get collapsed onto a single canonical tag per ID system:

```python
standardize_dict = {
    'DO_ID':   'DOID',
    'DOID_ID': 'DOID',
    'MESH_ID': 'MESH',
}
final_df['head_id_is'] = 'NCBI_ID'                              # uniform for gene heads
final_df['tail_id_is'] = final_df['tail_id_is'].replace(standardize_dict)

# Final canonical form: DOID_ID and MESH_ID
final_df['tail_id_is'] = final_df['tail_id_is'].apply(
    lambda x: 'DOID_ID' if isinstance(x, str) and x.startswith(('DOID', 'MOND')) else x
)
final_df['tail_id_is'] = final_df['tail_id_is'].replace('MESH', 'MESH_ID')

# Type columns also fixed at this stage
final_df['head_type'] = 'Gene'
final_df['tail_type'] = 'Disease'
```

### **Step 6 — Repair missing gene-head names**

Sources that didn't carry a `head_detail_name` (NCBI description) get backfilled through the synonym map → NCBI symbol → description chain:

```python
mask = final_df['head_detail_name'].isna()
print(f"Rows needing head_detail_name repair: {mask.sum():,}")

final_df.loc[mask, 'head'] = final_df.loc[mask, 'head'].str.replace('-', '', regex=False)
final_df.loc[mask, 'head'] = (
    final_df.loc[mask, 'head']
            .map(exploded_dict_NCBI_ALL_GENE_Syn_Dict)
            .fillna(final_df.loc[mask, 'head'])
)
mask2 = final_df['head_detail_name'].isna()
final_df.loc[mask2, 'head_detail_name'] = final_df.loc[mask2, 'head'].map(NCBI_ALL_Symb_Desc_dict)
```

### **Step 7 — Deduplicate with source-provenance preservation**

The core dedup: collapse on `(head, relation, tail)`, and for any column where rows came from multiple sources, **join all distinct values with `::`** rather than picking one. `kg_source` and `kg_type` use this join (so a row appearing in PharmKG and DRKG becomes `kg_source = 'DRKG::PharmKG'`); the other columns take `'first'` since their semantics are row-identical for the same triple.

```python
GROUP_COLS = ['head', 'relation', 'tail']

def merge_sources(x):
    return '::'.join(sorted(set(x.dropna())))

final_df_dedup = final_df.groupby(GROUP_COLS, as_index=False).agg({
    'head_type':        'first',
    'relation_type':    'first',
    'tail_type':        'first',
    'kg_source':        merge_sources,
    'head_id_is':       'first',
    'tail_id_is':       'first',
    'head_detail_name': 'first',
    'tail_detail_name': 'first',
    'kg_type':          merge_sources,
    'species':          'first',
})
```

This is what enables a triple to be tagged as **both Aging and Generalised** when it shows up in both — `kg_type` becomes `'Aging::Generalised'`, and the downstream split ([KG Construction](kg-construction.md)) can route that triple into both KG variants.

### **Step 8 — Post-dedup NaN audit**

Both real NaNs and the literal string `'nan'` (which sneaks in from `.astype(str)` calls during ID resolution) are counted side-by-side:

```python
def nan_summary(df):
    true_nan   = df.isna().sum()
    string_nan = df.apply(lambda c: c.astype(str).str.upper().eq('NAN').sum())
    return pd.DataFrame({
        'NaN_count':          true_nan,
        "'NAN'_string_count": string_nan,
        'Total_NaN_like':     true_nan + string_nan,
    })

nan_summary(final_df_dedup)
```

### **Step 9 — Drop unresolvable, fill tail names, restrict to REQUIRED_COLS**

```python
# Drop rows that still have no gene description (unresolvable heads)
final_df_dedup = final_df_dedup[~final_df_dedup['head_detail_name'].isna()].reset_index(drop=True)

# Last-chance tail_detail_name fill via cascading dicts
final_df_dedup['tail_detail_name'] = (
    final_df_dedup['tail_detail_name']
    .fillna(final_df_dedup['tail'].map(MESH_dict))
    .fillna(final_df_dedup['tail'].map(Mesh_supp_dict))
    .fillna(final_df_dedup['tail'].map(rest_mesh_dict))
    .fillna(final_df_dedup['tail'].map(MedGen_CUID_Source_ID_name_dict))
)
final_df_dedup = final_df_dedup[~final_df_dedup['tail_detail_name'].isna()]

# Restrict to canonical column order
final_df_dedup = final_df_dedup[REQUIRED_COLS]
```

### **Step 10 — Save**

```python
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
final_df_dedup.to_csv(OUT_PATH, index=False)
print(f"Saved {len(final_df_dedup):,} rows → {OUT_PATH}")
```

---

## **4.4 The 13-Column Canonical Schema**

Every relation-wise merged file ends up with these 13 columns, in this exact order:

| Column | Type | Purpose |
|---|---|---|
| `head` | str | Canonical head ID (NCBI Symbol, PubChem CID, GO ID, etc.) |
| `relation` | str | Relation name (e.g. `Gene_Disease`, `Chemical_Inhibits_BiologicalProcess`) |
| `tail` | str | Canonical tail ID |
| `head_type` | str | Node type (Gene, Chemical, Disease, Phenotype, ...) |
| `relation_type` | str | Optional finer-grained relation category (causal / associative / etc.) |
| `tail_type` | str | Node type of tail |
| `kg_source` | str | `::`-joined list of contributing source names (e.g. `DRKG::PharmKG::TARKG`) |
| `head_id_is` | str | ID system tag for head (`NCBI_ID`, `Pubchem`, `DOID_ID`, `HPO_ID`, ...) |
| `tail_id_is` | str | ID system tag for tail |
| `head_detail_name` | str | Human-readable description of head |
| `tail_detail_name` | str | Human-readable description of tail |
| `kg_type` | str | `::`-joined list of KG variants this triple belongs to: `Aging`, `Generalised`, or both |
| `species` | str | Species context (`Homo species` for human pipeline) |

The `::` join convention for `kg_source` and `kg_type` is what makes the downstream KG-variant split lossless.

---

## **4.5 Relation Coverage: What Gets Merged Where**

The full set of relation-wise merge notebooks under `processed_data_relation_wise_merge/generalised/` (human pipeline) covers every pairwise combination of node types EvoAge captures. Grouped by head/tail type:

### **Gene-centric relations (most heavily covered)**

| Relation | Notebook | Representative sources merged |
|---|---|---|
| Gene–Disease | `Relation_Wise_Gene_Disease.ipynb` | Monarch, DRKG, PharmKG, TARKG, Harmonizome, HALD, AgeAnno |
| Gene–Gene | `Relation_Wise_GENE_GENE.ipynb` | STRING, BioGRID, DRKG, PharmKG, Hetionet, MouseNet/YeastNet (cross-species) |
| Gene–Chemical | `Relation_Wise_GENE_CHEMICAL_clean.ipynb` | STITCH, ChEMBL, DRKG, PharmKG, DTInet |
| Gene–Pathway | `Relation_Wise_Gene_Pathway.ipynb` | Reactome, KEGG via Harmonizome, DRKG, TARKG |
| Gene–Phenotype | `Relation_Wise_GENE_PHENOTYPE_clean.ipynb` | HPO via Monarch, DRKG, Hetionet |
| Gene–Anatomy | `Relation_Wise_GENE_ANATOMY.ipynb` | Uberon via Monarch, Harmonizome tissue tables |
| Gene–Protein | `Relation_Wise_GENE_PROTEIN.ipynb` | UniProt, STRING, Hetionet |
| Gene–Mutation | `Relation_Wise_Gene_Mutation.ipynb` | Per-source mutation tables |
| Gene–Tissue | `Relation_Wise_Gene_Tissue.ipynb` | Tissue expression / GTEx-derived |
| Gene–BiologicalProcess | `Relation_Wise_GENE_BIOLOGICALPROCESS.ipynb` | AgeAnnoMO, AgingAtlas, GenAge, DRKG, GPKG, Hetionet, Monarch, TARKG |
| Gene–CellularComponent | `Relation_Wise_GENE_CELLULARCOMPONENT.ipynb` | GO via Monarch, Harmonizome |
| Gene–MolecularFunction | `Relation_Wise_Gene_MolecularFunction_clean.ipynb` | GO via Monarch, Harmonizome |
| miRNA–Gene | `Relation_Wise_Mirna_Gene.ipynb` | miRTarBase, TargetScan via Harmonizome |

### **Aging-relevant directional relations (Promotes / Inhibits / Pos-Neg-NoEffect)**

These are the relation types that distinguish the Aging KG variant:

| Relation | Notebook |
|---|---|
| Gene **promotes** BiologicalProcess | `Relation_Wise_GENE_PROMOTES_BIOLOFICALPROCESS.ipynb` |
| Gene **inhibits** BiologicalProcess | `Relation_Wise_Gene_inhibit_BioProcess.ipynb` |
| Gene Pos/Neg/No-Associated BiologicalProcess | `Relation_Wise_GENE_POS_NEG_NO_ASSOCIATED_BIOLOGICALPROCESS_Human.ipynb` |
| Chemical **promotes** BiologicalProcess | `Relation_Wise_CHEMICAL_PROMOTES_BIOLOGICALPROCESS_Human.ipynb` |
| Chemical **inhibits** BiologicalProcess | `Relation_Wise_CHEMICAL_INHIBITS_BIOLOGICALPROCESS_Human.ipynb` |
| Chemical Pos/Neg-Associated BiologicalProcess | `Relation_Wise_CHEMICAL_POS_NEG_ASSOCIATION_BIOLOGICALPROCESS_Human.ipynb` |
| Chemical No-effect BiologicalProcess | `Relation_Wise_CHEMICAL_Noeffect_BIOLOGICALPROCESS_Human.ipynb` |

### **Cross-species replication**

The same set of relation-wise notebooks is replicated per species under `OTHER_SPECIES/<species>/`:

```
OTHER_SPECIES/
├── Celegans/    22 notebooks
├── Drosophila/  18 notebooks
├── Mouse/       18 notebooks
├── Yeast/       9 notebooks
└── Zebrafish/   15 notebooks
```

Each species notebook follows the **exact same 10-step pattern as the human version** — the only differences are the species-specific gene/protein dictionaries, the `species` tag value, and which sources contribute to that species.

These species files feed directly into the ortholog mapping step ([Ortholog Mapping](ortholog-mapping.md)).

---

## **Next Steps**

1. ✅ **All relation-wise merges complete?** → Move to [KG Construction](kg-construction.md)
2. **Building a merge notebook for a new relation type?** → Copy the 10-step pattern from `Relation_Wise_Gene_Disease.ipynb`, swap in the appropriate sources and ID-resolution dictionaries, keep the `REQUIRED_COLS`/`CONCAT_COLS`/`GROUP_COLS` schema identical
