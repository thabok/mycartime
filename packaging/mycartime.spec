# PyInstaller spec for the mycartime backend, built in two variants:
#
#   MYCARTIME_VARIANT=lite   pyinstaller packaging/mycartime.spec   (default)
#   MYCARTIME_VARIANT=full   pyinstaller packaging/mycartime.spec
#
# "lite" ships without a bundled Chromium (PNG export degrades gracefully to
# a 501, see export_service.ChromiumNotAvailableError). "full" bundles the
# exact Chromium build Playwright would otherwise download, so PNG export
# works out of the box. See packaging/build.sh, which sets the env var and
# drives both builds; don't invoke this spec directly unless you know what
# you're doing.
#
# Run from the repo root (build.sh does `cd` there first) so all the
# relative paths below resolve correctly regardless of PyInstaller's own cwd
# handling.
import os

from PyInstaller.utils.hooks import collect_all

VARIANT = os.environ.get('MYCARTIME_VARIANT', 'lite')
if VARIANT not in ('lite', 'full'):
    raise SystemExit(f"Unknown MYCARTIME_VARIANT={VARIANT!r}, expected 'lite' or 'full'")

REPO_ROOT = os.path.abspath(os.path.join(SPECPATH, '..'))
BACKEND_SRC = os.path.join(REPO_ROOT, 'backend', 'src')
WEBUNTIS_SRC = os.path.join(REPO_ROOT, 'webuntis')

# The editable install of ../webuntis confuses PyInstaller's import scanner
# (its egg-link/finder-based __init__.py resolution isn't picked up by
# modulegraph the way a normal site-packages install would be), so its
# source dir is added to pathex directly and its submodules are collected
# explicitly rather than relying on the hidden-import scan to find them.
pathex = [BACKEND_SRC, WEBUNTIS_SRC]

datas = []
binaries = []
hiddenimports = [
    'webuntis',
    'webuntis.session',
    'webuntis.errors',
    'webuntis.objects',
    'webuntis.utils',
    'webuntis.utils.datetime_utils',
    'webuntis.utils.logger',
    'webuntis.utils.misc',
    'webuntis.utils.remote',
    'webuntis.utils.third_party',
    'webuntis.utils.timetable_utils',
    'webuntis.utils.userinput',
]

# ortools' CP-SAT solver is a compiled extension with a lot of protobuf
# plumbing that PyInstaller's static analysis misses if left to hidden-import
# guessing, so pull in everything the package ships.
for pkg in ('ortools', 'anthropic', 'flask_cors', 'diskcache', 'playwright'):
    pkg_datas, pkg_binaries, pkg_hiddenimports = collect_all(pkg)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hiddenimports

# --- Bundled resources (read via apppaths.resource_path / frontend_dist_path
# / doc_path when frozen; see backend/src/apppaths.py) ---
datas += [
    (os.path.join(REPO_ROOT, 'frontend', 'dist'), 'frontend_dist'),
    (os.path.join(BACKEND_SRC, 'assistant'), 'assistant'),
    (os.path.join(REPO_ROOT, 'doc', 'internal_doc.md'), 'doc'),
    (os.path.join(REPO_ROOT, '.env'), '.'),
]

chromium_dirs = []
if VARIANT == 'full':
    # Bundle the exact Chromium builds the installed `playwright` package
    # expects (see packaging/build.sh for how the revisions are picked and
    # validated), preserving the on-disk layout Playwright's driver expects
    # under a cache root, so PLAYWRIGHT_BROWSERS_PATH=<that root> just works
    # (see apppaths.py, which sets this env var when frozen). Two directories
    # are needed - `chromium-<rev>` (used for headless=False / channel=
    # "chromium") AND `chromium_headless_shell-<rev>` (what a plain
    # `p.chromium.launch()` - the default, headless=True - actually resolves
    # to on recent Playwright versions; export_service.py calls it exactly
    # that way). Bundling only the former was tried first and failed with
    # "Executable doesn't exist at .../chromium_headless_shell-<rev>/...".
    #
    # NOTE: deliberately NOT added to `datas` above. Chromium's app bundle
    # contains real Mach-O executables/frameworks; if PyInstaller's Analysis
    # sees them in `datas` it "reclassifies" them as BINARY (see
    # build_main.py's "binary vs. data reclassification" step) and then tries
    # to re-sign them as standalone Mach-O binaries during PKG assembly,
    # which corrupts the nested .app bundle (codesign fails on "Google Chrome
    # for Testing.app/Contents/Frameworks/...") and aborts the build. Instead
    # its files are added straight to `a.datas` after Analysis has already
    # run (see below), explicitly typed 'DATA', so they're carried through
    # verbatim as opaque data and never touched by codesign.
    _dirs_env = os.environ.get('MYCARTIME_CHROMIUM_DIRS')
    if not _dirs_env:
        raise SystemExit(
            "MYCARTIME_VARIANT=full requires MYCARTIME_CHROMIUM_DIRS (colon-separated) "
            "to point at cached chromium-<rev> / chromium_headless_shell-<rev> "
            "directories from ~/Library/Caches/ms-playwright (see packaging/build.sh)."
        )
    chromium_dirs = _dirs_env.split(':')
    for d in chromium_dirs:
        if not os.path.isdir(d):
            raise SystemExit(f"MYCARTIME_CHROMIUM_DIRS entry not found: {d}")

block_cipher = None

a = Analysis(
    [os.path.join(BACKEND_SRC, 'app.py')],
    pathex=pathex,
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    cipher=block_cipher,
)

def _collect_tree_preserving_symlinks(src_dir, dest_prefix):
    """
    Like a recursive `datas` add, but real symlinks (macOS .app/.framework
    bundles are full of them - e.g. Framework.framework/Versions/Current ->
    <version>) are added as PyInstaller SYMLINK TOC entries instead of being
    silently dropped (os.walk with followlinks=False, the safe default,
    won't descend into or copy the content behind them) or - worse -
    followed and copied as if they were real files/dirs (duplicating the
    entire versioned framework payload and losing the symlink Chromium's own
    Info.plist / dyld @rpath lookups expect to resolve at runtime).

    Returns a list of (dest_name, src_name, typecode) TOC entries, typecode
    'DATA' for real files and 'SYMLINK' for symlinks (src_name is then the
    symlink's own relative target, unresolved, exactly as PyInstaller's
    onefile extraction expects so it can recreate the link rather than copy
    its target's content).
    """
    entries = []
    for entry in os.scandir(src_dir):
        dest = os.path.join(dest_prefix, entry.name)
        if entry.is_symlink():
            entries.append((dest, os.readlink(entry.path), 'SYMLINK'))
        elif entry.is_dir():
            entries += _collect_tree_preserving_symlinks(entry.path, dest)
        else:
            entries.append((dest, entry.path, 'DATA'))
    return entries


for chromium_dir in chromium_dirs:
    chromium_rev_name = os.path.basename(os.path.normpath(chromium_dir))
    dest_prefix = os.path.join('playwright_browsers', chromium_rev_name)
    a.datas += _collect_tree_preserving_symlinks(chromium_dir, dest_prefix)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe_name = 'mycartime' if VARIANT == 'lite' else 'mycartime-full'

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=exe_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
