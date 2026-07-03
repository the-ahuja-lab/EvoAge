#!/usr/bin/env bash

export DGLBACKEND=pytorch
export PYTHONUNBUFFERED=1

NUM_PROC=22
LOGDIR="./eval_logs"
mkdir -p "$LOGDIR"

echo "[$(date)] Running TESTING only on CPU with $NUM_PROC threads..."

run_eval () {
  local tag=$1; shift
  echo "[$(date)] Starting $tag"
  stdbuf -o0 -e0 dglke_eval "$@" 2>&1 | tee "${LOGDIR}/${tag}.log"
  echo "[$(date)] Finished $tag"
}

# EvoAge 1-to-1
run_eval "EvoAge_1to1" \
  --model_name RESCAL \
  --dataset Evoage_1_to_1 \
  --data_path        /storage/Arushi/090526_EvoAge/kg_formation/final_kg_building_3/building_evoage_kg_new/Store_House \
  --data_files       entities_final.dict relation_final.dict EvoAge_1to1_KG_train_90.txt EvoAge_1to1_KG_valid_10.txt Aging_specific_1to1_KG_test_10.txt \
  --format udd_hrt \
  --model_path /storage/Arushi/090526_EvoAge/kg_formation/training_3/EvoAge_1_to_1/model_output/Rescal/RESCAL_Evoage_1_to_1_0 \
  --hidden_dim 64 --gamma 12.0 --batch_size_eval 512 --neg_sample_size_eval 16 \
  --num_proc $NUM_PROC --num_thread 1

# Aging 1-to-1
run_eval "Aging_1to1" \
  --model_name RESCAL \
  --dataset Aging_1_to_1 \
  --data_path        /storage/Arushi/090526_EvoAge/kg_formation/final_kg_building_3/building_aging_kg_new/Store_House \
  --data_files       entities_final.dict relation_final.dict Aging_specific_1to1_KG_train_80.txt Aging_specific_1to1_KG_valid_10.txt Aging_specific_1to1_KG_test_10.txt \
  --format udd_hrt \
  --model_path /storage/Arushi/090526_EvoAge/kg_formation/training_3/Aging_1_to_1/model_output/Rescal/RESCAL_Aging_1_to_1_0 \
  --hidden_dim 64 --gamma 12.0 --batch_size_eval 512 --neg_sample_size_eval 16 \
  --num_proc $NUM_PROC --num_thread 1

# EvoAge 121_12M
run_eval "EvoAge_121_12M" \
  --model_name RESCAL \
  --dataset Evoage_121_12M \
  --data_path        /storage/Arushi/090526_EvoAge/kg_formation/final_kg_building_3/building_evoage_kg_new/Store_House \
  --data_files       entities_final.dict relation_final.dict EvoAge_121_12M_KG_train_90.txt EvoAge_121_12M_KG_valid_10.txt Aging_specific_1to1_KG_test_10.txt \
  --format udd_hrt \
  --model_path /storage/Arushi/090526_EvoAge/kg_formation/training_3/EvoAge_121_12M/model_output/Rescal/RESCAL_Evoage_121_12M_1 \
  --hidden_dim 64 --gamma 12.0 --batch_size_eval 512 --neg_sample_size_eval 16 \
  --num_proc $NUM_PROC --num_thread 1

# Aging 121_12M
run_eval "Aging_121_12M" \
  --model_name RESCAL \
  --dataset Aging_121_12M \
  --data_path        /storage/Arushi/090526_EvoAge/kg_formation/final_kg_building_3/building_aging_kg_new/Store_House \
  --data_files       entities_final.dict relation_final.dict Aging_specific_121_12M_KG_train_90.txt Aging_specific_121_12M_KG_valid_10.txt Aging_specific_1to1_KG_test_10.txt \
  --format udd_hrt \
  --model_path /storage/Arushi/090526_EvoAge/kg_formation/training_3/Aging_121_12M/model_output/Rescal/RESCAL_Aging_121_12M_0 \
  --hidden_dim 64 --gamma 12.0 --batch_size_eval 512 --neg_sample_size_eval 16 \
  --num_proc $NUM_PROC --num_thread 1

echo "[$(date)] All evaluations complete. Logs in $LOGDIR/"