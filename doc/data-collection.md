# 01 — Data Collection

> 📂 **Source Code & Notebooks:** [pipeline/01_data_collection](https://github.com/the-ahuja-lab/EvoAge/tree/main/pipeline/01_data_collection)


## 1. Purpose

This is the **first step** of the EvoAge Knowledge Graph (KG) construction pipeline. The goal is to collect, catalogue, and version-pin all raw data from **48+ external sources** that will feed into the KG. Every source is timestamped and version-locked to ensure reproducibility (required for the Nature Communications reproducibility package).

---

## 2. Overview

EvoAge integrates data from **48+ named databases/resources** 

| Category | Sources |
|---|---|
| **Aging-specific databases** | GenAge, DrugAge, CellAge, Aging Atlas, AgeAnno
| **General biomedical KGs** | DRKG, PrimeKG, Hetionet, MonarchKG, CKG etc|
| **Protein/Gene interaction networks** | STRING, BioGRID, Biosnap etc |
| **Chemical/Drug/Target databases** | ChEMBL, DrugBank, BindingDB, STITCH, TTD |
| **Species-specific annotation** | FlyBase, WormBase, SGD, ZFIN, MGI|
| **Phytochemical / Traditional medicine** | PhytoHub, IMPPAT
| **Literature curation** | Manually curated hallmarks-of-aging ↔ biological process links 


---

## 3. Data Source Master Table

The full master table with **Version/Build**, **Last Download date**, **Download Link**, and **Reference/Publication** for all 48+ sources is documented in:

📄 **[DataCollection_01.md](file:///storage/Arushi/090526_EvoAge/kg_formation/DOCUMENTATION/data_collection_01/DataCollection_01.md)** — §2.2

This table is kept in sync with the manuscript's Supplementary Table.

### Key provenance fields per source

| Field | Purpose |
|---|---|
| **Version / Build** | Exact release pinned — traceable to a specific build |
| **Last Download** | Date the data was actually pulled |
| **Download Link** | Direct retrieval path (GitHub, FTP, Webpage) |
| **Reference / Link** | Primary publication or landing page |

---

## 4. Where Raw Data Lives

The actual downloaded raw data is stored in the working directory:

```
kg_formation/data_collection/
├── ageanno/
├── ageannomo/
├── agextend/
├── agingatlas/
├── agingbank/
├── bindingdb/
├── biograkn/
├── biogrid/
├── biosnap/
├── bock/
├── cellage/
├── chembl/
├── ckg/
├── crossbar/
├── digitalagingatlas/
├── drkg/
├── drugage/
├── drugbank/
├── dtinet/
├── evolf/
├── fic/
├── flybase/
├── genage/
├── gendr/
├── hald/
├── harmonizome/
├── hetionet/
├── hmd_hp/
├── ibkh/
├── immpat/
├── metaboage/
├── mgi_do/
├── mirTARbase/
├── monarchkg/
├── mousenet/
├── other_sources/
├── pharmkg/
├── pheknowlator/
├── phytohub/
├── primekg/
├── sgd/
├── sms/
├── stitch/
├── string/
├── tarkg/
├── ttd/
├── widb/
├── wormbase/
├── yeastnet/
├── zfin/
├── databases_for_mapping/    ← Reference files used in ID mapping (NCBI, PubChem, etc.)
├── data_collection.ipynb     ← Notebook documenting initial collection steps
```

**Each directory** (one per source or source group).

---

## 5. Species Coverage

Data was collected for **6 species**:

| Species | Common name | Key sources |
|---|---|---|
| *Mus musculus* | Mouse | MGI, MouseNet, STRING, STITCH |
| *Drosophila melanogaster* | Fruit fly | FlyBase, STRING, STITCH |
| *Caenorhabditis elegans* | Roundworm | WormBase, Worm Interactome DB, FICE, STRING, STITCH |
| *Saccharomyces cerevisiae* | Yeast | SGD, YeastNet, eSLDB, STRING, STITCH, BioGRID |
| *Danio rerio* | Zebrafish | ZFIN, STRING, STITCH |

---

## 6. Non-standard Provenance Cases

- **In house data** (AgeXtend, Evolf): generated internally, not downloaded from public repositories.
- **Custom Python script** (Harmonizome): data retrieved via the Harmonizome API — no flat-file bulk download.
- **Manually curated** (Literature category): hallmarks-of-aging ↔ biological process links curated by hand.

---


## 7. Next Step
→ **[Step 02 — Data Processing]: Per-source cleaning, ID normalisation, and KG-triple extraction.
