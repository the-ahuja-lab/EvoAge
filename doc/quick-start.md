# 🚀 Quick Start Guide

---

## **Quick File Overview**

### **1. [Home / Index](index.md)**
- 📊 Project overview and statistics
- 🚀 Quick start code examples
- 🏗️ Architecture diagram (text-based)
- 📖 Navigation to all sections
- 💻 System requirements

### **2. [Installation & Setup](installation.md)**
- 🔧 System prerequisites
- 🐍 Conda environment setup (with full `environment.yml` template)
- 🖥️ HPC cluster configuration (PBS/Torque)
- ⚙️ Configuration file templates
- ✔️ Installation verification script

### **3. [Data Collection](data-collection.md)**
- 📦 Master source table (48+ databases, version-pinned)
- 🗂️ Functional grouping by category
- 📁 Reproducibility & provenance tracking

### **4. [Preprocessing](preprocessing.md)**
- 🧬 Two paradigms (relation-typed CSV vs. raw RDF/OWL triples)
- 🛠️ Case-insensitive gene symbol resolution, chemical SMILES, and disease cascade lookup
- 📊 Entity mapping validation & output schemas

### **5. [Relation Processing](relation-processing.md)**
- 🔗 Relation-by-relation merging cascading logic
- 🛠️ Deduplication preserving cross-source provenance (`::` joined tags)
- 📊 Standardized 13-column canonical schemas

### **6. [Ortholog Mapping](ortholog-mapping.md)**
- 🧬 Ensembl Compara ortholog mapping (biomaRt & gprofiler2 cascade)
- 🔗 1-to-1 vs. 1-to-many ortholog strategies
- 🛠️ Homology queries and bijective row explosions for 1-to-many options

### **7. [KG Construction](kg-construction.md)**
- 🧬 Splitting unified multi-species graphs into Aging-specific vs. Biomedical KGs
- 🔗 Substring matching and default biomedical fallback buckets

### **8. [Tensors & Splitting](kg-tensors-and-splitting.md)**
- 🧠 PyTorch tensor generation, global node and relation ID mapping
- ⚙️ Deteriministic, parallelized ID builders
- 💾 Bi bijective int64 deduping representation
- 📝 Leakage-free train/valid/test splitting lineages (AB_test)

---
