"""
workers/ingestion.py — Celery ingestion pipeline task (Phase 2).

Pipeline stages:
  1. Clone (git) or extract (ZIP) the repository
  2. Extract metadata (languages, frameworks, file count)
  3. Update Postgres job status throughout
  4. Emit Socket.IO events for real-time frontend updates

Phase 3+ stubs are called at the end of this task:
  - parse_repository()   → Phase 3
  - embed_and_store()    → Phase 4
  - build_graph()        → Phase 5
"""

import os
import subprocess
import tempfile
from pathlib import Path

import structlog

from config import get_settings
from services.repo_service import (
    cleanup_job_dir,
    extract_repo_metadata,
    get_job_dir,
    validate_and_extract_zip,
)
from workers.celery_app import celery_app

logger = structlog.get_logger(__name__)
settings = get_settings()


def _emit_status(job_id: str, status: str, payload: dict) -> None:
    """
    Emit a Socket.IO event to notify the frontend of job progress.

    Uses the socketio server imported from main at call time to avoid
    circular imports during Celery worker startup.
    """
    try:
        # Lazy import to avoid circular dependency with FastAPI app
        import asyncio
        from main import sio

        async def _emit():
            await sio.emit(
                "ingestion_status",
                {"job_id": job_id, "status": status, **payload},
                room=job_id,
            )

        loop = asyncio.new_event_loop()
        loop.run_until_complete(_emit())
        loop.close()
    except Exception as exc:
        # Non-fatal — status is persisted in Postgres regardless
        logger.warning("Socket.IO emit failed", job_id=job_id, error=str(exc))


def _update_db_status(job_id: str, status: str, **kwargs) -> None:
    """Synchronous wrapper to update job status in Postgres from Celery worker."""
    import asyncio
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from services.repo_service import update_job_status

    async def _update():
        engine = create_async_engine(settings.database_url)
        Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with Session() as session:
            await update_job_status(session, job_id, status, **kwargs)
            await session.commit()
        await engine.dispose()

    loop = asyncio.new_event_loop()
    loop.run_until_complete(_update())
    loop.close()


def _clone_repo(repo_url: str, target_dir: Path, timeout: int) -> None:
    """
    Shallow-clone a GitHub repo into target_dir.

    Uses `--depth 1` for speed and `--single-branch` to avoid fetching
    all branches. Enforces a wall-clock timeout.

    Raises subprocess.TimeoutExpired or subprocess.CalledProcessError on failure.
    """
    target_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "git", "clone",
        "--depth", "1",
        "--single-branch",
        "--no-tags",
    ]

    # Inject GitHub token if available (enables private repos)
    github_token = settings.github_token
    if github_token:
        # Embed token in URL: https://token@github.com/...
        authenticated_url = repo_url.replace(
            "https://", f"https://{github_token}@"
        )
        cmd.append(authenticated_url)
    else:
        cmd.append(repo_url)

    cmd.append(str(target_dir))

    logger.info("Cloning repository", repo_url=repo_url, target=str(target_dir))

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=True,
    )
    logger.info("Clone complete", stdout=result.stdout[:200])


@celery_app.task(
    bind=True,
    name="workers.ingestion.ingest_repository",
    max_retries=2,
    default_retry_delay=10,
)
def ingest_repository(
    self,
    job_id: str,
    repo_url: str | None = None,
    zip_path: str | None = None,
) -> dict:
    """
    Main ingestion pipeline task.

    Called via: ingest_repository.delay(job_id, repo_url=...) or
                ingest_repository.delay(job_id, zip_path=...)

    Returns a summary dict stored as the Celery task result.
    """
    log = logger.bind(job_id=job_id, repo_url=repo_url)
    log.info("Ingestion task started")

    job_dir = get_job_dir(job_id)
    repo_root: Path | None = None

    try:
        # ── Stage 1: Acquire source ────────────────────────────────────────
        _update_db_status(job_id, "cloning")
        _emit_status(job_id, "cloning", {"message": "Cloning repository…"})

        if repo_url:
            repo_root = job_dir / "repo"
            _clone_repo(
                repo_url,
                repo_root,
                timeout=settings.repo_clone_timeout_seconds,
            )
        elif zip_path:
            zip_p = Path(zip_path)
            if not zip_p.exists():
                raise FileNotFoundError(f"ZIP file not found: {zip_path}")
            extract_dir = job_dir / "extracted"
            repo_root = validate_and_extract_zip(zip_p, extract_dir)
        else:
            raise ValueError("Either repo_url or zip_path must be provided.")

        # ── Stage 2: Extract metadata ──────────────────────────────────────
        _update_db_status(job_id, "parsing", metadata={"stage": "metadata"})
        _emit_status(job_id, "parsing", {"message": "Scanning repository…"})

        metadata = extract_repo_metadata(repo_root)
        total_files = metadata["total_files"]

        # Enforce file limit
        if total_files > settings.max_repo_files:
            raise ValueError(
                f"Repository has {total_files} files, exceeding the limit of "
                f"{settings.max_repo_files}. Please use a smaller repository."
            )

        log.info("Metadata extracted", **{k: v for k, v in metadata.items() if k != "languages"})

        _update_db_status(
            job_id, "parsing",
            metadata=metadata,
            total_files=total_files,
            processed_files=0,
        )
        _emit_status(job_id, "parsing", {
            "message": f"Found {total_files} files — {metadata['primary_language']} project",
            "metadata": metadata,
        })

        # ── Stage 3: Parse (Phase 3 stub) ─────────────────────────────────
        # parse_repository(repo_root, job_id) — implemented in Phase 3
        log.info("Parse stage skipped (Phase 3 not yet implemented)")

        # ── Stage 4: Embed + Qdrant (Phase 4 stub) ────────────────────────
        # embed_and_store(chunks, job_id) — implemented in Phase 4
        log.info("Embedding stage skipped (Phase 4 not yet implemented)")

        # ── Stage 5: Graph (Phase 5 stub) ─────────────────────────────────
        # build_graph(chunks, job_id) — implemented in Phase 5
        log.info("Graph stage skipped (Phase 5 not yet implemented)")

        # ── Done ───────────────────────────────────────────────────────────
        _update_db_status(
            job_id, "ready",
            metadata=metadata,
            total_files=total_files,
            processed_files=total_files,
        )
        _emit_status(job_id, "ready", {
            "message": "Repository ready for analysis",
            "metadata": metadata,
        })

        log.info("Ingestion complete", total_files=total_files)
        return {"job_id": job_id, "status": "ready", "metadata": metadata}

    except subprocess.TimeoutExpired:
        msg = f"Repository clone timed out after {settings.repo_clone_timeout_seconds}s."
        log.error("Clone timeout", timeout=settings.repo_clone_timeout_seconds)
        _update_db_status(job_id, "failed", error_message=msg)
        _emit_status(job_id, "failed", {"error": msg})
        return {"job_id": job_id, "status": "failed", "error": msg}

    except subprocess.CalledProcessError as exc:
        msg = f"Git clone failed: {exc.stderr[:300] if exc.stderr else str(exc)}"
        log.error("Clone failed", stderr=exc.stderr[:300] if exc.stderr else "")
        _update_db_status(job_id, "failed", error_message=msg)
        _emit_status(job_id, "failed", {"error": msg})
        return {"job_id": job_id, "status": "failed", "error": msg}

    except (ValueError, PermissionError, FileNotFoundError) as exc:
        msg = str(exc)
        log.error("Ingestion validation error", error=msg)
        _update_db_status(job_id, "failed", error_message=msg)
        _emit_status(job_id, "failed", {"error": msg})
        return {"job_id": job_id, "status": "failed", "error": msg}

    except Exception as exc:
        msg = f"Unexpected error: {type(exc).__name__}: {str(exc)[:300]}"
        log.exception("Ingestion task failed unexpectedly")
        _update_db_status(job_id, "failed", error_message=msg)
        _emit_status(job_id, "failed", {"error": msg})
        # Retry on unexpected errors (up to max_retries)
        raise self.retry(exc=exc)

    finally:
        # Always clean up the temp repo dir to avoid disk exhaustion
        # (parsed chunks/embeddings are stored in Qdrant/Neo4j, not on disk)
        if job_dir.exists():
            cleanup_job_dir(job_id)
            log.info("Temp directory cleaned up")
