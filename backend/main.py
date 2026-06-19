"""
main.py — FastAPI application entry point.

Initialises the app, configures middleware, registers routers,
and manages the lifespan of all external service connections.
"""

import structlog
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import socketio

from config import get_settings
from api import health, repo, search, graph, memory, chat
from api.db import init_db

logger = structlog.get_logger(__name__)
settings = get_settings()


# ── Socket.IO ─────────────────────────────────────────────────────────────────
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=settings.allowed_origins,
    logger=False,
    engineio_logger=False,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup / shutdown lifecycle manager."""
    logger.info("Starting Codebase Intelligence Agent", environment=settings.environment)

    # Initialise database tables
    await init_db()
    logger.info("Database initialised")

    yield  # ← app is running

    logger.info("Shutting down Codebase Intelligence Agent")


# ── FastAPI App ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Codebase Intelligence Agent",
    description="Hybrid-RAG system for natural-language code analysis.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ───────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(health.router, tags=["Infrastructure"])
app.include_router(repo.router,   prefix="/repo",   tags=["Repository"])
app.include_router(search.router, prefix="/search", tags=["Search"])
app.include_router(graph.router,  prefix="/repo",   tags=["Graph"])
app.include_router(memory.router, prefix="/memory", tags=["Memory"])
app.include_router(chat.router,   prefix="/chat",   tags=["Chat"])

# ── Mount Socket.IO ────────────────────────────────────────────────────────────
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)
