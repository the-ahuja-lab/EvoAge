#!/usr/bin/env bash
set -e

echo "Starting EvoAge FastAPI backend..."

exec poetry run gunicorn \
  -w 1 \
  --timeout 300 \
  -k uvicorn.workers.UvicornWorker \
  app.main:app \
  --bind 0.0.0.0:1026
