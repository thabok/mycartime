#!/bin/sh
# Starts the mycartime backend (Maven) and frontend (npm) together.
# Stop both with Ctrl+C.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
BACKEND_LOG="$SCRIPT_DIR/backend.log"
BACKEND_PORT=1337
FRONTEND_PORT=3000
FRONTEND_URL="http://localhost:$FRONTEND_PORT"

export JAVA_HOME="${JAVA_HOME:-/opt/homebrew/opt/openjdk}"
export PATH="$JAVA_HOME/bin:$PATH"

if lsof -tiTCP:$BACKEND_PORT -sTCP:LISTEN >/dev/null 2>&1 && lsof -tiTCP:$FRONTEND_PORT -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Backend (port $BACKEND_PORT) and frontend (port $FRONTEND_PORT) are already running."
  echo "Opening $FRONTEND_URL ..."
  open "$FRONTEND_URL"
  exit 0
fi

cleanup() {
  printf '\nStopping backend (pid %s)...\n' "$BACKEND_PID"
  kill "$BACKEND_PID" 2>/dev/null
  wait "$BACKEND_PID" 2>/dev/null
}
trap cleanup INT TERM EXIT

echo "Starting backend (log: $BACKEND_LOG)..."
mvn -q -f "$BACKEND_DIR/pom.xml" exec:java -Dexec.mainClass=com.thabok.main.Main > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!

echo "Starting frontend..."
(cd "$FRONTEND_DIR" && ./run.sh)
