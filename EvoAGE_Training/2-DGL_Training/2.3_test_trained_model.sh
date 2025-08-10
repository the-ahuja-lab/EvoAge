# CPU only testing
#!/usr/bin/env bash
# run_rotate_eval_cpu.sh

set -xe
source ~/miniconda3/etc/profile.d/conda.sh
conda activate dglke_env

export DGLBACKEND=pytorch
export PYTHONUNBUFFERED=1

# Dynamically detect CPU cores and use n - 1
TOTAL_CORES=$(nproc)
NUM_PROC=$((TOTAL_CORES - 1))

echo "[$(date)] Running TESTING only on CPU with $NUM_PROC threads..."

exec stdbuf -o0 -e0 dglke_eval \
  --model_name RotatE \
  --dataset EvoKG \
  --data_path Training_files/ \
  --data_files entities_final.dict relation_final.dict Train_final_10.txt valid_final.txt Test_final.txt \
  --format udd_hrt \
  --model_path model_output/rotat/RotatE_128Emb/ \
  --hidden_dim 256 \
  --gamma 12.0 \
  --batch_size_eval 256 \
  --neg_sample_size_eval 16 \
  --num_proc $NUM_PROC \
  --num_thread 1
