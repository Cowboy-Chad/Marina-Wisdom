#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"
source .venv/bin/activate

if [ ! -f "$PROJECT_DIR/frontend/dist/index.html" ]; then
  echo "No frontend build found — the API will run but nothing will be served at /."
  echo "Build it first:  cd frontend && npm install && npm run build"
fi

cd "$SCRIPT_DIR"
# HOST defaults to loopback: this app has no authentication, so it should not be
# reachable from the network. Override with HOST=0.0.0.0 if you need LAN access.
exec uvicorn backend.main:app --host "${HOST:-127.0.0.1}" --port "${PORT:-5173}" --reload
