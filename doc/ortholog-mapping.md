
# Orthology Mapping

#### #04 — Orthology Mapping (Non-Human → Human)

> 📂 **Source Code & Notebooks:** [pipeline/04_orthology_mapping](https://github.com/the-ahuja-lab/EvoAge/tree/main/pipeline/04_orthology_mapping)


## 1. Purpose

This is **Step 4** of the EvoAge Knowledge Graph (KG) construction pipeline. The goal is to convert all non-human species gene nodes to their **human ortholog equivalents** so that data from five model organisms can be unified into a single human-centric KG. This step produces two KG variants — a **strict 1:1 ortholog KG** and a **1:1 + 1:Many (1:1∪1:M) ortholog KG** — to support rigorous, fair link-prediction evaluation.

---

## 2. Overview

After Steps 01–03, processed triple files exist per species with species-specific gene identifiers. This step:

1. **Collects** all unique Gene nodes from each species' processed triple files.
2. **Converts** those genes to human orthologs using **Ensembl BioMart (release e114)**.
3. **Maps** the species-specific KG triples to human gene symbols, producing two ortholog-converted KG variants.

The two KG variants exist to guarantee that the **test set used for evaluation is always a subset of the KG being evaluated**, avoiding information leakage.

### Why two KGs?

| KG variant | Ortholog types included | Purpose |
|---|---|---|
| **1:1 KG** | `ortholog_one2one` only | Conservative mapping; each non-human gene maps to exactly one human gene. Used to **generate the test set** for link-prediction evaluation. |
| **1:1 ∪ 1:M KG** | `ortholog_one2one` + `ortholog_one2many` | Broader coverage; non-human genes can map to multiple human genes (row explosion). The 1:1 test set is guaranteed to be a subset of this KG, so evaluation is fair. |

note> [!IMPORTANT]
> The 1:1 test set is used to evaluate **both** KG variants. If a node in the test set came from a gene that only appears in the 1:M mapping, it would be absent from the 1:1 KG — making the comparison unfair. By building the 1:1∪1:M KG as a **superset** of the 1:1 KG, every test-set triple is guaranteed to exist in both KGs.


---

## 3. Pipeline — Step-by-Step

The pipeline consists of **5 sequential runs**, each implemented as a standalone script. The scripts are preserved in this documentation folder with `Run_N_` prefixes for traceability.

---

### Run 1 — Collect unique Gene nodes per species

📄 **Script**: [Run_1_collecting_all_species_Unique_gene.py](orthology_mapping_04/Run_1_collecting_all_species_Unique_gene.py)

**What it does:**
- Scans all processed triple CSVs under `processed_data_relation_wise_merge/generalised/OTHER_SPECIES/{Species}/`
- For each file, extracts every unique value from `head` (where `head_type == 'Gene'`) and `tail` (where `tail_type == 'Gene'`)
- Unions all genes across files for each species
- Saves one CSV per species: `{Species}_unique_genes.csv`

**Output files:**

| File 
|---|
| `Celegans_unique_genes.csv` 
| `Drosophila_unique_genes.csv`
| `Mouse_unique_genes.csv` 
| `Yeast_unique_genes.csv` 
| `Zebrafish_unique_genes.csv` 

**Output location:** `orthology_mapping/`

---

### Run 2 — Query Ensembl BioMart for human orthologs

📄 **Script**: [Run_2_Final_map_orthologs_to_human_desc.R](orthology_mapping_04/Run_2_Final_map_orthologs_to_human_desc.R)

**What it does:**
- For each species, reads the unique-gene CSV from Run 1
- **Resolves** gene symbols/IDs to Ensembl gene IDs using:
  1. **g:Profiler `gconvert()`** (primary) — pinned to archive `e114_eg62_p19` for reproducibility
  2. **biomaRt `getBM()`** (fallback) — for genes symbols which g:Profiler could not resolve
- **Queries** the source-species mart for human orthologs via BioMart attributes
- **Fetches human gene descriptions** from the `hsapiens_gene_ensembl` mart
- Saves per-species, per-orthology-type CSVs + summary files

---


**Output per species** (saved to `Human_Ortholog_Mapping_3/{Species}/`):

| File | Description |
|---|---|
| `{Species}_byType_ortholog_one2one.csv` | 1:1 orthologs only |
| `{Species}_byType_ortholog_one2many.csv` | 1:many orthologs only |

**Output columns in ortholog CSVs:**

```
source_species, input_gene, source_ensembl_id, source_symbol,
human_ensembl_id, human_symbol, human_description,
orthology_type, orthology_confidence, perc_id
```


---

### Run 3 — Build the 1:1 ortholog KG

📄 **Script**: [Run_3_1to1_converting.py]

**What it does:**
- Reads the `{Species}_byType_ortholog_one2one.csv` from Run 2
- Builds lookup dictionaries: `input_gene (uppercased) → human_symbol`, `→ human_description`, `→ ortholog_info`
- Iterates over each species' processed triple CSVs (original, pre-mapping)
- For each Gene node (head or tail):
  - If a 1:1 ortholog exists → replaces the gene symbol with the human symbol
  - Sets `{side}_species = 'Homo sapiens'`
  - Adds `{side}_detail_name` (human gene description) and `{side}_ortholog_info` (species, confidence, perc_id, type)
  - If no ortholog exists → gene is kept **unchanged** (remains in original species namespace)
- Saves each mapped file as `{original_name}_ortho_1_to_1.csv` alongside the original

**Mapping rule:** One source gene → exactly one human gene (no row explosion)

**Output suffix:** `_ortho_1_to_1.csv`

**Log file:** `_ORTHOLOG_MAPPING_LOG_1_to_1_BioMart.csv` (per-file mapping statistics)

---

### Run 4 — Merge 1:1 and 1:Many ortholog tables

📄 **Script**: [Run_4_merge_121_12M_tomake_121PLUS12M.py]

**What it does:**
- For each species, concatenates:
  - `{Species}_byType_ortholog_one2one.csv` (from Run 2)
  - `{Species}_byType_ortholog_one2many.csv` (from Run 2)
- Drops exact duplicate rows
- Saves the combined file as `{Species}_byType_ortholog_one2one_plus_one2many.csv`

**Purpose:** Creates the merged ortholog table that Run 5 will use to build the 1:1∪1:M KG.

**Output:** `Human_Ortholog_Mapping_3/{Species}/{Species}_byType_ortholog_one2one_plus_one2many.csv`

---

### Run 5 — Build the 1:1 ∪ 1:Many (1:1+1:M) ortholog KG

📄 **Script**: [Run_5_1toM_121_converting.py]

**What it does:**
- Reads the merged `{Species}_byType_ortholog_one2one_plus_one2many.csv` from Run 4
- Builds lookup dictionaries: `input_gene (uppercased) → [list of human_symbols]`
- Iterates over each species' processed triple CSVs
- For each Gene node (head or tail):
  - If orthologs exist → **explodes** the row: one source row becomes N rows (one per ortholog)
- Saves each mapped file as `{original_name}_ortho_1_to_one2one_plus_one2many.csv`

**Mapping rule:** One source gene → **one or more** human genes (row explosion possible)

**Output suffix:** `_ortho_1_to_one2one_plus_one2many.csv`

---

## 5. Next Step

→ **[Step 05 — Making Aging & Biomedical KG]**: Combine human + ortholog-mapped species triples into the final Aging KG and Biomedical KG variants.
