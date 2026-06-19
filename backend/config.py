"""
config.py — Central settings for the Codebase Intelligence Agent.

All settings are read from environment variables (via .env).
Uses pydantic-settings for validation and type coercion.
"""

from functools import lru_cache # memoization decorator
from typing import List

from pydantic import AnyHttpUrl, Field # http url field 
from pydantic_settings import BaseSettings, SettingsConfigDict # base settings 


class Settings(BaseSettings):
    """Application-wide configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ────────────────────────────────────────────────────────────
    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")
    secret_key: str = Field(default="change-me-in-production")

    # ── Ollama ─────────────────────────────────────────────────────────────────
    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_llm_model: str = Field(default="gemma4:latest")
    ollama_embedding_model: str = Field(default="qwen3-embedding:4b")
    ollama_embedding_dim: int = Field(default=2560)

    # ── Mem0 Cloud ─────────────────────────────────────────────────────────────
    mem0_api_key: str = Field(default="")

    # ── Qdrant ─────────────────────────────────────────────────────────────────
    qdrant_url: str = Field(default="http://localhost:6333")
    qdrant_api_key: str = Field(default="")
    qdrant_collection_name: str = Field(default="codebase_chunks")

    # ── Neo4j AuraDB ───────────────────────────────────────────────────────────
    neo4j_uri: str = Field(default="neo4j+s://xxxxxxxx.databases.neo4j.io")
    neo4j_username: str = Field(default="neo4j")
    neo4j_password: str = Field(default="")

    # ── Redis ──────────────────────────────────────────────────────────────────
    redis_url: str = Field(default="redis://localhost:6379/0")
    celery_broker_url: str = Field(default="redis://localhost:6379/1")
    celery_result_backend: str = Field(default="redis://localhost:6379/2")
    embedding_cache_ttl: int = Field(default=604800)  # 7 days

    # ── Postgres ───────────────────────────────────────────────────────────────
    database_url: str = Field(
        default="postgresql+asyncpg://agent:changeme123@localhost:5432/codebase_agent"
    )

    # ── GitHub ─────────────────────────────────────────────────────────────────
    github_token: str = Field(default="")

    # ── Ingestion Limits ───────────────────────────────────────────────────────
    max_repo_size_mb: int = Field(default=500)
    max_repo_files: int = Field(default=10000)
    repo_clone_timeout_seconds: int = Field(default=120)
    temp_repo_dir: str = Field(default="/tmp/repos")

    # ── CORS ───────────────────────────────────────────────────────────────────
    allowed_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:3001"]
    )

    # ── Rate Limiting ──────────────────────────────────────────────────────────
    chat_rate_limit: str = Field(default="20/minute")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings singleton. Use this everywhere — do not import Settings directly."""
    return Settings()
