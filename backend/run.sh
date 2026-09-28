#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
if [ ! -f "$PROJECT_DIR/.venv/bin/activate" ]; then
  echo "No virtualenv at $PROJECT_DIR/.venv" >&2
  echo "Create it first:  python3 -m venv .venv && .venv/bin/pip install -r backend/requirements.txt" >&2
  exit 1
fi

cd "$PROJECT_DIR"
source .venv/bin/activate

if [ ! -f "$PROJECT_DIR/frontend/dist/index.html" ]; then
  echo "No frontend build found — the API will run but nothing will be served at /."
  echo "Build it first:  cd frontend && npm install && npm run build"
fi
# HOST defaults to loopback: this app has no authentication, so it should not be
# reachable from the network. Override with HOST=0.0.0.0 if you need LAN access.
# Run from the project root, not backend/: `backend` is a package, so the repo root
# must be the working directory for `backend.main` to be importable.
# Invoke uvicorn as a module (`python3 -m uvicorn`) rather than the console script in
# .venv/bin — those scripts hard-code an absolute interpreter path at install time and
# break silently if the venv directory is ever moved or renamed.
exec python3 -m uvicorn backend.main:app --host "${HOST:-127.0.0.1}" --port "${PORT:-5173}" --reload
