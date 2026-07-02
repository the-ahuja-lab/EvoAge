# Step 03 — Relation-Wise Merge & Standardisation

## 1. Purpose

This is the **third step** of the EvoAge KG pipeline. After Step 02 produced per-source KG-triple files (each source in its own folder), this step **collects all relation files of the same type from every source, merges them, removes duplicates, and saves one unified file per relation type**.

For example, all `Gene_Disease` files from PrimeKG, DRKG, Hetionet, TARKG, CKG, etc. are merged into a single `Gene_Disease` output. This is done separately for **Human** data and for each **other species**.

After merging, two post-processing scripts (**Run1** and **Run2**) standardise labels and add species metadata across all merged files.

---

## 2. Input

Per-source processed KG-triple CSVs from **Step 02**, located in:
```
kg_formation/data_processing/<source_name>/
```

---

## 3. Output

Merged, deduplicated relation files saved to:
```
kg_formation/processed_data_relation_wise_merge/generalised/
├── <Relation_Type>/          ← One folder per relation (Human data)
│   └── merged_<relation>.csv
└── OTHER_SPECIES/
    ├── Celegans/             ← Species-specific merged relations
    ├── Drosophila/
    ├── Mouse/
    ├── Yeast/
    └── Zebrafish/
```

---

## 4. Relation-Wise Merge Notebooks (Human)

**84 Jupyter notebooks** handle the merging for all entity-pair combinations in **Human** data. Each notebook:

1. **Collects** all files of the same relation type from every source that produced it
2. **Aligns** to a common schema (same column names and order)
3. **Deduplicates** by `(Head, Relation, Tail)` triple
4. **Saves** the final merged file

### Entity types and relation coverage

| Head Entity | Relation targets |
|---|---|---|
| **Gene** |Anatomy, BiologicalProcess, CellularComponent, Chemical, Gene, Phenotype, Protein, Disease, MolecularFunction, Mutation, Pathway, Tissue; plus directional variants (Promotes/Inhibits/PosNeg BiologicalProcess) |
| **Protein** | Chemical, Disease, MolecularFunction, Pathway, BiologicalProcess, CellularComponent, Phenotype, Protein, Tissue |
| **ChemicalEntity** | BiologicalProcess, Disease, Gene, Mutation, Pathway, Protein, Tissue |
| **Disease** | Anatomy, Chemical, Disease, Gene, Mutation, Pathway, Phenotype |
| **Chemical** | Inhibits/Promotes/NoEffect/PosNegAssociation BiologicalProcess (Human-specific directional), Chemical–Chemical |
| **Anatomy** | Anatomy, BiologicalProcess, Chemical, Gene, CellularComponent |
| **Mutation** | Chemical, Disease, Gene, Mutation, Protein |
| **Phenotype** | ChemicalEntity, Disease, Gene, Phenotype, Protein |
| **PMID** | CellularComponent, Chemical, Disease, Protein, Tissue |
| **BiologicalProcess** | BiologicalProcess, CellularComponent, MolecularFunction, Protein |
| **CellularComponent** | CellularComponent, ChemicalEntity, Gene |
| **MolecularFunction** | ChemicalEntity, MolecularFunction, BiologicalProcess, Protein |
| **Pathway** | Gene, Pathway |
| **Plant** | Disease, Chemical |
| **Mirna** | Gene |

---

## 5. Other Species Merge Notebooks

Species-specific relation files are merged in the `OTHER_SPECIES/` subdirectory, organised by species:

| Species  | Key relations covered |
|---|---|---|
| **C. elegans** | Gene–Gene, Gene–BiologicalProcess, Gene–CellularComponent, Gene–Anatomy, Gene–Phenotype, Chemical–BiologicalProcess (Inhibits/Promotes/PosNeg/NoEffect), Chemical–Chemical, Chemical–Gene, Protein–Protein, etc. |
| **Mouse** | Gene–Gene, Gene–BiologicalProcess, Gene–CellularComponent, Gene–Anatomy, Gene–Phenotype, Gene–Disease, Chemical–Chemical, Chemical–Gene, Chemical–BiologicalProcess (directional), Protein–Protein, etc. |
| **Drosophila** | Gene–Gene, Gene–BiologicalProcess, Gene–CellularComponent, Gene–Anatomy, Gene–Phenotype, Chemical–BiologicalProcess (directional), Chemical–Gene, etc. |
| **Zebrafish** | Gene–Gene, Gene–BiologicalProcess, Gene–CellularComponent, Gene–Anatomy, Gene–Phenotype, Chemical–Chemical, Chemical–Gene, etc. |
| **Yeast**| Gene–Gene, Gene–BiologicalProcess, Gene–CellularComponent, Gene–Anatomy, Chemical–BiologicalProcess (directional), Chemical–Chemical, etc. |

---

## 6. Post-Processing Scripts

After all relation-wise merges are complete, two Python scripts are run sequentially to standardise the merged files:

### 6.1 Run1: Label Standardisation

📄 **`Run1_Standardize_labels.py`**

**What it does:** Fixes typos and inconsistencies in ID-source labels (`head_id_is`, `tail_id_is`) and relation names across all merged files.

**Columns cleaned:** `head_id_is`, `tail_id_is`, `relation`

**ID label mappings applied:**

| Wrong value | → Corrected to |
|---|---|
| `PubChem`, `Pubchem_ID`, `PubChem_ID` | `Pubchem` |
| `GO`, `QuickGO`, `Quick_Go` | `Quick_GO` |
| `UBERON` | `UBERON_ID` |
| `DO_ID`, `DOID_ID` | `DOID` |
| `MESH_ID` | `MESH` |
| `HPO`, `HP` | `HPO_ID` |
| `UniProt`, `Uniprot` | `Uniprot_ID` |
| `Reactome` | `Reactome_ID` |
| `NCBI` | `NCBI_ID` |
| `SGD_SysematicName` (typo) | `SGD_SystematicName` |

**Relation name mappings applied:**

| Wrong value | → Corrected to |
|---|---|
| `Gene_inhibits_BiologicalProcess` | `Gene_Inhibits_BiologicalProcess` |
| `Gene_promotes_BiologicalProcess` | `Gene_Promotes_BiologicalProcess` |
| `Gene_Anatomy` | `Gene_AnatomicalEntity` |
| `Anatomy_CellularComponent` | `AnatomicalEntity_CellularComponent` |

**Configuration:**
- Scans all `.csv` and `.parquet` files under the generalised folder
- Excludes `OTHER_SPECIES/` by default (configurable via `INCLUDE_OTHER_SPECIES` flag)
- Skips `.ipynb_checkpoints` and files starting with `_`
- Only modifies files where exact-match replacements are found (safe by design)
- Saves a log to `_LABEL_CLEANUP_LOG.csv`

---

### 6.2 Run2: KG-Type Check & Species Column Addition

📄 **`Run2_check_humanKG_filesand_kg_type_and_add_species_col.py`**

**What it does:** Scans all Human KG files (excluding `OTHER_SPECIES/`) and:
1. **Checks** if each file has a `kg_type` column (reports which files have it and which don't)
2. **Records** the unique `kg_type` values per file (e.g., `Aging`, `Biomedical`)
3. **Adds** `head_species` and `tail_species` columns set to `'Homo sapiens'` for all Human files (only if not already present)

**Output:**
- Modified files saved in place (species columns added)
- Summary report saved to `_KG_TYPE_CHECK.csv` with columns:
  - `file`: relative path
  - `has_kg_type`: True/False
  - `kg_type_values`: unique values found (e.g., `Aging | Biomedical`)
  - `species_cols_added`: whether species columns were newly added

---

## 7. Execution Order

```
Step 02 outputs (per-source files)
        │
        ▼
┌──────────────────────────────────────┐
│  84 Relation-Wise Merge Notebooks    │  ← Merge + deduplicate by relation type (Human)
│  84 Other-Species Merge Notebooks    │  ← Same for each species
└──────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────┐
│  Run1_Standardize_labels.py          │  ← Fix ID/relation label typos
└──────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────┐
│  Run2_check_humanKG_files...py       │  ← Verify kg_type; add species columns
└──────────────────────────────────────┘
        │
        ▼
  Standardised, merged relation files
  ready for Step 04 (Orthology Mapping)
```

---

## 8. File Summary

| Location | Description |
|---|---|
| Root (`Processed_data_relation_wise_merge_03/`) | Human relation-wise merge notebooks |
| Root | `Run1_Standardize_labels.py`, `Run2_check_humanKG_files...py` |
| `OTHER_SPECIES/Celegans/` | C. elegans relation merges |
| `OTHER_SPECIES/Drosophila/` | Drosophila relation merges |
| `OTHER_SPECIES/Mouse/` | Mouse relation merges |
| `OTHER_SPECIES/Yeast/` | Yeast relation merges |
| `OTHER_SPECIES/Zebrafish/` | Zebrafish relation merges |

---

## 9. Key Design Decisions

- **One notebook per relation pair**: Keeps merging logic modular — each relation type may have source-specific quirks in column naming or ID formats.
- **Species separation**: Human data is the primary KG; other species are processed separately and later integrated via orthology mapping (Step 04).
- **Post-merge standardisation**: Run1 and Run2 are run *after* all merges are complete to catch inconsistencies introduced by different notebook authors or source conventions.
- **`kg_type` tagging**: Every triple carries an `Aging` or `Biomedical` tag, enabling downstream splitting into KG variants.
