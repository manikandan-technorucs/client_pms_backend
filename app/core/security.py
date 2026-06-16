"""Security utilities for hashing and JWT."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from passlib.context import CryptContext
import jwt

from app.core.config import settings

# ── Secret Key Validation ─────────────────────────────────────────────────────
# IMPORTANT: SECRET_KEY MUST be set in the environment for production.
# A weak/default key means all JWT tokens can be forged.
_INSECURE_DEFAULTS = {
    "super-secret-key-change-me",
    "secret",
    "changeme",
    "your-secret-key",
    "",
}

SECRET_KEY = settings.SECRET_KEY

if not SECRET_KEY or SECRET_KEY.strip() in _INSECURE_DEFAULTS:
    raise RuntimeError(
        "\n\n"
        "═══════════════════════════════════════════════════════════════\n"
        "  FATAL: SECRET_KEY is not set or is insecure!\n"
        "  Set a strong SECRET_KEY in your .env file before starting.\n"
        "  Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\"\n"
        "═══════════════════════════════════════════════════════════════\n"
    )

ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
