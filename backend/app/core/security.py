"""Security utilities: password hashing and JWT token management."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import jwt

from app.config import settings


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    pwd_bytes = password.encode("utf-8")
    if len(pwd_bytes) > 72:
        raise ValueError("Password exceeds bcrypt's 72-byte limit")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    pwd_bytes = plain.encode("utf-8")[:72]
    hashed_bytes = hashed.encode("utf-8")
    return bcrypt.checkpw(pwd_bytes, hashed_bytes)


def create_access_token(
    subject: str | uuid.UUID,
    extra_claims: dict[str, Any] | None = None,
    session_id: str | None = None,
    session_token: str | None = None,
) -> str:
    """Create a short-lived JWT access token.

    If session_id/session_token are provided, they are embedded in the JWT
    so that request auth can validate the session (single sign-on + timeout).
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": "access",
        "iat": now,
        "exp": expire,
    }
    if session_id:
        payload["sid"] = session_id
    if session_token:
        payload["sess"] = session_token
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(
    subject: str | uuid.UUID,
    extra_claims: dict[str, Any] | None = None,
    session_id: str | None = None,
    session_token: str | None = None,
) -> str:
    """Create a long-lived JWT refresh token."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.refresh_token_expire_days)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": "refresh",
        "iat": now,
        "exp": expire,
    }
    if session_id:
        payload["sid"] = session_id
    if session_token:
        payload["sess"] = session_token
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token. Raises JWTError on failure."""
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
