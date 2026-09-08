"""
Persistence for the handful of config.py values that end users can edit at
runtime via the frontend Preferences dialog (see /api/v1/settings in app.py),
without requiring a source change or restart.
"""
import json
import logging
import os

import apppaths
import config

logger = logging.getLogger(__name__)

SETTINGS_FILE = apppaths.data_path('user_settings.json')

# Keys editable via the Preferences dialog, and how to validate an incoming
# value for each. WEBUNTIS_SCHOOL intentionally allows an empty string - some
# WebUntis tenants (like ours) don't need one.
EDITABLE_SETTINGS = {
    'WEBUNTIS_SERVER': lambda v: isinstance(v, str) and v.strip() != '',
    'WEBUNTIS_SCHOOL': lambda v: isinstance(v, str),
    'TIME_TOLERANCE_MINUTES': lambda v: isinstance(v, int) and not isinstance(v, bool) and v >= 0,
    'MAX_DRIVES_FULLTIME': lambda v: isinstance(v, int) and not isinstance(v, bool) and v >= 0,
    'MAX_DRIVES_PARTTIME': lambda v: isinstance(v, int) and not isinstance(v, bool) and v >= 0,
}


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


def get_current():
    """Current effective values (defaults, or persisted overrides if any)."""
    return {key: getattr(config, key) for key in EDITABLE_SETTINGS}


def update(values: dict):
    """Validate, persist, and apply a partial update. Raises ValueError on bad input."""
    for key, value in values.items():
        if key not in EDITABLE_SETTINGS:
            raise ValueError(f"Unknown setting: {key}")
        if not EDITABLE_SETTINGS[key](value):
            raise ValueError(f"Invalid value for {key}: {value!r}")

    current = get_current()
    current.update(values)

    with open(SETTINGS_FILE, 'w') as f:
        json.dump(current, f, indent=2)

    for key, value in values.items():
        setattr(config, key, value)

    return current
