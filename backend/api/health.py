"""
api/health.py — GET /health

Pings all backing services and returns their status.
Used by Docker healthcheck and the frontend status bar.
"""

import asyncio
import time
from typing import Dict, Literal

import httpx # http client for making async requests 
import structlog # create structured logs that can be parsed by other services 
from fastapi import APIRouter # APIRouter is a class that allows you to create a router for your API 
from pydantic import BaseModel # BaseModel is a class that allows you to create a model for your API 
from redis.asyncio import Redis # redis async client 
from sqlalchemy import text # sql client for executing sql queries 
from sqlalchemy.ext.asyncio import create_async_engine # async engine for postgres 

from config import get_settings # get_settings is a function that returns the settings for the application 

logger = structlog.get_logger(__name__) # logger is a logger for the application 
router = APIRouter()
settings = get_settings()

ServiceStatus = Literal["ok", "error"] # Literal is a type hint that can be used to create a type that can only have a certain value 


class ServiceCheck(BaseModel): # create a model for your API 
    status: ServiceStatus
    latency_ms: float
    detail: str = ""


class HealthResponse(BaseModel):
    status: ServiceStatus
    services: Dict[str, ServiceCheck]
    version: str = "0.1.0"


async def _check_qdrant() -> ServiceCheck: # check qdrant service
    """Ping Qdrant REST API."""
    t0 = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client: # if more than 5 seconds pass without a response , it will time out 
            resp = await client.get(f"{settings.qdrant_url}/healthz")
            resp.raise_for_status()
        return ServiceCheck(status="ok", latency_ms=round((time.perf_counter() - t0) * 1000, 2))
    except Exception as exc:  # if any error occurs 
        logger.warning("Qdrant health check failed", error=str(exc))
        return ServiceCheck(status="error", latency_ms=0, detail=str(exc))


async def _check_neo4j() -> ServiceCheck: # check neo4j service
    """Ping Neo4j AuraDB via the bolt driver."""
    t0 = time.perf_counter()
    try:
        from neo4j import AsyncGraphDatabase # neo4j async client 

        async with AsyncGraphDatabase.driver(
            settings.neo4j_uri, # neo4j uri 
            auth=(settings.neo4j_username, settings.neo4j_password), # neo4j username and password 
        ) as driver: # neo4j driver
            await driver.verify_connectivity()
        return ServiceCheck(status="ok", latency_ms=round((time.perf_counter() - t0) * 1000, 2))
    except Exception as exc: # if any error occurs 
        logger.warning("Neo4j health check failed", error=str(exc))
        return ServiceCheck(status="error", latency_ms=0, detail=str(exc))


async def _check_redis() -> ServiceCheck: # check redis service
    """Ping Redis via asyncio client."""
    t0 = time.perf_counter()
    try:
        r = Redis.from_url(settings.redis_url, decode_responses=True)
        await r.ping()
        await r.aclose()
        return ServiceCheck(status="ok", latency_ms=round((time.perf_counter() - t0) * 1000, 2))
    except Exception as exc:
        logger.warning("Redis health check failed", error=str(exc))
        return ServiceCheck(status="error", latency_ms=0, detail=str(exc))


async def _check_postgres() -> ServiceCheck: # check postgres service
    """Ping Postgres with a trivial query."""
    t0 = time.perf_counter()
    try:
        engine = create_async_engine(settings.database_url, pool_size=1)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        await engine.dispose()
        return ServiceCheck(status="ok", latency_ms=round((time.perf_counter() - t0) * 1000, 2))
    except Exception as exc:
        logger.warning("Postgres health check failed", error=str(exc))
        return ServiceCheck(status="error", latency_ms=0, detail=str(exc))


async def _check_ollama() -> ServiceCheck: # check ollama service
    """Ping Ollama to confirm LLM + embedding models are reachable."""
    t0 = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client: # if more than 5 seconds pass without a response , it will time out 
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
            resp.raise_for_status()
            models = [m["name"] for m in resp.json().get("models", [])]
            llm_ok = any(settings.ollama_llm_model.split(":")[0] in m for m in models)
            emb_ok = any(settings.ollama_embedding_model.split(":")[0] in m for m in models)
            detail = f"LLM={settings.ollama_llm_model}({'✓' if llm_ok else '✗'}) EMB={settings.ollama_embedding_model}({'✓' if emb_ok else '✗'})"
            status: ServiceStatus = "ok" if (llm_ok and emb_ok) else "error"
        return ServiceCheck(
            status=status,
            latency_ms=round((time.perf_counter() - t0) * 1000, 2),
            detail=detail,
        )
    except Exception as exc:
        logger.warning("Ollama health check failed", error=str(exc))
        return ServiceCheck(status="error", latency_ms=0, detail=str(exc))


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Check connectivity to all backing services in parallel.

    Returns overall 'ok' only if every service is reachable.
    Individual failures are surfaced in the `services` map.
    """
    checks = await asyncio.gather(
        _check_qdrant(),
        _check_neo4j(),
        _check_redis(),
        _check_postgres(),
        _check_ollama(),
        return_exceptions=False,
    )

    services = {
        "qdrant":   checks[0],
        "neo4j":    checks[1],
        "redis":    checks[2],
        "postgres": checks[3],
        "ollama":   checks[4],
    }

    overall: ServiceStatus = "ok" if all(s.status == "ok" for s in services.values()) else "error"

    logger.info("Health check completed", overall=overall, services={k: v.status for k, v in services.items()})

    return HealthResponse(status=overall, services=services)
