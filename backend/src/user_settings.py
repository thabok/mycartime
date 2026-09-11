"""
Persistence for the handful of config.py values that end users can edit at
runtime via the frontend Settings dialog (see /api/v1/settings in app.py),
without requiring a source change or restart.
"""
import json
import logging
import os

import config
import paths

logger = logging.getLogger(__name__)

SETTINGS_FILE = paths.data_path('user_settings.json')

# Keys editable via the Settings dialog, and how to validate an incoming
# value for each. WEBUNTIS_SCHOOL intentionally allows an empty string - some
# WebUntis tenants (like ours) don't need one.
EDITABLE_SETTINGS = {
    'WEBUNTIS_SERVER': lambda v: isinstance(v, str) and v.strip() != '',
    'WEBUNTIS_SCHOOL': lambda v: isinstance(v, str),
    'TIME_TOLERANCE_MINUTES': lambda v: isinstance(v, int) and not isinstance(v, bool) and v >= 0,
    'MAX_DRIVES_FULLTIME': lambda v: isinstance(v, int) and not isinstance(v, bool) and v >= 0,
    'MAX_DRIVES_PARTTIME': lambda v: isinstance(v, int) and not isinstance(v, bool) and v >= 0,
    'ANTHROPIC_API_KEY': lambda v: isinstance(v, str),
    'CLAUDE_CLI_PATH': lambda v: isinstance(v, str),
}

# Persisted like everything else, but never sent back to the client - callers
# get a boolean telling them whether one is stored instead. The settings file
# is written user-only (0600) because of these.
SECRET_SETTINGS = {'ANTHROPIC_API_KEY'}


def load_and_apply():
    """Apply any persisted overrides onto the config module. Call once at startup."""
    if not os.path.exists(SETTINGS_FILE):
        return
    try:
        with open(SETTINGS_FILE, 'r') as f:
            saved = json.load(f)
    except Exception:
        logger.warning(f"Could not read {SETTINGS_FILE}, ignoring", exc_info=True)
        return
    for key, value in saved.items():
        if key in EDITABLE_SETTINGS:
            setattr(config, key, value)


def _effective_values():
    """Everything that gets persisted, secrets included."""
    return {key: getattr(config, key) for key in EDITABLE_SETTINGS}


def get_current():
    """Current effective values, with secrets reduced to a "<KEY>_SET" flag."""
    exposed = {key: value for key, value in _effective_values().items()
               if key not in SECRET_SETTINGS}
    for key in SECRET_SETTINGS:
        exposed[f'{key}_SET'] = bool(getattr(config, key))
    return exposed


def update(values: dict):
    """Validate, persist, and apply a partial update. Raises ValueError on bad input."""
    for key, value in values.items():
        if key not in EDITABLE_SETTINGS:
            raise ValueError(f"Unknown setting: {key}")
        if not EDITABLE_SETTINGS[key](value):
            raise ValueError(f"Invalid value for {key}: {value!r}")

    current = _effective_values()
    current.update(values)

    # Created 0600 rather than chmod'd afterwards, so the API key is never
    # briefly readable by other accounts on a shared machine.
    fd = os.open(SETTINGS_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as f:
        json.dump(current, f, indent=2)
    os.chmod(SETTINGS_FILE, 0o600)

    for key, value in values.items():
        setattr(config, key, value)

    return get_current()
