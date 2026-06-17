"""Security utilities for hashing and JWT."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

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

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
) -> str:
    """Decode the JWT and return the authenticated username. Raises 401 on any failure."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: Optional[str] = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    return username
