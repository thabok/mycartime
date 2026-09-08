"""
Path resolution that works both when running from source (`python app.py`)
and when frozen into a PyInstaller onefile binary.

Two different notions of "base directory" are needed because a onefile
binary extracts itself into a fresh temp dir (`sys._MEIPASS`) on every
launch:

- RESOURCE_DIR: read-only files shipped with the app (the assistant
  skill/glossary files, doc/internal_doc.md, the built frontend, and - for
  the packaged build - the baked-in .env). Safe to resolve into the
  ephemeral extraction dir when frozen.
- DATA_DIR: files the app reads *and writes* across runs (cache, captures,
  logs, user_settings.json). Must NOT live in the ephemeral extraction dir
  when frozen, or every relaunch would silently reset them. Resolves to the
  directory containing the executable instead.

When running from source, both resolve the same way they always have
(paths relative to backend/src or the repo root), so local dev is
unaffected.
"""
import os
import sys

FROZEN = bool(getattr(sys, 'frozen', False))

_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_SRC_DIR, '..', '..'))

def _data_dir() -> str:
    if not FROZEN:
        return _SRC_DIR
    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    # Inside a macOS .app bundle (see packaging/make_app_bundles.sh), the
    # real executable lives at Foo.app/Contents/MacOS/<exe> - writing data
    # there would bury it inside the bundle (awkward to find, and wiped if
    # the user ever re-downloads/replaces the .app). Store it next to the
    # .app itself instead.
    bundle_marker = os.path.join('Contents', 'MacOS')
    if exe_dir.endswith(bundle_marker):
        app_bundle_dir = exe_dir[:-len(bundle_marker)].rstrip(os.sep)  # .../Foo.app
        return os.path.dirname(app_bundle_dir)  # folder containing Foo.app
    return exe_dir


RESOURCE_DIR = getattr(sys, '_MEIPASS', _SRC_DIR)
DATA_DIR = _data_dir()


def resource_path(*parts: str) -> str:
    """Path to a bundled read-only resource, e.g. resource_path('assistant', 'skill')."""
    return os.path.join(RESOURCE_DIR, *parts)


def data_path(*parts: str) -> str:
    """Path to a persistent, writable file, e.g. data_path('cache_dir')."""
    return os.path.join(DATA_DIR, *parts)


def doc_path(*parts: str) -> str:
    """Path to a repo-root `doc/` file. Source tree only when not frozen;
    bundled under `doc/` in RESOURCE_DIR for the packaged build."""
    base = resource_path('doc') if FROZEN else os.path.join(_REPO_ROOT, 'doc')
    return os.path.join(base, *parts)


def frontend_dist_path(*parts: str) -> str:
    """Path to the built frontend (frontend/dist). Source tree only when not
    frozen; bundled under `frontend_dist/` in RESOURCE_DIR for the packaged
    build."""
    base = resource_path('frontend_dist') if FROZEN else os.path.join(_REPO_ROOT, 'frontend', 'dist')
    return os.path.join(base, *parts)


# The "with Chromium" packaged build (see packaging/build.sh) bundles the
# Chromium build that `playwright install chromium` would otherwise download,
# under RESOURCE_DIR/playwright_browsers. Playwright reads this env var at
# import time to decide where to look for browsers, so it must be set before
# `playwright.sync_api` is imported anywhere (this module is imported first
# in app.py, ahead of export_service). Harmless no-op for the "lite" build
# (directory absent) and for running from source (not frozen).
if FROZEN:
    _bundled_browsers = resource_path('playwright_browsers')
    if os.path.isdir(_bundled_browsers):
        os.environ['PLAYWRIGHT_BROWSERS_PATH'] = _bundled_browsers
