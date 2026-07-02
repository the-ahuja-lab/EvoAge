> 📂 **Source Code & Notebooks:** [pipeline/08_evaluation_analysis](https://github.com/the-ahuja-lab/EvoAge/tree/main/pipeline/08_evaluation_analysis)

This document details supplementary evaluation analyses for the EvoAge knowledge graph model, consisting of three parts:


1. **Analysis 1**: Granular 1% species-specific and cross-species evaluation analysis.
2. **Analysis 2**: Shuffled KG test set baseline (null hypothesis) evaluation.
3. **Analysis 3**: Evaluation of KGs on Aging-specific test set.

---

## Analysis 1: — Granular 1% Species & Cross-Species Evaluation Analysis

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

---

## Analysis 2: Shuffled KG Test Set Baseline / Null Hypothesis Evaluation

### 2.1. Purpose

The purpose of this analysis is to establish baseline performance metrics (a null-hypothesis baseline) for the knowledge graph completion model (RESCAL, 64-dimension). By shuffling the head and tail entities of the test set triples independently while keeping relations fixed, we generate "fake" negative test sets. Evaluating the model trained on the real graph against these shuffled test sets allows us to verify if the model is genuinely learning meaningful biological associations rather than capturing simple statistical artifacts or frequency biases.

---

### 2.2. Pipeline Overview

All pipeline components for this analysis are structured under:
📂 `/storage/Arushi/090526_EvoAge/kg_formation/DOCUMENTATION/Other_Analysis_08/shuffled_kg_testset/`

```
shuffled_kg_testset/
│
├── Run1_make_shuffled_KG.py             ← Generates 30 shuffled test sets with deduplication
├── Run2_Testing/                        ← Evaluation scripts & outputs
│   ├── run_rescal_eval_all_shuffles.sh  ← Bash script to run dglke_eval sequentially
│   └── rescal_eval_all_shuffles.log     ← Evaluation log output for all 30 shuffles
└── Run3_testing_log_to_csv.py           ← Parses evaluation logs and generates summary statistics
```

---

### 2.3. Shuffled Test Set Generation Logic

The shuffled test sets are created using the script [Run1_make_shuffled_KG.py](file:///storage/Arushi/090526_EvoAge/kg_formation/DOCUMENTATION/Other_Analysis_08/shuffled_kg_testset/Run1_make_shuffled_KG.py):
1. **Source Dataset**: Loads the original test set: `EvoAge_1to1_KG_test.txt` (containing $N$ triples).
2. **Independent Shuffling**: The head and tail entity columns are independently and randomly permuted (using 30 different random seeds, 0 to 29), while keeping the relation column fixed.
3. **Collision Checking & Deduplication**: To ensure validity as negative samples, the script checks if any shuffled triple exists in the original test set. If a collision is detected, the colliding indices are iteratively reshuffled until a collision-free shuffled test set is generated.
4. **Outputs**: Generates 30 text files (`shuffled_test_000_seed0.txt` through `shuffled_test_029_seed29.txt`) and a summary CSV `shuffle_summary.csv` inside `Shuffled_EvoAge_testing/Store_House/shuffled_test_sets/`.

---

### 2.4. Evaluation Setup

The evaluation of the trained RESCAL model against the shuffled test sets is performed via [run_rescal_eval_all_shuffles.sh]:
- **Model**: RESCAL (64-dimensional embeddings, trained on `Evoage_121_12M` dataset).
- **Execution**: Runs CPU-based link prediction evaluation (`dglke_eval`) sequentially across all 30 shuffled test sets with 17 threads.
- **Negative Sampling**: Employs a negative sample size of 16 during evaluation.
- **Log Parsing**: The python script [Run3_testing_log_to_csv.py]extracts the test metrics (MRR, MR, HITS@1, HITS@3, HITS@10) from the log file and saves them to `rescal_shuffled_metrics.csv`.



### 2.5. Key Takeaway

**Significantly Lower Performance Compared to Real Graph**rd deviations across the 30 random shuffles are extremely low, showing that the random permutation generates highly consistent, stable baseline metrics.

---

## Analysis 3: Evaluation of KGs on Aging-Specific Test Set

### 3.1. Purpose

The purpose of this analysis is to evaluate how integrating aging-specific data with general biomedical knowledge and orthology mappings in **EvoAge** helps predict aging test sets. By comparing EvoAge against Aging-only graphs on the same aging test split (`Aging_specific_1to1_KG_test_10.txt`), we quantify how the broader semantic context and cross-species links in EvoAge help enrich and improve the representation of aging-specific biology.

---

### 3.2. Pipeline Overview

All pipeline components for this analysis are structured under:
📂 `Agingonly_testing_data/`

```
Agingonly_testing_data/
│
├── Aging_testing_data_on_allKGs.sh           ← Sequentially runs dglke_eval link prediction
├── Aging_testing_data_on_allKGs.log          ← Combined output logs of evaluation runs
└── Aging_testing_data_on_allKG_compling.py   ← Script that parses logs to compile rescal_testing_summary.csv
```

---

### 3.3. Evaluation Setup

- **Models Evaluated**: RESCAL models trained on:
  1. **EvoAge 1-to-1** (trained on `EvoAge_1to1_KG_train_90.txt` + `valid_10.txt`)
  2. **Aging 1-to-1** (trained on `Aging_specific_1to1_KG_train_80.txt` + `valid_10.txt`)
  3. **EvoAge 1:1∪1:M** (trained on `EvoAge_121_12M_KG_train_90.txt` + `valid_10.txt`)
  4. **Aging 1:1∪1:M** (trained on `Aging_specific_121_12M_KG_train_90.txt` + `valid_10.txt`)
- **Shared Test Set**: `Aging_specific_1to1_KG_test_10.txt` (148,311 triples).
- **Parameters**: Hidden dimension of 64, gamma margin of 12.0, evaluated via CPU link prediction with 22 threads, using 16 negative samples.
- **Log compiler script**: [Aging_testing_data_on_allKG_compling.py] extracts the test metrics from the log files and outputs a compiled CSV summary.


---

