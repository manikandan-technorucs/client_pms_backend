"""FastAPI application entrypoint."""
from __future__ import annotations

import sys
import asyncio

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.core.config import settings
from app.routers import auth, bugs, projects, tasks, attachments

# Initialize Sentry
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )

# Setup Loguru
logger.remove()
logger.add(sys.stderr, format="{time} {level} {message}", level="INFO")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Project Management System — Projects, Tasks, Bugs with file attachments.",
    version=settings.VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(projects.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")
app.include_router(bugs.router, prefix="/api/v1")
app.include_router(attachments.router, prefix="/api/v1")


@app.get("/", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "TechnoRUCS PMS API"}
