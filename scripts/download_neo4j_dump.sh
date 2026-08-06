#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULT_DUMP_DIR="$ROOT_DIR/data/neo4j"
HF_DATASET_URL="https://huggingface.co/datasets/gauravahuja77/EvoAge/tree/main"
HF_RESOLVE_BASE="https://huggingface.co/datasets/gauravahuja77/EvoAge/resolve/main"
HF_DUMP_PATH="kg_formation/neo4j/neo4j.dump.tar.gz"

DUMP_DIR="${DUMP_DIR:-$DEFAULT_DUMP_DIR}"
DUMP_FILENAME="${DUMP_FILENAME:-neo4j.dump.tar.gz}"
EXTRACTED_DUMP_FILENAME="${EXTRACTED_DUMP_FILENAME:-neo4j.dump}"
DRY_RUN=0

usage() {
  cat <<EOF
Usage: scripts/download_neo4j_dump.sh [options]

Downloads the EvoAge Neo4j dump before service setup.

Options:
  --dir PATH            Download directory. Default: data/neo4j
  --filename NAME       Local tarball filename. Default: neo4j.dump.tar.gz
  --dry-run             Print the download command without running it.
  -h, --help            Show this help.

Dataset page:
  $HF_DATASET_URL

Hugging Face file:
  $HF_DUMP_PATH

For large downloads, run this script in a separate terminal from the repo root.
EOF
}

log() { printf '\n[%s] %s\n' "$1" "$2"; }
info() { log INFO "$1"; }
fail() { log ERROR "$1"; exit 1; }

have() {
  command -v "$1" >/dev/null 2>&1
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

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dir)
      [[ $# -ge 2 ]] || fail "--dir requires a path."
      DUMP_DIR="$2"
      shift
      ;;
    --filename)
      [[ $# -ge 2 ]] || fail "--filename requires a filename."
      DUMP_FILENAME="$2"
      shift
      ;;
    --dry-run) DRY_RUN=1 ;;
    -h|--help)
      usage
      exit 0
      ;;
    *) fail "Unknown option: $1" ;;
  esac
  shift
done

DUMP_PATH="$DUMP_DIR/$DUMP_FILENAME"
EXTRACTED_DUMP_PATH="$DUMP_DIR/$EXTRACTED_DUMP_FILENAME"
DUMP_URL="$HF_RESOLVE_BASE/$HF_DUMP_PATH?download=true"

info "Dataset page: $HF_DATASET_URL"
info "Hugging Face file: $HF_DUMP_PATH"
info "Downloading Neo4j dump tarball to: $DUMP_PATH"

if [[ -f "$DUMP_PATH" ]]; then
  info "Dump already exists. Keeping existing file."
else
  run mkdir -p "$DUMP_DIR"
  if have curl; then
    run curl -L --fail --continue-at - --output "$DUMP_PATH" "$DUMP_URL"
  elif have wget; then
    run wget -c -O "$DUMP_PATH" "$DUMP_URL"
  else
    fail "curl or wget is required to download the dump."
  fi
fi

if [[ "$DRY_RUN" != "1" ]]; then
  [[ -s "$DUMP_PATH" ]] || fail "Downloaded dump is empty or missing: $DUMP_PATH"
fi

if [[ -f "$EXTRACTED_DUMP_PATH" ]]; then
  info "Extracted dump already exists. Keeping existing file: $EXTRACTED_DUMP_PATH"
else
  info "Extracting neo4j.dump into: $DUMP_DIR"
  run tar -xzf "$DUMP_PATH" -C "$DUMP_DIR"
fi

if [[ "$DRY_RUN" != "1" ]]; then
  if [[ ! -s "$EXTRACTED_DUMP_PATH" ]]; then
    FOUND_DUMP_PATH="$(find "$DUMP_DIR" -type f -name "$EXTRACTED_DUMP_FILENAME" | head -n 1)"
    [[ -n "$FOUND_DUMP_PATH" ]] || fail "Expected extracted dump missing under: $DUMP_DIR"
    ln -sf "$FOUND_DUMP_PATH" "$EXTRACTED_DUMP_PATH"
    info "Linked extracted dump to expected path: $EXTRACTED_DUMP_PATH"
  fi
fi

info "Neo4j dump ready: $EXTRACTED_DUMP_PATH"
info "Next: fill all required values in Backend/.env and Frontend/.env, then run: bash scripts/setup_services.sh"
