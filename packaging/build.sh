#!/bin/bash
# Builds standalone macOS binaries of the mycartime backend (which also
# serves the built frontend, see backend/src/app.py's serve_frontend route),
# via PyInstaller. Produces two onefile executables:
#
#   packaging/dist/mycartime       "lite":  no Chromium bundled, PNG export
#                                   gracefully 501s (see ChromiumNotAvailableError).
#   packaging/dist/mycartime-full  "full":  bundles the Chromium build Playwright
#                                   would otherwise download, so PNG export
#                                   works out of the box.
#
# Usage: ./packaging/build.sh [lite|full|both]   (default: both)
set -euo pipefail

VARIANT_ARG="${1:-both}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
WEBUNTIS_DIR="$ROOT_DIR/webuntis"
PACKAGING_DIR="$ROOT_DIR/packaging"
VENV_DIR="$ROOT_DIR/.venv"
ENV_FILE="$ROOT_DIR/.env"

if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: $ENV_FILE not found. It must exist (holds GITHUB_ISSUE_CREATION, " >&2
    echo "optionally ANTHROPIC_API_KEY) so it can be baked into the bundle." >&2
    exit 1
fi

echo "=== Building frontend (frontend/dist) ==="
cd "$FRONTEND_DIR"
if [ ! -d node_modules ]; then
    npm install
fi
npm run build
cd "$ROOT_DIR"

echo "=== Setting up backend virtualenv ($VENV_DIR) ==="
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"
pip install -q -r "$BACKEND_DIR/requirements.txt"
pip install -q -e "$WEBUNTIS_DIR"
pip install -q pyinstaller

# Needed for the "full" variant; harmless (fast no-op) for "lite" so it's
# always run, keeping this script simple.
python -m playwright install chromium

DIST_DIR="$PACKAGING_DIR/dist"
WORK_DIR="$PACKAGING_DIR/build"
rm -rf "$DIST_DIR" "$WORK_DIR"

build_variant() {
    local variant="$1"
    echo ""
    echo "=== Building '$variant' variant ==="

    if [ "$variant" = "full" ]; then
        # Pick the chromium-<rev> AND chromium_headless_shell-<rev> cache dirs
        # matching the *installed* playwright package (there may be several
        # revisions cached from past `playwright install` runs across other
        # projects) - see browsers.json bundled inside the playwright package
        # for the revisions it expects. Both are needed: export_service.py
        # calls `p.chromium.launch()` with the default headless=True, and
        # recent Playwright versions serve that from the separate
        # chromium_headless_shell build, not the full "chromium" one (that's
        # only used for headless=False / channel="chromium"). Confirmed by
        # reproducing the launch failure directly against a single-revision
        # bundle during development of this script - don't drop either one.
        local revs
        revs="$(python -c "
import json, playwright, os
pkg_dir = os.path.dirname(playwright.__file__)
with open(os.path.join(pkg_dir, 'driver', 'package', 'browsers.json')) as f:
    data = json.load(f)
for b in data['browsers']:
    if b['name'] in ('chromium', 'chromium-headless-shell'):
        print(b['name'] + ' ' + str(b['revision']))
")"
        local dirs=()
        while IFS=' ' read -r name rev; do
            [ -z "$name" ] && continue
            local dirname
            if [ "$name" = "chromium" ]; then
                dirname="chromium-$rev"
            else
                dirname="chromium_headless_shell-$rev"
            fi
            local chromium_dir="$HOME/Library/Caches/ms-playwright/$dirname"
            if [ ! -d "$chromium_dir" ] || [ ! -f "$chromium_dir/INSTALLATION_COMPLETE" ]; then
                echo "ERROR: expected Chromium cache dir not found/incomplete: $chromium_dir" >&2
                echo "Run 'playwright install chromium' first." >&2
                exit 1
            fi
            echo "Using Chromium cache: $chromium_dir"
            dirs+=("$chromium_dir")
        done <<< "$revs"
        export MYCARTIME_CHROMIUM_DIRS="$(IFS=:; echo "${dirs[*]}")"
    fi

    export MYCARTIME_VARIANT="$variant"
    (
        cd "$ROOT_DIR"
        pyinstaller --noconfirm \
            --distpath "$DIST_DIR" \
            --workpath "$WORK_DIR" \
            "$PACKAGING_DIR/mycartime.spec"
    )
    unset MYCARTIME_VARIANT
    unset MYCARTIME_CHROMIUM_DIRS
}

case "$VARIANT_ARG" in
    lite) build_variant lite ;;
    full) build_variant full ;;
    both) build_variant lite; build_variant full ;;
    *) echo "Usage: $0 [lite|full|both]" >&2; exit 1 ;;
esac

deactivate

echo ""
echo "=== Wrapping in .app bundles (double-clickable from Finder) ==="
"$PACKAGING_DIR/make_app_bundles.sh" "$VARIANT_ARG"

echo ""
echo "=== Build complete ==="
ls -lh "$DIST_DIR" | awk '{print $5, $9}' | grep -v '^ *$'
du -sh "$DIST_DIR"/* 2>/dev/null
