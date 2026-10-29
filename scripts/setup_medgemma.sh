#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/Backend"
RUN_DIR="$ROOT_DIR/.run"
LOG_DIR="${LOG_DIR:-$ROOT_DIR/logs}"
CACHE_DIR="${MEDGEMMA_CACHE_DIR:-$ROOT_DIR/.cache/medgemma}"

MEDGEMMA_ENV_NAME="${MEDGEMMA_ENV_NAME:-sglang}"
MEDGEMMA_MODEL_REPO="${MEDGEMMA_MODEL_REPO:-google/medgemma-27b-text-it}"
MEDGEMMA_MODEL_PATH="${MEDGEMMA_MODEL_PATH:-$BACKEND_DIR/medgemma-27b-local}"
MEDGEMMA_DOWNLOAD_WORKERS="${MEDGEMMA_DOWNLOAD_WORKERS:-4}"
MEDGEMMA_HF_TOKEN="${MEDGEMMA_HF_TOKEN:-${HF_TOKEN:-}}"
MEDGEMMA_HOST="${MEDGEMMA_HOST:-0.0.0.0}"
MEDGEMMA_PORT="${MEDGEMMA_PORT:-30001}"
MEDGEMMA_MEM_FRACTION="${MEDGEMMA_MEM_FRACTION:-0.9}"
MEDGEMMA_CONTEXT_LENGTH="${MEDGEMMA_CONTEXT_LENGTH:-32000}"
MEDGEMMA_CHUNKED_PREFILL_SIZE="${MEDGEMMA_CHUNKED_PREFILL_SIZE:-2048}"
MEDGEMMA_SCHEDULE_POLICY="${MEDGEMMA_SCHEDULE_POLICY:-lpm}"
DOWNLOAD_MODEL=1
START_SERVER=1
FORCE_DOWNLOAD=0

log() { printf '
[%s] %s
' "$1" "$2"; }
info() { log INFO "$1"; }
warn() { log WARN "$1"; }
fail() { log ERROR "$1"; exit 1; }

have() {
  command -v "$1" >/dev/null 2>&1
}

usage() {
  cat <<EOF
Usage: scripts/setup_medgemma.sh [options]

Sets up the local MedGemma SGLang environment, downloads the gated model into
Backend/medgemma-27b-local, and starts the local SGLang server.

WARNING:
  MedGemma 27B needs roughly 60GB VRAM; an 80GB GPU is recommended.
  If this machine does not have enough GPU memory, use USE=gemini with the
  Gemini API instead of USE=medgemma.
  Run this script from the repo root in a separate terminal, and continue the
  rest of setup/startup from another terminal in the same repo. Keep the
  MedGemma/SGLang server process running while the backend uses USE=medgemma.

Run this only when Backend/.env uses:
  USE=medgemma
  MEDGEMMA_BASE_URL=http://localhost:30001/v1
  MEDGEMMA_MODEL=medgemma-27b-local

Options:
  --download-only       Install/check env and download the model, but do not start SGLang.
  --skip-download       Start SGLang without downloading/checking the model from Hugging Face.
  --force-download      Re-run the Hugging Face download even when local files exist.
  -h, --help            Show this help.

Environment variables:
  MEDGEMMA_ENV_NAME                 Conda env name. Default: sglang
  MEDGEMMA_MODEL_REPO               HF model repo. Default: google/medgemma-27b-text-it
  MEDGEMMA_MODEL_PATH               Model path. Default: Backend/medgemma-27b-local
  MEDGEMMA_HF_TOKEN or HF_TOKEN      Hugging Face read token for the gated model.
  MEDGEMMA_DOWNLOAD_WORKERS         HF download workers. Default: 4
  MEDGEMMA_HOST                     Bind host. Default: 0.0.0.0
  MEDGEMMA_PORT                     Port. Default: 30001
  MEDGEMMA_MEM_FRACTION             Static GPU memory fraction. Default: 0.9
  MEDGEMMA_CONTEXT_LENGTH           Context length. Default: 32000
  MEDGEMMA_CHUNKED_PREFILL_SIZE     Chunked prefill size. Default: 2048
  MEDGEMMA_SCHEDULE_POLICY          Schedule policy. Default: lpm
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --download-only)
      START_SERVER=0
      ;;
    --skip-download)
      DOWNLOAD_MODEL=0
      ;;
    --force-download)
      FORCE_DOWNLOAD=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *) fail "Unknown option: $1" ;;
  esac
  shift
done

conda_env_exists() {
  local env_name="$1"
  conda env list | awk '{print $1}' | grep -qx "$env_name"
}

conda_run() {
  local env_name="$1"
  shift
  conda run -n "$env_name" "$@"
}

show_medgemma_warnings() {
  warn "!!! MEDGEMMA RESOURCE WARNING !!!"
  warn "MedGemma 27B needs roughly 60GB VRAM; an 80GB GPU is recommended."
  warn "If this host does not have enough GPU memory, set Backend/.env USE=gemini and use the Gemini API instead."
  warn "Run this script from the repo root in a separate terminal, then continue the rest of setup/startup from another terminal in the same repo."
  warn "Keep the MedGemma/SGLang server process running while the backend uses USE=medgemma."
}

setup_sglang_env() {
  have conda || fail "conda is required for MedGemma setup."

  if conda_env_exists "$MEDGEMMA_ENV_NAME"; then
    info "Conda env exists: $MEDGEMMA_ENV_NAME"
  else
    info "Creating conda env: $MEDGEMMA_ENV_NAME"
    conda create -n "$MEDGEMMA_ENV_NAME" python=3.11 -y
  fi

  info "Installing/updating SGLang and Hugging Face CLI in $MEDGEMMA_ENV_NAME"
  conda_run "$MEDGEMMA_ENV_NAME" python -m pip install --progress-bar on --upgrade pip
  conda_run "$MEDGEMMA_ENV_NAME" python -m pip install --progress-bar on "sglang[all]==0.5.15.post1" "huggingface_hub[cli]"
}

model_files_present() {
  [[ -s "$MEDGEMMA_MODEL_PATH/config.json" ]] || return 1
  grep -q '"model_type"' "$MEDGEMMA_MODEL_PATH/config.json" || return 1
  find "$MEDGEMMA_MODEL_PATH" -maxdepth 1 -type f \( -name '*.safetensors' -o -name '*.bin' \) -print -quit | grep -q .
}

download_model() {
  mkdir -p "$MEDGEMMA_MODEL_PATH"

  if [[ "$FORCE_DOWNLOAD" != "1" ]] && model_files_present; then
    info "MedGemma model files already exist and look complete. Keeping: $MEDGEMMA_MODEL_PATH"
    return
  fi

  if [[ -d "$MEDGEMMA_MODEL_PATH" ]] && ! model_files_present; then
    warn "Existing MedGemma directory is incomplete or invalid; re-running Hugging Face download: $MEDGEMMA_MODEL_PATH"
  fi

  info "Downloading MedGemma model..If model download gets aborted, check the README for instructions to resume the download."
  info "Model repo: $MEDGEMMA_MODEL_REPO"
  info "Target path: $MEDGEMMA_MODEL_PATH"

  local token_args=()
  local force_args=()
  if [[ -n "$MEDGEMMA_HF_TOKEN" ]]; then
    token_args=(--token "$MEDGEMMA_HF_TOKEN")
  else
    warn "No MEDGEMMA_HF_TOKEN/HF_TOKEN provided. The download requires that you are already logged in with hf auth login, or it will fail."
  fi
  if [[ "$FORCE_DOWNLOAD" == "1" ]]; then
    force_args=(--force-download)
  fi

  conda_run "$MEDGEMMA_ENV_NAME" hf download "$MEDGEMMA_MODEL_REPO" \
    --local-dir "$MEDGEMMA_MODEL_PATH" \
    "${token_args[@]}" \
    "${force_args[@]}" \
    --max-workers "$MEDGEMMA_DOWNLOAD_WORKERS"
}

start_server() {
  [[ -d "$MEDGEMMA_MODEL_PATH" ]] || fail "MedGemma model directory not found: $MEDGEMMA_MODEL_PATH"
  model_files_present || fail "MedGemma model directory is empty: $MEDGEMMA_MODEL_PATH"

  mkdir -p "$RUN_DIR" "$LOG_DIR" "$CACHE_DIR/tmp" "$CACHE_DIR/triton" "$CACHE_DIR/torch" "$CACHE_DIR/hf"

  export TMPDIR="$CACHE_DIR/tmp"
  export TEMP="$CACHE_DIR/tmp"
  export TMP="$CACHE_DIR/tmp"
  export TRITON_CACHE_DIR="$CACHE_DIR/triton"
  export TORCHINDUCTOR_CACHE_DIR="$CACHE_DIR/torch"
  export HF_HOME="$CACHE_DIR/hf"
  export HUGGINGFACE_HUB_CACHE="$CACHE_DIR/hf"
  export LIBRARY_PATH="/usr/lib/x86_64-linux-gnu:${LIBRARY_PATH:-}"
  export LD_LIBRARY_PATH="/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}"

  LOG_FILE="$LOG_DIR/medgemma_port${MEDGEMMA_PORT}.log"
  PID_FILE="$RUN_DIR/medgemma.pid"

  info "Starting MedGemma/SGLang server"
  info "Model path: $MEDGEMMA_MODEL_PATH"
  info "URL: http://localhost:${MEDGEMMA_PORT}/v1"
  info "Log file: $LOG_FILE"

  nohup conda run -n "$MEDGEMMA_ENV_NAME" python -m sglang.launch_server \
    --model-path "$MEDGEMMA_MODEL_PATH" \
    --port "$MEDGEMMA_PORT" \
    --host "$MEDGEMMA_HOST" \
    --mem-fraction-static "$MEDGEMMA_MEM_FRACTION" \
    --context-length "$MEDGEMMA_CONTEXT_LENGTH" \
    --schedule-policy "$MEDGEMMA_SCHEDULE_POLICY" \
    --chunked-prefill-size "$MEDGEMMA_CHUNKED_PREFILL_SIZE" \
    > "$LOG_FILE" 2>&1 &

  server_pid=$!
  printf '%s
' "$server_pid" > "$PID_FILE"

  info "Server started with PID: $server_pid"
  info "Watch logs with: tail -f $LOG_FILE"
}

show_medgemma_warnings
setup_sglang_env
if [[ "$DOWNLOAD_MODEL" == "1" ]]; then
  download_model
fi
if [[ "$START_SERVER" == "1" ]]; then
  start_server
else
  info "MedGemma download/setup complete. Start later with: bash scripts/setup_medgemma.sh --skip-download"
fi
