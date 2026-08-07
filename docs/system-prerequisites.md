# EvoAge System Prerequisites & Environment

This page documents the hardware, operating system, and software environment used to build, train, evaluate, and serve EvoAge. It corresponds to the **Computational Infrastructure**, **Graph Database Implementation**, **KGE Training**, and **Backend/Frontend** sections of the manuscript Methods.

<<<<<<< HEAD
Due to the scale of the integrated EvoAge Knowledge Graph (~1.2 billion triples, 16 entity types, and 89 relation types), standard workstation hardware is insufficient. Below is the minimum recommended hardware profile required to run the pipeline successfully.
=======
The integrated EvoAge knowledge graph contains **~1.23 billion unique triples** (~1.28 billion when source provenance is preserved), **45.6 million nodes**, **16 semantic node labels**, and **~89 relation types**, drawn from **51 source layers**. At this scale, ordinary desktop hardware is not sufficient — the requirements below are the practical minimum for reproducing the pipeline end to end.
>>>>>>> d0f0097 (Doc Changes)

---

## 1. Reference Systems

Two distinct machines were used. Only the first is required to reproduce the knowledge graph and embedding pipeline; the second is needed only if you intend to repeat the AgingKG-guided language model fine-tuning.

### 1.1. KG construction, embedding training, and evaluation

| Component | Specification |
|---|---|
| **Operating System** | Ubuntu 22.04 LTS (validated on 22.04.3) |
| **System RAM** | 629 GB |
| **GPU 1** | NVIDIA RTX 5000 Ada Generation — 32 GB VRAM |
| **GPU 2** | NVIDIA GeForce RTX 3090 — 24 GB VRAM |
| **CUDA** | 12.0 |
| **Python** | 3.10 |

This dual-GPU configuration enabled parallelized computation and efficient handling of large-scale graph data.

### 1.2. Language model fine-tuning (BioMistral / GraphGen)

| Component | Specification |
|---|---|
| **Operating System** | Ubuntu 22.04 LTS |
| **GPU** | NVIDIA B200 — 183 GB HBM3E |
| **CUDA** | 12.8 |

The large HBM3E pool is what makes parameter-efficient fine-tuning and local serving of BioMistral-7B and Qwen3-14B-FP8 practical on a single device.

---

## 2. Minimum Recommended Profile

If you are reproducing the pipeline on your own hardware, these are the floors rather than the specifications above.

| Resource | Minimum requirement | Why it is needed |
|---|---|---|
| **System RAM** | **250 GB** | In-memory relation-wise merges, global entity ID mapping, bijective int64 deduplication, and chunked train/validation/test splitting of billion-scale triple tables. |
| **GPU** | **≥ 24 GB VRAM**, dual-GPU recommended | DGL-KE training of 64-dimensional embeddings over ~1.2 billion triples, and GPU-scored edge-type prediction across all relation types. |
| **Storage** | **≥ 2 TB NVMe SSD** | Raw source databases, intermediate Parquet/CSV tables, the Neo4j store, and trained KGE tensors. NVMe (not SATA/HDD) matters for the chunked read/write phases. |
| **Operating System** | **Linux** — Ubuntu 22.04 LTS or RHEL | DGL, PyTorch, and the CUDA toolchain are configured for Linux. Ubuntu for workstations; RHEL for HPC cluster nodes. |
| **CUDA** | **12.0+** with a matching NVIDIA driver | Required by the DGL / PyTorch builds used for training and inference. |

> **Note**
> The validation workstation carried 629 GB RAM, but the pipeline has been optimized to execute within a 250 GB envelope. Below this, the relation-wise merge and deduplication stages will need to be re-chunked.

---

## 3. Software Stack

### 3.1. Graph database

| Software | Version | Role |
|---|---|---|
| **Neo4j** | v2025.03.0 | Stores the harmonized graph — 16 node labels, ~89 relationship types, with provenance retained on every relationship. |
| **APOC library** | Matched to the Neo4j release | Batched graph construction and post-processing alongside `LOAD CSV` bulk import. |

Unique constraints and indexes must be created on node identifiers **before** bulk loading, both for data integrity and for acceptable load/query performance.

### 3.2. Knowledge graph embedding

| Software | Version | Role |
|---|---|---|
| **DGL** (Deep Graph Library) | 1.1.2 | Backend for graph tensor operations. |
| **DGL-KE** | 0.1.0 (patched — see below) | Training and inference for TransE, RotatE, ComplEx, SimplE, DistMult, and RESCAL. |
| **PyTorch** | CUDA 12.0-compatible build | Custom GPU-optimized scripts for edge-type prediction and triple scoring. |

Two local modifications to DGL-KE are required for the EvoAge platform and are documented in the pipeline pages:

- **Type-constrained inference** — an entity-type mapping is injected so candidate entities are filtered by the expected head/tail type of the queried relation, preventing semantically invalid cross-type predictions.
- **Artifact caching** — entity and relation dictionaries are loaded once and held in memory instead of being re-read from disk per query, reducing artifact access time from 30–50 s to roughly 2–4 s and making interactive inference feasible.

**Training defaults:** 64-dimensional embeddings, batch size 2,048, learning rate 0.01, Adagrad optimizer, negative sampling, with `max_steps` computed per graph as `(epochs × training_triples) / batch_size` for 10 epochs.

### 3.3. Orthology mapping

| Resource | Version |
|---|---|
| **Ensembl BioMart** | Release e114 |

Used to map gene identifiers from mouse, yeast, worm, fly, and zebrafish onto human orthologs (one-to-one and one-to-many variants).

### 3.4. Platform — backend, agents, and frontend

| Software | Version | Role |
|---|---|---|
| **FastAPI** | — | RESTful microservice API: entity retrieval, relationship exploration, link prediction, hypothesis testing. |
| **Streamlit** | 1.48.0 | Web interface for graph exploration and hypothesis evaluation. |
| **Redis** | — | Request control, rate limiting, and caching. |
| **JWT authorization** | — | User authentication and request management. |
| **Kani** | — | Function-calling framework for the agent layer; the LLM invokes backend REST endpoints as tools rather than querying the graph directly. |

The complete frontend and backend dependency list with pinned versions is given in **Supplementary Table 4** of the manuscript.

### 3.5. Language model adaptation (optional)

| Software | Role |
|---|---|
| **GraphGen** | Comprehension-gap-driven synthetic data generation from Aging KG triples. |
| **KuzuDB** | Holds train and held-out test triples in separate namespaces to prevent leakage. |
| **SGLang** | Serves BioMistral-7B and Qwen3-14B-FP8 locally as OpenAI-compatible endpoints. |
| **LLaMA-Factory** | Supervised fine-tuning with DoRA (weight-decomposed low-rank adaptation). |
| **FlashAttention-2** | Required for the fine-tuning configuration (bf16 mixed precision, gradient checkpointing). |

Models used: **BioMistral-7B** (base to be adapted), **Qwen3-14B-FP8** (question generation), **MedGemma-27B** (blinded judge for the framework comparison).

### 3.6. Analysis and visualization

**Python** — pandas 2.3.2, numpy 2.2.6, matplotlib 3.10.3, statsmodels 0.14.5, scikit-learn, SciPy.

**R** (v4.2.3) — tidyverse 2.0.0, ggpubr 0.6.2, gghalves 0.1.4, ggprism 1.0.7, gridExtra 2.3, broom 1.0.10, effsize.

---

## 4. Verifying Your Environment

```bash
# OS and available memory (GB)
lsb_release -d
free -g

# GPUs, VRAM, and driver
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv

# CUDA toolkit
nvcc --version

# Python and core libraries
python3 --version
python3 -c "import torch, dgl; print('torch', torch.__version__, '| cuda', torch.version.cuda, '| gpus', torch.cuda.device_count()); print('dgl', dgl.__version__)"

# Neo4j
neo4j --version

# Free space on the target volume (need >= 2 TB)
df -h /path/to/evoage/storage
```

A healthy setup reports Linux, ≥ 250 GB total memory, at least one CUDA-visible GPU with ≥ 24 GB VRAM, `torch.cuda.device_count()` greater than zero, and ≥ 2 TB free on the data volume.

---

**Next:** [Step 01 — Data Collection](data_collection_01.md)
