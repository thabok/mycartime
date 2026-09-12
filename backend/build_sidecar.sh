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

# GITHUB_ISSUE_CREATION (feedback endpoint) and any other secrets live in the
# repo-root .env, which is gitignored and not something the Tauri shell
# passes to the sidecar - so it has to be baked into the build itself, or the
# packaged app can never create feedback issues. Only acceptable because the
# token is scoped to just "issues:write" on the single feedback repo; a
# broader token must never be shipped this way.
if [ ! -f "../.env" ]; then
  echo "../.env not found - the packaged app's feedback feature would have no GITHUB_ISSUE_CREATION token. Aborting." >&2
  exit 1
fi

python -m nuitka \
  --include-data-files=../.env=.env \
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
