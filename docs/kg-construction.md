# 05 — Making Aging & Biomedical KGs

> 📂 **Source Code & Notebooks:** [pipeline/05_kg_construction](https://github.com/the-ahuja-lab/EvoAge/tree/main/pipeline/05_kg_construction)

## 1. Purpose

This is **Step 5** of the EvoAge Knowledge Graph (KG) construction pipeline. The goal is to split the unified processed triples (from Steps 02–04) into two distinct KG categories — **Aging-specific** and **Biomedical (Generalised)** — based on the `kg_type` column assigned during data processing. This split is performed separately for Human data and for each non-human species (using both 1:1 and 1:1∪1:M ortholog-mapped files from Step 04). Additionally, this step generates Species_AssociatedWith connection triples that link each species to the genes/entities it is associated with.

---

## 2. Overview

The pipeline has **4 runs** across two phases:

| Phase | Runs | What it does |
|---|---|---|
| **Phase A: KG Splitting** | Run 1, Run 2, Run 3 | Splits every processed triple file into Aging vs Biomedical buckets using the `kg_type` column |
| **Phase B: Species Connections** | Run 4.1, Run 4.2 | Creates Species_AssociatedWith triples linking each species to its entities (one file per species) |

### How the `kg_type` classification works

Every triple file from Step 02/03 carries a `kg_type` column with one of these values:

| `kg_type` value | Routed to | Rationale |
|---|---|---|
| `aging` | **Aging only** | Triple comes from an aging-specific database (GenAge, DrugAge, CellAge, etc.) |
| `generalised` | **Biomedical only** | Triple comes from a general biomedical source (PrimeKG, DRKG, STRING, etc.) |
| `aging::generalised` | **Both Aging AND Biomedical** | Triple found in both KG's (e.g., aging genes that also appear in general KGs) |


---

## 3. Pipeline — Step-by-Step

---

### Run 1 — Split Human data by `kg_type`

📄 **Script**: [Run1_split_kg_by_type_human.py]

**What it does:**
- Reads all CSV/Parquet files under `processed_data_relation_wise_merge/generalised/` (excluding `OTHER_SPECIES/`)
- For each file, classifies every row by its `kg_type` value into Aging and/or Biomedical
- Saves Aging rows to `Aging_specific/Human/{relation_folder}/` (as Parquet)
- Saves Biomedical rows to `Biomedical/Human/{relation_folder}/` (as Parquet)
- The output directory structure mirrors the source relation-folder hierarchy

**Input:** `processed_data_relation_wise_merge/generalised/{RELATION_TYPE}/ALL_{RELATION_TYPE}.csv|parquet`

**Output:**
- `processed_data_relation_wise_merge/Aging_specific/Human/{RELATION_TYPE}/...parquet`
- `processed_data_relation_wise_merge/Biomedical/Human/{RELATION_TYPE}/...parquet`


**Log file:** [Human_KG_SPLIT_LOG.csv]

---

### Run 2 — Split 1:1 ortholog files by `kg_type` (other species)

📄 **Script**: [Run2_split_1to1_kg_by_type_otherspecies.py]

**What it does:**
- For each species, reads only `*_ortho_1_to_1.csv` files (produced by Step 04, Run 3)
- Splits rows by `kg_type` into Aging / Biomedical using the same classification logic as Run 1
- Saves to `Aging_specific/{Species}/{relation}/` and `Biomedical/{Species}/{relation}/` as CSV

**Log file:** `_OTHER_SPECIES_KG_SPLIT_LOG_1to1.csv`


---

### Run 3 — Split 1:1∪1:M ortholog files by `kg_type` (other species)

📄 **Script**: [Run3_split_12M_121_comb_kg_by_type_otherspecies.py]

**What it does:**
- Identical logic to Run 2, but reads `*_ortho_1_to_one2one_plus_one2many.csv` files (produced by Step 04, Run 5)
- Produces the Aging/Biomedical split for the broader ortholog mapping
**Log file:** `_OTHER_SPECIES_KG_SPLIT_LOG.csv`

---

### Run 4 — Generate Species_AssociatedWith connection triples

This run creates a new relation type: **`Species_AssociatedWith`**, which connects each species node to every entity (gene, protein, etc.) it is associated with in the KG.

#### Run 4.1 — Species triples for the 1:1 ortholog KG

📄 **Script**: [Run_4.1_make_species_triples_1_to_1.py]

**What it does:**
- Reads **all** Human generalised files + all `*_ortho_1_to_1.csv` files from other species
- For each file, extracts `head_species → Species_AssociatedWith → head` and `tail_species → Species_AssociatedWith → tail` triples
- Deduplicates across all files
- Splits by species and saves one Parquet per species

**Output:** `making_species_assocaitedwithconnection/1_to_1_ortholog/`

#### Run 4.2 — Species triples for the 1:1∪1:M ortholog KG

📄 **Script**: [Run_4.2_make_species_triples_combined121_12M.py]

**What it does:**
- Same logic as Run 4.1, but reads `*_ortho_1_to_one2one_plus_one2many.csv` for other species
- Produces species triples for the broader 1:1∪1:M KG

**Output:** `making_species_assocaitedwithconnection/one2one_plus_one2many_ortholog/`

---

## 5. Next Step

→ **[Step 06 — Final KG Building]**: Merge all Aging and Biomedical splits across species into the final consolidated KGs for training and evaluation.
