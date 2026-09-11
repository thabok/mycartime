"""
Filesystem locations for writable runtime state and read-only bundled assets.

These are split because the packaged build (Nuitka standalone, spawned by the
Tauri shell as a sidecar) inherits an arbitrary working directory and lives in a
read-only app bundle: writable state has to go to a per-user data directory,
while assets ship next to the executable.
"""
import os
import sys

from platformdirs import user_data_dir

APP_NAME = 'mycartime'

# Nuitka defines __compiled__ in every module it compiles.
IS_PACKAGED = '__compiled__' in globals()

_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))


def _resolve_data_dir() -> str:
    # Tauri passes APP_DATA_DIR when spawning the sidecar so both sides agree on
    # where settings and logs live; the fallback keeps unpackaged runs working.
    return os.environ.get('APP_DATA_DIR') or user_data_dir(APP_NAME, appauthor=False)


APP_DATA_DIR = _resolve_data_dir()
os.makedirs(APP_DATA_DIR, exist_ok=True)


def data_path(*parts: str) -> str:
    """Absolute path for writable state (cache, logs, settings, captures)."""
    return os.path.join(APP_DATA_DIR, *parts)


def _resource_roots() -> list[str]:
    if IS_PACKAGED:
        return [os.path.dirname(os.path.abspath(sys.executable))]
    # Unpackaged, assets sit either next to the code (assistant/skill) or at the
    # repo root (doc/), which the Nuitka build flattens into one dist directory.
    return [_MODULE_DIR, os.path.abspath(os.path.join(_MODULE_DIR, '..', '..'))]


def resource_path(*parts: str) -> str:
    """Absolute path for read-only assets shipped alongside the code."""
    relative = os.path.join(*parts)
    roots = _resource_roots()
    for root in roots:
        candidate = os.path.join(root, relative)
        if os.path.exists(candidate):
            return candidate
    return os.path.join(roots[0], relative)
