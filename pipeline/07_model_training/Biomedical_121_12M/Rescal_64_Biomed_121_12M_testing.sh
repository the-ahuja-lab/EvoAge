
#!/usr/bin/env bash

export DGLBACKEND=pytorch
export PYTHONUNBUFFERED=1

# Dynamically detect CPU cores and use n - 1
TOTAL_CORES=$(nproc)
NUM_PROC=22

echo "[$(date)] Running TESTING only on CPU with $NUM_PROC threads..."

exec stdbuf -o0 -e0 dglke_eval \
  --model_name RESCAL \
  --dataset Biomedical_121_12M \
  --data_path        /storage/Arushi/090526_EvoAge/kg_formation/final_kg_building_2/building_biomedical_kg_new/Store_House \
  --data_files       entities_final.dict relation_final.dict Biomedical_121_12M_KG_train_90.txt Biomedical_121_12M_KG_valid_10.txt Biomedical_1to1_KG_test_10.txt \
  --format udd_hrt \
  --model_path /storage/Arushi/090526_EvoAge/kg_formation/training_2/Biomedical_121_12M/model_output/Rescal/RESCAL_Biomedical_121_12M_1 \
  --hidden_dim 64 \
  --gamma 12.0 \
  --batch_size_eval 512 \
  --neg_sample_size_eval 16 \
  --num_proc $NUM_PROC \
  --num_thread 1