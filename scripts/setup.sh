#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/Backend"
FRONTEND_DIR="$ROOT_DIR/Frontend"

BACKEND_ENV_NAME="${BACKEND_ENV_NAME:-evoage_backend}"
FRONTEND_ENV_NAME="${FRONTEND_ENV_NAME:-evoage_frontend}"
NEO4J_APOC_VERSION="${NEO4J_APOC_VERSION:-5.26.14}"

INSTALL_BACKEND=0
INSTALL_FRONTEND=0
INSTALL_SYSTEM=0
INSTALL_NEO4J=0
INSTALL_REDIS=0
RESTORE_NEO4J=0
RUN_CHECKS=1
DRY_RUN=0
START_SERVICES=0
NEO4J_DUMP_PATH=""
CHECK_ONLY=0
ENV_MISSING=0

BACKEND_REQUIRED_KEYS=(
  NEO4J_URI NEO4J_USERNAME NEO4J_PASSWORD
  REDIS_HOST REDIS_PORT REDIS_PASSWORD
  JWT_SECRET_KEY
  NODE_MAPPINGS_PATH MODEL_PATH ENT_DICT_PATH REL_DICT_PATH
  DGLKE_INPUT_DIR DGLKE_DUMMY_HEAD_LIST DGLKE_DUMMY_REL_LIST
  API_BASE CUTOFF_FILE_NAME HYPOTHESIS_ENT_DICT_PATH
  HYPOTHESIS_TRIPLE_OUTPUT_DIR EDGE_TENSOR_PATH GEMINI_API_KEY
)

FRONTEND_REQUIRED_KEYS=(
  API_BASE_URL
)

usage() {
  cat <<'EOF'
Usage: scripts/setup.sh [options]

Automates EvoAge setup while keeping verification checks visible.

Common flows:
  scripts/setup.sh --all
  scripts/setup.sh --backend --frontend
  scripts/setup.sh --system --redis --neo4j --neo4j-dump /path/to/neo4j.dump
  scripts/setup.sh --check-only

Options:
  --all                 Install backend and frontend Python dependencies.
  --backend             Set up Backend conda env, deps, DGL-KE, and env template.
  --frontend            Set up Frontend conda env, deps, and env template.
  --system              Install apt-level prerequisites: Java, wget, curl, gpg.
  --neo4j               Install Neo4j 5 and APOC. Requires sudo on Debian/Ubuntu.
  --redis               Install Redis server. Requires sudo on Debian/Ubuntu.
  --neo4j-dump PATH     Restore a Neo4j dump after Neo4j install/start.
  --start-services      Enable/start Redis and Neo4j where installed.
  --check-only          Run verification checks without installing anything.
  --dry-run             Print commands instead of executing install commands.
  --skip-checks         Skip final verification checks.
  -h, --help            Show this help.

Environment variables:
  BACKEND_ENV_NAME      Backend conda env name. Default: evoage_backend
  FRONTEND_ENV_NAME     Frontend conda env name. Default: evoage_frontend
  NEO4J_PASSWORD        Initial Neo4j password and check password.
  REDIS_PASSWORD        Redis password to configure/check.
EOF
}

log() { printf '\n[%s] %s\n' "$1" "$2"; }
info() { log INFO "$1"; }
warn() { log WARN "$1"; }
fail() { log ERROR "$1"; exit 1; }

format_duration() {
  local total_seconds="$1"
  local minutes=$((total_seconds / 60))
  local seconds=$((total_seconds % 60))

  if [[ "$minutes" -gt 0 ]]; then
    printf '%dm %02ds' "$minutes" "$seconds"
  else
    printf '%ds' "$seconds"
  fi
}

run_step() {
  local label="$1"
  local estimate="$2"
  shift 2

  info "$label"
  info "Estimated time: $estimate"
  info "Started: $(date '+%Y-%m-%d %H:%M:%S')"

  local start_time
  start_time="$(date +%s)"
  set +e
  "$@"
  local exit_code=$?
  set -e
  local end_time
  end_time="$(date +%s)"
  local duration
  duration="$(format_duration "$((end_time - start_time))")"

  if [[ "$exit_code" -ne 0 ]]; then
    fail "$label failed after $duration"
  fi

  info "Finished: $label"
  info "Duration: $duration"
}

run() {
  if [[ "$DRY_RUN" == "1" ]]; then
    printf '[DRY-RUN] %q' "$1"
    shift || true
    for arg in "$@"; do
      printf ' %q' "$arg"
    done
    printf '\n'
  else
    "$@"
  fi
}

have() {
  command -v "$1" >/dev/null 2>&1
}

require_file() {
  [[ -f "$1" ]] || fail "Required file missing: $1"
}

require_dir() {
  [[ -d "$1" ]] || fail "Required directory missing: $1"
}

is_debian_like() {
  [[ -f /etc/os-release ]] && grep -Eq 'ID(_LIKE)?=.*(debian|ubuntu)' /etc/os-release
}

sudo_cmd() {
  if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
    run "$@"
  else
    have sudo || fail "sudo is required for system package installation."
    run sudo "$@"
  fi
}

sudo_append_line() {
  local line="$1"
  local file="$2"

  if [[ "$DRY_RUN" == "1" ]]; then
    printf '[DRY-RUN] append %q to %q\n' "$line" "$file"
  elif [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
    printf '%s\n' "$line" >> "$file"
  else
    printf '%s\n' "$line" | sudo tee -a "$file" >/dev/null
  fi
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --all)
        INSTALL_BACKEND=1
        INSTALL_FRONTEND=1
        ;;
      --backend) INSTALL_BACKEND=1 ;;
      --frontend) INSTALL_FRONTEND=1 ;;
      --system) INSTALL_SYSTEM=1 ;;
      --neo4j)
        INSTALL_SYSTEM=1
        INSTALL_NEO4J=1
        ;;
      --redis)
        INSTALL_SYSTEM=1
        INSTALL_REDIS=1
        ;;
      --neo4j-dump)
        [[ $# -ge 2 ]] || fail "--neo4j-dump requires a path."
        NEO4J_DUMP_PATH="$2"
        RESTORE_NEO4J=1
        shift
        ;;
      --start-services) START_SERVICES=1 ;;
      --check-only)
        CHECK_ONLY=1
        INSTALL_BACKEND=0
        INSTALL_FRONTEND=0
        INSTALL_SYSTEM=0
        INSTALL_NEO4J=0
        INSTALL_REDIS=0
        RESTORE_NEO4J=0
        ;;
      --dry-run) DRY_RUN=1 ;;
      --skip-checks) RUN_CHECKS=0 ;;
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

copy_env_template() {
  local component_dir="$1"
  local env_file="$component_dir/.env"
  local template_file="$component_dir/.env.example"

  require_file "$template_file"
  if [[ -f "$env_file" ]]; then
    info "Keeping existing $env_file"
  else
    info "Creating $env_file from .env.example"
    run cp "$template_file" "$env_file"
  fi
}

env_value() {
  local file="$1"
  local key="$2"

  [[ -f "$file" ]] || return 0
  awk -v key="$key" '
    BEGIN { FS = "=" }
    $0 ~ "^[[:space:]]*" key "[[:space:]]*=" {
      sub(/^[^=]*=/, "")
      print
    }
  ' "$file" 2>/dev/null | tail -n 1 | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//" || true
}

looks_unfilled() {
  local value="$1"
  [[ -z "$value" ]] && return 0
  [[ "$value" == *"YOUR_"* ]] && return 0
  [[ "$value" == *"SERVER_IP"* ]] && return 0
  [[ "$value" == *"/absolute/path"* ]] && return 0
  [[ "$value" == *"/path/to"* ]] && return 0
  [[ "$value" == *"replace-with"* ]] && return 0
  [[ "$value" == "change-me" ]] && return 0
  return 1
}

validate_env_file() {
  local file="$1"
  local strict="$2"
  shift 2
  local missing_keys=()

  if [[ ! -f "$file" ]]; then
    if [[ "$strict" == "1" ]]; then
      printf '[ERROR] Missing env file: %s. Run scripts/setup.sh --all first, then fill it.\n' "$file" >&2
      ENV_MISSING=1
      return 0
    fi
    warn "Missing env file: $file"
    ENV_MISSING=1
    return
  fi

  for key in "$@"; do
    local value
    value="$(env_value "$file" "$key")"
    if looks_unfilled "$value"; then
      missing_keys+=("$key")
      ENV_MISSING=1
    fi
  done

  if [[ "${#missing_keys[@]}" -gt 0 ]]; then
    if [[ "$strict" == "1" ]]; then
      printf '[ERROR] %s has missing or placeholder values: %s\n' "$file" "${missing_keys[*]}" >&2
    else
      warn "$file has values to fill later: ${missing_keys[*]}"
    fi
  fi
}

env_file_ready() {
  local file="$1"
  shift

  [[ -f "$file" ]] || return 1
  for key in "$@"; do
    local value
    value="$(env_value "$file" "$key")"
    if looks_unfilled "$value"; then
      return 1
    fi
  done
  return 0
}

show_first_run_guidance() {
  if [[ "$CHECK_ONLY" == "1" || "$ENV_MISSING" != "1" ]]; then
    return
  fi

  warn "Some .env values are still placeholders. This is normal after the first app dependency setup."
  info "Next steps:"
  printf '  1. Download the Neo4j dump: bash scripts/download_neo4j_dump.sh\n'
  printf '  2. Fill all required values in Backend/.env and Frontend/.env.\n'
  printf '  3. Configure services: bash scripts/setup_services.sh\n'
  printf '  4. Re-run strict verification: bash scripts/setup.sh --check-only\n'
  printf '  5. Start the app: bash scripts/start_app.sh\n'
}

quiet_check() {
  local label="$1"
  shift

  if [[ "$DRY_RUN" == "1" ]]; then
    printf '[DRY-RUN] quiet check: %s\n' "$label"
    return 0
  fi

  local output
  set +e
  output="$("$@" 2>&1)"
  local exit_code=$?
  set -e

  if [[ "$exit_code" == "0" ]]; then
    [[ -n "$output" ]] && printf '%s\n' "$output"
    return 0
  fi

  warn "$label failed."
  if [[ "${DEBUG_CHECKS:-0}" == "1" ]]; then
    printf '%s\n' "$output"
  else
    warn "Set DEBUG_CHECKS=1 and rerun the command to print the full underlying error."
  fi
  return 0
}

validate_env_files() {
  local strict="$1"
  ENV_MISSING=0

  info "Checking required .env values"
  validate_env_file "$BACKEND_DIR/.env" "$strict" "${BACKEND_REQUIRED_KEYS[@]}"
  validate_env_file "$FRONTEND_DIR/.env" "$strict" "${FRONTEND_REQUIRED_KEYS[@]}"

  if [[ "$strict" == "1" && "$ENV_MISSING" == "1" ]]; then
    fail "Fill required .env values before running final checks."
  fi
}

install_system_packages() {
  info "Checking operating system prerequisites"
  is_debian_like || fail "Automated system install currently supports Debian/Ubuntu only. Use docs for manual setup on other systems."

  sudo_cmd apt-get update
  sudo_cmd apt-get install -y openjdk-17-jdk wget curl gnupg ca-certificates

  if [[ "$INSTALL_REDIS" == "1" ]]; then
    info "Installing Redis"
    sudo_cmd apt-get install -y redis-server
    if [[ -n "${REDIS_PASSWORD:-}" ]]; then
      info "Configuring Redis password"
      sudo_cmd sed -i "s/^# requirepass .*/requirepass ${REDIS_PASSWORD}/" /etc/redis/redis.conf
    else
      warn "REDIS_PASSWORD not set; Redis will be installed without password changes."
    fi
    if [[ "$START_SERVICES" == "1" ]]; then
      sudo_cmd systemctl enable redis-server
      sudo_cmd systemctl restart redis-server
    fi
  fi

  if [[ "$INSTALL_NEO4J" == "1" ]]; then
    info "Installing Neo4j 5"
    if [[ ! -f /etc/apt/sources.list.d/neo4j.list ]]; then
      run wget -O /tmp/neo4j.gpg.key https://debian.neo4j.com/neotechnology.gpg.key
      sudo_cmd gpg --dearmor -o /usr/share/keyrings/neo4j.gpg /tmp/neo4j.gpg.key
      if [[ "$DRY_RUN" == "1" ]]; then
        printf '[DRY-RUN] write Neo4j apt source to /etc/apt/sources.list.d/neo4j.list\n'
      elif [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
        printf 'deb [signed-by=/usr/share/keyrings/neo4j.gpg] https://debian.neo4j.com stable 5\n' > /etc/apt/sources.list.d/neo4j.list
      else
        printf 'deb [signed-by=/usr/share/keyrings/neo4j.gpg] https://debian.neo4j.com stable 5\n' | sudo tee /etc/apt/sources.list.d/neo4j.list >/dev/null
      fi
      sudo_cmd apt-get update
    fi
    sudo_cmd apt-get install -y neo4j

    if [[ -n "${NEO4J_PASSWORD:-}" ]]; then
      info "Setting Neo4j initial password if database has not been initialized"
      sudo_cmd neo4j-admin dbms set-initial-password "$NEO4J_PASSWORD" || warn "Neo4j password may already be initialized; continuing."
    else
      warn "NEO4J_PASSWORD not set; skipping initial password setup."
    fi

    info "Installing APOC core plugin"
    sudo_cmd mkdir -p /var/lib/neo4j/plugins
    sudo_cmd wget -O "/var/lib/neo4j/plugins/apoc-${NEO4J_APOC_VERSION}-core.jar" "https://github.com/neo4j/apoc/releases/download/${NEO4J_APOC_VERSION}/apoc-${NEO4J_APOC_VERSION}-core.jar"
    sudo_cmd chown neo4j:neo4j "/var/lib/neo4j/plugins/apoc-${NEO4J_APOC_VERSION}-core.jar"
    if grep -q '^#\?dbms.security.procedures.unrestricted=' /etc/neo4j/neo4j.conf; then
      sudo_cmd sed -i 's/^#\?dbms.security.procedures.unrestricted=.*/dbms.security.procedures.unrestricted=apoc.*/' /etc/neo4j/neo4j.conf
    else
      sudo_append_line "dbms.security.procedures.unrestricted=apoc.*" /etc/neo4j/neo4j.conf
    fi
    if ! grep -q '^dbms.security.procedures.allowlist=apoc.*' /etc/neo4j/neo4j.conf; then
      sudo_append_line "dbms.security.procedures.allowlist=apoc.*" /etc/neo4j/neo4j.conf
    fi

    if [[ "$RESTORE_NEO4J" == "1" ]]; then
      if [[ "$DRY_RUN" != "1" ]]; then
        require_file "$NEO4J_DUMP_PATH"
      fi
      info "Restoring Neo4j database from $NEO4J_DUMP_PATH"
      sudo_cmd systemctl stop neo4j || true
      sudo_cmd mkdir -p /var/lib/neo4j/import
      sudo_cmd cp "$NEO4J_DUMP_PATH" /var/lib/neo4j/import/neo4j.dump
      sudo_cmd neo4j-admin database load neo4j --from-path=/var/lib/neo4j/import --overwrite-destination=true
    fi

    if [[ "$START_SERVICES" == "1" ]]; then
      sudo_cmd systemctl enable neo4j
      sudo_cmd systemctl restart neo4j
    fi
  fi
}

setup_conda_env() {
  local env_name="$1"
  local python_version="$2"

  if ! have conda; then
    if [[ "$DRY_RUN" == "1" ]]; then
      info "Would require conda to create/use env: $env_name"
      return
    fi
    fail "conda is required for automated Python environment setup."
  fi
  if conda env list | awk '{print $1}' | grep -qx "$env_name"; then
    info "Conda env exists: $env_name"
  else
    info "Creating conda env: $env_name"
    run conda create -n "$env_name" "python=$python_version" -y
  fi
}

conda_run() {
  local env_name="$1"
  shift
  if ! have conda && [[ "$DRY_RUN" == "1" ]]; then
    printf '[DRY-RUN] conda run -n %q' "$env_name"
    for arg in "$@"; do
      printf ' %q' "$arg"
    done
    printf '\n'
    return
  fi
  run conda run -n "$env_name" "$@"
}

setup_backend() {
  info "Setting up backend"
  info "Backend setup can take 20-75+ minutes on a fresh machine. The largest step is pip installing PyTorch/CUDA, DGL, PyKEEN, and scientific Python packages."
  require_dir "$BACKEND_DIR"
  require_file "$BACKEND_DIR/requirements.txt"
  require_dir "$BACKEND_DIR/dgl-ke/python"

  run_step "Backend [1/7] Preparing Backend/.env" "less than 1 minute" \
    copy_env_template "$BACKEND_DIR"
  run_step "Backend [2/7] Creating/checking conda env: $BACKEND_ENV_NAME" "1-5 minutes if env is new" \
    setup_conda_env "$BACKEND_ENV_NAME" "3.11"

  info "pip and conda will print their own package download/progress output below."
  run_step "Backend [3/7] Upgrading pip" "1-3 minutes" \
    conda_run "$BACKEND_ENV_NAME" python -m pip install --progress-bar on --upgrade pip
  run_step "Backend [4/7] Installing backend Python requirements" "15-60+ minutes on first run" \
    conda_run "$BACKEND_ENV_NAME" python -m pip install --progress-bar on --extra-index-url https://download.pytorch.org/whl/cu121 -r "$BACKEND_DIR/requirements.txt"
  run_step "Backend [5/7] Installing local DGL-KE package" "1-5 minutes" \
    conda_run "$BACKEND_ENV_NAME" python -m pip install --progress-bar on -e "$BACKEND_DIR/dgl-ke/python"
  run_step "Backend [6/7] Installing Poetry" "1-5 minutes" \
    conda_run "$BACKEND_ENV_NAME" python -m pip install --progress-bar on poetry
  run_step "Backend [7/7] Installing Poetry project dependencies" "2-15 minutes" \
    conda_run "$BACKEND_ENV_NAME" poetry -C "$BACKEND_DIR" install
}

setup_frontend() {
  info "Setting up frontend"
  info "Frontend setup usually takes 5-25 minutes on a fresh machine, depending on network speed."
  require_dir "$FRONTEND_DIR"
  require_file "$FRONTEND_DIR/requirements.txt"

  run_step "Frontend [1/4] Preparing Frontend/.env" "less than 1 minute" \
    copy_env_template "$FRONTEND_DIR"
  run_step "Frontend [2/4] Creating/checking conda env: $FRONTEND_ENV_NAME" "1-5 minutes if env is new" \
    setup_conda_env "$FRONTEND_ENV_NAME" "3.11"

  info "pip and conda will print their own package download/progress output below."
  run_step "Frontend [3/4] Upgrading pip" "1-3 minutes" \
    conda_run "$FRONTEND_ENV_NAME" python -m pip install --progress-bar on --upgrade pip
  run_step "Frontend [4/4] Installing frontend Python requirements" "5-20 minutes on first run" \
    conda_run "$FRONTEND_ENV_NAME" python -m pip install --progress-bar on -r "$FRONTEND_DIR/requirements.txt"
}

check_python_env() {
  local env_name="$1"
  local label="$2"
  if have conda && conda env list | awk '{print $1}' | grep -qx "$env_name"; then
    info "Checking $label Python environment"
    conda_run "$env_name" python --version
  else
    warn "$label conda env not found: $env_name"
  fi
}

run_checks() {
  info "Running setup verification checks"

  if [[ "$CHECK_ONLY" == "1" ]]; then
    validate_env_files 1
  else
    validate_env_files 0
  fi
  show_first_run_guidance

  local backend_url
  local frontend_url
  local raw_backend_url
  local raw_frontend_url
  local neo4j_uri_for_check
  local neo4j_username_for_check
  local neo4j_password_for_check
  local redis_password_for_check
  local redis_db_for_check
  local app_urls_not_running=0
  local backend_env_ready=0
  local frontend_env_ready=0

  if env_file_ready "$BACKEND_DIR/.env" "${BACKEND_REQUIRED_KEYS[@]}"; then
    backend_env_ready=1
  fi
  if env_file_ready "$FRONTEND_DIR/.env" "${FRONTEND_REQUIRED_KEYS[@]}"; then
    frontend_env_ready=1
  fi

  raw_backend_url="$(env_value "$FRONTEND_DIR/.env" API_BASE_URL)"
  if looks_unfilled "$raw_backend_url"; then
    raw_backend_url="$(env_value "$BACKEND_DIR/.env" API_BASE)"
  fi
  if looks_unfilled "$raw_backend_url"; then
    backend_url="http://localhost:1026"
    warn "Backend URL is not configured yet; using default for display: $backend_url"
  else
    backend_url="$raw_backend_url"
  fi

  raw_frontend_url="$(env_value "$BACKEND_DIR/.env" FRONTEND_URL)"
  if looks_unfilled "$raw_frontend_url"; then
    frontend_url="http://localhost:8501"
    warn "FRONTEND_URL is not configured yet; using default for display: $frontend_url"
  else
    frontend_url="$raw_frontend_url"
  fi

  neo4j_uri_for_check="${NEO4J_URI:-$(env_value "$BACKEND_DIR/.env" NEO4J_URI)}"
  neo4j_uri_for_check="${neo4j_uri_for_check:-bolt://localhost:7687}"
  neo4j_username_for_check="${NEO4J_USERNAME:-$(env_value "$BACKEND_DIR/.env" NEO4J_USERNAME)}"
  neo4j_username_for_check="${neo4j_username_for_check:-neo4j}"
  neo4j_password_for_check="${NEO4J_PASSWORD:-$(env_value "$BACKEND_DIR/.env" NEO4J_PASSWORD)}"
  redis_password_for_check="${REDIS_PASSWORD:-$(env_value "$BACKEND_DIR/.env" REDIS_PASSWORD)}"
  redis_db_for_check="${REDIS_DB:-$(env_value "$BACKEND_DIR/.env" REDIS_DB)}"
  redis_db_for_check="${redis_db_for_check:-0}"

  info "Backend URL configured for frontend: $backend_url"
  info "Frontend URL configured for backend emails: $frontend_url"

  have python3 && python3 --version || warn "python3 not found on PATH."
  have java && java -version || warn "Java not found on PATH."
  have redis-cli && redis-cli --version || warn "redis-cli not found on PATH."
  have neo4j && neo4j --version || warn "neo4j not found on PATH."
  have cypher-shell && cypher-shell --version || warn "cypher-shell not found on PATH."

  check_python_env "$BACKEND_ENV_NAME" "backend"
  check_python_env "$FRONTEND_ENV_NAME" "frontend"

  if have redis-cli; then
    if looks_unfilled "$redis_password_for_check"; then
      warn "Skipping Redis ping: REDIS_PASSWORD is not configured yet. setup_services.sh will configure Redis and sync Backend/.env."
    else
      info "Checking Redis ping"
      if ! redis-cli -a "$redis_password_for_check" -n "$redis_db_for_check" PING >/dev/null 2>&1; then
        warn "Redis ping failed. If this is the first run, configure services next with scripts/setup_services.sh."
      else
        info "Redis ping succeeded."
      fi
    fi
  fi

  if have cypher-shell; then
    if looks_unfilled "$neo4j_password_for_check"; then
      warn "Skipping Neo4j login: NEO4J_PASSWORD is not configured yet. setup_services.sh will set it and restore the dump."
    else
      info "Checking Neo4j login"
      if ! cypher-shell -a "$neo4j_uri_for_check" -u "$neo4j_username_for_check" -p "$neo4j_password_for_check" "SHOW DATABASES;" >/dev/null 2>&1; then
        warn "Neo4j login failed. If this is the first run, install/configure Neo4j next with scripts/setup_services.sh."
      elif ! cypher-shell -a "$neo4j_uri_for_check" -u "$neo4j_username_for_check" -p "$neo4j_password_for_check" "MATCH (n) RETURN count(n) AS nodeCount;" >/dev/null 2>&1; then
        warn "Neo4j login worked, but node-count check failed. This is expected before restoring the EvoAge dump."
      else
        info "Neo4j login and graph node-count check succeeded."
      fi
    fi
  fi

  if [[ "$CHECK_ONLY" != "1" ]]; then
    info "Skipping backend/frontend URL reachability during initial setup. Run scripts/start_app.sh after .env and services are configured."
  elif have curl; then
    info "Checking backend URL reachability"
    if curl -fsS "$backend_url/" >/dev/null 2>&1; then
      info "Backend URL is reachable: $backend_url"
    else
      app_urls_not_running=1
      info "Backend URL is not reachable yet: $backend_url"
      info "This is expected if you have not started the EvoAge app processes yet."
    fi

    info "Checking frontend URL reachability"
    if curl -fsS "$frontend_url/" >/dev/null 2>&1; then
      info "Frontend URL is reachable: $frontend_url"
    else
      app_urls_not_running=1
      info "Frontend URL is not reachable yet: $frontend_url"
      info "This is expected if you have not started the EvoAge app processes yet."
    fi

    if [[ "$app_urls_not_running" == "1" ]]; then
      info "Next step after successful setup checks: bash scripts/start_app.sh"
      info "For an SSH/server setup, expose the apps with:"
      info "BACKEND_HOST=0.0.0.0 FRONTEND_HOST=0.0.0.0 BACKEND_PUBLIC_URL=$backend_url FRONTEND_PUBLIC_URL=$frontend_url bash scripts/start_app.sh"
    fi
  else
    warn "curl not found; skipping backend/frontend URL reachability checks."
  fi

  if [[ -f "$BACKEND_DIR/.env" ]] && have conda && conda env list | awk '{print $1}' | grep -qx "$BACKEND_ENV_NAME"; then
    if [[ "$backend_env_ready" != "1" ]]; then
      warn "Skipping backend config import check until Backend/.env placeholders are filled."
    else
      info "Checking backend imports and configuration"
      quiet_check "Backend config import check" \
        conda run -n "$BACKEND_ENV_NAME" env PYTHONDONTWRITEBYTECODE=1 bash -lc "cd '$BACKEND_DIR' && python - <<'PY'
from app.utils.environment import CONFIG
print('Backend config loaded')
print(f'Neo4j URI: {CONFIG.NEO4J.URI}')
print(f'Redis: {CONFIG.REDIS.HOST}:{CONFIG.REDIS.PORT}/{CONFIG.REDIS.DB}')
PY"
    fi
  fi

  if [[ -f "$FRONTEND_DIR/.env" ]] && have conda && conda env list | awk '{print $1}' | grep -qx "$FRONTEND_ENV_NAME"; then
    if [[ "$frontend_env_ready" != "1" ]]; then
      warn "Skipping frontend config import check until Frontend/.env placeholders are filled."
    else
      info "Checking frontend imports"
      quiet_check "Frontend import check" \
        conda run -n "$FRONTEND_ENV_NAME" env PYTHONDONTWRITEBYTECODE=1 bash -lc "cd '$FRONTEND_DIR' && python - <<'PY'
import os
from dotenv import load_dotenv
load_dotenv(dotenv_path='.env')
print('Frontend API_BASE_URL=' + os.getenv('API_BASE_URL', 'http://localhost:1026'))
PY"
    fi
  fi

  info "Verification complete"
}

main() {
  parse_args "$@"
  require_dir "$BACKEND_DIR"
  require_dir "$FRONTEND_DIR"

  if [[ "$INSTALL_SYSTEM" == "1" ]]; then
    install_system_packages
  fi
  if [[ "$INSTALL_BACKEND" == "1" ]]; then
    setup_backend
  fi
  if [[ "$INSTALL_FRONTEND" == "1" ]]; then
    setup_frontend
  fi
  if [[ "$RUN_CHECKS" == "1" ]]; then
    run_checks
  fi
}

main "$@"
