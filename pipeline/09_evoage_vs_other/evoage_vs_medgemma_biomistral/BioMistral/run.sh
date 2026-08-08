#!/bin/bash

# Exit on errors
set -e

# ==========================================================
# Environment Setup
# ==========================================================
# Override CONDA_SH / CONDA_ENV if your conda lives elsewhere.
CONDA_SH="${CONDA_SH:-$HOME/miniconda3/etc/profile.d/conda.sh}"
CONDA_ENV="${CONDA_ENV:-vllm3}"
source "$CONDA_SH"
export TMPDIR=$HOME/tmp
export TEMP=$HOME/tmp
export TMP=$HOME/tmp
export TRITON_CACHE_DIR=$HOME/triton_cache
export TORCHINDUCTOR_CACHE_DIR=$HOME/torch_cache
export HF_HOME=$HOME/hf_cache
export HUGGINGFACE_HUB_CACHE=$HOME/hf_cache

conda activate "$CONDA_ENV"

export LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:$LIBRARY_PATH
export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH

# Use port 50000 as default (easy to customize)
PORT="${PORT:-50000}"

# Get script's directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Create logs directory inside script's directory
mkdir -p logs

SGLANG_PYTHON="${SGLANG_PYTHON:-$(command -v python)}"

# Point MODEL_PATH at your local copy of the model.
MODEL_PATH="${MODEL_PATH:-/home/suvenduk/Two_level/models/BioMistral}"
LOG_PREFIX="biomistral"

if [ ! -d "$MODEL_PATH" ]; then
  echo "ERROR: MODEL_PATH does not exist: $MODEL_PATH" >&2
  echo "Set it to your local model directory, e.g. MODEL_PATH=/path/to/model ./run.sh" >&2
  exit 1
fi

echo "=========================================================="
echo " Starting server for: $MODEL_PATH"
echo " Port: $PORT"
echo "=========================================================="

# 1. Launch SGLang Server in background
nohup $SGLANG_PYTHON \
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

# Define trap to clean up the background server process on exit
cleanup() {
  echo "Stopping server PID $SERVER_PID..."
  kill -15 $SERVER_PID 2>/dev/null || true
  sleep 2
  kill -9 $SERVER_PID 2>/dev/null || true
}
trap cleanup EXIT

# 2. Wait for server initialization
echo "Waiting for SGLang server on port $PORT to be ready..."
while ! curl -s "http://127.0.0.1:${PORT}/v1/models" > /dev/null; do
  if ! kill -0 $SERVER_PID 2>/dev/null; then
    echo "ERROR: Server process $SERVER_PID died unexpectedly! Check logs: logs/${LOG_PREFIX}_port${PORT}.log"
    exit 1
  fi
  echo "Server not ready yet. Waiting 10 seconds..."
  sleep 10
done

echo "Server is UP and ready!"

# 3. Run Python evaluation script
echo "Executing python script..."
$SGLANG_PYTHON run_hypothesis.py --output-dir "." --server-url "http://127.0.0.1:${PORT}/v1"

echo "Execution completed successfully!"
