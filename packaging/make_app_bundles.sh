#!/bin/bash
# Wraps the onefile binaries built by packaging/build.sh in minimal macOS
# .app bundles, so they're double-clickable from Finder (a bare Mach-O
# executable with no bundle around it isn't - Finder/LaunchServices has no
# association for it and falls back to opening it as text).
#
# The bundle's CFBundleExecutable is a tiny launcher script that opens the
# real binary in Terminal.app, so startup logs and any crash output stay
# visible to the user instead of the process running invisibly.
#
# Usage: ./packaging/make_app_bundles.sh [lite|full|both]   (default: both)
set -euo pipefail

VARIANT_ARG="${1:-both}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="$ROOT_DIR/packaging/dist"

make_app() {
    local binary_name="$1"
    local app_name="$2"
    local bundle_id="$3"

    local binary_path="$DIST_DIR/$binary_name"
    if [ ! -f "$binary_path" ]; then
        echo "ERROR: $binary_path not found. Run packaging/build.sh first." >&2
        exit 1
    fi

    local app_dir="$DIST_DIR/$app_name.app"
    rm -rf "$app_dir"
    mkdir -p "$app_dir/Contents/MacOS"

    cp "$binary_path" "$app_dir/Contents/MacOS/$binary_name"
    chmod +x "$app_dir/Contents/MacOS/$binary_name"

    cat > "$app_dir/Contents/MacOS/launcher" <<LAUNCHER
#!/bin/bash
DIR="\$(cd "\$(dirname "\$0")" && pwd)"
open -a Terminal "\$DIR/$binary_name"
LAUNCHER
    chmod +x "$app_dir/Contents/MacOS/launcher"

    cat > "$app_dir/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>$app_name</string>
    <key>CFBundleDisplayName</key>
    <string>$app_name</string>
    <key>CFBundleIdentifier</key>
    <string>$bundle_id</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleExecutable</key>
    <string>launcher</string>
    <key>LSMinimumSystemVersion</key>
    <string>11.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
PLIST

    echo "Created $app_dir"
}

case "$VARIANT_ARG" in
    lite) make_app "mycartime" "MyCarTime" "com.mycartime.app" ;;
    full) make_app "mycartime-full" "MyCarTime (PNG export)" "com.mycartime.app.full" ;;
    both)
        make_app "mycartime" "MyCarTime" "com.mycartime.app"
        make_app "mycartime-full" "MyCarTime (PNG export)" "com.mycartime.app.full"
        ;;
    *) echo "Usage: $0 [lite|full|both]" >&2; exit 1 ;;
esac
