"""
Encryption for secrets persisted in user_settings.json (currently just the
WebUntis password). The key lives in its own 0600 file in the app data dir,
next to the settings file it protects - this guards against casual exposure
of the settings file (backups, accidental sharing, other accounts on a
shared machine) but not against an attacker with full access to the same
machine, who could read the key file too.
"""
import os

from cryptography.fernet import Fernet

import paths

_KEY_FILE = paths.data_path('.settings_key')
_fernet = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is not None:
        return _fernet

    if os.path.exists(_KEY_FILE):
        with open(_KEY_FILE, 'rb') as f:
            key = f.read()
    else:
        # Created 0600 rather than chmod'd afterwards, so the key is never
        # briefly readable by other accounts on a shared machine.
        key = Fernet.generate_key()
        fd = os.open(_KEY_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, 'wb') as f:
            f.write(key)
        os.chmod(_KEY_FILE, 0o600)

    _fernet = Fernet(key)
    return _fernet


def encrypt(value: str) -> str:
    """Encrypt a value for storage on disk."""
    return _get_fernet().encrypt(value.encode('utf-8')).decode('ascii')


def decrypt(token: str) -> str:
    """Reverse encrypt(); raises cryptography.fernet.InvalidToken on tampered/foreign input."""
    return _get_fernet().decrypt(token.encode('ascii')).decode('utf-8')
