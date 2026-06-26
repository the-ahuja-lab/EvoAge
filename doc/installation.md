# Installation & Setup Guide

This page details the system requirements, environment setup, cluster configurations, and verification scripts necessary to run the EvoAge pipeline.

---

## 💻 **1. System Prerequisites**

Due to the massive scale of the knowledge graph (nearly 1 billion triples across 6 species), the pipeline requires significant computational resources for preprocessing, ortholog mapping, and KGE training.

*   **Compute (RAM)**: Minimum **629GB RAM** is required for in-memory graph joins and chunked splits.
*   **GPU Hardware**: Multi-GPU cluster setup. Evaluated on **NVIDIA RTX 5000 Ada** and **NVIDIA RTX 3090** GPUs.
*   **Storage**: Minimum **2TB** of high-speed NVMe SSD storage to store raw databases, intermediate parquet tables, and trained KGE tensors.
*   **Operating System**: Linux (Ubuntu 20.04+ recommended or RedHat Enterprise Linux on HPC cluster).
*   **Job Scheduler**: PBS/Torque (HPC cluster scheduler).
*   **Python**: Version `3.8` up to `3.10`.
*   **R Environment**: Version `4.2+` (required for Ensembl BioMart ortholog lookup).

---

## 🐍 **2. Conda Environment Setup**

We use Conda to manage Python dependencies, libraries, and GPU packages. Below is the canonical `environment.yml` used for the EvoAge project:

### **`environment.yml` Template**

```yaml
name: evoage_env
channels:
  - pytorch
  - dglteam
  - nvidia
  - conda-forge
  - defaults
dependencies:
  - python=3.8.16
  - pytorch=1.13.1
  - torchvision=0.14.1
  - torchaudio=0.13.1
  - pytorch-cuda=11.7
  - dgl-cuda11.7=1.1.0
  - pandas=1.5.3
  - numpy=1.23.5
  - pyarrow=11.0.0
  - scikit-learn=1.2.2
  - scipy=1.10.1
  - pip
  - pip:
    - dgl-ke
    - pykeen==1.10.1
    - cugraph-cu11==23.04.0
    - minijinja
    - zensical
```

### **Setting up the environment**

Execute the following commands in your shell to clone the repository and initialize the Conda environment:

```bash
# Clone the repository
git clone <repo-url>
cd EvoAge-Documentation

# Create the conda environment
conda env create -f environment.yml

# Activate the environment
conda activate evoage_env
```

---

## 🖥️ **3. HPC Cluster Configuration (PBS/Torque)**

The training pipelines and large-scale relation merges are submitted as batch jobs using PBS. A standard submission script template for a DGL-KE training job is shown below:

```bash
#!/bin/bash
#PBS -N EvoAge_Training
#PBS -q gpu_queue
#PBS -l nodes=1:ppn=16:gpus=2
#PBS -l walltime=48:00:00
#PBS -o training_output.log
#PBS -e training_error.log

# Load modules if required by your cluster
# module load cuda/11.7

# Activate the Conda environment
source $(conda info --base)/etc/profile.d/conda.sh
conda activate evoage_env

# Run the training command
python -m dglke.train \
    --model_name RESCAL \
    --dataset EvoAge_121_12M \
    --data_path /storage/Arushi/090526_EvoAge/Store_House/ \
    --format udt_tsv \
    --batch_size 2048 \
    --neg_sample_size 256 \
    --hidden_dim 400 \
    --gamma 12.0 \
    --lr 0.1 \
    --gpu 0 1 \
    --max_step 5000000 \
    --save_path /storage/Arushi/090526_EvoAge/training_runs/
```

---

## ⚙️ **4. Directory Configurations**

Before executing pipeline steps, configure the local path mappings in the configuration scripts. Set the absolute path of the workspace:

```python
# config.py or inside individual scripts
BASE_DIR = '/storage/Arushi/090526_EvoAge/kg_formation/'
PROC_DIR = BASE_DIR + 'processed_data/'
DB_DIR   = BASE_DIR + 'data_collection/databases_for_mapping/'
```

---

## ✔️ **5. Installation Verification Script**

To verify that PyTorch, DGL-KE, and CUDA are properly integrated and that the GPU is accessible within the active environment, create and run the following verification script:

```python
# verify_env.py
import sys
import torch
import dgl
import numpy as np

print("=== EvoAge Environment Verification ===")
print(f"Python Version: {sys.version}")
print(f"PyTorch Version: {torch.__version__}")
print(f"DGL Version: {dgl.__version__}")
print(f"CUDA Available: {torch.cuda.is_available()}")

if torch.cuda.is_available():
    print(f"GPU Device Count: {torch.cuda.device_count()}")
    print(f"Current Device Name: {torch.cuda.get_device_name(0)}")
    
    # Run test tensor calculation on GPU
    x = torch.rand(5, 5).cuda()
    y = torch.rand(5, 5).cuda()
    z = torch.matmul(x, y)
    print("GPU Tensor multiplication test: SUCCESS")
else:
    print("WARNING: CUDA is not available. GPU-based training will not work!")
print("=======================================")
```

Run the validation script using:
```bash
python verify_env.py
```
