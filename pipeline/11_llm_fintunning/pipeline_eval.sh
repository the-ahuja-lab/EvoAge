#!/bin/bash

# Exit on errors
set -e

# ==========================================================
# Configurations & Paths (Relative paths preferred)
# ==========================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Conda python and executable binaries
CONDA_BASE="${CONDA_BASE:-$HOME/miniconda3}"
VLLM_PYTHON="${VLLM_PYTHON:-$CONDA_BASE/envs/vllm3/bin/python}"
GRAPHGEN_PYTHON="${GRAPHGEN_PYTHON:-$CONDA_BASE/envs/graphgen/bin/python}"
LM_EVAL_BIN="${LM_EVAL_BIN:-$CONDA_BASE/envs/lm-eval/bin/lm-eval}"
BASE_PYTHON="${BASE_PYTHON:-python3}"

TRAINEE_PORT=${TRAINEE_PORT:-30000}
SYNTHESIZER_PORT=${SYNTHESIZER_PORT:-30001}
EVAL_PORT=${EVAL_PORT:-50000}

FINETUNED_MODEL_PATH="models/BioMistral-Finetuned4"
SYNTHESIZER_MODEL="Qwen/Qwen3-14B-FP8"

# ==========================================================
# Step 4: Target Domain Evaluation (KG Test Triples)
# ==========================================================
if [ -z "$SKIP_STEP_4" ]; then
    echo "=========================================================="
    echo "Step 4: Target Domain Evaluation..."
    echo "=========================================================="

    # 4a. Ingest test data into KuzuDB
    echo "Ingesting test dataset into test DB..."
    if [ ! -f "load_kuzu_test.py" ]; then
        echo "Error: load_kuzu_test.py not found."
        exit 1
    fi
    $GRAPHGEN_PYTHON load_kuzu_test.py

    # 4b. Launch servers
    mkdir -p logs

    echo "Launching Trainee Server (Finetuned Model) on port $TRAINEE_PORT..."
    nohup $VLLM_PYTHON -m sglang.launch_server \
        --model-path "$FINETUNED_MODEL_PATH" \
        --port $TRAINEE_PORT \
        --mem-fraction-static 0.45 \
        --disable-cuda-graph \
        --attention-backend torch_native \
        > logs/biomistral_eval_port${TRAINEE_PORT}.log 2>&1 &
    TRAINEE_PID=$!

    echo "Launching Synthesizer/Judge Server (Qwen3) on port $SYNTHESIZER_PORT..."
    nohup $VLLM_PYTHON -m sglang.launch_server \
        --model-path "$SYNTHESIZER_MODEL" \
        --port $SYNTHESIZER_PORT \
        --mem-fraction-static 0.45 \
        --context-length 32768 \
        --schedule-policy lpm \
        --chunked-prefill-size 4096 \
        --max-running-requests 128 \
        --watchdog-timeout 3600 \
        > logs/qwen3_eval_port${SYNTHESIZER_PORT}.log 2>&1 &
    SYNTHESIZER_PID=$!

    cleanup_servers() {
        echo "Cleaning up SGLang servers..."
        if [ ! -z "$TRAINEE_PID" ]; then
            kill $TRAINEE_PID 2>/dev/null || true
        fi
        if [ ! -z "$SYNTHESIZER_PID" ]; then
            kill $SYNTHESIZER_PID 2>/dev/null || true
        fi
        pkill -f "sglang.launch_server.*$TRAINEE_PORT" || true
        pkill -f "sglang.launch_server.*$SYNTHESIZER_PORT" || true
    }
    # Set trap to clean up evaluation servers on error or exit
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

    wait_for_server $TRAINEE_PORT "Trainee (Finetuned)"
    wait_for_server $SYNTHESIZER_PORT "Synthesizer/Judge"

    # 4c. Run GraphGen test evaluation
    export SYNTHESIZER_BACKEND=openai_api
    export SYNTHESIZER_MODEL="$SYNTHESIZER_MODEL"
    export SYNTHESIZER_BASE_URL="http://localhost:${SYNTHESIZER_PORT}/v1"
    export TRAINEE_BACKEND=openai_api
    export TRAINEE_MODEL="default"
    export TRAINEE_BASE_URL="http://localhost:${TRAINEE_PORT}/v1"
    export PYTHONPATH=$(pwd)/GraphGen

    OUTPUT_DIR="cache/output/test_evaluation_finetuned"
    echo "Running GraphGen test evaluation pipeline..."
    $GRAPHGEN_PYTHON -u GraphGen/graphgen/run.py \
        --config_file test_evaluate.yaml \
        --output_dir "$OUTPUT_DIR"

    # 4d. Answer Resolution (performed while the Synthesizer judge server is still active)
    echo "Consolidating and resolving evaluation answers..."
    $BASE_PYTHON resolve_kg_evaluation.py \
        --input "${OUTPUT_DIR}/judge" \
        --output "judge_results_resolved.csv" \
        --type edge \
        --endpoints "http://localhost:${SYNTHESIZER_PORT}/v1" \
        --workers 8

    # Tear down servers for Step 4
    cleanup_servers
    # Clear trap so they aren't double killed on normal script exit
    trap - EXIT
else
    echo "Skipping Step 4: Target Domain Evaluation"
fi

if [ -z "$SKIP_STEP_5" ]; then
    echo "=========================================================="
    echo "Step 5: General Clinical Evaluation..."
    echo "=========================================================="

    echo "Launching Finetuned model for lm-eval on port $EVAL_PORT..."
    nohup $VLLM_PYTHON -m sglang.launch_server \
      --model-path "$FINETUNED_MODEL_PATH" \
      --port $EVAL_PORT \
      --host 0.0.0.0 \
      --mem-fraction-static 0.9 \
      --context-length 8192 \
      --schedule-policy lpm \
      --chunked-prefill-size 2048 \
      > logs/biomistral_port${EVAL_PORT}.log 2>&1 &
    EVAL_PID=$!

    cleanup_eval_server() {
        echo "Cleaning up SGLang evaluation server..."
        if [ ! -z "$EVAL_PID" ]; then
            kill $EVAL_PID 2>/dev/null || true
        fi
        pkill -f "sglang.launch_server.*$EVAL_PORT" || true
    }
    trap cleanup_eval_server EXIT

    wait_for_server $EVAL_PORT "Fine-Tuned Evaluator"

    mkdir -p results
    echo "Executing lm-eval tasks..."
    $LM_EVAL_BIN run \
      --model local-completions \
      --model_args model="${FINETUNED_MODEL_PATH}",base_url=http://localhost:${EVAL_PORT}/v1/completions,num_concurrent=1,max_retries=3 \
      --tasks medmcqa,pubmedqa,global_mmlu_full_en_anatomy,global_mmlu_full_en_clinical_knowledge,global_mmlu_full_en_college_biology,global_mmlu_full_en_college_medicine,global_mmlu_full_en_medical_genetics,global_mmlu_full_en_professional_medicine,global_mmlu_full_en_virology \
      --output_path results/biomistral_finetuned4 \
      --trust_remote_code

    cleanup_eval_server
    trap - EXIT
else
    echo "Skipping Step 5: General Clinical Evaluation"
fi

echo "Step 4 & 5 completed successfully!"
