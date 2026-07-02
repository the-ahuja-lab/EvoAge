
#!/usr/bin/env bash

export DGLBACKEND=pytorch
export PYTHONUNBUFFERED=1

# Dynamically detect CPU cores and use n - 1
TOTAL_CORES=$(nproc)
NUM_PROC=22

echo "[$(date)] Running TESTING only on CPU with $NUM_PROC threads..."

exec stdbuf -o0 -e0 dglke_eval \
  --model_name RESCAL \
  --dataset Biomedical_1_to_1 \
  --data_path        /storage/Arushi/090526_EvoAge/kg_formation/final_kg_building_2/building_biomedical_kg_new/Store_House \
  --data_files       entities_final.dict relation_final.dict Biomedical_1to1_KG_train_80.txt Biomedical_1to1_KG_valid_10.txt Biomedical_1to1_KG_test_10.txt \
  --format udd_hrt \
  --model_path /storage/Arushi/090526_EvoAge/kg_formation/training_2/Biomedical_1_to_1/model_output/Rescal/RESCAL_Biomedical_1_to_1_0 \
  --hidden_dim 64 \
  --gamma 12.0 \
  --batch_size_eval 512 \
  --neg_sample_size_eval 16 \
  --num_proc $NUM_PROC \
  --num_thread 1
  