#!/bin/bash
# Runs the full app (Flask backend + Vite frontend) for local development.
#
# - Frontend runs via `npm run dev` (Vite), so it hot-reloads on file changes.
# - Backend runs via `python -m src.app`; restart this script after backend
#   code changes since Flask's own auto-reloader is not used here.
#
# Usage: ./run.sh
set -e
cd "$(dirname "$0")" || exit 1

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
WEBUNTIS_DIR="$ROOT_DIR/webuntis"

# Make sure the frontend submodule is checked out (e.g. on a fresh clone).
if [ -z "$(ls -A "$FRONTEND_DIR" 2>/dev/null)" ]; then
    echo "Frontend submodule not initialized, fetching it..."
    git -C "$ROOT_DIR" submodule update --init --recursive
fi

echo "Setting up backend virtual environment..."
if [ ! -d "$ROOT_DIR/.venv" ]; then
    python3 -m venv "$ROOT_DIR/.venv"
fi
source "$ROOT_DIR/.venv/bin/activate"
pip install -q -r "$BACKEND_DIR/requirements.txt"
pip install -q -e "$WEBUNTIS_DIR"
deactivate

echo "Installing frontend dependencies..."
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    (cd "$FRONTEND_DIR" && npm install)
fi

# Track child PIDs so both processes are stopped together on exit/Ctrl+C.
PIDS=()
cleanup() {
    echo ""
    echo "Shutting down..."
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
    wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Starting backend on http://localhost:1338 ..."
(
    source "$ROOT_DIR/.venv/bin/activate"
    cd "$BACKEND_DIR/src"
    python app.py 2>&1 | sed -u 's/^/[backend]  /'
) &
PIDS+=($!)

echo "Starting frontend (Vite dev server, hot reload) ..."
(
    cd "$FRONTEND_DIR"
    npm run dev 2>&1 | sed -u 's/^/[frontend] /'
) &
PIDS+=($!)

sleep 1
open -a Safari "http://localhost:8080"

wait
