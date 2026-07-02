
#!/usr/bin/env bash

# set -xe
# source ~/miniconda3/etc/profile.d/conda.sh
# conda activate dglke_env

export DGLBACKEND=pytorch
export PYTHONUNBUFFERED=1

# Dynamically detect CPU cores and use n - 1
TOTAL_CORES=$(nproc)
NUM_PROC=$((TOTAL_CORES - 15))

echo "[$(date)] Running TESTING only on CPU with $NUM_PROC threads..."

stdbuf -o0 -e0 dglke_eval \
  --model_name RESCAL \
  --dataset 1_per_Evoage_121_12M \
  --data_path        /storage/Arushi/090526_EvoAge/kg_formation/final_kg_building_2/building_evoage_with_1_percent_species_testsplit/Store_House \
  --data_files       entities_final.dict relation_final.dict EvoAge_1to1_1toM_train_90.txt EvoAge_1to1_1toM_valid_10.txt Human.txt \
  --format udd_hrt \
  --model_path /storage/Arushi/090526_EvoAge/kg_formation/training_2/1_per_species_test_EvoAge_121_12M/model_output/Rescal/RESCAL_1_per_Evoage_121_12M_3 \
  --hidden_dim 64 \
  --gamma 12.0 \
  --batch_size_eval 512 \
  --neg_sample_size_eval 16 \
  --num_proc $NUM_PROC \
  --num_thread 1


stdbuf -o0 -e0 dglke_eval \
  --model_name RESCAL \
  --dataset 1_per_Evoage_121_12M \
  --data_path        /storage/Arushi/090526_EvoAge/kg_formation/final_kg_building_2/building_evoage_with_1_percent_species_testsplit/Store_House \
  --data_files       entities_final.dict relation_final.dict EvoAge_1to1_1toM_train_90.txt EvoAge_1to1_1toM_valid_10.txt Yeast.txt \
  --format udd_hrt \
  --model_path /storage/Arushi/090526_EvoAge/kg_formation/training_2/1_per_species_test_EvoAge_121_12M/model_output/Rescal/RESCAL_1_per_Evoage_121_12M_3 \
  --hidden_dim 64 \
  --gamma 12.0 \
  --batch_size_eval 512 \
  --neg_sample_size_eval 16 \
  --num_proc $NUM_PROC \
  --num_thread 1



stdbuf -o0 -e0 dglke_eval \
  --model_name RESCAL \
  --dataset 1_per_Evoage_121_12M \
  --data_path        /storage/Arushi/090526_EvoAge/kg_formation/final_kg_building_2/building_evoage_with_1_percent_species_testsplit/Store_House \
  --data_files       entities_final.dict relation_final.dict EvoAge_1to1_1toM_train_90.txt EvoAge_1to1_1toM_valid_10.txt Celegans.txt \
  --format udd_hrt \
  --model_path /storage/Arushi/090526_EvoAge/kg_formation/training_2/1_per_species_test_EvoAge_121_12M/model_output/Rescal/RESCAL_1_per_Evoage_121_12M_3 \
  --hidden_dim 64 \
  --gamma 12.0 \
  --batch_size_eval 512 \
  --neg_sample_size_eval 16 \
  --num_proc $NUM_PROC \
  --num_thread 1


stdbuf -o0 -e0 dglke_eval \
  --model_name RESCAL \
  --dataset 1_per_Evoage_121_12M \
  --data_path        /storage/Arushi/090526_EvoAge/kg_formation/final_kg_building_2/building_evoage_with_1_percent_species_testsplit/Store_House \
  --data_files       entities_final.dict relation_final.dict EvoAge_1to1_1toM_train_90.txt EvoAge_1to1_1toM_valid_10.txt Drosophila.txt \
  --format udd_hrt \
  --model_path /storage/Arushi/090526_EvoAge/kg_formation/training_2/1_per_species_test_EvoAge_121_12M/model_output/Rescal/RESCAL_1_per_Evoage_121_12M_3 \
  --hidden_dim 64 \
  --gamma 12.0 \
  --batch_size_eval 512 \
  --neg_sample_size_eval 16 \
  --num_proc $NUM_PROC \
  --num_thread 1



stdbuf -o0 -e0 dglke_eval \
  --model_name RESCAL \
  --dataset 1_per_Evoage_121_12M \
  --data_path        /storage/Arushi/090526_EvoAge/kg_formation/final_kg_building_2/building_evoage_with_1_percent_species_testsplit/Store_House \
  --data_files       entities_final.dict relation_final.dict EvoAge_1to1_1toM_train_90.txt EvoAge_1to1_1toM_valid_10.txt Zebrafish.txt \
  --format udd_hrt \
  --model_path /storage/Arushi/090526_EvoAge/kg_formation/training_2/1_per_species_test_EvoAge_121_12M/model_output/Rescal/RESCAL_1_per_Evoage_121_12M_3 \
  --hidden_dim 64 \
  --gamma 12.0 \
  --batch_size_eval 512 \
  --neg_sample_size_eval 16 \
  --num_proc $NUM_PROC \
  --num_thread 1


stdbuf -o0 -e0 dglke_eval \
  --model_name RESCAL \
  --dataset 1_per_Evoage_121_12M \
  --data_path        /storage/Arushi/090526_EvoAge/kg_formation/final_kg_building_2/building_evoage_with_1_percent_species_testsplit/Store_House \
  --data_files       entities_final.dict relation_final.dict EvoAge_1to1_1toM_train_90.txt EvoAge_1to1_1toM_valid_10.txt Mouse.txt \
  --format udd_hrt \
  --model_path /storage/Arushi/090526_EvoAge/kg_formation/training_2/1_per_species_test_EvoAge_121_12M/model_output/Rescal/RESCAL_1_per_Evoage_121_12M_3 \
  --hidden_dim 64 \
  --gamma 12.0 \
  --batch_size_eval 512 \
  --neg_sample_size_eval 16 \
  --num_proc $NUM_PROC \
  --num_thread 1


stdbuf -o0 -e0 dglke_eval \
  --model_name RESCAL \
  --dataset 1_per_Evoage_121_12M \
  --data_path        /storage/Arushi/090526_EvoAge/kg_formation/final_kg_building_2/building_evoage_with_1_percent_species_testsplit/Store_House \
  --data_files       entities_final.dict relation_final.dict EvoAge_1to1_1toM_train_90.txt EvoAge_1to1_1toM_valid_10.txt CrossSpecies.txt \
  --format udd_hrt \
  --model_path /storage/Arushi/090526_EvoAge/kg_formation/training_2/1_per_species_test_EvoAge_121_12M/model_output/Rescal/RESCAL_1_per_Evoage_121_12M_3 \
  --hidden_dim 64 \
  --gamma 12.0 \
  --batch_size_eval 512 \
  --neg_sample_size_eval 16 \
  --num_proc $NUM_PROC \
  --num_thread 1