"""
Password hashing and verification using bcrypt.

All passwords are hashed with bcrypt (cost factor 12) before storage.
Verification uses constant-time comparison to prevent timing attacks.
"""

import bcrypt


def get_password_hash(password: str) -> str:
    """Hash a plain-text password using bcrypt.

    Uses a random salt with cost factor 12 (2^12 = 4096 iterations).
    The salt is embedded in the output hash (60-char string), so
    no separate salt storage is needed.

    bcrypt format: $2b$12$[22-char-salt][31-char-hash]
    """
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password_bytes, salt).decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain-text password against a bcrypt hash.

    Uses bcrypt.checkpw() which extracts the salt from the stored hash,
    re-hashes the input password with the same salt, and compares.
    The try/except catches malformed hash strings gracefully.
    """
    try:
        return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False
