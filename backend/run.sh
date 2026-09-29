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
# HOST defaults to loopback. Requests now carry a bearer token, but registration
# is honor-system and the traffic is plain HTTP, so keeping this off the network
# by default is still the right call. Override with HOST=0.0.0.0 for LAN access.
# Run from the project root, not backend/: `backend` is a package, so the repo root
# must be the working directory for `backend.main` to be importable.
# Invoke uvicorn as a module (`python3 -m uvicorn`) rather than the console script in
# .venv/bin — those scripts hard-code an absolute interpreter path at install time and
# break silently if the venv directory is ever moved or renamed.
#
# --reload is a development convenience (it watches the filesystem and restarts on
# every edit). Turn it off with RELOAD=0 when the app is serving testers: a restart
# mid-transcription loses that job, and the watcher is pure overhead when nobody is
# editing the code.
RELOAD_FLAG=""
[ "${RELOAD:-1}" = "0" ] || RELOAD_FLAG="--reload"

exec python3 -m uvicorn backend.main:app \
  --host "${HOST:-127.0.0.1}" \
  --port "${PORT:-5173}" \
  $RELOAD_FLAG
