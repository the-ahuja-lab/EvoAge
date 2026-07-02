# Step 01 — Data Collection

## 1. Purpose

This is the **first step** of the EvoAge Knowledge Graph (KG) construction pipeline. The goal is to collect, catalogue, and version-pin all raw data from **~50 external sources** that will feed into the KG. Every source is timestamped and version-locked to ensure reproducibility (required for the Nature Communications reproducibility package).

---

## 2. Overview

EvoAge integrates data from **48+ named databases/resources** plus 2 curation categories (Literature, species connection grouping). These span:

| Category | Sources | What they contribute |
|---|---|---|
| **Aging-specific databases** | GenAge, DrugAge, CellAge, AgeXtend, Aging Atlas, AgeAnno, AgeAnnoMO, AgingBank, Digital Aging Atlas, HALD, MetaboAge, Evolf | Gene/drug/cell ↔ aging relations; feed the **Aging KG** variant |
| **General biomedical KGs** | DRKG, PrimeKG, Hetionet, MonarchKG, CKG, CROssBAR, iBKH, TARKG, PharmKG, BOCK KG, BioGrakn, PheKnowLator | Disease–gene–chemical–phenotype context; feed the **Biomedical KG** variant |
| **Protein/Gene interaction networks** | STRING, BioGRID, Biosnap, MouseNet v2, YeastNet v3, Worm Interactome Database, FICE | Gene–Gene and Protein–Protein edges (species-specific where applicable) |
| **Chemical/Drug/Target databases** | ChEMBL, DrugBank, BindingDB, STITCH, TTD, DTInet, SMS | Chemical–Gene and Chemical–Target edges |
| **Species-specific annotation** | FlyBase (Drosophila), WormBase (C. elegans), SGD (Yeast), ZFIN (Zebrafish), MGI (Mouse) | Gene ID resolution, symbol mapping, species-specific annotation |
| **miRNA / Regulatory** | miRTarBase 2025 | miRNA–Gene regulatory edges |
| **Phytochemical / Traditional medicine** | PhytoHub, IMPPAT, AyurvedicPlantClassifier, PhytoChemicalDiversity, phytochemicals DB, Ayurvedic medicine catalogue, CEVOpen | Plant–compound and Ayurvedic compound data |
| **Literature curation** | Manually curated hallmarks-of-aging ↔ biological process links | Aging–BiologicalProcess relation triples |
| **Cross-species connection** | iBKH, miRTarBase, PheKnowLator | Cross-species/cross-entity linking |

---

## 3. Data Source Master Table

The full master table with **Version/Build**, **Last Download date**, **Download Link**, and **Reference/Publication** for all 48+ sources is documented in:

📄 **[DataCollection_01.md](file:///storage/Arushi/090526_EvoAge/kg_formation/DOCUMENTATION/data_collection_01/DataCollection_01.md)** — §2.2

This table is kept in sync with the manuscript's Supplementary Table for Nature Communications.

### Key provenance fields per source

| Field | Purpose |
|---|---|
| **Version / Build** | Exact release pinned — traceable to a specific build |
| **Last Download** | Date the data was actually pulled |
| **Download Link** | Direct retrieval path (GitHub, FTP, or "In house data" / "manually curated") |
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
├── cellage/
├── chembl/
├── ckg/
├── crossbar/
├── digitalagingatlas/
├── drkg/
├── drugage/
├── drugbank/
├── dtinet/
├── eSLDB/
├── evolf/
├── fic/
├── flybase/
├── genage/
├── gendr/
├── gpkg/
├── hald/
├── harmonizome/
├── hetionet/
├── hmd_hp/
├── ibkh/
├── ikgraph/
├── immpat/
├── immunekg/
├── metaboage/
├── mgi_do/
├── mirTARbase/
├── mirnaatlas/
├── mirnatissueatlas/
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
├── PharMeBiNet/
├── RNAkg/
├── databases_for_mapping/    ← Reference files used in ID mapping (NCBI, PubChem, etc.)
├── data_collection.ipynb     ← Notebook documenting initial collection steps
└── RAEDME.txt
```

**Total: 61 subdirectories** (one per source or source group) + 3 files.

---

## 5. Species Coverage

Data was collected for **6 species**:

| Species | Common name | Key sources |
|---|---|---|
| *Homo sapiens* | Human | All 48+ sources |
| *Mus musculus* | Mouse | MGI, MouseNet v2, STRING, STITCH |
| *Drosophila melanogaster* | Fruit fly | FlyBase, STRING, STITCH |
| *Caenorhabditis elegans* | Roundworm | WormBase, Worm Interactome DB, FICE, STRING, STITCH |
| *Saccharomyces cerevisiae* | Yeast | SGD, YeastNet v3, eSLDB, STRING, STITCH, BioGRID |
| *Danio rerio* | Zebrafish | ZFIN, STRING, STITCH |

---

## 6. Non-standard Provenance Cases

- **In house data** (AgeXtend, Evolf): generated internally, not downloaded from public repositories.
- **Custom Python script** (Harmonizome): data retrieved via the Harmonizome API — no flat-file bulk download.
- **Manually curated** (Literature category): hallmarks-of-aging ↔ biological process links curated by hand.

---

## 7. Quick Stats

- **Total named sources**: 48 databases/resources + 2 curation categories
- **Earliest source vintage**: DRKG (May 2020)
- **Most recent downloads**: miRTarBase 2025, PheKnowLator (17-May-2026)
- **Species-specific annotation sources**: 5 (FlyBase, WormBase, SGD, ZFIN, MGI)
- **Phytochemical/Ayurvedic sources**: 7

---


## 8. Next Step
→ **[Step 02 — Data Processing]: Per-source cleaning, ID normalisation, and KG-triple extraction.
