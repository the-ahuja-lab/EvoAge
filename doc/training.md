# 07 — Model Training and Evaluation
> 📂 **Source Code & Notebooks:** [pipeline/07_model_training](https://github.com/the-ahuja-lab/EvoAge/tree/main/pipeline/07_model_training)


## 1. Purpose

This is **Step 7** of the EvoAge Knowledge Graph (KG) construction pipeline. The goal is to train Knowledge Graph Embedding (KGE) models to learn vector representations for entities (nodes) and relations across each of the KG configurations. 

This step focuses on:
1. **Selecting the Best KGE Algorithm**: Benchmarking 6 models (TransE, RotatE, ComplEx, SimplE, DistMult, and RESCAL) on the unified `EvoAge_1:1∪1:M` KG.
2. **Quantifying the Benefits of Orthology and EvoAge Combination**: Training the selected model (RESCAL) on all 6 KGs to measure the impact of 1:1∪1:M ortholog mappings and the union of Aging and Biomedical KGs.


---

## 2. Environment and Framework

- **Framework**: DGL-KE (Deep Graph Library - Knowledge Embedding), optimized for large-scale KG training.

---

## 3. Benchmarked Models

All models were evaluated on the unified `EvoAge_121_12M` dataset using **64-dimensional embeddings**.

1. **RESCAL**: A tensor factorization model that represents relations as full $d \times d$ matrices, allowing it to capture rich bilinear entity-relation-entity interactions.
2. **RotatE**: Defines relations as rotations in a complex entity space, ensuring excellent tracking of composition, inversion, and symmetry.
3. **SimplE**: A bilinear model that assigns dual embedding vectors to each entity, capturing independent roles as head and tail nodes.
4. **DistMult**: A bilinear diagonal model representing relations as diagonal matrices. It is structurally symmetric, which limits its ability to model directional relations.
5. **ComplEx**: Extends DistMult to a complex space, introducing asymmetric bilinear scoring capable of modeling directed graphs.
6. **TransE**: A translational distance model where relation vectors represent additive translations between head and tail entity vectors in a real space.

---

## 4. Hyperparameter Settings

Below is the standard configuration used for training the larger KGs (EvoAge and Biomedical):

| Parameter | Value | Description |
|---|---|---|
| `--batch_size` | `2048` | Training batch size |
| `--neg_sample_size` | `32` | Number of negative samples drawn per positive triple |
| `--batch_size_eval` | `512` | Evaluation batch size |
| `--neg_sample_size_eval` | `16` | Number of negative samples used in evaluation |
| `--hidden_dim` | `64` | Embedding dimension |
| `--gamma` | `12.0` | Margin parameter for distance/rotation scoring functions |
| `--lr` | `0.01` | Learning rate (with Adagrad optimizer via `-adv`) |
| `--eval_interval` | `2,500,000` | Steps between evaluation runs |
| `--max_step` | *Dynamic* | Total training steps, equivalent to exactly **10 epochs** |

### Max Steps Calculation
The total training steps (`--max_step`) are calculated using the formula:
```
max_step = (No of epoch * trainingtriple count) / batch_size
```

---

## 5. Evaluation Tasks

Two distinct evaluation methodologies were implemented to benchmark model performance:

### Task A: Link Prediction (`dglke_eval`)
- **Query Type**: Head prediction `(?, r, t)` and Tail prediction `(h, r, ?)`.
- **Methodology**: For each validation or test triple, 16 negative entities are sampled. The model ranks the ground-truth entity against the negatives.
- **Metrics**: Hits@1, Hits@3, Hits@10, Mean Rank (MR), and Mean Reciprocal Rank (MRR).

### Task B: Relation Prediction / Edge Type Prediction (Custom PyTorch Scripts)
- **Query Type**: Relation type prediction `(h, ?, t)`.
- **Methodology**: For every test triple, scores are computed for **all 89 relation types** in the ontology. The correct relation is ranked against the other 88 classes.
- **Metrics**: Hits@1, Hits@3, Hits@10, and MRR.
- **Design Strategy**: Custom scripts (e.g., `64_rescal_edge_type_metrics.py`) perform chunked relation evaluation on GPU to prevent memory overflow.

---

## 6. Training & Evaluation Scripts Directory

The script files are organized as follows:

```
DOCUMENTATION/Training_07/
│
├── Aging_1_to_1/
│   └── Rescal_64.sh                                     ← RESCAL 10-epoch training script
│
├── Aging_121_12M/
│   └── Rescal_64.sh                                     ← RESCAL 10-epoch training script
│
├── Biomedical_1_to_1/
│   ├── Rescal_64.sh                                     ← Training script
│   ├── Rescal_64_Biomed_1_to_1_testing.sh               ← CPU-based link prediction eval
│   └── edge_type/
│       └── B_121_64_rescal_edge_type_metrics.py         ← Relation prediction script
│
├── Biomedical_121_12M/
│   ├── Rescal_64.sh                                     ← Training script
│   ├── Rescal_64_Biomed_121_12M_testing.sh              ← CPU-based link prediction eval
│   └── edge_type/
│       └── B_121_64_rescal_edge_type_metrics.py         ← Relation prediction script
│
├── EvoAge_1_to_1/
│   ├── Rescal_64.sh                                     ← Training script
│   └── Rescal_64_Evoage_1_to_1_testing.sh               ← CPU-based link prediction eval
│
└── EvoAge_121_12M/
    ├── Run_1_train_test/                                ← Main scripts for all 6 models
    │   ├── RotatE_64.sh / RotatE_64_testing.sh
    │   ├── transe_64.sh / Transe_64_testing.sh
    │   ├── complex_64.sh / Complex_64_testing.sh
    │   ├── Dismult.sh / Dismult_64_testing.sh
    │   ├── Simple_64.sh / Simple_64_testing.sh
    │   ├── Rescal_64.sh / Rescal_64_testing.sh
    │   └── readme.txt                                   ← execution notes
    │
    └── Run2_64_edge_type_testing/                       ← Custom edge type prediction python scripts
        ├── 64_transE_edgetype_metrics.py
        ├── 64_rotate_edge_type_metrics.py
        ├── 64_complex_edge_type_metric.py
        ├── 64_dismult_edge_type_metrics.py
        ├── 64_simple_edge_type_metrics.py
        └── 64_rescal_edge_type_metrics.py
```

---
