#!/bin/bash

# Exit on errors
set -e

# ==========================================================
# Environment Setup
# ==========================================================
source ~/miniconda3/etc/profile.d/conda.sh
export TMPDIR=$HOME/tmp
export TEMP=$HOME/tmp
export TMP=$HOME/tmp
export TRITON_CACHE_DIR=$HOME/triton_cache
export TORCHINDUCTOR_CACHE_DIR=$HOME/torch_cache
export HF_HOME=$HOME/hf_cache
export HUGGINGFACE_HUB_CACHE=$HOME/hf_cache

conda activate sglang

export LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:$LIBRARY_PATH
export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH


PORT=30001

# Get script's directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Create logs directory inside script's directory
mkdir -p logs


MODEL_PATH="medgemma-27b-local/"
LOG_PREFIX="medgemma"

echo "=========================================================="
echo " Starting server for: $MODEL_PATH"
echo " Port: $PORT"
echo "=========================================================="

# 1. Launch SGLang Server in background
nohup python3 \
  -m sglang.launch_server \
  --model-path "$MODEL_PATH" \
  --port $PORT \
  --host 0.0.0.0 \
  --mem-fraction-static 0.9 \
  --context-length 32000 \
  --schedule-policy lpm \
  --chunked-prefill-size 2048 \
  > "logs/${LOG_PREFIX}_port${PORT}.log" 2>&1 &

SERVER_PID=$!
echo "Server started with PID: $SERVER_PID. Logging to logs/${LOG_PREFIX}_port${PORT}.log"