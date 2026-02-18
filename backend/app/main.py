"""FastAPI application entry point."""
import logging
import structlog
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db
from app.api.documents import router as documents_router
from app.api.financial_data import router as financial_data_router
from app.api.modelling import router as modelling_router
from app.api.export import router as export_router

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)
logging.basicConfig(level=logging.INFO if not settings.debug else logging.DEBUG)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise database tables on startup."""
    logger.info("Starting Financial Modelling Platform...")
    await init_db()
    logger.info("Database initialised.")
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered financial document extraction and modelling platform",
    lifespan=lifespan,
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Routers
app.include_router(documents_router, prefix="/api/v1")
app.include_router(financial_data_router, prefix="/api/v1")
app.include_router(modelling_router, prefix="/api/v1")
app.include_router(export_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": settings.app_version}


@app.get("/api/v1/info")
async def api_info():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "endpoints": {
            "documents": "/api/v1/documents",
            "financial_data": "/api/v1/financial-data",
            "models": "/api/v1/models",
            "export": "/api/v1/export",
        },
    }
