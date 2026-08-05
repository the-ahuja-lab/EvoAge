# Step 02 — Data Processing (Per-Source)

## 1. Purpose

This is the **second step** of the EvoAge KG pipeline. Each of the ~50 collected data sources has a **different format, schema, and identifier system**. This step processes every source individually — cleaning, normalising IDs, resolving gene symbols, and converting raw data into a **standardised KG-triple format**:

```
Head | Relation | Tail | Head_type | Tail_type | Source | KG_Source | Head_detail_name | Tail_detail_name | Head_id_is | Tail_id_is | kg_type
```

Because each data source is different, a **tailored processing strategy** was developed for each source in its own Jupyter notebook.

---

## 2. Input

Raw data from **Step 01 (Data Collection)**, located in:
```
kg_formation/data_collection/<source_name>/
```

Plus shared reference/mapping dictionaries:
- **NCBI gene_info** — GeneID ↔ Symbol ↔ Synonyms (per species)
- **PubChem CID-Synonym** — compound name → PubChem CID
- **ChEBI** — ChEBI ID mappings
- **UniProt** — protein ID resolution
- **DO / DOID / MONDO** — disease ontology mappings
- **GO (Quick_GO)** — Gene Ontology term resolution
- **UBERON** — anatomical entity ontology
- **HPO** — Human Phenotype Ontology
- **Reactome** — pathway IDs

---

## 3. Output

Processed KG-triple CSV files saved into:
```
kg_formation/data_processing/<source_name>/
```

Each output file follows the standard schema with columns:
`Head`, `Relation`, `Tail`, `Head_type`, `Tail_type`, `Source`, `KG_Source`, `Head_detail_name`, `Tail_detail_name`, `Head_id_is`, `Tail_id_is`, `kg_type`

---

## 4. Processing Notebooks (Human Data)

**31 notebooks** process human (and sometimes multi-species) data sources:

### Aging-Specific Sources

| Notebook | Source | Species | Key processing |
|---|---|---|---|
| `genage.ipynb` | GenAge (genage_models.csv) | Human, Mouse, Drosophila, C. elegans, Yeast | NCBI gene symbol resolution per species; separate output per species |
| `drugage.ipynb` | DrugAge (two source files) | Multi-species | PubChem CID resolution for compounds; parallel processing of two input files |
| `ageanno.ipynb` | AgeAnno | Human | Cell-type and aging-annotation mapping |
| `ageannomo.ipynb` | AgeAnnoMO | Multi-organism | Multi-organism aging annotation mapping |
| `agextend.ipynb` | AgeXtend (in-house) | Multi-species | 9 hallmark TSV files → Chemical–Hallmark CSVs; drug–aging data per species |
| `aging_atlas.ipynb` | Aging Atlas | Human | Aging gene/protein annotation processing |
| `digital_aging_atlas.ipynb` | Digital Ageing Atlas | Human, Mouse | Gene → Tissue (BTO) edges; module-based processing |
| `gendr.ipynb` | GenDR | Mouse, Drosophila, C. elegans, Yeast | Dietary restriction gene manipulations |
| `hald.ipynb` | HALD | Human | Entity + triple files; Carbohydrate/Lipid/Peptide type normalisation |
| `MetaboAge.ipynb` | MetaboAge | Human | Metabolite–aging associations |
|

### General Biomedical KGs

| Notebook | Source | Key processing |
|---|---|---|
| `PrimeKG.ipynb` | PrimeKG (kg.csv) | 25 relation types; split by relation, full ID standardisation |
| `DRKG.ipynb` | DRKG (drkg.tsv) | Parse `EntityType::ID` format; split into per-relation CSVs |
| `hetionet.ipynb` | Hetionet | Anatomy, Gene, Disease, Chemical edges; UBERON/NCBI/DOID mapping |
| `monarchkg1.ipynb` / `monarchkg2.ipynb` | Monarch KG | Full reference dict loading (NCBI, PubChem, ChEBI, UniProt, DO, MONDO); two-part processing |
| `ckg.ipynb` | CKG (Clinical KG) | Full ID standardisation across all CKG relation types from TSV files |
| `crossbar.ipynb` | CROssBAR | Node/edge file processing with reference DB lookups |
| `ibkh.ipynb` | iBKH | Cross-species entity linking |
| `tarkg.ipynb` | TAR-KG | Multiple relation types (Disease–Gene, Disease–Anatomy, Gene–Disease, etc.) |
| `pharmkg.ipynb` | PharmKG-180k | Gene–Gene, Gene–Disease, Gene–Chemical via NCBI symbol mapping |
| `bock_kg.ipynb` | BOCK KG | Entity ID → label/name lookup dictionaries; edge file filtering |
| `phenknowlator.ipynb` | PheKnowLator | Phenotype–knowledge graph processing |

### Chemical / Drug / Target

| Notebook | Source | Key processing |
|---|---|---|
| `biningdb_sms_biosnap_chembl_drugbank.ipynb` | BindingDB, SMS, Biosnap, ChEMBL, DrugBank | Combined processing of 5 chemical/drug databases |
| `STITCH_STRING_Human_KG.ipynb` | STITCH + STRING (Human) | Chemical–Chemical + Protein–Protein interactions for human |
| `STRING.ipynb` | STRING (multi-species) | PPI networks for all 6 species (Human, Mouse, Drosophila, C. elegans, Yeast, Zebrafish) |

### Other Sources

| Notebook | Source | Key processing |
|---|---|---|
| `harmonizome_part1.ipynb` + `harmonizone_part2.ipynb` | Harmonizome | Two-part: API-generated intermediates → final merged KG CSVs |
| `immpat_ttd_phytohub_othersources.ipynb` | IMMPAT, TTD, PhytoHub, other phytochemical sources | Ayurveda/phytochemical processing; Plant–Chemical, Chemical–Disease edges |
| `mirTARbase.ipynb` | miRTarBase | miRNA–Gene regulatory edges |
| `Agingbank.ipynb` | AgingBank | Aging gene bank processing |

---

## 5. Species-Specific Processing

Species-specific data sources are processed in a **separate subdirectory**:

```
data_processing_02/species_specific_data_source/
├── Celegans/
│   ├── fic.ipynb            ← FICE (Functional Interactome of C. elegans)
│   ├── stitch.ipynb         ← STITCH chemical interactions
│   ├── string.ipynb         ← STRING PPI network
│   ├── wormbase.ipynb       ← WormBase gene annotations
│   └── worminteractomedatabase.ipynb  ← Worm Interactome Database
│
├── Drosophila/
│   ├── flybase.ipynb        ← FlyBase allele/gene data
│   ├── stitch.ipynb         ← STITCH chemical interactions
│   └── string.ipynb         ← STRING PPI network
│
├── Mouse/
│   ├── mgido.ipynb          ← MGI + Disease Ontology mappings
│   ├── stitch.ipynb         ← STITCH chemical interactions
│   └── string_mousenet.ipynb ← STRING + MouseNet v2 combined PPI
│
├── Yeast/
│   ├── esldb.ipynb          ← eSLDB (Essential gene database)
│   ├── sgd.ipynb            ← SGD (Saccharomyces Genome Database)
│   ├── stitch_ch_ch.ipynb   ← STITCH Chemical–Chemical
│   ├── stitch_ch_ge.ipynb   ← STITCH Chemical–Gene
│   └── string_yeastnet_biogrid.ipynb  ← STRING + YeastNet v3 + BioGRID combined
│
└── Zebrafish/
    ├── stitch.ipynb         ← STITCH chemical interactions
    ├── string.ipynb         ← STRING PPI network
    └── zfin.ipynb           ← ZFIN gene/phenotype annotations
```

---

## 6. Common Processing Pattern

Although each notebook uses a tailored strategy, they follow a shared general pattern:

1. **Load raw data** from `data_collection/<source>/`
2. **Load reference dictionaries** (NCBI gene_info, PubChem synonyms, ontology mappings)
3. **Map identifiers** — resolve gene symbols, chemical names, disease IDs to standardised ontology IDs
4. **Assign entity types** — categorise heads and tails (Gene, ChemicalEntity, Disease, Pathway, etc.)
5. **Define relations** — map source-specific relationship labels to the EvoAge unified relation vocabulary
6. **Build KG triples** — create rows with the standard schema columns
7. **Save output** — write per-relation CSV files to `data_processing/<source>/`

### Standard output schema columns

| Column | Description |
|---|---|
| `Head` | Head entity identifier (standardised) |
| `Relation` | Relation type (e.g., `Gene_Disease`, `ChemicalEntity_Protein`) |
| `Tail` | Tail entity identifier (standardised) |
| `Head_type` | Entity type of head (e.g., Gene, ChemicalEntity, Disease) |
| `Tail_type` | Entity type of tail |
| `Source` | Original database name |
| `KG_Source` | KG source label |
| `Head_detail_name` | Human-readable name for head entity |
| `Tail_detail_name` | Human-readable name for tail entity |
| `Head_id_is` | ID namespace for head (e.g., NCBI_ID, Pubchem, DOID) |
| `Tail_id_is` | ID namespace for tail |
| `kg_type` | KG category (Aging / Biomedical) |

---

## 7. Key Design Decisions

- **One notebook per source**: Ensures source-specific edge cases are handled without affecting other sources.
- **Reference dictionaries loaded per notebook**: Each notebook loads only the dictionaries it needs (e.g., GenAge needs per-species NCBI lookups; DrugAge needs PubChem synonym dictionaries).
- **Species separation**: Human data and species-specific data are processed in separate notebooks/folders to keep the pipeline clean.
- **`kg_type` assignment**: Each triple is tagged as either `Aging` or `Biomedical` depending on the source, enabling downstream splitting into KG variants.

---

## 8. File Summary

| Location | Description |
|---|---|---|
| `data_processing_02/` (root) | Human/general source processing |
| `data_processing_02/species_specific_data_source/Celegans/` |  C. elegans-specific sources |
| `data_processing_02/species_specific_data_source/Drosophila/` | Drosophila-specific sources |
| `data_processing_02/species_specific_data_source/Mouse/` | Mouse-specific sources |
| `data_processing_02/species_specific_data_source/Yeast/` | Yeast-specific sources |
| `data_processing_02/species_specific_data_source/Zebrafish/` | Zebrafish-specific sources |


