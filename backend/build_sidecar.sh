#!/usr/bin/env bash
#
# Compiles the Flask backend into a self-contained directory that the Tauri app
# ships as a resource and spawns as a sidecar process. Run once per target OS -
# Nuitka does not cross-compile.
#
# Output: backend/dist/app.dist/ (executable "app" plus its bundled runtime)
set -euo pipefail

cd "$(dirname "$0")"

OUT_DIR="dist"

python -m nuitka \
  --standalone \
  --output-dir="$OUT_DIR" \
  --output-filename=mycartime-backend \
  --assume-yes-for-downloads \
  --remove-output \
  --nofollow-import-to=pytest \
  --nofollow-import-to=nuitka \
  --include-package=webuntis \
  --include-package=ortools \
  --include-package-data=ortools \
  --include-package=anthropic \
  --include-package=diskcache \
  --include-package=flask_cors \
  --include-data-dir=src/assistant/skill=assistant/skill \
  --include-data-files=../doc/internal_doc.md=doc/internal_doc.md \
  src/app.py

echo "Built: $OUT_DIR/app.dist/mycartime-backend"
