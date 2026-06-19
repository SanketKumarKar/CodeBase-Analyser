"""
services/parser/fallback_parser.py — Whole-file coarse chunker.

Used for:
  1. Languages not supported by the AST/Tree-sitter parsers
     (Java, Go, Rust, Ruby, PHP, C, C++, Shell, SQL, …)
  2. Files that fail parsing due to syntax errors
  3. Very short scripts with no named definitions

Produces a single CodeChunk per file with `is_coarse = True`.
The chunk is still embedded and graph-indexed — it just lacks
function/class boundary precision.
"""

from pathlib import Path
from typing import List, Optional

import structlog

from services.parser.chunk_schema import CodeChunk

logger = structlog.get_logger(__name__)

# Maximum characters to include in a coarse chunk.
# Truncated to avoid exceeding LLM context windows when used as retrieval context.
MAX_COARSE_CHARS = 8_000

# Language from file extension (subset not covered by other parsers)
_EXT_TO_LANG = {
    ".java":  "java",
    ".go":    "go",
    ".rs":    "rust",
    ".rb":    "ruby",
    ".php":   "php",
    ".cs":    "csharp",
    ".cpp":   "cpp",
    ".cc":    "cpp",
    ".cxx":   "cpp",
    ".c":     "c",
    ".h":     "c",
    ".sh":    "shell",
    ".bash":  "shell",
    ".zsh":   "shell",
    ".sql":   "sql",
    ".html":  "html",
    ".css":   "css",
    ".scss":  "css",
    ".yaml":  "yaml",
    ".yml":   "yaml",
    ".toml":  "toml",
    ".json":  "json",
    ".md":    "markdown",
    ".txt":   "text",
    ".xml":   "xml",
}


def _detect_language(file_path: Path) -> str:
    """Best-effort language detection from file extension."""
    return _EXT_TO_LANG.get(file_path.suffix.lower(), "other")


def parse_fallback_file(
    file_path: Path,
    repo_root: Path,
    repo_id: str,
    language: Optional[str] = None,
) -> List[CodeChunk]:
    """
    Produce a single coarse CodeChunk for any file.

    Args:
        file_path: Absolute path to the file.
        repo_root: Absolute path to the repo root (for relative path calc).
        repo_id:   Ingestion job ID.
        language:  Override detected language (used when called from js_parser
                   as a fallback for a known language).

    Returns:
        A list containing exactly one CodeChunk, or an empty list if the
        file is empty or unreadable.
    """
    rel_path = str(file_path.relative_to(repo_root))

    try:
        source = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        logger.warning("Cannot read file for fallback parsing", path=rel_path, error=str(exc))
        return []

    source = source.strip()
    if not source:
        return []

    detected_lang = language or _detect_language(file_path)
    total_lines   = source.count("\n") + 1

    # Truncate very large files to avoid blowing up embedding/context limits
    truncated = False
    if len(source) > MAX_COARSE_CHARS:
        source = source[:MAX_COARSE_CHARS]
        truncated = True
        logger.debug("Coarse chunk truncated", path=rel_path, chars=MAX_COARSE_CHARS)

    code = source + ("\n\n[... truncated ...]" if truncated else "")

    chunk = CodeChunk(
        repo_id=repo_id,
        file_path=rel_path,
        language=detected_lang,
        chunk_type="coarse",
        name=file_path.stem,
        code=code,
        start_line=1,
        end_line=total_lines,
        is_coarse=True,
    )

    logger.debug("Fallback chunk created", path=rel_path, language=detected_lang)
    return [chunk]
