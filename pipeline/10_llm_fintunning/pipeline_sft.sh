#!/bin/bash

# Exit on errors
set -e

# ==========================================================
# Configurations & Paths (Relative paths preferred)
# ==========================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

CONDA_BASE="${CONDA_BASE:-$HOME/miniconda3}"
LLAMA_ENV_DIR="${LLAMA_ENV_DIR:-$CONDA_BASE/envs/llamafactory}"
export PATH="$LLAMA_ENV_DIR/bin:$PATH"

YAML_FILE="biomistral_lora_sft_optimized4.yaml"
BASE_MODEL="BioMistral/BioMistral-7B"
ADAPTER_DIR="LLaMA-Factory/saves/BioMistral-7B/lora/sft_optimized3"
EXPORT_DIR="models/BioMistral-Finetuned4"

if [ ! -f "$YAML_FILE" ]; then
    echo "Error: Training configuration file '$YAML_FILE' not found."
    exit 1
fi

echo "=========================================================="
# Step 3: LLaMA-Factory SFT Fine-Tuning
echo "Step 3a: Initiating LLaMA-Factory Supervised Fine-Tuning (SFT)..."
# ==========================================================
# If resume_from_checkpoint is specified, verify it exists. If not, strip it to prevent training crash.
CHECKPOINT_PATH=$(grep -E "^resume_from_checkpoint:" "$YAML_FILE" | awk '{print $2}')
if [ ! -z "$CHECKPOINT_PATH" ] && [ ! -d "$CHECKPOINT_PATH" ]; then
    echo "Warning: resume_from_checkpoint path '$CHECKPOINT_PATH' not found. Removing from YAML for a clean start."
    sed -i '/^resume_from_checkpoint:/d' "$YAML_FILE"
fi

cd LLaMA-Factory
echo "Starting training via llamafactory-cli..."
llamafactory-cli train "../$YAML_FILE"

echo "=========================================================="
# Step 3b: Export and Merge Weights
echo "Step 3b: Exporting and merging adapter weights..."
# ==========================================================
cd "$SCRIPT_DIR"
mkdir -p "models"

# Make adapter path relative to the current dir or use the parsed YAML output_dir
YAML_OUTPUT_DIR=$(grep -E "^output_dir:" "$YAML_FILE" | awk '{print $2}')
if [ ! -z "$YAML_OUTPUT_DIR" ]; then
    ADAPTER_DIR="LLaMA-Factory/$YAML_OUTPUT_DIR"
fi

echo "Merging base model '$BASE_MODEL' with adapters from '$ADAPTER_DIR'..."
echo "Output will be written to '$EXPORT_DIR'"

llamafactory-cli export \
    --model_name_or_path "$BASE_MODEL" \
    --adapter_name_or_path "$ADAPTER_DIR" \
    --template mistral \
    --finetuning_type lora \
    --export_dir "$EXPORT_DIR" \
    --export_size 5 \
    --export_device auto

echo "=========================================================="
# Step 3c: Tokenizer Config Patching
echo "Step 3c: Patching tokenizer configuration..."
# ==========================================================
TOKENIZER_CONFIG="$EXPORT_DIR/tokenizer_config.json"
if [ -f "$TOKENIZER_CONFIG" ]; then
    echo "Applying patch for 'extra_special_tokens' serialization in $TOKENIZER_CONFIG..."
    # Replace empty list with empty object to prevent downstream vLLM/SGLang loading crashes
    sed -i 's/"extra_special_tokens": \[\]/"extra_special_tokens": \{\}/g' "$TOKENIZER_CONFIG"
    echo "Patch successfully applied."
else
    echo "Warning: $TOKENIZER_CONFIG not found. Skipping patch."
fi

echo "Step 3 SFT & export completed successfully!"
