#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_ENV="$ROOT_DIR/Backend/.env"
FRONTEND_ENV="$ROOT_DIR/Frontend/.env"

NEO4J_APOC_VERSION="${NEO4J_APOC_VERSION:-5.26.14}"
NEO4J_URI="${NEO4J_URI:-}"
NEO4J_USERNAME="${NEO4J_USERNAME:-}"
NEO4J_PASSWORD="${NEO4J_PASSWORD:-}"
REDIS_HOST="${REDIS_HOST:-}"
REDIS_PORT="${REDIS_PORT:-}"
REDIS_USERNAME="${REDIS_USERNAME:-}"
REDIS_PASSWORD="${REDIS_PASSWORD:-}"
REDIS_DB="${REDIS_DB:-}"
BACKEND_PUBLIC_URL="${BACKEND_PUBLIC_URL:-}"
FRONTEND_PUBLIC_URL="${FRONTEND_PUBLIC_URL:-}"

DUMP_PATH="$ROOT_DIR/data/neo4j/neo4j.dump"
SETUP_NEO4J=1
SETUP_REDIS=1
DRY_RUN=0

usage() {
  cat <<'EOF'
Usage: scripts/setup_services.sh [options]

Installs/configures Neo4j + Redis, restores the EvoAge Neo4j dump, syncs
service connection values into Backend/.env and Frontend/.env, and runs checks.

Run this as a normal user:
  bash scripts/setup_services.sh

Do not prefer "sudo bash scripts/setup_services.sh"; this script calls sudo
only for system-level commands.

Before running this script:
  1. Run: bash scripts/download_neo4j_dump.sh
  2. Fill Backend/.env and Frontend/.env with all required values.

Options:
  --dump PATH           Optional dump path. Default: data/neo4j/neo4j.dump.
                        Use the extracted neo4j.dump produced by download_neo4j_dump.sh.
  --skip-neo4j          Do not install/configure/restore Neo4j.
  --skip-redis          Do not install/configure Redis.
  --dry-run             Print commands without changing system services.
  -h, --help            Show this help.

Required values:
  NEO4J_PASSWORD        Read from Backend/.env or shell environment.
  REDIS_PASSWORD        Read from Backend/.env or shell environment.

Full application validation:
  This script checks only the values needed for Redis and Neo4j setup.
  Run "bash scripts/setup.sh --check-only" after service setup to validate
  model paths, JWT/API values, imports, and app URLs.

Optional Backend/.env or shell values:
  NEO4J_URI             Default: neo4j://localhost:7687
  NEO4J_USERNAME        Default: neo4j
  REDIS_HOST            Default: localhost
  REDIS_PORT            Default: 6379
  REDIS_USERNAME        Default: default
  REDIS_DB              Default: 0
  API_BASE              Used as backend public URL. Default: http://localhost:1026
  FRONTEND_URL          Used as frontend public URL. Default: http://localhost:8501
EOF
}

log() { printf '\n[%s] %s\n' "$1" "$2"; }
info() { log INFO "$1"; }
warn() { log WARN "$1"; }
fail() { log ERROR "$1"; exit 1; }

have() {
  command -v "$1" >/dev/null 2>&1
}

run() {
  if [[ "$DRY_RUN" == "1" ]]; then
    local display_arg
    display_arg="$1"
    if [[ -n "${NEO4J_PASSWORD:-}" ]]; then
      display_arg="${display_arg//$NEO4J_PASSWORD/<redacted>}"
    fi
    if [[ -n "${REDIS_PASSWORD:-}" ]]; then
      display_arg="${display_arg//$REDIS_PASSWORD/<redacted>}"
    fi
    printf '[DRY-RUN] %q' "$display_arg"
    shift || true
    for arg in "$@"; do
      display_arg="$arg"
      if [[ -n "${NEO4J_PASSWORD:-}" ]]; then
        display_arg="${display_arg//$NEO4J_PASSWORD/<redacted>}"
      fi
      if [[ -n "${REDIS_PASSWORD:-}" ]]; then
        display_arg="${display_arg//$REDIS_PASSWORD/<redacted>}"
      fi
      printf ' %q' "$display_arg"
    done
    printf '\n'
  else
    "$@"
  fi
}

sudo_cmd() {
  if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
    run "$@"
  else
    have sudo || fail "sudo is required for Neo4j/Redis package installation."
    run sudo "$@"
  fi
}

sudo_write_file() {
  local content="$1"
  local path="$2"

  if [[ "$DRY_RUN" == "1" ]]; then
    printf '[DRY-RUN] write %q to %q\n' "$content" "$path"
  elif [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
    printf '%s\n' "$content" > "$path"
  else
    printf '%s\n' "$content" | sudo tee "$path" >/dev/null
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

neo4j_conf_value() {
  local key="$1"

  [[ -f /etc/neo4j/neo4j.conf ]] || return 0
  awk -F= -v key="$key" '
    $1 == key {
      value = $2
      sub(/#.*/, "", value)
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", value)
      print value
      exit
    }
  ' /etc/neo4j/neo4j.conf
}

neo4j_resolve_dir() {
  local key="$1"
  local default_path="$2"
  local value

  value="$(neo4j_conf_value "$key")"
  value="${value:-$default_path}"

  case "$value" in
    /*) printf '%s\n' "$value" ;;
    *) printf '/var/lib/neo4j/%s\n' "$value" ;;
  esac
}

is_debian_like() {
  [[ -f /etc/os-release ]] && grep -Eq 'ID(_LIKE)?=.*(debian|ubuntu)' /etc/os-release
}

require_env() {
  local name="$1"
  [[ -n "${!name:-}" ]] || fail "$name is required. Fill it in Backend/.env, or pass it as an environment variable."
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
  [[ "$value" == *"/absolute/path"* ]] && return 0
  [[ "$value" == *"/path/to"* ]] && return 0
  [[ "$value" == *"replace-with"* ]] && return 0
  [[ "$value" == "change-me" ]] && return 0
  return 1
}

set_from_backend_env_if_empty() {
  local variable_name="$1"
  local key="$2"
  local current_value="${!variable_name:-}"
  local file_value

  if [[ -n "$current_value" ]]; then
    return
  fi

  file_value="$(env_file_value "$BACKEND_ENV" "$key")"
  if ! looks_unfilled "$file_value"; then
    printf -v "$variable_name" '%s' "$file_value"
  fi
}

hydrate_config_from_env_files() {
  ensure_env_files

  set_from_backend_env_if_empty NEO4J_URI NEO4J_URI
  set_from_backend_env_if_empty NEO4J_USERNAME NEO4J_USERNAME
  set_from_backend_env_if_empty NEO4J_PASSWORD NEO4J_PASSWORD
  set_from_backend_env_if_empty REDIS_HOST REDIS_HOST
  set_from_backend_env_if_empty REDIS_PORT REDIS_PORT
  set_from_backend_env_if_empty REDIS_USERNAME REDIS_USERNAME
  set_from_backend_env_if_empty REDIS_PASSWORD REDIS_PASSWORD
  set_from_backend_env_if_empty REDIS_DB REDIS_DB
  set_from_backend_env_if_empty BACKEND_PUBLIC_URL API_BASE
  set_from_backend_env_if_empty FRONTEND_PUBLIC_URL FRONTEND_URL

  NEO4J_URI="${NEO4J_URI:-neo4j://localhost:7687}"
  NEO4J_USERNAME="${NEO4J_USERNAME:-neo4j}"
  REDIS_HOST="${REDIS_HOST:-localhost}"
  REDIS_PORT="${REDIS_PORT:-6379}"
  REDIS_USERNAME="${REDIS_USERNAME:-default}"
  REDIS_DB="${REDIS_DB:-0}"
  BACKEND_PUBLIC_URL="${BACKEND_PUBLIC_URL:-http://localhost:1026}"
  FRONTEND_PUBLIC_URL="${FRONTEND_PUBLIC_URL:-http://localhost:8501}"
}

resolve_dump_path() {
  [[ -n "$DUMP_PATH" ]] || fail "Dump path is required unless --skip-neo4j is used."
  [[ "$DRY_RUN" == "1" || -f "$DUMP_PATH" ]] || fail "Neo4j dump not found: $DUMP_PATH. Run: bash scripts/download_neo4j_dump.sh"

  case "$DUMP_PATH" in
    *.tar.gz|*.tgz)
      local dump_dir
      dump_dir="$(dirname "$DUMP_PATH")"
      local extracted_path="$dump_dir/neo4j.dump"
      info "Neo4j dump tarball provided; extracting/checking: $extracted_path"
      if [[ "$DRY_RUN" == "1" ]]; then
        run tar -xzf "$DUMP_PATH" -C "$dump_dir"
      elif [[ -s "$extracted_path" ]]; then
        info "Using existing extracted dump: $extracted_path"
      else
        tar -xzf "$DUMP_PATH" -C "$dump_dir"
        if [[ ! -s "$extracted_path" ]]; then
          local found_dump_path
          found_dump_path="$(find "$dump_dir" -type f -name "neo4j.dump" | head -n 1)"
          [[ -n "$found_dump_path" ]] || fail "Expected extracted dump missing under: $dump_dir"
          ln -sf "$found_dump_path" "$extracted_path"
          info "Linked extracted dump to expected path: $extracted_path"
        fi
      fi
      DUMP_PATH="$extracted_path"
      ;;
  esac
}

ensure_env_files() {
  if [[ ! -f "$BACKEND_ENV" ]]; then
    run cp "$ROOT_DIR/Backend/.env.example" "$BACKEND_ENV"
  fi
  if [[ ! -f "$FRONTEND_ENV" ]]; then
    run cp "$ROOT_DIR/Frontend/.env.example" "$FRONTEND_ENV"
  fi
}

set_env_value() {
  local file="$1"
  local key="$2"
  local value="$3"

  if [[ "$DRY_RUN" == "1" ]]; then
    printf '[DRY-RUN] set %s in %s\n' "$key" "$file"
    return
  fi

  if grep -q "^${key}=" "$file"; then
    sed -i "s|^${key}=.*|${key}=${value}|" "$file"
  else
    printf '\n%s=%s\n' "$key" "$value" >> "$file"
  fi
}

sync_env_values() {
  info "Syncing service URLs/passwords into .env files"
  ensure_env_files

  set_env_value "$BACKEND_ENV" "NEO4J_URI" "$NEO4J_URI"
  set_env_value "$BACKEND_ENV" "NEO4J_USERNAME" "$NEO4J_USERNAME"
  if [[ "$SETUP_NEO4J" == "1" ]]; then
    set_env_value "$BACKEND_ENV" "NEO4J_PASSWORD" "$NEO4J_PASSWORD"
  fi
  set_env_value "$BACKEND_ENV" "REDIS_HOST" "$REDIS_HOST"
  set_env_value "$BACKEND_ENV" "REDIS_PORT" "$REDIS_PORT"
  set_env_value "$BACKEND_ENV" "REDIS_USERNAME" "$REDIS_USERNAME"
  set_env_value "$BACKEND_ENV" "REDIS_DB" "$REDIS_DB"
  if [[ "$SETUP_REDIS" == "1" ]]; then
    set_env_value "$BACKEND_ENV" "REDIS_PASSWORD" "$REDIS_PASSWORD"
  fi
  set_env_value "$BACKEND_ENV" "API_BASE" "$BACKEND_PUBLIC_URL"
  set_env_value "$BACKEND_ENV" "FRONTEND_URL" "$FRONTEND_PUBLIC_URL"

  set_env_value "$FRONTEND_ENV" "API_BASE_URL" "$BACKEND_PUBLIC_URL"
}

install_base_packages() {
  info "Installing base system prerequisites"
  is_debian_like || fail "Automated service setup currently supports Debian/Ubuntu only."
  sudo_cmd apt-get update
  sudo_cmd apt-get install -y openjdk-17-jdk wget curl gnupg ca-certificates redis-tools
}

setup_redis() {
  info "Installing and configuring Redis"
  sudo_cmd apt-get install -y redis-server
  sudo_cmd sed -i "s/^# requirepass .*/requirepass ${REDIS_PASSWORD}/" /etc/redis/redis.conf
  sudo_cmd systemctl enable redis-server
  sudo_cmd systemctl restart redis-server

  if [[ "$DRY_RUN" == "1" ]]; then
    return
  fi

  info "Checking Redis"
  redis-cli -a "$REDIS_PASSWORD" -n "$REDIS_DB" PING
}

wait_for_neo4j() {
  local attempts="${1:-60}"
  local delay_seconds="${2:-10}"

  info "Waiting for Neo4j database availability"
  for attempt in $(seq 1 "$attempts"); do
    if cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USERNAME" -p "$NEO4J_PASSWORD" \
      "RETURN 1 AS ok;" >/dev/null 2>&1; then
      info "Neo4j is accepting database queries."
      return 0
    fi

    if [[ "$attempt" == "$attempts" ]]; then
      break
    fi
    info "Neo4j not ready yet. Retry $attempt/$attempts; waiting ${delay_seconds}s."
    sleep "$delay_seconds"
  done

  warn "Neo4j did not become query-ready within $((attempts * delay_seconds)) seconds."
  warn "Check logs with: sudo tail -n 120 /var/log/neo4j/debug.log"
  return 1
}

setup_neo4j() {
  local neo4j_data_dir
  local neo4j_plugins_dir

  resolve_dump_path

  info "Installing Neo4j 5"
  if [[ ! -f /etc/apt/sources.list.d/neo4j.list ]]; then
    run wget -O /tmp/neo4j.gpg.key https://debian.neo4j.com/neotechnology.gpg.key
    sudo_cmd gpg --dearmor -o /usr/share/keyrings/neo4j.gpg /tmp/neo4j.gpg.key
    sudo_write_file "deb [signed-by=/usr/share/keyrings/neo4j.gpg] https://debian.neo4j.com stable 5" /etc/apt/sources.list.d/neo4j.list
    sudo_cmd apt-get update
  fi
  sudo_cmd apt-get install -y neo4j

  info "Neo4j version"
  neo4j --version || true

  info "Stopping Neo4j before password/database restore"
  sudo_cmd systemctl stop neo4j || true

  neo4j_data_dir="$(neo4j_resolve_dir server.directories.data /var/lib/neo4j/data)"
  neo4j_plugins_dir="$(neo4j_resolve_dir server.directories.plugins /var/lib/neo4j/plugins)"
  info "Neo4j data directory: $neo4j_data_dir"
  info "Neo4j plugins directory: $neo4j_plugins_dir"

  info "Setting Neo4j initial password if database has not been initialized"
  sudo_cmd neo4j-admin dbms set-initial-password "$NEO4J_PASSWORD" || warn "Neo4j password may already be initialized; continuing."

  info "Installing APOC core plugin"
  sudo_cmd mkdir -p "$neo4j_plugins_dir"
  sudo_cmd wget -O "$neo4j_plugins_dir/apoc-${NEO4J_APOC_VERSION}-core.jar" "https://github.com/neo4j/apoc/releases/download/${NEO4J_APOC_VERSION}/apoc-${NEO4J_APOC_VERSION}-core.jar"
  sudo_cmd chown neo4j:neo4j "$neo4j_plugins_dir/apoc-${NEO4J_APOC_VERSION}-core.jar"

  if grep -q '^#\?dbms.security.procedures.unrestricted=' /etc/neo4j/neo4j.conf; then
    sudo_cmd sed -i 's/^#\?dbms.security.procedures.unrestricted=.*/dbms.security.procedures.unrestricted=apoc.*/' /etc/neo4j/neo4j.conf
  else
    sudo_append_line "dbms.security.procedures.unrestricted=apoc.*" /etc/neo4j/neo4j.conf
  fi
  if ! grep -q '^dbms.security.procedures.allowlist=apoc.*' /etc/neo4j/neo4j.conf; then
    sudo_append_line "dbms.security.procedures.allowlist=apoc.*" /etc/neo4j/neo4j.conf
  fi

  info "Restoring EvoAge Neo4j dump"
  sudo_cmd mkdir -p /var/lib/neo4j/import
  sudo_cmd cp "$DUMP_PATH" /var/lib/neo4j/import/neo4j.dump
  sudo_cmd neo4j-admin database load neo4j --from-path=/var/lib/neo4j/import --overwrite-destination=true

  info "Fixing Neo4j data/plugin ownership after restore"
  sudo_cmd chown -R neo4j:neo4j "$neo4j_data_dir"
  sudo_cmd chown -R neo4j:neo4j "$neo4j_plugins_dir"
  sudo_cmd chmod -R u+rwX,g+rX "$neo4j_data_dir"

  info "Starting Neo4j after APOC config and database restore"
  sudo_cmd systemctl enable neo4j
  sudo_cmd systemctl restart neo4j

  if [[ "$DRY_RUN" == "1" ]]; then
    return
  fi

  wait_for_neo4j || fail "Neo4j service started, but the database is not query-ready. Fix the log issue above, then rerun checks."

  info "Checking Neo4j login"
  cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USERNAME" -p "$NEO4J_PASSWORD" "SHOW DATABASES;"

  info "Checking EvoAge graph node count"
  cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USERNAME" -p "$NEO4J_PASSWORD" "MATCH (n) RETURN count(n) AS nodeCount;"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dump)
      [[ $# -ge 2 ]] || fail "--dump requires a path."
      DUMP_PATH="$2"
      shift
      ;;
    --skip-neo4j) SETUP_NEO4J=0 ;;
    --skip-redis) SETUP_REDIS=0 ;;
    --dry-run) DRY_RUN=1 ;;
    -h|--help)
      usage
      exit 0
      ;;
    *) fail "Unknown option: $1" ;;
  esac
  shift
done

hydrate_config_from_env_files
if [[ "$SETUP_NEO4J" == "1" ]]; then
  require_env NEO4J_PASSWORD
fi
if [[ "$SETUP_REDIS" == "1" ]]; then
  require_env REDIS_PASSWORD
fi
sync_env_values
install_base_packages

if [[ "$SETUP_REDIS" == "1" ]]; then
  setup_redis
fi
if [[ "$SETUP_NEO4J" == "1" ]]; then
  setup_neo4j
fi

info "Service setup complete"
info "Next: run full setup verification with: bash scripts/setup.sh --check-only"
