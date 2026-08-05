#!/usr/bin/env bash
# initialize and activate
eval "$(conda shell.bash hook)"
conda activate dglke_env

export DGLBACKEND=pytorch
export PYTHONUNBUFFERED=1

echo "[$(date)] Activated env and set DGLBACKEND. Launching training…"

# prefix the training CLI with stdbuf to turn off buffering in any subprocess
exec stdbuf -o0 -e0 dglke_train \
  --model_name       RESCAL \
  --dataset          Aging_121_12M \
  --data_path        /storage/Arushi/090526_EvoAge/kg_formation/final_kg_building_2/building_aging_kg_new/Store_House \
  --data_files       entities_final.dict relation_final.dict Aging_specific_121_12M_KG_train_90.txt Aging_specific_121_12M_KG_valid_10.txt Aging_specific_1to1_KG_test_10.txt \
  --format           udd_hrt \
  --batch_size       2048 \
  --neg_sample_size  32 \
  --batch_size_eval  512 \
  --neg_sample_size_eval 16 \
  --hidden_dim       64 \
  --gamma            12.0 \
  --lr               0.01 \
  --max_step         5868 \
  --log_interval     10 \
  --eval_interval    3000 \
  --save_path        /storage/Arushi/090526_EvoAge/kg_formation/training_2/Aging_121_12M/model_output/Rescal \
  --gpu              1 \
  -adv \
  -a 1.0 \
  --valid \
  --test