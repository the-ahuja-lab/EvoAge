#!/usr/bin/env bash
set -e

echo "🔪 Killing any old processes…"

pkill -u "$(whoami)" gunicorn || true
pkill -f "python -m app.main" -u "$(whoami)" || true

echo "🚀 Starting main API server…"
nohup \
  poetry run gunicorn -w 2 --timeout 300 \
    -k uvicorn.workers.UvicornWorker app.main:app \
    --bind 0.0.0.0:1026 \
  > neo4j_api_logs.log 2>&1 &

echo "✅ Check Log for Deployment."
