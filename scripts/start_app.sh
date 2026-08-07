#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/Backend"
FRONTEND_DIR="$ROOT_DIR/Frontend"
RUN_DIR="$ROOT_DIR/.run"
LOG_DIR="$ROOT_DIR/logs"
DGL_DATASET_URL="https://huggingface.co/datasets/gauravahuja77/EvoAge/tree/main"

BACKEND_ENV_NAME="${BACKEND_ENV_NAME:-evoage_backend}"
FRONTEND_ENV_NAME="${FRONTEND_ENV_NAME:-evoage_frontend}"
BACKEND_HOST="${BACKEND_HOST:-}"
BACKEND_PORT="${BACKEND_PORT:-}"
FRONTEND_HOST="${FRONTEND_HOST:-}"
FRONTEND_PORT="${FRONTEND_PORT:-}"
BACKEND_PUBLIC_URL="${BACKEND_PUBLIC_URL:-}"
FRONTEND_PUBLIC_URL="${FRONTEND_PUBLIC_URL:-}"
BACKEND_LOCAL_URL="${BACKEND_LOCAL_URL:-}"
FRONTEND_LOCAL_URL="${FRONTEND_LOCAL_URL:-}"
BACKEND_WORKERS="${BACKEND_WORKERS:-1}"
BACKEND_TIMEOUT="${BACKEND_TIMEOUT:-300}"

START_BACKEND=1
START_FRONTEND=1
RUN_CHECKS=1
STOP_EXISTING=0
STOP_ONLY=0

usage() {
  cat <<'EOF'
Usage: scripts/start_app.sh [options]

Starts the EvoAge backend and frontend in the background, then prints URLs.

Options:
  --backend-only        Start only the backend.
  --frontend-only       Start only the frontend.
  --stop                Stop app processes previously started by this script.
  --restart             Stop existing app processes started by this script first.
  --no-check            Skip URL reachability checks after starting.
  -h, --help            Show this help.

Environment variables:
  BACKEND_ENV_NAME      Backend conda env name. Default: evoage_backend
  FRONTEND_ENV_NAME     Frontend conda env name. Default: evoage_frontend
  BACKEND_HOST          Backend bind host. Default: 0.0.0.0
  BACKEND_PORT          Backend port. Default: port from API_BASE/API_BASE_URL, else 1026
  FRONTEND_HOST         Frontend bind host. Default: 0.0.0.0
  FRONTEND_PORT         Frontend port. Default: port from FRONTEND_URL, else 8501
  BACKEND_PUBLIC_URL    URL printed/checked for backend. Default: Frontend/.env API_BASE_URL,
                        then Backend/.env API_BASE, then http://localhost:BACKEND_PORT
  FRONTEND_PUBLIC_URL   URL printed/checked for frontend. Default: Backend/.env FRONTEND_URL,
                        then http://localhost:FRONTEND_PORT
  BACKEND_LOCAL_URL     Local fallback URL printed/checked. Default: http://localhost:BACKEND_PORT
  FRONTEND_LOCAL_URL    Local fallback URL printed/checked. Default: http://localhost:FRONTEND_PORT
EOF
}

log() { printf '\n[%s] %s\n' "$1" "$2"; }
info() { log INFO "$1"; }
warn() { log WARN "$1"; }
fail() { log ERROR "$1"; exit 1; }

have() {
  command -v "$1" >/dev/null 2>&1
}

require_dir() {
  [[ -d "$1" ]] || fail "Required directory missing: $1"
}

env_file_value() {
  local file="$1"
  local key="$2"

  [[ -f "$file" ]] || return 0
  awk -v key="$key" '
    BEGIN { FS = "=" }
    $0 ~ "^[[:space:]]*" key "[[:space:]]*=" {
      sub(/^[^=]*=/, "")
      print
    }
  ' "$file" | tail -n 1 | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//"
}

looks_unfilled() {
  local value="$1"
  [[ -z "$value" ]] && return 0
  [[ "$value" == *"YOUR_"* ]] && return 0
  [[ "$value" == *"SERVER_IP"* ]] && return 0
  [[ "$value" == *"SERVER_IP_OR_DOMAIN"* ]] && return 0
  [[ "$value" == *"/absolute/path"* ]] && return 0
  [[ "$value" == *"/path/to"* ]] && return 0
  [[ "$value" == *"replace-with"* ]] && return 0
  [[ "$value" == *"localhost:"* ]] && return 1
  [[ "$value" == "change-me" ]] && return 0
  return 1
}

url_port_or_default() {
  local url="$1"
  local default_port="$2"
  local without_scheme
  local host_port

  if looks_unfilled "$url"; then
    printf '%s\n' "$default_port"
    return
  fi

  without_scheme="${url#*://}"
  host_port="${without_scheme%%/*}"
  if [[ "$host_port" =~ :([0-9]+)$ ]]; then
    printf '%s\n' "${BASH_REMATCH[1]}"
  else
    printf '%s\n' "$default_port"
  fi
}

is_local_url() {
  local url="$1"
  [[ "$url" =~ ^https?://(localhost|127\.0\.0\.1|0\.0\.0\.0)(:|/|$) ]]
}

choose_public_url() {
  local candidate
  local first_filled=""

  for candidate in "$@"; do
    if looks_unfilled "$candidate"; then
      continue
    fi
    if [[ -z "$first_filled" ]]; then
      first_filled="$candidate"
    fi
    if ! is_local_url "$candidate"; then
      printf '%s\n' "$candidate"
      return
    fi
  done

  printf '%s\n' "$first_filled"
}

hydrate_runtime_config() {
  local backend_url_from_frontend_env
  local backend_url_from_backend_env
  local frontend_url_from_backend_env
  local selected_backend_url
  local selected_frontend_url

  backend_url_from_frontend_env="$(env_file_value "$FRONTEND_DIR/.env" API_BASE_URL)"
  backend_url_from_backend_env="$(env_file_value "$BACKEND_DIR/.env" API_BASE)"
  frontend_url_from_backend_env="$(env_file_value "$BACKEND_DIR/.env" FRONTEND_URL)"

  selected_backend_url="$(choose_public_url "$backend_url_from_frontend_env" "$backend_url_from_backend_env")"
  selected_frontend_url="$(choose_public_url "$frontend_url_from_backend_env")"

  BACKEND_PORT="${BACKEND_PORT:-$(url_port_or_default "$selected_backend_url" 1026)}"
  FRONTEND_PORT="${FRONTEND_PORT:-$(url_port_or_default "$selected_frontend_url" 8501)}"

  BACKEND_HOST="${BACKEND_HOST:-0.0.0.0}"
  FRONTEND_HOST="${FRONTEND_HOST:-0.0.0.0}"

  if [[ -z "$BACKEND_PUBLIC_URL" ]]; then
    if looks_unfilled "$selected_backend_url"; then
      BACKEND_PUBLIC_URL="http://localhost:${BACKEND_PORT}"
    else
      BACKEND_PUBLIC_URL="$selected_backend_url"
    fi
  fi

  if [[ -z "$FRONTEND_PUBLIC_URL" ]]; then
    if looks_unfilled "$selected_frontend_url"; then
      FRONTEND_PUBLIC_URL="http://localhost:${FRONTEND_PORT}"
    else
      FRONTEND_PUBLIC_URL="$selected_frontend_url"
    fi
  fi

  BACKEND_LOCAL_URL="${BACKEND_LOCAL_URL:-http://localhost:${BACKEND_PORT}}"
  FRONTEND_LOCAL_URL="${FRONTEND_LOCAL_URL:-http://localhost:${FRONTEND_PORT}}"
}

resolve_backend_env_path() {
  local value="$1"
  local root_dir_path

  root_dir_path="$(env_file_value "$BACKEND_DIR/.env" ROOT_DIR_PATH)"
  value="${value//\$\{ROOT_DIR_PATH\}/$root_dir_path}"
  value="${value//\$ROOT_DIR_PATH/$root_dir_path}"

  if [[ -n "$value" && "$value" != /* ]]; then
    value="$BACKEND_DIR/$value"
  fi
  if [[ "$value" != "/" ]]; then
    value="${value%/}"
  fi

  printf '%s\n' "$value"
}

backend_env_path_value() {
  local key="$1"
  resolve_backend_env_path "$(env_file_value "$BACKEND_DIR/.env" "$key")"
}

check_required_file() {
  local label="$1"
  local path="$2"

  if looks_unfilled "$path"; then
    warn "$label is missing or still a placeholder in Backend/.env"
    return 1
  fi
  if [[ ! -f "$path" ]]; then
    warn "$label not found: $path"
    return 1
  fi
  return 0
}

check_required_dir() {
  local label="$1"
  local path="$2"

  if looks_unfilled "$path"; then
    warn "$label is missing or still a placeholder in Backend/.env"
    return 1
  fi
  if [[ ! -d "$path" ]]; then
    warn "$label not found: $path"
    return 1
  fi
  return 0
}

check_backend_model_artifacts() {
  local missing=0
  local model_path
  local ent_dict_path
  local rel_dict_path
  local node_mappings_path
  local dummy_head_path
  local dummy_rel_path

  [[ -f "$BACKEND_DIR/.env" ]] || fail "Backend/.env is missing. Create it from Backend/.env.example and fill required values."

  model_path="$(backend_env_path_value MODEL_PATH)"
  ent_dict_path="$(backend_env_path_value ENT_DICT_PATH)"
  rel_dict_path="$(backend_env_path_value REL_DICT_PATH)"
  node_mappings_path="$(backend_env_path_value NODE_MAPPINGS_PATH)"
  dummy_head_path="$(backend_env_path_value DGLKE_DUMMY_HEAD_LIST)"
  dummy_rel_path="$(backend_env_path_value DGLKE_DUMMY_REL_LIST)"

  info "Checking backend DGL-EvoKG model/data files"
  check_required_dir "MODEL_PATH" "$model_path" || missing=1
  check_required_file "MODEL_PATH/config.json" "$model_path/config.json" || missing=1
  check_required_file "ENT_DICT_PATH" "$ent_dict_path" || missing=1
  check_required_file "REL_DICT_PATH" "$rel_dict_path" || missing=1
  check_required_file "NODE_MAPPINGS_PATH" "$node_mappings_path" || missing=1
  check_required_file "DGLKE_DUMMY_HEAD_LIST" "$dummy_head_path" || missing=1
  check_required_file "DGLKE_DUMMY_REL_LIST" "$dummy_rel_path" || missing=1

  if [[ "$missing" == "1" ]]; then
    warn "Backend was not started because required DGL-EvoKG model/data artifacts are missing."
    warn "Download or copy the DGL-EvoKG artifacts from: $DGL_DATASET_URL"
    warn "Then set Backend/.env ROOT_DIR_PATH to the directory containing Model/, Node_Mapping/, and Dummy_Input/."
    warn "After fixing the paths, rerun: bash scripts/start_app.sh --restart"
    fail "Backend model/data preflight failed."
  fi

  info "Backend DGL-EvoKG model/data file check passed."
}

check_blackwell_cuda_compatibility() {
  local gpu_info
  local gpu_name=""
  local capability=""
  local arch_list=""

  [[ "$START_BACKEND" == "1" ]] || return 0
  have conda || return 0
  conda_env_exists "$BACKEND_ENV_NAME" || return 0

  if have nvidia-smi; then
    gpu_info="$(nvidia-smi --query-gpu=name,compute_cap --format=csv,noheader 2>/dev/null | head -n 1 || true)"
    if [[ -n "$gpu_info" ]]; then
      gpu_name="${gpu_info%%,*}"
      capability="${gpu_info#*,}"
      gpu_name="$(printf '%s' "$gpu_name" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
      capability="$(printf '%s' "$capability" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
    fi
  fi

  if [[ -z "$capability" ]]; then
    gpu_info="$(conda run -n "$BACKEND_ENV_NAME" python - <<'PYGPU' 2>/dev/null || true
import torch

try:
    if not torch.cuda.is_available():
        raise SystemExit
    major, minor = torch.cuda.get_device_capability(0)
    print("|".join([torch.cuda.get_device_name(0), f"{major}.{minor}"]))
except Exception:
    pass
PYGPU
)"
    if [[ -n "$gpu_info" ]]; then
      IFS='|' read -r gpu_name capability <<< "$gpu_info"
    fi
  fi

  arch_list="$(conda run -n "$BACKEND_ENV_NAME" python - <<'PYARCH' 2>/dev/null || true
import torch

try:
    print(",".join(torch.cuda.get_arch_list()))
except Exception:
    pass
PYARCH
)"

  if [[ "$capability" == 12.* && "$arch_list" != *"sm_120"* ]]; then
    warn "Detected a Blackwell GPU ($gpu_name, compute capability $capability), but the backend PyTorch build does not include sm_120 CUDA kernels."
    warn "Backend startup may fail with: CUDA error: no kernel image is available for execution on the device."
    warn "This is only needed for Blackwell GPUs. Install a CUDA 12.8+ PyTorch build in '$BACKEND_ENV_NAME', then rerun: bash scripts/start_app.sh --restart"
    warn "Example: conda run -n $BACKEND_ENV_NAME python -m pip install --upgrade --force-reinstall torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128"
  fi
}


parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --backend-only)
        START_BACKEND=1
        START_FRONTEND=0
        ;;
      --frontend-only)
        START_BACKEND=0
        START_FRONTEND=1
        ;;
      --stop) STOP_ONLY=1 ;;
      --restart) STOP_EXISTING=1 ;;
      --no-check) RUN_CHECKS=0 ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        fail "Unknown option: $1"
        ;;
    esac
    shift
  done
}

conda_env_exists() {
  local env_name="$1"
  conda env list | awk '{print $1}' | grep -qx "$env_name"
}

is_running_pid() {
  local pid_file="$1"
  [[ -f "$pid_file" ]] || return 1

  local pid
  pid="$(<"$pid_file")"
  [[ "$pid" =~ ^[0-9]+$ ]] || return 1
  kill -0 "$pid" >/dev/null 2>&1
}

stop_from_pid_file() {
  local label="$1"
  local pid_file="$2"

  if is_running_pid "$pid_file"; then
    local pid
    pid="$(<"$pid_file")"
    info "Stopping existing $label process: PID $pid"
    kill "$pid" >/dev/null 2>&1 || true
    sleep 2
    if kill -0 "$pid" >/dev/null 2>&1; then
      warn "$label process did not stop quickly; leaving it running. Stop PID $pid manually if needed."
    else
      rm -f "$pid_file"
    fi
  fi
}

start_backend() {
  local pid_file="$RUN_DIR/backend.pid"
  local log_file="$LOG_DIR/backend.log"

  if is_running_pid "$pid_file"; then
    info "Backend already appears to be running: PID $(<"$pid_file")"
    return
  fi

  check_backend_model_artifacts

  info "Starting backend on $BACKEND_PUBLIC_URL"
  info "Backend log: $log_file"
  nohup conda run -n "$BACKEND_ENV_NAME" bash -lc \
    "cd '$BACKEND_DIR' && poetry run gunicorn -w '$BACKEND_WORKERS' --timeout '$BACKEND_TIMEOUT' -k uvicorn.workers.UvicornWorker app.main:app --bind '$BACKEND_HOST:$BACKEND_PORT'" \
    >"$log_file" 2>&1 &
  printf '%s\n' "$!" > "$pid_file"
}

start_frontend() {
  local pid_file="$RUN_DIR/frontend.pid"
  local log_file="$LOG_DIR/frontend.log"

  if is_running_pid "$pid_file"; then
    info "Frontend already appears to be running: PID $(<"$pid_file")"
    return
  fi

  info "Starting frontend on $FRONTEND_PUBLIC_URL"
  info "Frontend log: $log_file"
  nohup conda run -n "$FRONTEND_ENV_NAME" bash -lc \
    "cd '$FRONTEND_DIR' && streamlit run streamlit_app.py --server.port='$FRONTEND_PORT' --server.address='$FRONTEND_HOST' --server.enableCORS=false" \
    >"$log_file" 2>&1 &
  printf '%s\n' "$!" > "$pid_file"
}

check_url() {
  local label="$1"
  local url="$2"
  local retries="${3:-20}"

  if ! have curl; then
    warn "curl not found; skipping $label URL check."
    return
  fi

  info "Checking $label URL: $url"
  for _ in $(seq 1 "$retries"); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      info "$label is reachable: $url"
      return 0
    fi
    sleep 2
  done

  warn "$label was not reachable yet: $url"
  return 1
}

check_url_with_local_fallback() {
  local label="$1"
  local public_url="$2"
  local local_url="$3"

  if check_url "$label" "$public_url"; then
    return 0
  fi

  if [[ "$public_url" == "$local_url" ]]; then
    return 1
  fi

  info "Checking $label localhost fallback: $local_url"
  if curl -fsS "$local_url" >/dev/null 2>&1; then
    warn "$label is running locally, but the public/server URL is not reachable."
    warn "Check server IP/DNS, firewall/security-group rules, and whether the port is open from your client machine."
    return 0
  fi

  warn "$label is not reachable on localhost either. Check the log file for startup errors."
  return 1
}

main() {
  parse_args "$@"

  require_dir "$BACKEND_DIR"
  require_dir "$FRONTEND_DIR"
  hydrate_runtime_config
  mkdir -p "$RUN_DIR" "$LOG_DIR"

  if [[ "$STOP_ONLY" == "1" ]]; then
    [[ "$START_BACKEND" == "1" ]] && stop_from_pid_file "backend" "$RUN_DIR/backend.pid"
    [[ "$START_FRONTEND" == "1" ]] && stop_from_pid_file "frontend" "$RUN_DIR/frontend.pid"
    info "Stop command complete."
    exit 0
  fi

  have conda || fail "conda is required. Run scripts/setup.sh --all first."

  if [[ "$START_BACKEND" == "1" ]] && ! conda_env_exists "$BACKEND_ENV_NAME"; then
    fail "Backend conda env not found: $BACKEND_ENV_NAME. Run scripts/setup.sh --all first."
  fi
  if [[ "$START_FRONTEND" == "1" ]] && ! conda_env_exists "$FRONTEND_ENV_NAME"; then
    fail "Frontend conda env not found: $FRONTEND_ENV_NAME. Run scripts/setup.sh --all first."
  fi

  if [[ "$STOP_EXISTING" == "1" ]]; then
    [[ "$START_BACKEND" == "1" ]] && stop_from_pid_file "backend" "$RUN_DIR/backend.pid"
    [[ "$START_FRONTEND" == "1" ]] && stop_from_pid_file "frontend" "$RUN_DIR/frontend.pid"
  fi

  [[ "$START_BACKEND" == "1" ]] && check_blackwell_cuda_compatibility
  [[ "$START_BACKEND" == "1" ]] && start_backend
  [[ "$START_FRONTEND" == "1" ]] && start_frontend

  info "App start commands have been issued."
  info "Backend public URL:   $BACKEND_PUBLIC_URL"
  info "Backend local URL:    $BACKEND_LOCAL_URL"
  info "Frontend public URL:  $FRONTEND_PUBLIC_URL"
  info "Frontend local URL:   $FRONTEND_LOCAL_URL"
  info "Logs: $LOG_DIR"
  info "PID files: $RUN_DIR"

  if [[ "$RUN_CHECKS" == "1" ]]; then
    [[ "$START_BACKEND" == "1" ]] && check_url_with_local_fallback "Backend" "$BACKEND_PUBLIC_URL/" "$BACKEND_LOCAL_URL/"
    [[ "$START_FRONTEND" == "1" ]] && check_url_with_local_fallback "Frontend" "$FRONTEND_PUBLIC_URL/" "$FRONTEND_LOCAL_URL/"
  fi
}

main "$@"
