#!/usr/bin/env bash
# run_rescal.sh

set -xe                          # echo each command and exit on error
source ~/miniconda3/etc/profile.d/conda.sh
conda activate dglke_env

export DGLBACKEND=pytorch
export PYTHONUNBUFFERED=1        # force Python stdio unbuffered

echo "[$(date)] Activated env and set DGLBACKEND. Launching RESCAL training…"

# prefix the training CLI with stdbuf to turn off buffering in any subprocess
exec stdbuf -o0 -e0 dglke_train \
  --model_name       RESCAL \
  --dataset          Biomedical_1_to_1 \
  --data_path        /storage/Arushi/090526_EvoAge/kg_formation/final_kg_building_2/building_biomedical_kg_new/Store_House \
  --data_files       entities_final.dict relation_final.dict Biomedical_1to1_KG_train_80.txt Biomedical_1to1_KG_valid_10.txt Biomedical_1to1_KG_test_10.txt \
  --format           udd_hrt \
  --batch_size       2048 \
  --neg_sample_size  32 \
  --batch_size_eval  512 \
  --neg_sample_size_eval 16 \
  --hidden_dim       64 \
  --gamma            12.0 \
  --lr               0.01 \
  --max_step         4616344 \
  --log_interval     10000 \
  --eval_interval    2500000 \
  --save_path        /storage/Arushi/090526_EvoAge/kg_formation/training_2/Biomedical_1_to_1/model_output/Rescal \
  --gpu              1 \
  -adv \
  -a 1.0 \
  --valid
