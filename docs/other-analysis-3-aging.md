# Aging-Specific Test Set

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
