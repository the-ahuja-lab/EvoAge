#!/bin/bash

# Exit on errors
set -e

# ==========================================================
# Configurations & Paths (Relative paths preferred)
# ==========================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Conda python binaries
CONDA_BASE="${CONDA_BASE:-$HOME/miniconda3}"
VLLM_PYTHON="${VLLM_PYTHON:-$CONDA_BASE/envs/vllm3/bin/python}"
GRAPHGEN_PYTHON="${GRAPHGEN_PYTHON:-$CONDA_BASE/envs/graphgen/bin/python}"
BASE_PYTHON="${BASE_PYTHON:-python3}"

TRAINEE_PORT=${TRAINEE_PORT:-30000}
SYNTHESIZER_PORT=${SYNTHESIZER_PORT:-30001}
RUN_ID=${RUN_ID:-$(date +%s)}

# ==========================================================
# Step 1: KG Ingestion
# ==========================================================
if [ -z "$SKIP_STEP_1" ]; then
    echo "=========================================================="
    echo "Step 1: Ingesting KG into KuzuDB..."
    echo "=========================================================="
    if [ ! -f "load_kuzu.py" ]; then
        echo "Error: load_kuzu.py not found in current directory."
        exit 1
    fi
    $GRAPHGEN_PYTHON load_kuzu.py
else
    echo "Skipping Step 1: KG Ingestion"
fi

# ==========================================================
# Step 2: GraphGen Question Generation
# ==========================================================
if [ -z "$SKIP_STEP_2" ]; then
    echo "=========================================================="
    echo "Step 2: Starting SGLang Servers and GraphGen generation..."
    echo "=========================================================="
mkdir -p logs

echo "Launching Trainee Server (BioMistral-7B) on port $TRAINEE_PORT..."
nohup $VLLM_PYTHON -m sglang.launch_server \
    --model-path BioMistral/BioMistral-7B \
    --port $TRAINEE_PORT \
    --mem-fraction-static 0.45 \
    --disable-cuda-graph \
    --attention-backend torch_native \
    > logs/biomistral_port${TRAINEE_PORT}.log 2>&1 &
TRAINEE_PID=$!

echo "Launching Synthesizer Server (Qwen3-14B-FP8) on port $SYNTHESIZER_PORT..."
nohup $VLLM_PYTHON -m sglang.launch_server \
    --model-path Qwen/Qwen3-14B-FP8 \
    --port $SYNTHESIZER_PORT \
    --mem-fraction-static 0.45 \
    --context-length 32768 \
    --schedule-policy lpm \
    --chunked-prefill-size 4096 \
    --max-running-requests 128 \
    --watchdog-timeout 3600 \
    > logs/qwen3_14b_fp8_port${SYNTHESIZER_PORT}.log 2>&1 &
SYNTHESIZER_PID=$!

cleanup_servers() {
    echo "Cleaning up SGLang servers..."
    if [ ! -z "$TRAINEE_PID" ]; then
        kill $TRAINEE_PID 2>/dev/null || true
    fi
    if [ ! -z "$SYNTHESIZER_PID" ]; then
        kill $SYNTHESIZER_PID 2>/dev/null || true
    fi
    # Extra safety pkill
    pkill -f "sglang.launch_server.*$TRAINEE_PORT" || true
    pkill -f "sglang.launch_server.*$SYNTHESIZER_PORT" || true
}
trap cleanup_servers EXIT

# Health check loops
wait_for_server() {
    local port=$1
    local name=$2
    echo "Waiting for $name server on port $port to start..."
    for i in {1..60}; do
        if curl -s http://localhost:${port}/v1/models >/dev/null; then
            echo "$name server is up!"
            return 0
        fi
        sleep 5
    done
    echo "Error: $name server failed to start within 5 minutes."
    exit 1
}

wait_for_server $TRAINEE_PORT "Trainee"
wait_for_server $SYNTHESIZER_PORT "Synthesizer"

# Run GraphGen dataset generation
export SYNTHESIZER_BACKEND=openai_api
export SYNTHESIZER_MODEL="Qwen/Qwen3-14B-FP8"
export SYNTHESIZER_BASE_URL="http://localhost:${SYNTHESIZER_PORT}/v1"
export TRAINEE_BACKEND=openai_api
export TRAINEE_MODEL="BioMistral/BioMistral-7B"
export TRAINEE_BASE_URL="http://localhost:${TRAINEE_PORT}/v1"
export PYTHONPATH=$(pwd)/GraphGen

OUTPUT_DIR="cache/output/$RUN_ID"
echo "Running GraphGen pipeline..."
$GRAPHGEN_PYTHON -u GraphGen/graphgen/run.py \
    --config_file custom_kuzu_qa.yaml \
    --output_dir "$OUTPUT_DIR"

# Shutdown servers via trap cleanup_servers on exit

# Associated script: register datasets
echo "=========================================================="
echo "Registering Generated Datasets..."
# ==========================================================
$BASE_PYTHON register_datasets.py \
    --output_dir "$OUTPUT_DIR" \
    --llama_dir "LLaMA-Factory" \
    --yaml_file "biomistral_lora_sft_optimized4.yaml"

echo "Step 1 & 2 completed successfully. Datasets saved to: $OUTPUT_DIR"
else
    echo "Skipping Step 2: GraphGen Question Generation"
fi
