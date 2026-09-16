cd "$(dirname "$0")/.." || exit 1

# rm -rf before npm run build: Tauri only adds/overwrites the staged backend
# resource dir, never removes files dropped from a prior build (see build.ps1
# for the numexpr/pandas crash this caused).
time (python3 -m venv .venv && . .venv/bin/activate && python -m pip install --upgrade pip && pip install -r src/backend/requirements.txt && pip install nuitka && ./src/backend/build_sidecar.sh && cd src/frontend && npm install && cd ../.. && rm -rf src/src-tauri/target/release/backend && cd src && npm run build)
open src/src-tauri/target/release/bundle/dmg
