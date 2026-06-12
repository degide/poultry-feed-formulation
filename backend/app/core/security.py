"""Security primitives: password hashing (bcrypt) and JWT.

We use the `bcrypt` library directly rather than via passlib to avoid the
well-known passlib/bcrypt-4.x version-probe incompatibility, and `python-jose`
for JWT encode/decode. Tokens carry the user id in `sub` and expire after
ACCESS_TOKEN_EXPIRE_MINUTES (24h by default).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

# bcrypt has a hard 72-byte input limit; longer passwords are truncated.
_BCRYPT_MAX_BYTES = 72


def hash_password(password: str) -> str:
    pw = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        pw = plain_password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
        return bcrypt.checkpw(pw, password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(
    subject: str | int,
    expires_delta: timedelta | None = None,
) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta
        or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {"sub": str(subject), "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> int | None:
    """Return the user id encoded in the token, or None if invalid/expired."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        sub = payload.get("sub")
        return int(sub) if sub is not None else None
    except (JWTError, ValueError):
        return None
