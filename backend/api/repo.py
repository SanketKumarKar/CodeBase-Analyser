"""
api/repo.py — Repository ingestion endpoints (Phase 2).

Routes:
  POST /repo/upload      — start an ingestion job (GitHub URL or ZIP)
  GET  /repo/status/{id} — poll job status
"""

import os
import tempfile
import uuid
from pathlib import Path
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import get_session
from config import get_settings
from services.repo_service import (
    create_job,
    extract_repo_name_from_url,
    get_job,
    validate_github_url,
)
from workers.ingestion import ingest_repository

logger = structlog.get_logger(__name__)
router = APIRouter()
settings = get_settings()


# ── Request / Response schemas ─────────────────────────────────────────────────
# pydantic is used for data validation

class UploadByURLRequest(BaseModel):
    github_url: str

    @field_validator("github_url") # validator is used to validate the github_url
    @classmethod
    def validate_url(cls, v: str) -> str: # cls is the class itself, v is the value to be validated
        return validate_github_url(v)


class JobResponse(BaseModel): # response model is used to define the response
    job_id: str # unique identifier for the job
    status: str # status of the job
    repo_url: Optional[str] = None # url of the repository
    repo_name: Optional[str] = None # name of the repository
    metadata: Optional[dict] = None # metadata of the repository
    error_message: Optional[str] = None # error message if the job failed
    total_files: Optional[int] = None # total number of files in the repository
    processed_files: Optional[int] = None # number of files processed in the repository
    total_chunks: Optional[int] = None # total number of chunks in the repository
    created_at: Optional[str] = None # time when the job was created
    updated_at: Optional[str] = None # time when the job was updated


# ── POST /repo/upload ──────────────────────────────────────────────────────────

@router.post(
    "/upload",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start a repository ingestion job",
)
async def upload_repo(
    # Multipart fields — both optional so we can handle URL-only JSON too
    github_url: Optional[str] = Form(default=None),
    file: Optional[UploadFile] = File(default=None),
    db: AsyncSession = Depends(get_session),
) -> JSONResponse:
    """
    Start an ingestion job from either a GitHub URL or a ZIP file upload.

    Returns immediately with a `job_id`. Poll `GET /repo/status/{job_id}`
    or listen on Socket.IO room `job_id` for real-time progress.

    - **github_url** (form field): public GitHub repo URL
    - **file** (multipart): ZIP archive of the repository
    """
    if not github_url and not file:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide either a 'github_url' form field or a ZIP file upload.",
        )

    # ── GitHub URL path ────────────────────────────────────────────────────
    if github_url:
        try:
            clean_url = validate_github_url(github_url)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

        repo_name = extract_repo_name_from_url(clean_url)
        job = await create_job(db, repo_url=clean_url, repo_name=repo_name)

        # Dispatch Celery task asynchronously
        ingest_repository.delay(str(job.id), repo_url=clean_url)

        logger.info("Ingestion job queued (URL)", job_id=str(job.id), repo_url=clean_url)
        return JSONResponse(status_code=202, content=job.to_dict())

    # ── ZIP upload path ────────────────────────────────────────────────────
    if file:
        # Validate content type
        if file.content_type not in ("application/zip", "application/x-zip-compressed"):
            raise HTTPException(
                status_code=400,
                detail=f"Expected a ZIP file, got '{file.content_type}'.",
            )

        # Check filename
        if not (file.filename or "").endswith(".zip"):
            raise HTTPException(status_code=400, detail="File must have a .zip extension.")

        # Save upload to temp file (streaming, not fully in memory)
        max_bytes = settings.max_repo_size_mb * 1024 * 1024
        temp_dir = Path(settings.temp_repo_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)

        job_id = str(uuid.uuid4())
        zip_save_path = temp_dir / job_id / "upload.zip"
        zip_save_path.parent.mkdir(parents=True, exist_ok=True)

        bytes_written = 0
        try:
            with open(zip_save_path, "wb") as fp:
                while chunk := await file.read(8192):
                    bytes_written += len(chunk)
                    if bytes_written > max_bytes:
                        raise HTTPException(
                            status_code=413,
                            detail=f"ZIP exceeds size limit of {settings.max_repo_size_mb} MB.",
                        )
                    fp.write(chunk)
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("ZIP save failed", error=str(exc))
            raise HTTPException(status_code=500, detail="Failed to save uploaded file.")

        repo_name = Path(file.filename).stem
        job = await create_job(db, repo_name=repo_name)

        # Dispatch Celery task
        ingest_repository.delay(str(job.id), zip_path=str(zip_save_path))

        logger.info("Ingestion job queued (ZIP)", job_id=str(job.id), filename=file.filename)
        return JSONResponse(status_code=202, content=job.to_dict())


# ── GET /repo/status/{job_id} ─────────────────────────────────────────────────

@router.get(
    "/status/{job_id}",
    response_model=JobResponse,
    summary="Get ingestion job status",
)
async def repo_status(
    job_id: str,
    db: AsyncSession = Depends(get_session),
) -> dict:
    """
    Poll the status of an ingestion job.

    Status values: `pending` → `cloning` → `parsing` → `embedding` → `graphing` → `ready` | `failed`
    """
    job = await get_job(db, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        )
    return job.to_dict()
    # {
    #     "total_files": total_files,
    #     "total_bytes": total_bytes,
    #     "total_size_mb": round(total_bytes / (1024 * 1024), 2),
    #     "languages": sorted_languages,
    #     "primary_language": next(iter(sorted_languages), "unknown"),
    #     "frameworks": detected_frameworks,
    #     "top_level_entries": sorted(top_dirs),
    # }
