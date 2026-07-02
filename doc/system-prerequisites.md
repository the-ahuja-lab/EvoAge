# EvoAge System Prerequisites

This document details the hardware specifications, storage configurations, and operating system requirements of the workstation on which all EvoAge data processing, graph construction, model training, and evaluation are performed.

Due to the scale of the integrated EvoAge Knowledge Graph (~1.04 billion triples, 16 entity types, and 89 relation types), standard workstation hardware is insufficient. Below is the minimum recommended hardware profile required to run the pipeline successfully.

---

## 1. System Requirements Master Profile

| Resource Component | Specification Requirement | Rationale / Usage |
|---|---|---|
| **Compute (RAM)** | **Minimum 250 GB RAM** | Required for in-memory graph joins, global ID mappings, and chunked splits of billion-scale tensors. |
| **GPU Hardware** | **Multi-GPU cluster setup** | Evaluated and benchmarked on NVIDIA RTX 5000 Ada Generation (32 GB VRAM) and NVIDIA RTX 3090 (24 GB VRAM) GPUs. |
| **Storage** | **Minimum 2 TB high-speed NVMe SSD** | Needed to store raw source databases, intermediate Parquet/CSV tables, and final trained KGE tensors. |
| **Operating System** | **Linux (Ubuntu 20.04+ / RHEL)** | Ubuntu 20.04+ (LTS recommended) or RedHat Enterprise Linux (RHEL) on high-performance computing (HPC) clusters. |

---

## 2. Component Details

### 2.1. Compute Memory (RAM)
The final stage of graph building involves merging multiple multi-species datasets and executing high-throughput deduplication (using bijective int64 encoding) and chunked test/train splits. To process the graph and run the model training successfully, a **minimum of 250 GB RAM** is required.

> [!NOTE]
> *Our benchmarking and validation workstation was equipped with 600 GB RAM, but the pipeline has been optimized to execute within a minimum envelope of 250 GB RAM.*

### 2.2. GPU Hardware Configuration
EvoAge leverages Knowledge Graph Embedding (KGE) algorithms (such as RESCAL and RotatE) trained via the Deep Graph Library (DGL-KE). To handle billion-scale relational learning, the training is accelerated using a **multi-GPU setup**. The model training and evaluation runs were successfully validated using:
- **NVIDIA RTX 5000 Ada Generation** (32 GB VRAM)
- **NVIDIA RTX 3090** (24 GB VRAM)

### 2.3. Storage Infrastructure
The raw data collected from 48+ external databases, together with the intermediate processed Parquet files and final PyTorch tensor outputs (`.pt` formats), consumes substantial disk space. A **minimum of 2 TB high-speed NVMe SSD storage** is required to guarantee low-latency read/write access during data loading and chunked graph subtraction.

### 2.4. Operating System Environment
The pipeline relies on DGL, PyTorch, and CUDA drivers configured for Linux environments. The recommended systems are:
- **Ubuntu 20.04+ LTS** for local high-performance workstations.
- **RedHat Enterprise Linux (RHEL)** for execution on university or enterprise HPC cluster nodes.
