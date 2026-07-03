#!/usr/bin/env bash
# run_rescal_eval_all_shuffles.sh
set -xe
source ~/miniconda3/etc/profile.d/conda.sh
conda activate dglke_env
export DGLBACKEND=pytorch
export PYTHONUNBUFFERED=1

TOTAL_CORES=$(nproc)
NUM_PROC=$((TOTAL_CORES - 15))

DATA_PATH="/storage/Arushi/090526_EvoAge/kg_formation/training_3/Shuffled_EvoAge_testing/Store_House/shuffled_test_sets"
MODEL_PATH="/storage/Arushi/090526_EvoAge/kg_formation/training_3/EvoAge_121_12M/model_output/Rescal/RESCAL_Evoage_121_12M_1"
LOG_FILE="${DATA_PATH}/rescal_eval_all_shuffles.log"

# Clear/start the combined log
echo "Combined RESCAL eval log — started $(date)" > "$LOG_FILE"

echo "[$(date)] Running TESTING on CPU with $NUM_PROC threads for 30 shuffled test sets..."

for i in $(seq -f "%03g" 0 29); do
    SEED=$((10#$i))   # strip leading zeros for the seed number in filename
    TEST_FILE="shuffled_test_${i}_seed${SEED}.txt"

    echo "" | tee -a "$LOG_FILE"
    echo "=====================================================" | tee -a "$LOG_FILE"
    echo "===== SHUFFLE_ID: ${i} | SEED: ${SEED} | START: $(date) =====" | tee -a "$LOG_FILE"
    echo "=====================================================" | tee -a "$LOG_FILE"

    stdbuf -o0 -e0 dglke_eval \
        --model_name RESCAL \
        --dataset          Evoage_121_12M \
        --data_path        "$DATA_PATH" \
        --data_files       entities_final.dict relation_final.dict EvoAge_121_12M_KG_train_90.txt EvoAge_121_12M_KG_valid_10.txt "$TEST_FILE" \
        --format udd_hrt \
        --model_path "$MODEL_PATH" \
        --hidden_dim 64 \
        --gamma 12.0 \
        --batch_size_eval 512 \
        --neg_sample_size_eval 16 \
        --num_proc $NUM_PROC \
        --num_thread 1 \
        2>&1 | tee -a "$LOG_FILE"

    echo "===== SHUFFLE_ID: ${i} | END: $(date) =====" | tee -a "$LOG_FILE"
done

echo "[$(date)] All 30 shuffle evaluations complete. Combined log at: $LOG_FILE"