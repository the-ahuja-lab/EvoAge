# 🚀 Quick Start Guide

## **1. Minimal Installation**
```bash
git clone <repo-url>
cd EvoAge
conda env create -f environment.yml
conda activate evoage_env
```

## **2. Using the Knowledge Graph**

You can interact with the EvoAge Knowledge Graph in three primary ways:

### **1. Interactive Exploration (Streamlit Frontend)**
The easiest way to start exploring the Knowledge Graph is through the LLM-assisted web interface.
- **Start the Frontend**: Navigate to the `frontend/` directory, activate your `evoage_frontend` conda environment, and run:
  ```bash
  streamlit run streamlit_app.py --server.port=8501
  ```
- **Natural Language Querying**: Once the server is running, open `http://localhost:8501`. You can ask questions directly, e.g., *"What pathways link Rapamycin to lifespan extension?"*
- **Graph Visualization**: The frontend allows you to visually explore node connections across species, making it ideal for hypothesis generation.

### **2. Programmatic Access (FastAPI Backend)**
For developers integrating EvoAge into their computational pipelines, the REST API provides direct access to the Knowledge Graph Embeddings (KGE).
- **Start the Backend**: Navigate to the `backend/` directory, activate your `evoage_backend` conda environment, and run the server:
  ```bash
  poetry run gunicorn -w 1 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:1026
  ```
- **Interactive API Docs**: Navigate to `http://localhost:1026/docs` to see the Swagger UI.
- **Capabilities**: Run queries for link prediction, test biological hypotheses, and score biological plausibility in batch operations.

### **3. Direct Graph Queries (Neo4j Cypher)**
For advanced data science tasks or direct graph algorithms, you can query the unified graph directly using Cypher.
- **Connect**: Open a `cypher-shell` or use the Neo4j Browser at `http://localhost:7474`.
- **Query Example**:
  ```cypher
  // Example: Find orthologs associated with a specific aging hallmark
  MATCH (h:HumanGene)-[:ORTHOLOG]->(m:ModelOrganismGene)-[:ASSOCIATED_WITH]->(p:Phenotype {name: "Aging"})
  RETURN h.symbol, m.symbol LIMIT 10;
  ```

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
