#!/bin/bash

# Exit on errors
set -e

# ==========================================================
# Help documentation
# ==========================================================
show_help() {
    echo "Usage: ./run_pipeline.sh [options]"
    echo ""
    echo "Options:"
    echo "  -s, --step <steps>     Comma-separated list of steps to run (e.g. 1,2 or 3 or 4,5)."
    echo "                         Steps mapping:"
    echo "                           Step 1: KG DB Preparation & Ingestion"
    echo "                           Step 2: GraphGen Question-Answer Generation"
    echo "                           Step 3: LLaMA-Factory SFT & Export (DoRA)"
    echo "                           Step 4: KG Test Triples Evaluation & Answer Resolution"
    echo "                           Step 5: General Clinical Evaluation (lm-eval)"
    echo "  -a, --all              Run all 5 steps of the pipeline end-to-end (Default if no step is specified)."
    echo "  -c, --conda-base <dir> Path to Miniconda/Conda base directory (Default: \$HOME/miniconda3)."
    echo "  -r, --run-id <id>      Specify a custom Run ID for GraphGen output cache (Default: current epoch timestamp)."
    echo "  -h, --help             Display this help message."
    echo ""
}

# ==========================================================
# Parse arguments
# ==========================================================
STEPS=""
CONDA_BASE_DIR="$HOME/miniconda3"
RUN_ID_VAL=$(date +%s)
ALL_STEPS=false

while [[ "$#" -gt 0 ]]; do
    case $1 in
        -s|--step) STEPS="$2"; shift ;;
        -a|--all) ALL_STEPS=true ;;
        -c|--conda-base) CONDA_BASE_DIR="$2"; shift ;;
        -r|--run-id) RUN_ID_VAL="$2"; shift ;;
        -h|--help) show_help; exit 0 ;;
        *) echo "Unknown parameter passed: $1"; show_help; exit 1 ;;
    esac
    shift
done

# Enforce script directory to be working directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Export variables for sub-scripts
export CONDA_BASE="$CONDA_BASE_DIR"
export RUN_ID="$RUN_ID_VAL"

# Determine which steps to execute
RUN_S1=false
RUN_S2=false
RUN_S3=false
RUN_S4=false
RUN_S5=false

if [ "$ALL_STEPS" = true ] || [ -z "$STEPS" ]; then
    RUN_S1=true
    RUN_S2=true
    RUN_S3=true
    RUN_S4=true
    RUN_S5=true
else
    # Parse comma-separated steps
    IFS=',' read -ra ADDR <<< "$STEPS"
    for s in "${ADDR[@]}"; do
        case $s in
            1) RUN_S1=true ;;
            2) RUN_S2=true ;;
            3) RUN_S3=true ;;
            4) RUN_S4=true ;;
            5) RUN_S5=true ;;
            *) echo "Invalid step specified: $s. Valid steps are 1, 2, 3, 4, 5."; exit 1 ;;
        esac
    done
fi

echo "=========================================================="
echo "Starting EvoAge LLM Build & Evaluation Pipeline"
echo "  Run ID:     $RUN_ID"
echo "  Conda Base: $CONDA_BASE"
echo "  Steps:      $( [ "$RUN_S1" = true ] && echo -n "1 " )$( [ "$RUN_S2" = true ] && echo -n "2 " )$( [ "$RUN_S3" = true ] && echo -n "3 " )$( [ "$RUN_S4" = true ] && echo -n "4 " )$( [ "$RUN_S5" = true ] && echo -n "5 " )"
echo "=========================================================="

# ==========================================================
# Run Phase 1 & 2 (Data Generation)
# ==========================================================
if [ "$RUN_S1" = true ] || [ "$RUN_S2" = true ]; then
    export SKIP_STEP_1=true
    export SKIP_STEP_2=true
    
    if [ "$RUN_S1" = true ]; then
        unset SKIP_STEP_1
    fi
    if [ "$RUN_S2" = true ]; then
        unset SKIP_STEP_2
    fi
    
    echo "Executing Data Generation Pipeline..."
    ./pipeline_data_gen.sh
fi

# ==========================================================
# Run Phase 3 (Fine-tuning & Weight Export)
# ==========================================================
if [ "$RUN_S3" = true ]; then
    echo "Executing Fine-tuning & Weight Export..."
    ./pipeline_sft.sh
fi

# ==========================================================
# Run Phase 4 & 5 (Evaluation)
# ==========================================================
if [ "$RUN_S4" = true ] || [ "$RUN_S5" = true ]; then
    export SKIP_STEP_4=true
    export SKIP_STEP_5=true
    
    if [ "$RUN_S4" = true ]; then
        unset SKIP_STEP_4
    fi
    if [ "$RUN_S5" = true ]; then
        unset SKIP_STEP_5
    fi
    
    echo "Executing Evaluation Pipeline..."
    ./pipeline_eval.sh
fi

echo "=========================================================="
echo "Pipeline execution finished successfully!"
echo "=========================================================="
