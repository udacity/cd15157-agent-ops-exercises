"""Authentication (demo). A password proves identity; a flag only claims it.

Passwords are salted PBKDF2 hashes (stdlib). Every seeded demo user shares
``DEV_PASSWORD`` — local convenience, not a security model.
"""

import hashlib
import hmac
import os

from realthor.sessions import get_user

DEV_PASSWORD = "realthor-dev"

_PBKDF2_ROUNDS = 120_000
_SALT_BYTES = 16


def hash_password(password: str, salt: bytes | None = None) -> str:
    if salt is None:
        salt = os.urandom(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ROUNDS)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, hash_hex = stored.split("$", 1)
        salt = bytes.fromhex(salt_hex)
    except (ValueError, AttributeError):
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ROUNDS)
    return hmac.compare_digest(candidate.hex(), hash_hex)


def authenticate(app_db_path: str, user_id: str, password: str):
    """Return a UserContext only after the password checks out; else None."""
    # Imported here to avoid a circular import (context imports from sessions too).
    from realthor.context import UserContext

    row = get_user(app_db_path, user_id)
    if row is None or not verify_password(password, str(row["password_hash"])):
        return None
    return UserContext(
        user_id=str(row["user_id"]),
        role=str(row["role"]),
        region_access=str(row["region_access"]),
    )
