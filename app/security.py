"""Password hashing helpers.

Uses PBKDF2-HMAC-SHA256 from the standard library so the template has ZERO
extra crypto dependencies and runs anywhere. It's a sound, salted, iterated
hash — fine for a starter.

PRODUCTION TIP: for a real user base, prefer a memory-hard hash. Swap these two
functions for `bcrypt` or `argon2-cffi` (add the dep in pyproject.toml). The
rest of the app only calls `hash_password` / `verify_password`, so it's a
one-file change.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

_ALGORITHM = "pbkdf2_sha256"
_ITERATIONS = 240_000
_SALT_BYTES = 16


def hash_password(password: str) -> str:
    """Return an encoded hash: ``algo$iterations$salt_hex$hash_hex``."""
    salt = secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    return f"{_ALGORITHM}${_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    """Constant-time check of a plaintext password against an encoded hash."""
    try:
        algorithm, iterations_s, salt_hex, hash_hex = encoded.split("$")
        if algorithm != _ALGORITHM:
            return False
        iterations = int(iterations_s)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except (ValueError, AttributeError):
        return False

    candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return hmac.compare_digest(candidate, expected)
