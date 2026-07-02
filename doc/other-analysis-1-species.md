# Species Evaluation

> 📂 **Source Code & Notebooks:** [pipeline/08_evaluation_analysis](https://github.com/the-ahuja-lab/EvoAge/tree/main/pipeline/08_evaluation_analysis)

This document details supplementary evaluation analyses for the EvoAge knowledge graph model, consisting of three parts:
1. **Analysis 1**: Granular 1% species-specific and cross-species evaluation analysis.
2. **Analysis 2**: Shuffled KG test set baseline (null hypothesis) evaluation.
3. **Analysis 3**: Evaluation of KGs on Aging-specific test set.

---

## Analysis 1: — Granular 1% Species & Cross-Species Evaluation

### 1.1. Purpose

This section details the granular 1% species-specific and cross-species evaluation analysis. The purpose of this analysis is to evaluate KGE model performance (RESCAL, 64-dimension) at a fine-grained level across distinct species boundaries and cross-species interfaces. Rather than evaluating the model on a single uniform test set, the testing data is partitioned into **7 distinct sub-test sets** representing individual species and cross-species boundaries.

---

### 1.2. Pipeline Overview

All pipeline components for this analysis are structured under:
📂 `building_evoage_with_1_percent_species_testsplit/`

```
building_evoage_with_1_percent_species_testsplit/
│
├── Training/
│   ├── Run1_percent_species_test_set.ipynb ← Test set split generation details
│   ├── Run2_per_Rescal_64.sh ← Model training bash script (10 epochs)
│   ├── Run3_Rescal_64_testing.sh ← CPU-based link prediction eval bash script
│   └── Run4_per_rescal_edge_type_metrics.py ← GPU-based custom edge type prediction script
│
└── Store_House/                                        ← Holds final split txt files for evaluation
```

---

### 1.3. Test Set Splitting Logic

The evaluation dataset is divided into two primary categories:

#### 1.3.1. Species-Specific 1% Test Sets (Within-Species Biology)
For each individual species (Human, Yeast, C. elegans, Drosophila, Zebrafish, Mouse):
1. **Filter Non-Human Nodes**: Human genes mapped via orthology are separated from species-specific nodes (e.g., phenotypes, cell components, chemicals). An upper bound threshold representing human nodes is defined (e.g. `3,062,099` for Yeast). Triples where **both** head and tail are species-specific (IDs $\ge \text{threshold}$) are selected.
2. **1% Sampling**: Exactly 1% of the total triples of the species' subgraph are randomly sampled from these eligible triples.
3. **Training Exclusions**: The sampled triples are subtracted from the species subgraph to avoid leakage.

#### 1.3.2. Cross-Species 1% Test Set (Cross-Species Interactions)
To evaluate the model's accuracy on relationships bridging human genes and other species' entities:
1. **Size Balancing**: The total size of the cross-species test set is balanced to match the human 1% test set size.
2. **Sampling Filter**: Triples are sampled where one node (head/tail) is a human gene mapping to that species (using mapped gene lists) and the other node (tail/head) is a species-specific entity within that species' ID range.
3. **Training Exclusions**: The sampled triples are removed from the training pool.

#### 1.3.3. Compilation and Splitting
- **Training (90%)**: The combined remaining 99% training triples are saved as `EvoAge_1to1_1toM_train_90.txt`.
- **Validation (10%)**: The combined remaining validation triples are saved as `EvoAge_1to1_1toM_valid_10.txt`.
- **Individual Test Sets**: Evaluated as `Human.txt`, `Yeast.txt`, `Celegans.txt`, `Drosophila.txt`, `Zebrafish.txt`, `Mouse.txt`, and `CrossSpecies.txt`.

---

### 1.4. Model Training & Evaluation Setup

#### 1.4.1. Model Training
Trained via DGL-KE utilizing the [Run2_per_Rescal_64.sh] script:
- **Model**: RESCAL (64-dimensional embeddings)
- **Batch Size**: 2048
- **LR**: 0.01 
- **Max Steps**:(Equivalent to exactly **10 epochs**)
  $$\text{max\_step} = \frac{10 \text{ epochs} \times 1,094,669,926 \text{ training triples}}{2048 \text{ batch size}}$$

#### 1.4.2. Link Prediction Evaluation
Executed via the [Run3_Rescal_64_testing.sh]script using CPU-parallel threads (`dglke_eval`).

#### 1.4.3. Relation / Edge Type Prediction Evaluation
Executed via the [Run4_per_rescal_edge_type_metrics.py] script. It evaluates the rank of the true relation out of all 89 candidate relations in a chunked manner on the GPU.

---

### 1.5. Evaluation Results

#### 1.5.1. Task A — Relation / Edge Type Prediction `(h, ?, t)`

#### 1.5.2. Task B — Link Prediction `(?, r, t)` / `(h, r, ?)`

---

### 1.6. Key Takeaways

1. **Varying Species Complexity**:
2. **Strong Cross-Species Prediction**: The model predicts cross-species boundaries with high accuracy, demonstrating that mapping species orthologs onto human genes creates a highly coherent combined vector space.
