"""
Financial Modelling Platform – FastAPI application entry point.
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app.config import settings
from app.database import init_db
from app.api import documents, extraction, modelling, export


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("Starting Financial Modelling Platform...")
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    init_db()
    logger.info("Database initialised.")
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "AI-powered financial modelling platform. "
        "Upload documents, extract structured data, and build dynamic financial models."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ─────────────────────────────────────────────────────────────────
app.include_router(documents.router, prefix="/api")
app.include_router(extraction.router, prefix="/api")
app.include_router(modelling.router, prefix="/api")
app.include_router(export.router, prefix="/api")


# ── Health check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/", tags=["root"])
def root():
    return {
        "message": "Financial Modelling Platform API",
        "docs": "/docs",
        "health": "/health",
    }
