"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from backend.app.core.config import settings
from backend.app.db.models import Base
from backend.app.db.session import engine


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="API for the synthetic Fraud Command Center portfolio project.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", tags=["system"])
def health() -> dict:
    """Return service and database health for local and deployment checks."""

    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.app_env,
        "database": "connected",
    }


@app.get("/", include_in_schema=False)
def root() -> dict:
    return {"message": "Fraud Command Center API", "docs": "/docs"}
