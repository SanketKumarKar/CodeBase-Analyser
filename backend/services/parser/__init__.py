"""
services/parser/__init__.py — Public API for the parsing subsystem.

The main entry point is `parse_repository()` which orchestrates all parsers
and returns the full list of CodeChunk objects for a repository.
"""

from pathlib import Path
from typing import List

import structlog

from services.parser.chunk_schema import CodeChunk
from services.parser.fallback_parser import parse_fallback_file
from services.parser.js_parser import parse_js_file
from services.parser.python_parser import parse_python_file

logger = structlog.get_logger(__name__)

# File extensions handled by each parser
_PYTHON_EXTENSIONS  = {".py", ".pyi"}
_JS_TS_EXTENSIONS   = {".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx"}

# Directories to always skip
_SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv",
    ".next", "dist", "build", "target", "vendor", ".idea",
}

# Extensions to skip entirely (binary / generated / lock files)
_SKIP_EXTENSIONS = {
    ".pyc", ".pyo", ".pyd",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp",
    ".woff", ".woff2", ".ttf", ".eot",
    ".zip", ".tar", ".gz", ".bz2", ".rar",
    ".exe", ".dll", ".so", ".dylib",
    ".pdf", ".doc", ".docx", ".xls",
    ".lock",           # package-lock, yarn.lock, Pipfile.lock
    ".map",            # source maps
}


def parse_repository(repo_root: Path, repo_id: str) -> List[CodeChunk]:
    """
    Walk a repository and parse all source files into CodeChunk objects.

    Dispatch logic:
      .py / .pyi       → python_parser (AST)
      .js .ts .jsx .tsx → js_parser (Tree-sitter, falls back to coarse)
      everything else  → fallback_parser (coarse, whole-file)

    Args:
        repo_root: Absolute path to the cloned/extracted repository root.
        repo_id:   Ingestion job UUID, embedded in every chunk for traceability.

    Returns:
        A flat list of all CodeChunk objects across the entire repository.
        Callers should not assume ordering.
    """
    all_chunks: List[CodeChunk] = []
    file_count  = 0
    chunk_count = 0
    skipped     = 0

    for root, dirs, files in (repo_root).walk() if hasattr(repo_root, "walk") else _os_walk(repo_root):
        # Prune skip dirs in-place
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]

        for fname in files:
            file_path = root / fname
            ext = file_path.suffix.lower()

            if ext in _SKIP_EXTENSIONS:
                skipped += 1
                continue

            file_count += 1

            try:
                if ext in _PYTHON_EXTENSIONS:
                    chunks = parse_python_file(file_path, repo_root, repo_id)
                elif ext in _JS_TS_EXTENSIONS:
                    chunks = parse_js_file(file_path, repo_root, repo_id)
                else:
                    chunks = parse_fallback_file(file_path, repo_root, repo_id)

                all_chunks.extend(chunks)
                chunk_count += len(chunks)

            except Exception as exc:  # noqa: BLE001 — never let one file break the whole parse
                logger.warning(
                    "Parser error on file — skipping",
                    path=str(file_path),
                    error=f"{type(exc).__name__}: {exc}",
                )
                skipped += 1

    logger.info(
        "Repository parsing complete",
        repo_id=repo_id,
        files_parsed=file_count,
        chunks_produced=chunk_count,
        files_skipped=skipped,
    )
    return all_chunks


def _os_walk(root: Path):
    """Compatibility shim — Path.walk() was added in Python 3.12."""
    import os
    for dirpath, dirnames, filenames in os.walk(root):
        yield Path(dirpath), dirnames, filenames
