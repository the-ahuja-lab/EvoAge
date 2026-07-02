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

## 💻 **System Requirements**

- **Compute**: 629GB RAM, Multi-GPU setup (RTX 5000 Ada, RTX 3090)
- **Storage**: ~2TB for full pipeline outputs
- **OS**: Linux (Ubuntu 20.04+)
- **Job Scheduler**: PBS/Torque (HPC cluster)
- **Python**: 3.8+, PyTorch, DGL-KE, cuGraph

See [Installation Guide](installation.md) for detailed setup.

---

## 📖 **How to Use EvoAge**

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
**Lead Developer**: Arushi Sharma  


**Last Updated**: June 2026  
**Status**: Under review at Nature Communications
