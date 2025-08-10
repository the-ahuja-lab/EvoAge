#!/usr/bin/env bash
# run_rotate.sh

set -xe                          # echo each command and exit on error
source ~/miniconda3/etc/profile.d/conda.sh
conda activate dglke_env

export DGLBACKEND=pytorch
export PYTHONUNBUFFERED=1        # <— force Python stdio unbuffered

echo "[$(date)] Activated env and set DGLBACKEND. Launching training…"

# prefix the training CLI with stdbuf to turn off buffering in any subprocess
exec stdbuf -o0 -e0 dglke_train \
  --model_name       RotatE \
  --dataset          EvoKG \
  --data_path        Training_files/ \
  --data_files       entities_final.dict relation_final.dict Train_final_10.txt valid_final.txt Test_final.txt \
  --format           udd_hrt \
  --batch_size       2048 \
  --neg_sample_size  32 \
  --batch_size_eval  128 \
  --neg_sample_size_eval 16 \
  --hidden_dim       128 \
  --double_ent       \
  --gamma            12.0 \
  --lr               0.01 \
  --max_step         4099091 \
  --log_interval     10000 \
  --eval_interval    2500000 \
  --save_path        model_output/rotatE \
  --gpu              0 1 \
  -adv               \
  -a 1.0             \
  --valid            \
  --test
