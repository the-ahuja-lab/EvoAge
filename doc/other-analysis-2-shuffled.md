# Shuffled KG Baseline

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
