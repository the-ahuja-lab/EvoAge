EvoKG Triple Processing & DGL-KE Training Pipeline
This repository contains a complete pipeline for preparing, training, testing, and predicting on Knowledge Graph (KG) triples using DGL-KE with the RotatE embedding model.
It takes raw triple CSV files as input, assigns unique IDs to entities and relations, splits them into train/validation/test sets, trains a RotatE model, and provides tools for prediction, scoring, and result visualization.


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

Splits triples into 80% Train / 10% Validation / 10% Test.

Outputs go to Training_files/.

2.2 — Train RotatE Model
File: 2.2_train_model_rotatE.sh

bash
Copy
Edit
bash 2.2_train_model_rotatE.sh


2.3 — Test Trained Model
File: 2.3_test_trained_model.sh

bash
Copy
Edit
bash 2.3_test_trained_model.sh
Runs CPU-based evaluation.

Step 3 — Prediction & Scoring
3.1 — Get Top-K Predictions
File: 3.1_predict_topK.py

Input: head.list, relation.list

Output: Top-10 tails with scores.

bash
Copy
Edit
python3 3.1_predict_topK.py
3.2 — Batch Triple Scoring
File: 3.2_Get_batch_triple_score.py

Input: head.list, relation.list, tail.list

Output: Triple_score.tsv

bash

python3 3.2_Get_batch_triple_score.py
3.3 — Edge Type Prediction
Predicts the most probable relation type for given head–tail pairs.

Useful for link prediction tasks.

Step 4 — Plotting & Result Analysis
This section contains Jupyter notebooks for visualizing training metrics, model comparison, and prediction results.

4.1_6Models_Best_Selection.ipynb — Compare performance metrics across 6 trained models to select the best.

4.2_RotatE_inc_Emb_Validation_Tesing_Metric.ipynb — Plot validation and testing metrics over training.

4.3_RotatE-Inc_Emb_Loss.ipynb — Visualize training loss trends.

4.4_Edge-type_prediction_metric.ipynb — Analyze accuracy metrics for edge-type predictions.

⚙️ Requirements
bash

# 1) Create a new conda environment with Python 3.11
conda create -n my_env python=3.11 -y

# 2) Activate the environment
conda activate my_env

# 3) Install libraries from your .yml file
conda env update --file environment.yml --prune

# 4) Install the current project in editable mode
cd dglke
pip install -e .
