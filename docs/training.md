# 8. Model Training and Evaluation

> 📂 **Source Code & Notebooks:** [pipeline/07_model_training](../pipeline/07_model_training/)


## 8.1. Purpose

This is **Step 7** of the EvoAge Knowledge Graph (KG) construction pipeline (now documented as Section 8). The goal is to train Knowledge Graph Embedding (KGE) models to learn vector representations for entities (nodes) and relations across each of the KG configurations. 

This step focuses on:
1. **Selecting the Best KGE Algorithm**: Benchmarking 6 models (TransE, RotatE, ComplEx, SimplE, DistMult, and RESCAL) on the unified `EvoAge_1:1∪1:M` KG.
2. **Quantifying the Benefits of Orthology and EvoAge Combination**: Training the selected model (RESCAL) on all 6 KGs to measure the impact of 1:1∪1:M ortholog mappings and the union of Aging and Biomedical KGs.


---

## 8.2. Environment and Framework

- **Framework**: DGL-KE (Deep Graph Library - Knowledge Embedding), optimized for large-scale KG training.
- **Conda Environment**: `dglke_env`
- **Backend**: PyTorch (`export DGLBACKEND=pytorch`)
- **Output Control**: Stdout buffering is turned off using `export PYTHONUNBUFFERED=1` and `stdbuf -o0 -e0` inside the bash scripts, ensuring log messages are written to disk immediately without delays.

---

## 8.3. Benchmarked Models

All models were evaluated on the unified `EvoAge_121_12M` dataset using **64-dimensional embeddings** (except RotatE, which utilizes a complex space and thus requires 128-dimensional embeddings for entities via `--double_ent`).

1. **RESCAL**: A tensor factorization model that represents relations as full $d \times d$ matrices, allowing it to capture rich bilinear entity-relation-entity interactions.
2. **RotatE**: Defines relations as rotations in a complex entity space, ensuring excellent tracking of composition, inversion, and symmetry.
3. **SimplE**: A bilinear model that assigns dual embedding vectors to each entity, capturing independent roles as head and tail nodes.
4. **DistMult**: A bilinear diagonal model representing relations as diagonal matrices. It is structurally symmetric, which limits its ability to model directional relations.
5. **ComplEx**: Extends DistMult to a complex space, introducing asymmetric bilinear scoring capable of modeling directed graphs.
6. **TransE**: A translational distance model where relation vectors represent additive translations between head and tail entity vectors in a real space.

---

## 8.4. Hyperparameter Settings

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
With `No of epoch = 10` for all training runs.


For the KGs, this resulted in the following steps:
- **EvoAge 1:1∪1:M** (`1,007,666,176` triples): `4,920,245` steps
- **EvoAge 1:1** (`1,000,744,942` triples): `4,886,449` steps
- **Biomedical 1:1∪1:M** (`964,167,065` triples): `4,707,847` steps
- **Biomedical 1:1** (`945,427,302` triples): `4,616,344` steps
- **Aging 1:1 & 1:1∪1:M** (approx. `1,200,000` triples): `5,868` steps (evaluated with a logs/evaluation scale-down: `--log_interval 10`, `--eval_interval 3000`)

---

## 8.5. Evaluation Tasks

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

## 8.6. Training & Evaluation Scripts Directory

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

## 8.7. Results and Performance

### 8.7.1. KGE Model Comparison on EvoAge 1:1∪1:M (Link Prediction)

Evaluated on `EvoAge_1to1_KG_test.txt` using the standard link prediction evaluation (`dglke_eval` on CPU):

| Model | Hits@1 | Hits@3 | Hits@10 | Mean Rank (MR) | MRR |
|---|---:|---:|---:|---:|---:|
| **RESCAL** | **0.8110** | **0.9242** | **0.9972** | **1.52** | **0.8754** |
| **RotatE** | 0.8089 | 0.9215 | 0.9870 | 1.63 | 0.8725 |
| **SimplE** | 0.7744 | 0.8944 | 0.9917 | 1.73 | 0.8462 |
| **DisMult** | 0.7651 | 0.8821 | 0.9786 | 1.94 | 0.8360 |
| **ComplEx** | 0.7404 | 0.8848 | 0.9902 | 1.82 | 0.8249 |
| **TransE** | 0.0049 | 0.0275 | 0.2129 | 13.86 | 0.0926 |

> [!NOTE]
> RESCAL outperforms the other models, yielding the highest Hit@1 (0.8110) and MRR (0.8754). TransE struggles with the scale and semantic density of the dataset, achieving very low scores.

---

### 8.7.2. Dataset Comparison (Relation / Edge Type Prediction)

Evaluated using the custom relation prediction scripts with the selected **RESCAL (64D)** model on all 6 dataset variants:

| Dataset Variant | Entity Embeddings | Relation Embeddings | Eval Triples | Hits@1 | Hits@3 | Hits@10 | MRR |
|---|---|---|---:|---:|---:|---:|---:|
| **Aging 1:1** | $(45.5\text{M}, 64)$ | $(89, 64, 64)$ | 148,310 | 0.7524 | 0.8299 | 0.8538 | 0.7967 |
| **Aging 1:1∪1:M** | $(45.5\text{M}, 64)$ | $(89, 64, 64)$ | 148,310 | 0.7576 | 0.8326 | 0.8570 | 0.8008 |
| **Biomedical 1:1** | $(45.5\text{M}, 64)$ | $(89, 64, 64)$ | 118,178,414 | 0.4045 | 0.4830 | 0.6115 | 0.4763 |
| **Biomedical 1:1∪1:M** | $(45.5\text{M}, 64)$ | $(89, 64, 64)$ | 118,178,414 | 0.3960 | 0.5116 | 0.6537 | 0.4826 |
| **EvoAge 1:1** | $(45.5\text{M}, 64)$ | $(89, 64, 64)$ | 118,325,555 | 0.4198 | 0.5566 | 0.7293 | 0.5239 |
| **EvoAge 1:1∪1:M** | $(45.5\text{M}, 64)$ | $(89, 64, 64)$ | 118,325,555 | **0.5795** | **0.7058** | **0.8299** | **0.6634** |

#### Key Findings:
1. **Value of 1:1∪1:M Orthology**: Combining many-to-many orthologs (`1:1∪1:M`) yields a significant performance boost over strictly one-to-one (`1:1`) KGs. On EvoAge, MRR increases from **0.5239** to **0.6634**, and Hits@1 improves from **0.4198** to **0.5795**.
2. **Impact of Combining Aging and Biomedical KGs**: The unified EvoAge KG (merging Aging and Biomedical domains and adding `Species_AssociatedWith` relations) significantly outperforms the Biomedical KG alone. Under the 1:1∪1:M scheme, MRR increases from **0.4826 (Biomedical)** to **0.6634 (EvoAge)**.
3. **Small vs Large Graph Performance**: The Aging-specific KG shows high metrics due to its small size and curated structure (~148k test triples vs. ~118M for EvoAge/Biomedical). However, combining it into the larger EvoAge framework allows the model to leverage general biomedical contexts, yielding a highly expressive representation.
