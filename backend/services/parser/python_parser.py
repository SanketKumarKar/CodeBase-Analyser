"""
services/parser/python_parser.py — AST-based Python code chunker.

Produces CodeChunk objects for:
  - Module-level imports (batched into a single 'import' chunk)
  - Top-level function definitions ('function' chunks)
  - Top-level class definitions ('class' chunks)
  - Methods inside classes ('method' chunks)

Uses only stdlib `ast` — no external deps required.
"""

import ast
import textwrap
from pathlib import Path
from typing import List, Optional

import structlog

from services.parser.chunk_schema import CodeChunk

logger = structlog.get_logger(__name__)


def _node_source(source_lines: List[str], node: ast.AST) -> str:
    """Extract the source text for an AST node using its line number info."""
    start = node.lineno - 1          # type: ignore[attr-defined]
    end   = node.end_lineno          # type: ignore[attr-defined]
    snippet = source_lines[start:end]
    # Dedent to remove class-level indentation from methods
    return textwrap.dedent("".join(snippet)).rstrip()


def _extract_imports(tree: ast.Module, source_lines: List[str]) -> List[str]:
    """
    Collect all top-level import strings.

    Returns a list of strings like ['import os', 'from pathlib import Path'].
    """
    imports: List[str] = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            imports.append(_node_source(source_lines, node).strip())
    return imports


def _decorator_names(node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) -> List[str]:
    """Extract decorator names as strings (e.g. '@router.get', '@property')."""
    names: List[str] = []
    for dec in node.decorator_list:
        if isinstance(dec, ast.Name):
            names.append(f"@{dec.id}")
        elif isinstance(dec, ast.Attribute):
            names.append(f"@{dec.attr}")
        elif isinstance(dec, ast.Call):
            func = dec.func
            if isinstance(func, ast.Name):
                names.append(f"@{func.id}")
            elif isinstance(func, ast.Attribute):
                names.append(f"@{func.attr}")
    return names


def parse_python_file(
    file_path: Path,
    repo_root: Path,
    repo_id: str,
) -> List[CodeChunk]:
    """
    Parse a single Python file into a list of CodeChunk objects.

    Returns an empty list (with a warning log) if the file cannot be parsed.
    Falls back to a single coarse file-level chunk if the AST has no
    named definitions (e.g. pure script files).
    """
    rel_path = str(file_path.relative_to(repo_root))
    chunks: List[CodeChunk] = []

    try:
        source = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        logger.warning("Cannot read Python file", path=rel_path, error=str(exc))
        return []

    source_lines = [line + "\n" for line in source.splitlines()]

    try:
        tree = ast.parse(source, filename=rel_path)
    except SyntaxError as exc:
        logger.warning("Python syntax error — skipping file", path=rel_path, error=str(exc))
        return []

    all_imports = _extract_imports(tree, source_lines)

    # ── Import chunk ───────────────────────────────────────────────────────
    if all_imports:
        chunks.append(CodeChunk(
            repo_id=repo_id,
            file_path=rel_path,
            language="python",
            chunk_type="import",
            name=None,
            code="\n".join(all_imports),
            start_line=1,
            end_line=1,
            imports=all_imports,
        ))

    # ── Top-level definitions ──────────────────────────────────────────────
    has_definitions = False

    for node in ast.iter_child_nodes(tree):
        # ── Top-level function ─────────────────────────────────────────────
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            has_definitions = True
            chunks.append(CodeChunk(
                repo_id=repo_id,
                file_path=rel_path,
                language="python",
                chunk_type="function",
                name=node.name,
                code=_node_source(source_lines, node),
                start_line=node.lineno,
                end_line=node.end_lineno,  # type: ignore[attr-defined]
                imports=all_imports,
                decorators=_decorator_names(node),
            ))

        # ── Class definition ───────────────────────────────────────────────
        elif isinstance(node, ast.ClassDef):
            has_definitions = True
            class_code = _node_source(source_lines, node)

            chunks.append(CodeChunk(
                repo_id=repo_id,
                file_path=rel_path,
                language="python",
                chunk_type="class",
                name=node.name,
                code=class_code,
                start_line=node.lineno,
                end_line=node.end_lineno,  # type: ignore[attr-defined]
                imports=all_imports,
                decorators=_decorator_names(node),
            ))

            # ── Methods inside the class ───────────────────────────────────
            for item in ast.iter_child_nodes(node):
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    chunks.append(CodeChunk(
                        repo_id=repo_id,
                        file_path=rel_path,
                        language="python",
                        chunk_type="method",
                        name=item.name,
                        code=_node_source(source_lines, item),
                        start_line=item.lineno,
                        end_line=item.end_lineno,  # type: ignore[attr-defined]
                        imports=all_imports,
                        decorators=_decorator_names(item),
                        parent_name=node.name,
                    ))

    # ── Fallback: no named defs → module-level chunk ───────────────────────
    if not has_definitions and source.strip():
        chunks.append(CodeChunk(
            repo_id=repo_id,
            file_path=rel_path,
            language="python",
            chunk_type="module",
            name=Path(rel_path).stem,
            code=source.rstrip(),
            start_line=1,
            end_line=len(source_lines),
            imports=all_imports,
        ))

    logger.debug("Parsed Python file", path=rel_path, chunks=len(chunks))
    return chunks
