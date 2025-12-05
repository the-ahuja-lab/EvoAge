# EvoAge Triple Processing & DGL-KE Training Pipeline

This repository provides a complete, end-to-end pipeline for preparing, training, testing, and performing predictions on Knowledge Graph (KG) triples using **DGL-KE** with the **RotatE embedding model**.  
The pipeline ingests raw triple CSV files, assigns unique IDs to entities and relations, performs dataset splitting, trains the model, and supports prediction, scoring, and result visualization.

---

## ✅ Step 1 — Preprocessing & Indexing  
> File: 1_EvoKG_Complete_files.ipynb

This step converts raw triple data into a DGL-KE-compatible indexed format.

Key Operations:
- Reads raw triple CSV files.
- Assigns unique integer IDs to all entities and relations.
- Generates one-hot encoded triples for DGL-KE compatibility.
- Saves the processed outputs:
  - entities_final.dict
  - relation_final.dict
  - Indexed triple files for training and evaluation.

---

## ✅ Step 2 — Dataset Preparation & Model Training

### 2.1 Dataset Splitting (80:10:10)  
> File: 1_Splitting_80_10_10.ipynb

Splits the indexed triples into:
- 80% Training set
- 10% Validation set
- 10% Test set

Output Directory:
Training_files/

---

### 2.2 Train RotatE Model  
> File: 2_train_model_rotatE.sh

This script trains the RotatE embedding model using DGL-KE.

Execution Command:
```bash
nohup bash 2.2_train_model_rotatE.sh > rotate_128_emb.log &
```
Output:
```bash
- Trained RotatE model embeddings
- Training logs (rotate_128_emb.log)
```
---

### 2.3 Test Trained Model  
> File: 3_test_trained_model.sh

Evaluates the trained model on the test dataset using CPU-based evaluation.

Execution Command:
```bash
nohup bash 3_test_trained_model.sh > rotate_128_emb_testing.log &
```
---

## ✅ Step 3 — Prediction & Scoring

### 3.1 Top-K Tail Prediction  
> File: 1_predict_topK.py

Predicts the Top-K most probable tail entities for a given (head, relation) pair.

Inputs:
```bash
- head.list
- relation.list
```
Outputs:
```bash
- Top-10 predicted tail entities with confidence scores
```
Execution Command:
```bash
nohup python 3.1_predict_topK.py > top10.log &
```
---

### 3.2 Batch Triple Scoring  
> File: 3.2_Get_batch_triple_score.py

Computes confidence scores for a large batch of triples.

Inputs:
```bash
- head.list
- relation.list
- tail.list
```

Output:
```bash
- Triple_score.tsv containing scored triples
```
Execution Command:
```bash
python3 3.2_Get_batch_triple_score.py
```
---

### 3.3 Edge Type (Relation) Prediction

Purpose:
Predicts the most probable relation type (edge type) for a given head–tail entity pair.

Use Case:
- Link prediction
- Relation inference
- Knowledge graph completion

Inputs:
- List of head entities
- List of tail entities

Outputs:
- Predicted relation type(s)
- Associated confidence scores

---

## 📦 Summary of Capabilities

- Raw triple preprocessing and indexing  
- Automated dataset splitting  
- RotatE model training with DGL-KE  
- CPU-based model evaluation  
- Top-K tail entity prediction  
- Batch triple scoring  
- Relation (edge type) prediction  

This pipeline supports scalable and reproducible experiments for large-scale knowledge graph embedding and inference tasks.
