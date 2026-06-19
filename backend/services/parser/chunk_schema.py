"""
services/parser/chunk_schema.py — Pydantic model for a normalized code chunk.

Every parser (Python AST, Tree-sitter JS/TS, fallback) produces CodeChunk objects.
This schema is the single source of truth for what a chunk looks like before
it gets embedded and upserted to Qdrant.
"""

import uuid
from typing import List, Optional

from pydantic import BaseModel, Field


class CodeChunk(BaseModel):
    """
    A single addressable unit of source code extracted from a repository.

    Chunks are the fundamental unit of the entire pipeline:
    - Embedded → Qdrant (Phase 4)
    - Nodes in Neo4j (Phase 5)
    - Context windows fed to the LLM (Phase 7)
    """

    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    """Unique identifier for this chunk. Stable across re-ingestions of the same content."""

    repo_id: str
    """Job ID of the parent ingestion job."""

    file_path: str
    """Relative path from repo root, e.g. 'src/auth/service.py'."""

    language: str
    """Detected language: 'python', 'javascript', 'typescript', etc."""

    chunk_type: str
    """
    Granularity of this chunk:
    - 'function'  — top-level function definition
    - 'class'     — class definition (body includes methods)
    - 'method'    — method inside a class
    - 'module'    — entire file (used when a file has no named definitions)
    - 'import'    — import block at the top of the file
    - 'coarse'    — whole-file fallback for unsupported languages
    """

    name: Optional[str] = None
    """Function/class/method name, or None for module-level chunks."""

    code: str
    """The raw source text of this chunk."""

    start_line: int
    """1-indexed first line of this chunk in the source file."""

    end_line: int
    """1-indexed last line of this chunk in the source file."""

    imports: List[str] = Field(default_factory=list)
    """Imported names/modules visible at this chunk's scope."""

    decorators: List[str] = Field(default_factory=list)
    """Decorator names applied to this function/class, e.g. ['@router.get', '@property']."""

    parent_name: Optional[str] = None
    """For methods: the name of the enclosing class."""

    is_coarse: bool = False
    """True when this chunk was produced by the fallback (whole-file) parser."""

    def content_for_embedding(self) -> str:
        """
        Build the text that will be embedded.

        Prepends a structured header so the embedding model has context
        about what the code does — not just the raw tokens.

        Format:
          [language] [chunk_type] [name]
          File: [file_path]
          [code]
        """
        header_parts = [f"[{self.language}]", f"[{self.chunk_type}]"]
        if self.name:
            header_parts.append(self.name)
        if self.parent_name:
            header_parts.append(f"(in {self.parent_name})")

        header = " ".join(header_parts)
        return f"{header}\nFile: {self.file_path}\n\n{self.code}"
