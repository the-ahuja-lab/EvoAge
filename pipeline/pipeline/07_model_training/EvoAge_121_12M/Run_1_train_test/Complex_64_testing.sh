
#!/usr/bin/env bash

set -xe
source ~/miniconda3/etc/profile.d/conda.sh
conda activate dglke_env

export DGLBACKEND=pytorch
export PYTHONUNBUFFERED=1

# Dynamically detect CPU cores and use n - 1
TOTAL_CORES=$(nproc)
NUM_PROC=$((TOTAL_CORES - 20))

echo "[$(date)] Running TESTING only on CPU with $NUM_PROC threads..."

exec stdbuf -o0 -e0 dglke_eval \
  --model_name ComplEx \
  --dataset Evoage_121_12M \
  --data_path        /storage/Arushi/090526_EvoAge/kg_formation/final_kg_building_2/building_evoage_kg_new/Store_House \
  --data_files       entities_final.dict relation_final.dict EvoAge_121_12M_KG_train_90.txt EvoAge_121_12M_KG_valid_10.txt EvoAge_1to1_KG_test.txt \
  --format udd_hrt \
  --model_path /storage/Arushi/090526_EvoAge/kg_formation/training_2/EvoAge_121_12M/model_output/Complex/ComplEx_Evoage_121_12M_1 \
  --hidden_dim 64 \
  --gamma 12.0 \
  --batch_size_eval 512 \
  --neg_sample_size_eval 16 \
  --num_proc $NUM_PROC \
  --num_thread 1