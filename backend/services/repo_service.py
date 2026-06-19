"""
services/repo_service.py — Business logic for repository ingestion.

Handles:
- GitHub URL validation and cloning
- ZIP file upload, extraction, and zip-slip protection
- Metadata extraction (language detection, framework signals)
- Ingestion job CRUD in Postgres
- Socket.IO status broadcast

Deliberately separated from the HTTP layer (api/repo.py) so it's
independently testable and reusable by the Celery worker.
"""

import hashlib # it is used to calculate the hash of the files
import mimetypes # it is used to determine the MIME type of a file
import os
import re # it is used to match the regex of the files
import shutil # it is used to remove the files Shell Utils
import uuid # it is used to generate the UUID of the files
import zipfile # it is used to extract the files
from pathlib import Path 
from typing import Any, Dict, Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import IngestionJob
from config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


# ── Constants ──────────────────────────────────────────────────────────────────

GITHUB_URL_RE = re.compile(
    r"^https?://github\.com/(?P<owner>[\w.-]+)/(?P<repo>[\w.-]+?)(?:\.git)?/?$"
)

# Framework signal files → framework name
FRAMEWORK_SIGNALS: Dict[str, str] = {
    "package.json":       "node",
    "requirements.txt":   "python",
    "pyproject.toml":     "python",
    "setup.py":           "python",
    "Cargo.toml":         "rust",
    "pom.xml":            "java-maven",
    "build.gradle":       "java-gradle",
    "go.mod":             "go",
    "Gemfile":            "ruby",
    "composer.json":      "php",
    "tsconfig.json":      "typescript",
    "next.config.js":     "nextjs",
    "next.config.mjs":    "nextjs",
    "vite.config.ts":     "vite",
    "vite.config.js":     "vite",
    "Dockerfile":         "docker",
    "docker-compose.yml": "docker-compose",
    ".github":            "github-actions",
}

# Extension → language mapping
EXTENSION_LANGUAGES: Dict[str, str] = {
    ".py":   "python",
    ".js":   "javascript",
    ".ts":   "typescript",
    ".tsx":  "typescript",
    ".jsx":  "javascript",
    ".java": "java",
    ".go":   "go",
    ".rs":   "rust",
    ".rb":   "ruby",
    ".php":  "php",
    ".cs":   "csharp",
    ".cpp":  "cpp",
    ".c":    "c",
    ".h":    "c",
    ".md":   "markdown",
    ".yaml": "yaml",
    ".yml":  "yaml",
    ".json": "json",
    ".toml": "toml",
    ".sh":   "shell",
    ".sql":  "sql",
}

# Directories to skip during metadata scan
SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv",
    ".next", "dist", "build", "target", "vendor", ".idea", ".vscode",
}


# ── Job CRUD ───────────────────────────────────────────────────────────────────

async def create_job(
    db: AsyncSession,
    repo_url: Optional[str] = None,
    repo_name: Optional[str] = None,
) -> IngestionJob:
    """Insert a new ingestion job in 'pending' state."""
    job = IngestionJob(
        id=uuid.uuid4(), #uuid4 is a function that generates a random UUID
        status="pending",
        repo_url=repo_url,
        repo_name=repo_name,
    )
    db.add(job)
    await db.flush()  # get the id without committing
    logger.info("Ingestion job created", job_id=str(job.id), repo_url=repo_url)
    return job


async def get_job(db: AsyncSession, job_id: str) -> Optional[IngestionJob]:
    """Fetch a job by UUID string. Returns None if not found."""
    try:
        uid = uuid.UUID(job_id) # convert string to UUID
    except ValueError:
        return None
    result = await db.execute(select(IngestionJob).where(IngestionJob.id == uid))
    return result.scalar_one_or_none() # returns the first result or None if no result


async def update_job_status(
    db: AsyncSession,
    job_id: str,
    status: str,
    *,
    metadata: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None,
    total_files: Optional[int] = None,
    processed_files: Optional[int] = None,
    total_chunks: Optional[int] = None,
) -> Optional[IngestionJob]:
    """Update a job's status and optional fields. Commits the session."""
    job = await get_job(db, job_id)
    if not job:
        logger.warning("update_job_status: job not found", job_id=job_id)
        return None

    job.status = status
    if metadata is not None:
        job.repo_metadata = metadata
    if error_message is not None:
        job.error_message = error_message
    if total_files is not None:
        job.total_files = total_files
    if processed_files is not None:
        job.processed_files = processed_files
    if total_chunks is not None:
        job.total_chunks = total_chunks

    await db.commit()
    await db.refresh(job)
    logger.info("Ingestion job updated", job_id=job_id, status=status)
    return job


# ── Validation ─────────────────────────────────────────────────────────────────

def validate_github_url(url: str) -> str:
    """
    Validate and normalise a GitHub URL.

    Returns the cleaned URL on success.
    Raises ValueError with a user-facing message on failure.
    """
    url = url.strip().rstrip("/")
    if not GITHUB_URL_RE.match(url):
        raise ValueError(
            "Invalid GitHub URL. Expected format: https://github.com/owner/repo"
        )
    return url


def extract_repo_name_from_url(url: str) -> str:
    """Extract 'owner/repo' from a GitHub URL."""
    m = GITHUB_URL_RE.match(url)
    if m:
        return f"{m.group('owner')}/{m.group('repo')}"
    return url.split("/")[-1]


# ── Metadata extraction ────────────────────────────────────────────────────────

def extract_repo_metadata(repo_path: Path) -> Dict[str, Any]:
    """
    Walk a cloned/extracted repo and collect:
    - File count and breakdown by language
    - Detected framework signals
    - Rough size in bytes
    - Top-level directory structure

    Skips common noise dirs (node_modules, .git, __pycache__, etc).
    """
    language_counts: Dict[str, int] = {}
    detected_frameworks: list[str] = []
    total_files = 0
    total_bytes = 0
    top_dirs: list[str] = []

    # Top-level dirs for explorer tree
    for entry in repo_path.iterdir():
        if entry.is_dir() and entry.name not in SKIP_DIRS:
            top_dirs.append(entry.name)
        elif entry.is_file():
            top_dirs.append(entry.name)

    # Check framework signals at repo root
    for signal_file, framework in FRAMEWORK_SIGNALS.items():
        if (repo_path / signal_file).exists():
            if framework not in detected_frameworks:
                detected_frameworks.append(framework)

    # Walk the tree
    for root, dirs, files in os.walk(repo_path):
        # Prune skip dirs in-place so os.walk doesn't descend into them
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        for fname in files:
            fpath = Path(root) / fname
            try:
                size = fpath.stat().st_size
            except OSError:
                continue

            total_files += 1
            total_bytes += size

            ext = fpath.suffix.lower()
            lang = EXTENSION_LANGUAGES.get(ext, "other")
            language_counts[lang] = language_counts.get(lang, 0) + 1

    # Sort languages by file count descending
    sorted_languages = dict(
        sorted(language_counts.items(), key=lambda x: x[1], reverse=True)
    )

    return {
        "total_files": total_files,
        "total_bytes": total_bytes,
        "total_size_mb": round(total_bytes / (1024 * 1024), 2),
        "languages": sorted_languages,
        "primary_language": next(iter(sorted_languages), "unknown"),
        "frameworks": detected_frameworks,
        "top_level_entries": sorted(top_dirs),
    }


# ── ZIP handling ───────────────────────────────────────────────────────────────

def validate_and_extract_zip(zip_path: Path, extract_to: Path) -> Path:
    """
    Extract a ZIP file with zip-slip protection and size validation.

    Returns the path to the extracted contents root.
    Raises ValueError for invalid/malicious ZIPs.
    Raises PermissionError for zip-slip attempts.
    """
    max_bytes = settings.max_repo_size_mb * 1024 * 1024
    extract_to.mkdir(parents=True, exist_ok=True) # creates the directory if it doesn't exist

    with zipfile.ZipFile(zip_path, "r") as zf:
        # Check for zip-slip: every member path must resolve inside extract_to
        for member in zf.infolist():
            member_path = (extract_to / member.filename).resolve()
            if not str(member_path).startswith(str(extract_to.resolve())):
                raise PermissionError(
                    f"Zip-slip attempt detected in member: {member.filename}"
                )

        # Check total uncompressed size
        total_size = sum(m.file_size for m in zf.infolist())
        if total_size > max_bytes:
            raise ValueError(
                f"ZIP contents exceed size limit ({settings.max_repo_size_mb} MB). "
                f"Got {total_size / (1024*1024):.1f} MB."
            )

        zf.extractall(extract_to)

    # If the zip contained a single top-level directory, return that as the root
    entries = list(extract_to.iterdir())
    if len(entries) == 1 and entries[0].is_dir():
        return entries[0]
    return extract_to


# ── Temp directory management ──────────────────────────────────────────────────

def get_job_dir(job_id: str) -> Path:
    """Return the temp working directory for a job (not created yet)."""
    return Path(settings.temp_repo_dir) / job_id


def cleanup_job_dir(job_id: str) -> None:
    """Remove the temp working directory for a job. Safe to call even if missing."""
    job_dir = get_job_dir(job_id)
    if job_dir.exists():
        shutil.rmtree(job_dir, ignore_errors=True)
        logger.info("Cleaned up job directory", job_id=job_id, path=str(job_dir))
