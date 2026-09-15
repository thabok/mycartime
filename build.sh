# rm -rf before npm run build: Tauri only adds/overwrites the staged backend
# resource dir, never removes files dropped from a prior build (see build.ps1
# for the numexpr/pandas crash this caused).
time (python3 -m venv .venv && . .venv/bin/activate && python -m pip install --upgrade pip && pip install -r backend/requirements.txt && pip install nuitka && ./backend/build_sidecar.sh && cd frontend && npm install && cd .. && rm -rf src-tauri/target/release/backend && npm run build)
open src-tauri/target/release/bundle/dmg
