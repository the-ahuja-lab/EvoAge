EvoAge Triple Processing & DGL-KE Training Pipeline
This repository contains a complete pipeline for preparing, training, testing, and predicting on Knowledge Graph (KG) triples using DGL-KE with the RotatE embedding model. It takes raw triple CSV files as input, assigns unique IDs to entities and relations, splits them into train/validation/test sets, trains a RotatE model, and provides tools for prediction, scoring, and result visualization.

🚀 Pipeline Overview
Step 1 — Preprocessing & Indexing
File: 1.1EvoKG_Complete_files.ipynb

Reads raw triple CSV files.
Assigns unique IDs to all entities and relations.
Generates one-hot encoded triples for DGL-KE compatibility.
Saves processed mappings (entities_final.dict, relation_final.dict) and triple sets.
Step 2 — Dataset Preparation & Training
2.1 — Dataset Splitting
File: 2.1_Splitting_80_10_10.ipynb

Splits triples into:
80% Train
10% Validation
10% Test
Outputs go to Training_files/
2.2 — Train RotatE Model
File: 2.2_train_model_rotatE.sh

nohup bash 2.2_train_model_rotatE.sh > rotate_128_emb.log &
2.3 — Test Trained Model
File: 2.3_test_trained_model.sh

nohup bash 2.3_test_trained_model.sh > rotate_128_emb_testing.log &  #Runs CPU-based evaluation.
Step 3 — Prediction & Scoring
3.1 — Get Top-K Predictions
File: 3.1_predict_topK.py

Input: head.list, relation.list
Output: Top-10 tails with scores
nohup python 3.1_predict_topK.py > top10.log &
3.2 — Batch Triple Scoring
File: 3.2_Get_batch_triple_score.py

Input: head.list, relation.list, tail.list
Output: Triple_score.tsv
python3 3.2_Get_batch_triple_score.py
3.3 — Edge Type Prediction
Purpose: Predicts the most probable relation type (edge type) for a given head–tail pair.

Use case: Link prediction and relation inference tasks.
Input: List of head entities and tail entities.
Output: Predicted relation type(s) with associated scores.
