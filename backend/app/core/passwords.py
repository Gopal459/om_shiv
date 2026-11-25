import hashlib
import os
import secrets
from typing import Tuple

ITERATIONS = 100_000
ALGORITHM = "sha256"


def hash_password(password: str) -> str:
    """Hashes password with PBKDF2-HMAC-SHA256 and a random 16-byte salt."""
    salt = secrets.token_bytes(16)
    key = hashlib.pbkdf2_hmac(
        ALGORITHM,
        password.encode("utf-8"),
        salt,
        ITERATIONS,
    )
    return f"pbkdf2_{ALGORITHM}${ITERATIONS}${salt.hex()}${key.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Safely verifies plain password against stored pbkdf2 hash."""
    if not hashed_password or not isinstance(hashed_password, str):
        return False
    parts = hashed_password.split("$")
    if len(parts) != 4 or parts[0] != f"pbkdf2_{ALGORITHM}":
        return False
    try:
        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
        expected_key = bytes.fromhex(parts[3])
    except (ValueError, TypeError):
        return False

    key = hashlib.pbkdf2_hmac(
        ALGORITHM,
        plain_password.encode("utf-8"),
        salt,
        iterations,
    )
    return secrets.compare_digest(key, expected_key)
