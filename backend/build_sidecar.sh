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

# On Windows the sidecar would otherwise launch with a console subsystem,
# popping up a terminal window alongside the Tauri UI; its stdout/stderr are
# already captured to the log files in app.py, not a console.
IS_WINDOWS=false
WINDOWS_ONLY_FLAGS=()
if [[ "$OSTYPE" == "msys"* || "$OSTYPE" == "cygwin"* || "$OSTYPE" == "win32"* ]]; then
  IS_WINDOWS=true
  # A CC/CXX pointing at MinGW64 (e.g. inherited from the calling shell) takes
  # priority over --msvc in Nuitka's Scons backend, silently defeating the
  # pin below and making the build depend on whatever toolchain the shell
  # happens to export - unset them so --msvc=latest is unconditionally honored.
  unset CC CXX
  WINDOWS_ONLY_FLAGS=(
    --windows-console-mode=disable
    # Force MSVC (Nuitka's --msvc takes the MSVC toolset version, not the VS
    # product version) so the build doesn't silently fall back to MinGW64 if
    # it happens to be present on the machine. "latest" rather than a pinned
    # version (e.g. "14.3" for VS2022) because GitHub-hosted windows-latest
    # runners upgrade their bundled VS/MSVC toolset over time, which breaks a
    # hardcoded pin outright instead of just picking a different (but still
    # present) toolset.
    --msvc=latest
    # Nuitka does not pick the bundled MSVC C++ runtime (msvcp140.dll etc.)
    # from PATH: it shells out to `vswhere -latest` and grabs whatever
    # redist folder ships inside that VS install, regardless of which
    # compiler actually built the extension modules it is bundling (this
    # project falls back to MinGW64, since this machine's installed MSVC is
    # too old for Python 3.12). A machine with only an old Visual Studio
    # registered (e.g. VS2019, redist 14.29) then gets paired with
    # ortools.dll, which needs a far newer C++ STL, and every CP-SAT solve
    # dies with an access violation - the sidecar crashes during its solver
    # warm-up before it ever answers an HTTP request, which looks from the
    # outside like the backend hanging. `=no` disables that auto-detection
    # entirely so the build no longer depends on which VS version happens to
    # be installed on the machine doing the building; the block below then
    # supplies a known-good runtime explicitly instead.
    --include-windows-runtime-dlls=no
  )
fi

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

# Nuitka's standalone mode statically follows every import it finds in the
# source of an included module, even ones nested in a function body that this
# app never calls - not just what's reachable at runtime. That drags in extra
# modules we don't use: pandas (pulled in unconditionally by
# ortools.sat.python.cp_model, which this app does use) only reaches scipy
# through its optional sparse-array, plotting, and interpolation helpers,
# none of which this app calls. Flask's own click usage (app.cli) is a real,
# always-imported dependency and must stay.
# --show-progress/--show-scons: without a real terminal attached (e.g. piped
# through build.ps1 or a CI log), Nuitka's default output is a \r-updating
# progress bar and an otherwise-silent C-compilation phase - both effectively
# invisible to anything reading the stream line by line. These force plain,
# newline-terminated progress and compiler-invocation output instead.
python -m nuitka \
  --include-data-files=../.env=.env \
  --standalone \
  --output-dir="$OUT_DIR" \
  --output-filename=mycartime-backend \
  --assume-yes-for-downloads \
  --nofollow-import-to=pytest \
  --nofollow-import-to=nuitka \
  --nofollow-import-to=scipy \
  --include-package=ortools \
  --include-package-data=ortools \
  --include-package=diskcache \
  --include-package=flask_cors \
  --include-data-dir=src/assistant/skill=assistant/skill \
  --include-data-files=src/assistant/harry-potter-spinning-verbs.txt=assistant/harry-potter-spinning-verbs.txt \
  --include-data-files=../doc/internal_doc.md=doc/internal_doc.md \
  "${WINDOWS_ONLY_FLAGS[@]+"${WINDOWS_ONLY_FLAGS[@]}"}" \
  src/app.py

# --include-windows-runtime-dlls=no (above) stops Nuitka from bundling a CRT
# it auto-detected via vswhere, so the dist directory ships without one at
# all except for vcruntime140(_1).dll, which Nuitka always copies straight
# from the Python install (sys.prefix) rather than the vswhere-guessed path,
# since the official CPython installer ships those two next to python.exe.
# Explicitly bundle the rest of the CRT - and overwrite those two - from
# System32 so the exe is self-contained (does not depend on target machines
# already having a compatible redist installed) and pinned to one known
# source (the machine-wide runtime kept current by Windows Update, the same
# one an unpackaged `python backend/src/app.py` run already links against).
if [[ "$IS_WINDOWS" == true ]]; then
  windir="${SYSTEMROOT:-C:\Windows}"
  system32="$(cygpath -u "$windir" 2>/dev/null || echo "$windir")/System32"
  crt_dlls=(
    msvcp140 msvcp140_1 msvcp140_2 msvcp140_atomic_wait msvcp140_codecvt_ids
    vcruntime140 vcruntime140_1 concrt140
  )
  for crt in "${crt_dlls[@]}"; do
    source="$system32/$crt.dll"
    [[ -f "$source" ]] || continue
    cp -f "$source" "$OUT_DIR/app.dist/$crt.dll"
    echo "Bundled $crt.dll from the system runtime"
  done
fi

echo "Built: $OUT_DIR/app.dist/mycartime-backend"
