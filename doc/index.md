# EvoAge: Multi-Species Aging Knowledge Graph Platform

**EvoAge** is a comprehensive knowledge graph (KG) integration platform combining 48+ biomedical databases into ~1 billion RDF triples across six species (Human, Mouse, Zebrafish, Drosophila, C. elegans, Yeast). EvoAge integrates aging-specific and biomedical context to enable predictive aging biology research through knowledge graph embeddings and machine learning.

---

## 📊 **Quick Stats**

| Metric | Value |
|--------|-------|
| **Databases Integrated** | 48+ biomedical sources |
| **Total Triples** | ~1 billion across all KGs |
| **Species Covered** | 6 (Human, Mouse, Zebrafish, Drosophila, C. elegans, Yeast) |
| **Relation Types** | 60+ semantic relations |
| **KG Variants** | 3 (Aging-specific, Biomedical, Combined EvoAge) |
| **Best KGE Model** | RESCAL (Test MRR: 0.874, Hit@10: 0.997) |
| **Ortholog Strategies** | 2 (1-to-1 representatives, 1-to-many 121_12M) |

---

## 🚀 **Quick Start**

### **Installation (5 minutes)**
```bash
# Clone and setup environment
git clone <repo-url>
cd EvoAge-Documentation
conda env create -f environment.yml
conda activate evoage_env
```

### **Build Your First KG (30 minutes)**
```python
from evoage.preprocessing import download_sources, merge_triples
from evoage.orthology import map_orthologs

# Download data from 48+ sources
data = download_sources(species=['human', 'mouse'])

# Map orthologs
ortho_data = map_orthologs(data, strategy='1-to-1')

# Merge and standardize
kg = merge_triples(ortho_data, kg_variant='aging')
```

---

## 📚 **Documentation Sections**

### **Phase 1: Data Engineering**
- [**Installation & Setup**](installation.md) — Environment, dependencies, cluster access
- [**Data Collection**](data-collection.md) — Sourcing from 48+ databases
- [**Preprocessing**](preprocessing.md) — Cleaning, standardization, validation

### **Phase 2: Knowledge Graph Construction**
- [**Relation Processing**](relation-processing.md) — Handling 60+ relation types
- [**Ortholog Mapping**](ortholog-mapping.md) — Ensembl Compara ortholog mapping (1-to-1 and 1-to-many)
- [**KG Construction**](kg-construction.md) — Creating Aging vs Biomedical KG variants

### **Phase 3: Tensors & Training**
- [**Tensors & Splitting**](kg-tensors-and-splitting.md) — Converting to integer tensors and train/valid/test splitting

### **Reference**
- [**Quick Start Guide**](quick-start.md) — Brief framework checklist
- [**Documentation Structure**](documentation-structure.md) — Navigation mapping and roadmap

---

## 🧬 **The EvoAge Pipeline**

```
┌─────────────────────────────────────────────────────────────┐
│                   DATA COLLECTION                           │
│  (48+ databases: DrugAge, GenAge, DRKG, PrimeKG, etc.)     │
└────────────┬────────────────────────────────────────────────┘
             │
┌────────────▼────────────────────────────────────────────────┐
│               PREPROCESSING & VALIDATION                     │
│  • SMILES canonicalization (chemistry)                      │
│  • Gene symbol resolution (tiered, per-species)             │
│  • Relation type standardization                            │
└────────────┬────────────────────────────────────────────────┘
             │
┌────────────▼────────────────────────────────────────────────┐
│            ORTHOLOG MAPPING (Ensembl Compara)               │
│  • 1-to-1: Single representative human gene per target      │
│  • 1-to-many: All ortholog types (121_12M)                 │
└────────────┬────────────────────────────────────────────────┘
             │
        ┌────┴────┐
        │          │
┌───────▼──┐  ┌────▼──────┐
│  Aging   │  │ Biomedical│
│   KG     │  │    KG     │
└────┬─────┘  └────┬──────┘
     │             │
     └──────┬──────┘
            │
     ┌──────▼──────┐
     │ EvoAge KG   │
     │  (Combined) │
     └──────┬──────┘
            │
 ┌──────────▼──────────────────┐
 │   KGE TRAINING (DGL-KE)       │
 │   6 Models: RESCAL, RotatE... │
 └──────────┬──────────────────┘
            │
 ┌──────────▼──────────────────────────────┐
 │           EVALUATION TASKS                 │
 │  • Edge type prediction                   │
 │  • Null-hypothesis (shuffled) KGs         │
 │  • Aging-specific test set (AB_test)      │
 │  • Per-relation statistical cutoffs       │
 │  • 1% species-specific test set           │
 └──────────┬──────────────────────────────┘
            │
 ┌──────────▼──────────────────┐
 │    DOWNSTREAM ANALYSIS        │
 │  • LLM-based QA scoring       │
 │  • Candidate compound ranking │
 │  • Feature extraction (cuGraph)
 │  • Community detection        │
 └───────────────────────────────┘
```

---

## 📦 **Key Components**

### **Three KG Variants**
1. **Aging KG**: Aging-specific data (DrugAge, GenAge, CellAge, etc.) + 48 species orthologs
2. **Biomedical KG**: General biomedical data (DRKG, PrimeKG, STRING, etc.)
3. **EvoAge (Combined)**: Aging + Biomedical contexts for richer predictions

### **Two Ortholog Strategies**
- **1-to-1**: One representative human ortholog per gene target
- **1-to-many (121_12M)**: All ortholog types for broader coverage

### **Six KGE Models Evaluated**
- RESCAL ⭐ **(Best: MRR 0.874, Hit@10 0.997)**
- RotatE
- ComplEx
- SimplE
- DistMult
- TransE

---

## 🔬 **Key Publications & References**

This work is currently under review at **Nature Communications** (Reference manuscript included in repo).

**Key Datasets**:
- Aging Sources: DrugAge, GenAge, GenDR, CellAge, AgeXtend, Aging Atlas
- Biomedical Sources: DRKG, PrimeKG, Hetionet, Monarch, STRING, miRTarBase
- Ortholog Mapping: Ensembl Compara (biomaRt, release e114)

---

## 💻 **System Requirements**

- **Compute**: 629GB RAM, Multi-GPU setup (RTX 5000 Ada, RTX 3090)
- **Storage**: ~2TB for full pipeline outputs
- **OS**: Linux (Ubuntu 20.04+)
- **Job Scheduler**: PBS/Torque (HPC cluster)
- **Python**: 3.8+, PyTorch, DGL-KE, cuGraph

See [Installation Guide](installation.md) for detailed setup.

---

## 📖 **How to Use This Documentation**

1. **New to EvoAge?** Start with [Overview & Installation](installation.md)
2. **Want to reproduce the pipeline?** Follow the step-by-step [Data Collection](data-collection.md) → [Preprocessing](preprocessing.md) → [Relation Processing](relation-processing.md) → [Ortholog Mapping](ortholog-mapping.md) → [KG Construction](kg-construction.md) → [Tensors & Splitting](kg-tensors-and-splitting.md)
3. **Troubleshooting?** See structure/reference guides.

---

## 📁 **Repository Structure**

```
evoage/
├── data/                          # Raw data, processed KGs
├── preprocessing/                 # Scripts: download, clean, standardize
├── orthology/                     # Ensembl Compara mapping
├── kg_construction/               # Merging, splitting, tensor building
├── training/                      # DGL-KE training pipelines
├── evaluation/                    # Edge prediction, cutoff calibration
├── analysis/                      # Dashboards, visualizations
├── notebooks/                     # Jupyter notebooks per source type
└── doc/                           # This documentation
```

---

## 👥 **Authors & Attribution**

**Principal Investigator**: Gaurav Ahuja (IIIT-Delhi)  
**Lead Developer**: Arushi Arora  
**Collaborators**: [Additional team members]

---

## 📝 **License**

[Specify your license here: MIT, Apache 2.0, etc.]

---

## 🤝 **Contributing**

[Guidelines for contributing updates to documentation or code]

---

## 📧 **Contact & Support**

- **Issues/Bugs**: [GitHub Issues]
- **Questions**: [Contact email]
- **Lab Website**: [The Ahuja Lab](https://the-ahuja-lab.github.io/)

---

## 🔗 **Quick Links**

- [Nature Communications Manuscript](link-to-preprint)
- [GitHub Repository](link)
- [Interactive KG Browser](link-if-available)
- [The Ahuja Lab](https://the-ahuja-lab.github.io/)

---

**Last Updated**: June 2026  
**Status**: Under review at Nature Communications
