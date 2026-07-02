# 2. Data Collection

This section documents all data sources integrated into EvoAge — the master source table (also provided as a Supplementary Table with the manuscript), download provenance, and how each source feeds into the KG construction pipeline.

---

## **2.1 Overview**

EvoAge integrates **48+ data sources** spanning:

- **Aging-specific databases** (GenAge, DrugAge, CellAge, AgeAnno, etc.)
- **General biomedical knowledge graphs** (DRKG, PrimeKG, Hetionet, Monarch, CKG, etc.)
- **Protein-protein / gene-gene interaction networks** (STRING, BioGRID, IntAct-style resources)
- **Drug / chemical / chemical-target databases** (ChEMBL, DrugBank, BindingDB, STITCH, TTD)
- **Species-specific resources** (FlyBase, WormBase, SGD, ZFIN, MGI, species interactomes)
- **Phytochemical / Ayurvedic compound sources** (plant-compound and traditional-medicine databases)
- **Literature-curated hallmark-of-aging relations** (manually curated links between the hallmarks of aging and biological processes)

All sources are version-pinned and timestamped at download to ensure reproducibility — this is required for the Nature Communications reproducibility package (frozen splits, source versions, download dates).

---

## **2.2 Master Data Source Table**

This is the canonical source table — identical to the Supplementary Table accompanying the manuscript. **Every source here must keep its Version/Build and Last Download fields in sync with the manuscript supplement.**

| Data Source | Version / Build | Last Download | Download Link | Reference / Link |
|---|---|---|---|---|
| AgeAnno | version 1.0 | Mar 27 2025 | https://github.com/vikkihuangkexin/AgeAnno/tree/main | https://academic.oup.com/nar/article/51/D1/D805/6749541 |
| AgeAnnoMO | version 1.0 | Apr 15 2025 | https://github.com/vikkihuangkexin/AgeAnnoMO | https://relab.xidian.edu.cn/AgeAnnoMO |
| AgeXtend | version 1.0 | Jan 2025 | In house data | https://www.nature.com/articles/s43587-024-00763-4 |
| AgingBank | version 1.0 | Apr 15 2025 | https://bio-bigdata.hrbmu.edu.cn/AgingBank/download.html | https://academic.oup.com/bib/article/23/6/bbac438/6760117 |
| Aging Atlas | version 1.0 | Feb 2025 | https://ngdc.cncb.ac.cn/aging/index | https://academic.oup.com/nar/article/49/D1/D825/5943197 |
| BindingDB | 28-May-2023 | 28-May-2023 | https://library.ucsd.edu/dc/object/bb6496315b | https://www.bindingdb.org/rwd/bind/index.jsp |
| BioGrakn | Version 0.1 | 10-January-2025 | https://github.com/typedb/biograkn | https://link.springer.com/chapter/10.1007/978-3-319-61566-0_28 |
| Biosnap | August 2018 release | May 2023 | ChG-InterDecagon: https://snap.stanford.edu/biodata/datasets/10016/10016-ChG-InterDecagon.html · ChCh-Miner: https://snap.stanford.edu/biodata/datasets/10001/10001-ChCh-Miner.html · ChG-TargetDecagon: https://snap.stanford.edu/biodata/datasets/10015/10015-ChG-TargetDecagon.html | https://snap.stanford.edu/biodata/index.html |
| CKG (Clinical Knowledge Graph) | version 1.0 | May 30 2024 | https://github.com/MannLabs/CKG | https://www.nature.com/articles/s41587-021-01145-6 |
| CROssBAR | 2021 version | 10 Jan 2025 | https://github.com/cansyl/CROssBAR/archive/refs/heads/master.zip | https://academic.oup.com/nar/article/49/16/e96/6310792 |
| CellAge | Build 3 (23/04/2023) | January 2025 | https://genomics.senescence.info/cells/ | https://academic.oup.com/nar/article/46/D1/D1083/4599180 |
| ChEMBL | v33 (released 31-May-2023) | May 2023 | https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_33/ | https://www.ebi.ac.uk/chembl/ |
| DRKG | version 1.0 | May 4 2020 | https://github.com/gnn4dr/DRKG | https://arxiv.org/abs/2212.03911 |
| DTInet (drug-target interaction) | 9/1/2017 version | 11-January-2025 | https://github.com/luoyunan/DTINet | https://www.frontiersin.org/journals/bioinformatics/articles/10.3389/fbinf.2025.1649337/full |
| Digital Aging Atlas | Database Build: 5 | January 2025 | https://ageing-map.org/atlas/downloads/ | https://pure.amsterdamumc.nl/en/publications/the-digital-ageing-atlas-integrating-the-diversity-of-age-related |
| DrugAge | Build: 5 | Nov 29 2024 | https://genomics.senescence.info/drugs/ | https://genomics.senescence.info/drugs/ |
| DrugBank | version v5.1.10 | May 2023 | https://go.drugbank.com/releases/5-1-10 | https://pubmed.ncbi.nlm.nih.gov/29126136/ |
| Evolf | Version v1 | March 2025 | In house data | https://www.sciencedirect.com/science/article/pii/S2211124726000811 |
| FICE (Functional Interactome of C. elegans) | version FIC_v2018_01 | January 2025 | http://worm.biomedtzc.cn/#/download | https://biologydirect.biomedcentral.com/articles/10.1186/s13062-020-00271-6 |
| FlyBase | FB2024_02 release | June 2024 | https://flybase.org/releases/FB2024_02/precomputed_files/alleles/ | https://flybase.org/ |
| BOCK KG | version 1.0 | September 2024 | https://zenodo.org/records/8124854 | https://link.springer.com/article/10.1186/s12859-023-05451-5 |
| GenDR | Build 4 (24/06/2017) | January 2025 | https://genomics.senescence.info/diet/ | https://journals.plos.org/plosgenetics/article?id=10.1371/journal.pgen.1002834 |
| GenAge | Build 21 (8/28/2023) | January 2025 | https://genomics.senescence.info/genes/index.html | https://academic.oup.com/nar/article/52/D1/D900/7337614 |
| BioGRID | Release 4.4.221 | May 2023 | https://downloads.thebiogrid.org/BioGRID/Release-Archive/BIOGRID-4.4.221/ | https://academic.oup.com/nar/article/34/suppl_1/D535/1133554 |
| HALD (Human Aging and Longevity Knowledge graph) | Downloaded January 2025 | January 2025 | https://figshare.com/articles/dataset/HALD_a_human_aging_and_longevity_knowledge_graph_for_precision_gerontology_and_geroscience_analyses/22828196/4 | https://www.nature.com/articles/s41597-023-02781-0 |
| Harmonizome | version 3.0 | February 2025 | Custom Python script | https://academic.oup.com/nar/article/53/D1/D1016/7905315 |
| Hetionet | version 1.0 | February 2025 | https://github.com/hetio/hetionet | https://elifesciences.org/articles/26726 |
| IMPPAT | version 2.0 | January 2025 | https://cb.imsc.res.in/imppat | https://www.nature.com/articles/s41598-018-22631-z |
| MGI (Mouse Genome Informatics) | Downloaded January 2025 | January 2025 | https://www.informatics.jax.org/downloads/reports/index.html | https://pmc.ncbi.nlm.nih.gov/articles/PMC11075557/ |
| **Literature** *(hallmarks-of-aging ↔ biological process curation)* | — | — | manually curated | — |
| MetaboAge | August 2020 | January 2025 | https://www.metaboage.info/download/ | https://link.springer.com/article/10.1007/s10522-020-09892-w |
| MonarchKG | 5 January 2024 | January 2025 | https://data.monarchinitiative.org/monarch-kg/latest/monarch-kg.tar.gz | https://academic.oup.com/nar/article/52/D1/D938/7449493 |
| MouseNet v2 | version 2 | January 2025 | https://www.inetbio.org/mousenet/ | https://academic.oup.com/nar/article/44/D1/D848/2502647 |
| PharmKG | version 3 | January 2025 | https://zenodo.org/records/4077338 | https://academic.oup.com/bib/article/22/4/bbaa344/6042240 |
| PhytoHub | Version 1.4 | March 2025 | https://phytohub.eu/entries | https://hal.science/hal-01697081/file/2017_Giacomoni_ICPH_Qu%C3%A9bec.pdf |
| PrimeKG | Feb 2023 version | January 2025 | https://dataverse.harvard.edu/api/access/datafile/6180620 | https://www.nature.com/articles/s41597-023-01960-3 |
| SGD (Saccharomyces Genome Database) | Downloaded January 2025 | January 2025 | http://sgd-archive.yeastgenome.org/curation/literature/ | https://academic.oup.com/nar/article/26/1/73/2379479 |
| SMS (Small Molecule Suite) | Harvard, 2019 | May 2023 | https://lsp.connect.hms.harvard.edu/smallmoleculesuite/ | https://www.sciencedirect.com/science/article/pii/S245194561930073X |
| STITCH | version 5 | January 2025 | https://stitch-db.org/ | https://academic.oup.com/nar/article/44/D1/D380/2503089 |
| STRING | version 12 | January 2025 | https://string-db.org/ | https://string-db.org/ |
| TARKG | October 2024 version | January 2025 | https://tarkg.ddtmlab.org/download | https://academic.oup.com/bioinformatics/article/40/10/btae598/7818343 |
| TTD (Therapeutic Target Database) | 2024 version | March 2025 | https://ttd.idrblab.cn/full-data-download | https://academic.oup.com/nar/article/52/D1/D1465/7275004 |
| Worm Interactome Database | version 8 | January 2025 | https://interactome.dfci.harvard.edu/C_elegans/index.php?page=download | https://interactome.dfci.harvard.edu/C_elegans/ |
| WormBase | version WS287 (2024) | January 2025 | https://ftp.ebi.ac.uk/pub/databases/wormbase/parasite/datasets/ | https://www.wormbase.org/ |
| YeastNet v3 | version 3 | January 2025 | https://www.inetbio.org/yeastnet/downloadnetwork.php | https://www.inetbio.org/yeastnet/ |
| ZFIN (Zebrafish Information Network) | 2024 | January 2025 | https://zfin.org/downloads | https://pubmed.ncbi.nlm.nih.gov/21036866/ |
| **species connection** *(cross-species ortholog/connection sources)* | — | — | — | — |
| iBKH | 2023-03-21 | January 2025 | https://github.com/wcm-wanglab/iBKH/tree/main/iBKH/iBKH_2021_05_03 | https://www.cell.com/iscience/fulltext/S2589-0042(23)00537-0 |
| miRTarBase 2025 | Release 10.0 | 17-05-2026 | https://mirtarbase.cuhk.edu.cn/~miRTarBase/miRTarBase_2025 | miRTarBase 2025: updates to the collection of experimentally validated microRNA–target interactions, *Nucleic Acids Research* |
| PheKnowLator | v1 | 17-05-2026 | https://github.com/callahantiff/PheKnowLator | https://www.nature.com/articles/s41597-024-03171-w |
| **Other sources (phytochemical / Ayurvedic compound data)** | | | | |
| AyurvedicPlantClassifier (english.xlsx) | March 2024 | July 2025 | https://github.com/akshachrya/AyurvedicPlantClassifier/blob/main/data/english.xlsx | same |
| PhytoChemicalDiversity (all_species_compound_data.csv) | July 2025 | July 2025 | https://github.com/alrichardbollans/PhytoChemicalDiversity/blob/master/collect_and_compile_data/collect_compound_data/outputs/all_species_compound_data.csv | same |
| phytochemicals (phyto_chemicals.db) | February 2023 | July 2025 | https://github.com/asgarhussain/phytochemicals/blob/main/phyto_chemicals.db | same |
| Ayurvedic medicine catalogue (Database.json) | March 2019 | July 2025 | https://github.com/kuralamuthan300/ayurvedic-medicine-catalogue/blob/master/Database.json | same |
| CEVOpen (Plant_compound.csv) | June 2021 | July 2025 | https://github.com/petermr/CEVOpen/blob/master/Data%20Analysis/Plant_compound.csv | same |

> **Note on bare category rows**: *Literature* and *species connection* are not standalone downloadable databases — they are curation categories. **Literature** denotes manually curated links connecting the hallmarks of aging to relevant biological processes (used to build aging ↔ biological-process relation triples). **species connection** groups sources (iBKH, miRTarBase, PheKnowLator) used primarily to establish cross-species/cross-entity connections rather than aging- or disease-specific content on their own.

---

## **2.3 Source Categories (Functional Grouping)**

While the table above is the single master/supplementary reference, it's useful to mentally group sources by what they contribute to the KG:

### **A. Aging-Specific Sources**
GenAge, DrugAge, GenDR, CellAge, AgeXtend, Aging Atlas, AgeAnno, AgeAnnoMO, AgingBank, Digital Aging Atlas, HALD, MetaboAge, Evolf

→ Feed the **Aging KG** variant directly (gene/drug/cell ↔ aging relations).

### **B. General Biomedical Knowledge Graphs**
DRKG, PrimeKG, Hetionet, MonarchKG, CKG, CROssBAR, iBKH, TARKG, PharmKG, BOCK KG, BioGrakn, PheKnowLator

→ Feed the **Biomedical KG** variant (disease-gene-chemical-phenotype context).

### **C. Protein/Gene Interaction Networks**
STRING, BioGRID, Biosnap, MouseNet v2, YeastNet v3, Worm Interactome Database, FICE

→ Gene-Gene / Protein-Protein edges, species-specific where noted.

### **D. Chemical / Drug / Target Databases**
ChEMBL, DrugBank, BindingDB, STITCH, TTD, DTInet, SMS

→ Chemical-Gene and Chemical-Target edges.

### **E. Species-Specific Annotation Resources**
FlyBase (Drosophila), WormBase (C. elegans), SGD (Yeast), ZFIN (Zebrafish), MGI (Mouse)

→ Gene ID resolution, symbol mapping, and species-specific annotation — critical inputs to the Ortholog Mapping pipeline (see 06_KGConstruction.md §6.1).

### **F. miRNA / Regulatory**
miRTarBase 2025

→ miRNA-Gene regulatory edges.

### **G. Phytochemical / Traditional Medicine**
PhytoHub, IMPPAT, AyurvedicPlantClassifier, PhytoChemicalDiversity, phytochemicals (phyto_chemicals.db), Ayurvedic medicine catalogue, CEVOpen

→ Plant-compound and Ayurvedic-compound data, feeding Chemical-entity nodes for compound-aging association work (relevant to candidate screening, e.g. chrysin and other CS-inhibitor candidates).

### **H. Literature Curation**
Hallmarks-of-aging ↔ biological process links

→ Aging-BiologicalProcess relation triples, manually curated rather than bulk-downloaded.

### **I. Cross-Species Connection Sources**
iBKH, miRTarBase, PheKnowLator

→ Support cross-species entity linking used in ortholog/connection mapping.

---

## **2.4 Download Provenance & Reproducibility**

Each source row in the master table carries four reproducibility-critical fields, matched 1:1 to the manuscript's Supplementary Table:

| Field | Purpose |
|---|---|
| **Version / Build** | Exact release pinned — required because aging databases (GenAge, DrugAge, CellAge) update periodically and results must be traceable to a specific build |
| **Last Download** | Date the data was actually pulled — distinct from the database's own release date |
| **Download Link** | Direct retrieval path (GitHub repo, FTP, institutional archive, or "In house data" / "Custom Python script" / "manually curated" for non-bulk sources) |
| **Reference / Link** | Primary publication or landing page describing the resource |

### **Non-standard provenance cases**

- **In house data** (AgeXtend, Evolf): generated internally rather than downloaded from a public repository — document the generating script/notebook alongside the table entry.
- **Custom Python script** (Harmonizome): no flat-file bulk download exists; a script queries the Harmonizome API. Keep the script version-controlled alongside the data version.
- **Manually curated** (Literature category): no download link applies; curation date and curator should be tracked instead of a "Last Download" date.

### **Version mismatches to watch for**

During the Nature Communications revision, a **BioGRID 4.4.221 vs. 5.0.257** mismatch was found in yeast-specific notebooks — always cross-check the version actually used in each species notebook against the version recorded in this table before finalizing any KG build.

---

## **2.5 Building Your Local Source Manifest**

For your own working copy (separate from the manuscript supplement, useful for day-to-day pipeline runs), maintain a `source_manifest.csv` that mirrors the master table plus operational metadata:

```csv
source_name,version,last_download,download_link,n_records,n_columns,local_path,hash_md5,notes
GenAge,Build 21 (8/28/2023),January 2025,https://genomics.senescence.info/genes/index.html,,,/storage/Arushi/090526_EvoAge/data/raw/aging/genage.csv,,
DrugAge,Build 5,Nov 29 2024,https://genomics.senescence.info/drugs/,,,/storage/Arushi/090526_EvoAge/data/raw/aging/drugAge.csv,,
STRING,version 12,January 2025,https://string-db.org/,,,/storage/Arushi/090526_EvoAge/data/raw/biomedical/string.tsv,,confidence>0.7 filter applied downstream
```

Fill in `n_records`, `n_columns`, `local_path`, and `hash_md5` as each source is actually pulled onto the cluster — this gives you a working, queryable inventory distinct from (but consistent with) the static manuscript table above.

---

## **2.6 Next Steps**

1. ✅ **Master table finalized?** → Move to [Preprocessing](03_Preprocessing.md) (per-source cleaning, gene symbol resolution, relation standardization)
2. **Need ortholog/species mapping for these sources?** → See KG Construction §6.1 (06_KGConstruction.md)
3. **Tracking version mismatches across notebooks?** → Log them here and cross-reference against the Supplementary Table before each KG rebuild

---

## **Reference: Quick Counts**

- **Total sources in master table**: 48 named databases/resources + 2 curation categories (Literature, species connection grouping)
- **Earliest source vintage**: DRKG (May 2020)
- **Most recent downloads**: miRTarBase 2025, PheKnowLator (17-05-2026)
- **Species-specific annotation sources**: 5 (FlyBase, WormBase, SGD, ZFIN, MGI)
- **Phytochemical/Ayurvedic sources**: 7 (PhytoHub, IMPPAT, AyurvedicPlantClassifier, PhytoChemicalDiversity, phyto_chemicals.db, Ayurvedic medicine catalogue, CEVOpen)
