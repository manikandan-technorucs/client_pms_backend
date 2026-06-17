"""Async database engine and session factory."""
from __future__ import annotations

import ssl
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

DATABASE_URL: str = settings.DATABASE_URL

_POOL_SIZE = settings.DB_POOL_SIZE
_MAX_OVERFLOW = settings.DB_MAX_OVERFLOW
_POOL_TIMEOUT = settings.DB_POOL_TIMEOUT
_POOL_RECYCLE = settings.DB_POOL_RECYCLE

connect_args = {}
if "azure.com" in DATABASE_URL:
    ssl_context = ssl.create_default_context()
    connect_args["ssl"] = ssl_context

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=_POOL_SIZE,
    max_overflow=_MAX_OVERFLOW,
    pool_timeout=_POOL_TIMEOUT,
    pool_recycle=_POOL_RECYCLE,
    connect_args=connect_args,
)

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that provides an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
