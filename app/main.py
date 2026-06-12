"""FastAPI application entrypoint."""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.routers import auth, bugs, projects, tasks

UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(
    title="TechnoRUCS PMS API",
    description="Project Management System — Projects, Tasks, Bugs with file attachments.",
    version="1.0.0",
)

# CORS — allow Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded files as static assets
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Register routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(projects.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")
app.include_router(bugs.router, prefix="/api/v1")


@app.get("/", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "TechnoRUCS PMS API"}
