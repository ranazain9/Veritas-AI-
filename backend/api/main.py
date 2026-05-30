"""FastAPI application — production entry: uvicorn backend.api.main:app"""

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import api_router, public_router
from backend.audit_store import init_db

load_dotenv()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    origins = os.getenv("CORS_ORIGINS", "*").split(",")
    application = FastAPI(
        title="Veritas AI API",
        description="Counter-deception multi-agent compliance audits",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in origins if o.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(public_router)
    application.include_router(api_router)
    return application


app = create_app()
