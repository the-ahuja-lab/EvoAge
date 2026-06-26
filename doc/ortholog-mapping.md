# 5. Ortholog Mapping

After relation-wise merging produces per-relation, per-species CSVs ([Relation Processing](relation-processing.md)), the non-human species data still has genes in their native ID systems (WormBase, FlyBase, MGI, SGD, ZFIN). To make these connect to the human-anchored Aging/Biomedical KGs, every non-human gene needs to be mapped to its human ortholog. This section documents that pipeline: collecting unique genes per species, querying Ensembl BioMart for orthologs, and producing two parallel ortholog-mapped KG variants — **121** (1-to-1 only) and **121+12M** (1-to-1 plus 1-to-many).

---

## **5.1 Pipeline Overview**

```
OTHER_SPECIES/<species>/*.csv (relation-wise merged, species-native gene IDs)
        │
        ▼
collecting_all_species_Unique_gene.py
   → one *_unique_genes.csv per species (deduplicated gene list)
        │
        ▼
Final_Final_map_orthologs_to_human_desc.R   (Ensembl BioMart, e114, via biomaRt + gprofiler2)
   → <Species>_byType_ortholog_one2one.csv
   → <Species>_byType_ortholog_one2many.csv
   → <Species>_byType_ortholog_many2many.csv   (kept aside, not used downstream)
        │
        ├──────────────────────────────┐
        ▼                              ▼
  1to1_converting.py            merge_121_12M_tomake_121PLUS12M.py
  (maps one2one only)           (concatenates one2one + one2many,
        │                        drops exact dupes)
        ▼                              ▼
  *_ortho_1_to_1.csv            1toM_121_converting.py
  (= "121" KG input)            (explodes rows for 1-to-many orthologs)
                                       │
                                       ▼
                              *_ortho_1_to_one2one_plus_one2many.csv
                              (= "121+12M" KG input)
```

Two KG variants come out the other end of this pipeline:

| Variant | Ortholog types used | Row behavior | Use case |
|---|---|---|---|
| **121** | 1-to-1 only | One row stays one row — gene is simply renamed to its human symbol | Conservative, no row inflation, cleanest signal |
| **121+12M** | 1-to-1 **and** 1-to-many | A gene with N human orthologs explodes into N rows | Broader coverage, captures duplication/divergence relationships, more triples |

---

## **5.2 Step 1 — Collect Unique Genes Per Species**

**Script**: `collecting_all_species_Unique_gene.py`

Before querying Ensembl, every relation-wise CSV for a species is scanned to pull out the complete, deduplicated set of gene identifiers that actually appear in that species' KG — from **both** the `head` and `tail` columns, filtered by `head_type`/`tail_type == 'Gene'`:

```python
def extract_genes_from_file(path):
    header = pd.read_csv(path, nrows=0).columns.tolist()
    need = ['head', 'tail', 'head_type', 'tail_type']
    usecols = [c for c in need if c in header]

    df = pd.read_csv(path, usecols=usecols, low_memory=False)
    genes = set()

    if 'head' in df.columns and 'head_type' in df.columns:
        mask = df['head_type'].str.strip().str.lower() == 'gene'
        genes.update(df.loc[mask, 'head'].dropna().astype(str).unique())

    if 'tail' in df.columns and 'tail_type' in df.columns:
        mask = df['tail_type'].str.strip().str.lower() == 'gene'
        genes.update(df.loc[mask, 'tail'].dropna().astype(str).unique())

    return genes
```

This is run once per species across **every** relation-wise CSV in that species' folder, with results unioned into a single gene set:

```python
SPECIES_CONFIG = {
    'Celegans'   : ('Celegans',   'Caenorhabditis elegans',  'Celegans_gene'),
    'Drosophila' : ('Drosophila', 'Drosophila melanogaster', 'Droso_gene'),
    'Mouse'      : ('Mouse',      'Mus musculus',            'Mouse_gene'),
    'Yeast'      : ('Yeast',      'Saccharomyces cerevisiae','Yeast_gene'),
    'Zebrafish'  : ('Zebrafish',  'Danio rerio',             'Zebrafish_gene'),
}

for species, (folder, canonical_species, col_name) in SPECIES_CONFIG.items():
    csv_files = [f for f in glob.glob(os.path.join(ROOT, folder, '*', '*.csv'))
                 if '.ipynb_checkpoints' not in f
                 and not os.path.basename(f).startswith('_SUMMARY')
                 and 'ortho_1_to_' not in os.path.basename(f)]

    all_genes = set()
    for path in csv_files:
        all_genes.update(extract_genes_from_file(path))

    gene_df = pd.DataFrame({
        col_name:    sorted(all_genes),
        'Node_type': 'Gene',
        'species':   canonical_species,
    })
    gene_df.to_csv(f'{species}_unique_genes.csv', index=False)
```

Note the column naming convention — each species gets its own gene-column name (`Celegans_gene`, `Droso_gene`, `Mouse_gene`, `Yeast_gene`, `Zebrafish_gene`) rather than a shared generic name, because this matches what the R script's `species_info` table expects per-species (`gene_col` field).

**Output**: 5 files — `Celegans_unique_genes.csv`, `Drosophila_unique_genes.csv`, `Mouse_unique_genes.csv`, `Yeast_unique_genes.csv`, `Zebrafish_unique_genes.csv` — each a clean list of every distinct gene ID that appears anywhere in that species' merged KG.

---

## **5.3 Step 2 — Query Ensembl BioMart for Human Orthologs**

**Script**: `Final_Final_map_orthologs_to_human_desc.R`

This is the actual ortholog lookup, run once per species against Ensembl (pinned to **release e114**, May 2025 archive, for reproducibility — current/default mirrors serve whatever the latest release is, which would break reproducibility months later).

### **Why two tools (biomaRt + gprofiler2)?**

Species gene lists arrive as a mix of symbols, synonyms, and sometimes stale IDs. A single resolution path isn't reliable enough, so the script uses a **two-stage resolution cascade**:

```r
# Stage 1: g:Convert (gprofiler2) — robust, cross-namespace symbol -> Ensembl ID
resolved <- safe_gconvert(genes, gp_org)

# Stage 2: biomaRt fallback for anything g:Convert couldn't resolve
still <- setdiff(unique(genes), resolved$input_gene)
if (length(still)) {
  fb <- id_map |> filter(k_name %in% norm_key(still) | k_id %in% norm_key(still)) |> ...
  resolved <- bind_rows(resolved, fb)
}
```

g:Convert handles the bulk of symbol→Ensembl resolution; biomaRt's own genome-wide `id_map` (built once per species from `ensembl_gene_id` + `external_gene_name`) catches anything left over. Both stages are version-pinned: g:Profiler is checked against the same Ensembl release (`GP_TARGET_ENSEMBL <- 114`) and falls back to a fixed archive (`e114_eg62_p19`) if the current g:Profiler release has drifted.

### **Connection robustness**

Every BioMart call goes through retry wrappers because Ensembl's REST endpoint intermittently returns transient 500s:

```r
CONNECT_TRIES <- 15
ALLOW_MIRROR_FALLBACK <- FALSE   # mirrors serve the CURRENT release, not e114 — never fall back silently

connect_mart <- function(dataset) {
  for (attempt in seq_len(CONNECT_TRIES)) {
    m <- tryCatch(useEnsembl(biomart = "genes", dataset = dataset, host = ENSEMBL_HOST),
                  error = function(e) { Sys.sleep(min(10 * attempt, 30)); NULL })
    if (!is.null(m)) return(m)
  }
  stop("e114 archive host unreachable after ", CONNECT_TRIES, " tries...")
}

safe_getBM <- function(..., label = "query") {
  for (attempt in seq_len(MAX_TRIES)) {
    res <- tryCatch(getBM(...), error = function(e) { Sys.sleep(3 * attempt); NULL })
    if (!is.null(res)) return(res)
  }
  stop(sprintf("[%s] failed after %d attempts.", label, MAX_TRIES))
}
```

`ALLOW_MIRROR_FALLBACK <- FALSE` is a deliberate reproducibility guard — it would be easy to silently fall back to a regional mirror serving the current Ensembl release, which would quietly break the e114 pin without erroring. The script chooses to fail loudly instead.

### **Homology query (chunked)**

IDs are queried in chunks of 200 (`CHUNK_SIZE`) to keep individual requests small and retry-friendly, pulling all the fields needed for downstream confidence filtering and provenance:

```r
HOM_ATTRS <- c(
  "ensembl_gene_id", "external_gene_name",
  "hsapiens_homolog_ensembl_gene", "hsapiens_homolog_associated_gene_name",
  "hsapiens_homolog_orthology_type", "hsapiens_homolog_orthology_confidence",
  "hsapiens_homolog_perc_id"
)

get_homologs_chunked <- function(ids, mart) {
  chunks <- split(unique(ids), ceiling(seq_along(ids) / CHUNK_SIZE))
  out <- lapply(seq_along(chunks), function(j)
    safe_getBM(attributes = HOM_ATTRS, filters = "ensembl_gene_id",
               values = chunks[[j]], mart = mart))
  bind_rows(out)
}
```

Human gene **descriptions** are fetched separately from the human mart (`hsapiens_gene_ensembl`) and cached in-session (`.human_desc_cache`) so the same human Ensembl ID is never queried twice across species:

```r
get_human_descriptions <- function(ids, human_mart) {
  miss <- ids[!vapply(ids, function(i) exists(i, envir = .human_desc_cache), logical(1))]
  # ... query only the missing ones, cache results ...
}
```

### **Output split by orthology_type**

The final matched table is split and written **one file per orthology type**, per species:

```r
for (t in unique(matched$orthology_type)) {
  write_csv(filter(matched, orthology_type == t),
            file.path(sp_dir, paste0(sp$species_name, "_byType_", t, ".csv")))
}
```

This produces, per species:

| File | Orthology type | Used downstream? |
|---|---|---|
| `<Species>_byType_ortholog_one2one.csv` | 1 source gene ↔ 1 human gene | ✅ Yes — feeds both 121 and 121+12M |
| `<Species>_byType_ortholog_one2many.csv` | 1 source gene ↔ N human genes | ✅ Yes — feeds 121+12M only |
| `<Species>_byType_ortholog_many2many.csv` | N source genes ↔ M human genes | ❌ Not used in either KG variant |

Plus per-species diagnostics: `<Species>_UNMAPPED.txt`, `<Species>_SYMBOL_NOT_FOUND.txt`, `<Species>_PerGene_Summary.csv`, and a master `AllSpecies_Orthology_Summary.csv` with coverage stats across all five species.

---

## **5.4 Step 3 — Build the Two KG Variants**

### **5.4.1 1-to-1 Only (121)**

**Script**: `1to1_converting.py`

Loads each species' `_byType_ortholog_one2one.csv` and builds simple `gene → human_symbol` dictionaries:

```python
def build_ortholog_dicts(biomart_path, species_key):
    bm = pd.read_csv(biomart_path)
    bm['ortholog_info'] = (
        'species: ' + species_key +
        ' ::: original_gene: '        + bm['input_gene'].astype(str) +
        ' ::: orthology_confidence: ' + bm['orthology_confidence'].astype(str) +
        ' ::: perc_identity: '        + bm['perc_id'].astype(str) +
        ' ::: orthology_type: '       + bm['orthology_type'].astype(str)
    )
    bm = bm[bm['human_symbol'].notna()].copy()
    bm['input_gene_upper'] = bm['input_gene'].astype(str).str.upper()

    gene2ortho = dict(zip(bm['input_gene_upper'], bm['human_symbol']))
    gene2desc  = dict(zip(bm['input_gene_upper'], bm['human_description']))
    gene2info  = dict(zip(bm['input_gene_upper'], bm['ortholog_info']))
    return gene2ortho, gene2desc, gene2info
```

Because the mapping is strictly 1-to-1, **no row explosion is needed** — each gene value is simply swapped in place for both `head` and `tail` columns:

```python
def map_one_side(df, side, gene2ortho, gene2desc, gene2info, original_species):
    type_col = f'{side}_type'
    is_gene  = df[type_col].astype(str).str.strip().str.lower() == 'gene'

    keys = df.loc[is_gene, side].astype(str).str.upper()
    mapped_mask = is_gene.copy()
    mapped_mask[is_gene] = keys.map(gene2ortho).notna().values

    mapped_keys = df.loc[mapped_mask, side].astype(str).str.upper()
    df.loc[mapped_mask, side]                   = mapped_keys.map(gene2ortho).values
    df.loc[mapped_mask, f'{side}_detail_name']  = mapped_keys.map(gene2desc).values
    df.loc[mapped_mask, f'{side}_species']      = 'Homo sapiens'
    df.loc[mapped_mask, f'{side}_ortholog_info']= mapped_keys.map(gene2info).values
    return int(mapped_mask.sum())
```

**Unmapped genes are left unchanged** (not dropped) — they keep their native species ID and `species` tag as the original organism, so the row survives but stays a non-human-anchored node.

Every triple file across all 5 species gets run through this same `map_one_side` call for both `head` and `tail`, producing one `*_ortho_1_to_1.csv` per input file.

### **5.4.2 Merging 1-to-1 with 1-to-Many**

**Script**: `merge_121_12M_tomake_121PLUS12M.py`

Before building the 121+12M KG, the two BioMart ortholog tables (one2one and one2many) are concatenated per species into a single combined ortholog reference table:

```python
species_list = ["Yeast", "Celegans", "Drosophila", "Zebrafish", "Mouse"]

for species in species_list:
    one2one_file  = species_dir / f"{species}_byType_ortholog_one2one.csv"
    one2many_file = species_dir / f"{species}_byType_ortholog_one2many.csv"

    df1 = pd.read_csv(one2one_file)
    df2 = pd.read_csv(one2many_file)

    merged = pd.concat([df1, df2], ignore_index=True).drop_duplicates()
    merged.to_csv(species_dir / f"{species}_byType_ortholog_one2one_plus_one2many.csv", index=False)
```

This is the pivot point — `1toM_121_converting.py` reads from this **combined** file.

### **5.4.3 1-to-1 Plus 1-to-Many (121+12M)**

**Script**: `1toM_121_converting.py`

This is the more involved conversion, because **a single source gene can now map to multiple human orthologs**, which means a single triple row needs to become multiple rows — one per ortholog.

```python
def build_ortholog_dicts_121_12M(biomart_path, species_key):
    bm = pd.read_csv(biomart_path)
    bm['ortholog_info'] = (...)  # same provenance string as in 1to1_converting.py

    bm = bm[bm['human_symbol'].notna()].copy()
    bm['input_gene_upper'] = bm['input_gene'].astype(str).str.upper()
    bm = bm.drop_duplicates(subset=['input_gene_upper', 'human_symbol'], keep='first')

    gene2orthos = bm.groupby('input_gene_upper')['human_symbol'].apply(list).to_dict()
    gene2descs  = bm.groupby('input_gene_upper')['human_description'].apply(list).to_dict()
    gene2infos  = bm.groupby('input_gene_upper')['ortholog_info'].apply(list).to_dict()
    return gene2orthos, gene2descs, gene2infos
```

**Exploding one side**:

```python
def explode_side(df, side, gene2orthos, gene2descs, gene2infos, original_species):
    is_gene = df[f'{side}_type'].astype(str).str.strip().str.lower() == 'gene'

    df[f'_{side}_orthos'] = df[side].apply(lambda v: [v])          # default: no explosion
    df[f'_{side}_descs']  = [[pd.NA]] * len(df)
    df[f'_{side}_infos']  = [[pd.NA]] * len(df)

    df.loc[is_gene, f'_{side}_orthos'] = df.loc[is_gene, side].apply(
        lambda v: gene2orthos.get(str(v).upper(), [v]))            # fallback: [original] if unmapped
    df.loc[is_gene, f'_{side}_descs']  = df.loc[is_gene, side].apply(
        lambda v: gene2descs.get(str(v).upper(), [pd.NA]))
    df.loc[is_gene, f'_{side}_infos']  = df.loc[is_gene, side].apply(
        lambda v: gene2infos.get(str(v).upper(), [pd.NA]))

    mapped_keys = set(gene2orthos.keys())
    df['_was_mapped_' + side] = is_gene & df[side].astype(str).str.upper().isin(mapped_keys)

    # Explode all 3 list columns together so they stay row-aligned
    df = df.explode([f'_{side}_orthos', f'_{side}_descs', f'_{side}_infos'], ignore_index=True)

    df[side] = df[f'_{side}_orthos']
    df.loc[df['_was_mapped_' + side], f'{side}_detail_name']   = df.loc[df['_was_mapped_' + side], f'_{side}_descs']
    df.loc[df['_was_mapped_' + side], f'{side}_ortholog_info'] = df.loc[df['_was_mapped_' + side], f'_{side}_infos']
    df.loc[df['_was_mapped_' + side], f'{side}_species']       = 'Homo sapiens'

    df.drop(columns=[f'_{side}_orthos', f'_{side}_descs', f'_{side}_infos'], inplace=True)
    return df
```

**Order of operations matters**: head is exploded first, then tail is exploded on the already-head-exploded frame — this is what produces the N×M cartesian product:

```python
if head_has_gene:
    df = explode_side(df, 'head', gene2orthos, gene2descs, gene2infos, original_species)
else:
    df['head_species'], df['head_ortholog_info'] = original_species, pd.NA

if tail_has_gene:
    df = explode_side(df, 'tail', gene2orthos, gene2descs, gene2infos, original_species)
else:
    df['tail_species'], df['tail_ortholog_info'] = original_species, pd.NA
```

---

## **5.5 Output File Naming Convention**

| Suffix | Meaning | Produced by |
|---|---|---|
| `*_ortho_1_to_1.csv` | 121 KG input — 1-to-1 orthologs only, no row explosion | `1to1_converting.py` |
| `*_ortho_1_to_one2one_plus_one2many.csv` | 121+12M KG input — 1-to-1 + 1-to-many, exploded | `1toM_121_converting.py` |

---

## **5.6 Key Design Decisions Worth Remembering**

- **e114 pin, no silent mirror fallback**: reproducibility was prioritized explicitly enough to make the script fail loudly rather than silently drift.
- **Two-stage gene resolution**: g:Convert Primary → biomaRt fallback catches genes that fail in the first pass.
- **many2many orthologs are excluded entirely** from both KG variants due to noise.
- **Unmapped genes are kept, not dropped**, in both conversions.
- **Explosion order (head-then-tail) produces the cartesian product** for 121+12M.

---

## **Next Steps**

1. ✅ **Ortholog mapping done for all 5 species?** → Move to [KG Construction](kg-construction.md)
2. **Adding a 6th species?** → Add to `SPECIES_CONFIG` in `collecting_all_species_Unique_gene.py` and map datasets.
