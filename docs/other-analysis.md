# 9. Granular 1% Species & Cross-Species Evaluation Analysis

> 📂 **Source Code & Notebooks:** [pipeline/08_evaluation_analysis](../pipeline/08_evaluation_analysis/)


## 9.1. Purpose

This document details the granular 1% species-specific and cross-species evaluation analysis. The purpose of this analysis is to evaluate KGE model performance (RESCAL, 64-dimension) at a fine-grained level across distinct species boundaries and cross-species interfaces. Rather than evaluating the model on a single uniform test set, the testing data is partitioned into **7 distinct sub-test sets** representing individual species and cross-species boundaries.

---

## 9.2. Pipeline Overview

All pipeline components for this analysis are structured under:
📂 `/storage/Arushi/090526_EvoAge/kg_formation/DOCUMENTATION/Other_Analysis_08/building_evoage_with_1_percent_species_testsplit/`

```
building_evoage_with_1_percent_species_testsplit/
│
├── Training/
│   ├── Run1_percent_species_test_set.ipynb             ← Test set split generation details
│   ├── Run2_per_Rescal_64.sh                           ← Model training bash script (10 epochs)
│   ├── Run3_Rescal_64_testing.sh                       ← CPU-based link prediction eval bash script
│   └── Run4_per_rescal_edge_type_metrics.py            ← GPU-based custom edge type prediction script
│
└── Store_House/                                        ← Holds final split txt files for evaluation
```

---

## 9.3. Test Set Splitting Logic

The evaluation dataset is divided into two primary categories:

### 9.3.1. Species-Specific 1% Test Sets (Within-Species Biology)
For each individual species (Human, Yeast, C. elegans, Drosophila, Zebrafish, Mouse):
1. **Filter Non-Human Nodes**: Human genes mapped via orthology are separated from species-specific nodes (e.g., phenotypes, cell components, chemicals). An upper bound threshold representing human nodes is defined (e.g. `3,062,099` for Yeast). Triples where **both** head and tail are species-specific (IDs $\ge \text{threshold}$) are selected.
2. **1% Sampling**: Exactly 1% of the total triples of the species' subgraph are randomly sampled from these eligible triples.
3. **Training Exclusions**: The sampled triples are subtracted from the species subgraph to avoid leakage.

### 9.3.2. Cross-Species 1% Test Set (Cross-Species Interactions)
To evaluate the model's accuracy on relationships bridging human genes and other species' entities:
1. **Size Balancing**: The total size of the cross-species test set is balanced to match the human 1% test set size (`1,243,079` triples).
2. **Equal Species Contribution**: Each of the 5 non-human species contributes exactly:
   $$\text{target\_count} = \frac{1,243,079}{5} \approx 248,616 \text{ triples}$$
3. **Sampling Filter**: Triples are sampled where one node (head/tail) is a human gene mapping to that species (using mapped gene lists) and the other node (tail/head) is a species-specific entity within that species' ID range.
4. **Training Exclusions**: The sampled triples are removed from the training pool.

### 9.3.3. Compilation and Splitting
- **Training (90%)**: The combined remaining 99% training triples are saved as `EvoAge_1to1_1toM_train_90.txt`.
- **Validation (10%)**: The combined remaining validation triples are saved as `EvoAge_1to1_1toM_valid_10.txt`.
- **Individual Test Sets**: Evaluated as `Human.txt`, `Yeast.txt`, `Celegans.txt`, `Drosophila.txt`, `Zebrafish.txt`, `Mouse.txt`, and `CrossSpecies.txt`.

---

## 9.4. Model Training & Evaluation Setup

### 9.4.1. Model Training
Trained via DGL-KE utilizing the `Run2_per_Rescal_64.sh` script:
- **Model**: RESCAL (64-dimensional embeddings)
- **Batch Size**: 2048
- **Negative Sample Size**: 32
- **LR**: 0.01 (Adagrad optimizer)
- **Max Steps**: `5,345,068` (Equivalent to exactly **10 epochs**)
  $$\text{max\_step} = \frac{10 \text{ epochs} \times 1,094,669,926 \text{ training triples}}{2048 \text{ batch size}}$$

### 9.4.2. Link Prediction Evaluation
Executed via the `Run3_Rescal_64_testing.sh` script using CPU-parallel threads (`dglke_eval`).

### 9.4.3. Relation / Edge Type Prediction Evaluation
Executed via the `Run4_per_rescal_edge_type_metrics.py` script. It evaluates the rank of the true relation out of all 89 candidate relations in a chunked manner on the GPU.

---

## 9.5. Evaluation Results

### 9.5.1. Task A — Relation / Edge Type Prediction `(h, ?, t)`
Ranks the true relation type against the 88 incorrect candidate relations in the ontology:

| Test Set | Total Triples | MRR | Hits@1 | Hits@3 | Hits@10 |
|---|---:|---:|---:|---:|---:|
| **Yeast** | 64,097 | **0.9817** | **0.9755** | **0.9856** | **0.9938** |
| **Celegans** | 153,886 | 0.9585 | 0.9409 | 0.9718 | 0.9869 |
| **Zebrafish** | 240,473 | 0.8692 | 0.8277 | 0.8949 | 0.9488 |
| **Drosophila** | 108,731 | 0.8468 | 0.7984 | 0.8776 | 0.9404 |
| **CrossSpecies** | 9,708,096 | 0.7766 | 0.7017 | 0.8269 | 0.8969 |
| **Human** | 11,193,293 | 0.6617 | 0.5874 | 0.6907 | 0.8108 |
| **Mouse** | 183,470 | 0.4499 | 0.3569 | 0.4785 | 0.6336 |

### 9.5.2. Task B — Link Prediction `(?, r, t)` / `(h, r, ?)`
Ranks the true entity against 16 negative entities sampled at test time:

| Test Set | Total Triples | MRR | Hits@1 | Hits@3 | Hits@10 |
|---|---:|---:|---:|---:|---:|
| **Celegans** | 153,886 | **0.9976** | **0.9965** | **0.9985** | **0.9992** |
| **Yeast** | 64,097 | 0.9958 | 0.9920 | 0.9995 | 0.9997 |
| **CrossSpecies** | 9,708,096 | 0.9904 | 0.9864 | 0.9934 | 0.9952 |
| **Zebrafish** | 240,473 | 0.9870 | 0.9805 | 0.9918 | 0.9966 |
| **Drosophila** | 108,731 | 0.9796 | 0.9689 | 0.9883 | 0.9958 |
| **Mouse** | 183,470 | 0.8921 | 0.8656 | 0.9013 | 0.9373 |
| **Human** | 11,193,293 | 0.8701 | 0.8026 | 0.9217 | 0.9975 |

---

## 9.6. Key Takeaways

1. **Varying Species Complexity**: Performance varies significantly across species. Small, highly curated species subgraphs (Yeast, C. elegans) achieve near-perfect metrics (MRR $> 0.95$). More complex genomes like Human and Mouse show lower scores, reflecting the larger search space and biological noise.
2. **Strong Cross-Species Prediction**: The model predicts cross-species boundaries with high accuracy (Link Prediction MRR = **0.9904**, Edge Type MRR = **0.7766**), demonstrating that mapping species orthologs onto human genes creates a highly coherent combined vector space.
3. **Consistency Across Tasks**: Species ranking orders are highly consistent between standard link prediction and custom edge type classification, verifying model stability.
