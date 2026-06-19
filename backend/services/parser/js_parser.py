"""
services/parser/js_parser.py — Tree-sitter based JS/TS code chunker.

Produces CodeChunk objects for JavaScript and TypeScript files by walking
the Tree-sitter concrete syntax tree.

Extracted node types:
  - function_declaration / arrow_function / function_expression → 'function'
  - class_declaration → 'class'
  - method_definition → 'method'
  - import_statement (batched) → 'import'

Runs correctly on Linux (Docker container). On Windows host, tree-sitter
compiles natively but may require Build Tools — always run via Docker in prod.
"""

from pathlib import Path
from typing import List, Optional

import structlog

from services.parser.chunk_schema import CodeChunk

logger = structlog.get_logger(__name__)

# ── Lazy-load tree-sitter to avoid import errors when not installed ────────────
_TS_AVAILABLE = False
_PYTHON_LANG = None  # placeholder variable name kept for consistency
_JS_LANG = None
_TS_LANG = None

try:
    import tree_sitter_javascript as tsjava
    import tree_sitter_typescript as tstype
    from tree_sitter import Language, Parser

    JS_LANGUAGE  = Language(tsjava.language())
    TSX_LANGUAGE = Language(tstype.language_tsx())
    TS_LANGUAGE  = Language(tstype.language_typescript())
    _TS_AVAILABLE = True
    logger.debug("Tree-sitter JS/TS language bindings loaded")
except Exception as exc:  # noqa: BLE001
    logger.warning(
        "Tree-sitter not available — JS/TS will use fallback parser",
        error=str(exc),
    )


def _get_language(language: str):
    """Return the correct Language object for js/ts/tsx."""
    if language == "javascript":
        return JS_LANGUAGE
    if language == "typescript":
        return TS_LANGUAGE
    return TSX_LANGUAGE  # default for .tsx


def _node_text(node, source_bytes: bytes) -> str:
    """Extract UTF-8 text for a tree-sitter node."""
    return source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _find_name(node, source_bytes: bytes) -> Optional[str]:
    """
    Try to extract the identifier/name from a function or class node.

    Walks one level of children looking for 'identifier' or 'property_identifier'.
    """
    for child in node.children:
        if child.type in ("identifier", "property_identifier"):
            return _node_text(child, source_bytes)
    return None


def _collect_imports(root_node, source_bytes: bytes) -> List[str]:
    """Collect all top-level import_statement texts."""
    imports: List[str] = []
    for child in root_node.children:
        if child.type == "import_statement":
            imports.append(_node_text(child, source_bytes).strip())
    return imports


def _walk_class_methods(
    class_node,
    source_bytes: bytes,
    repo_id: str,
    rel_path: str,
    language: str,
    imports: List[str],
    class_name: Optional[str],
) -> List[CodeChunk]:
    """
    Extract method chunks from inside a class body.

    Handles class_body → method_definition and property nodes.
    """
    method_chunks: List[CodeChunk] = []

    # Find the class_body child
    body = next((c for c in class_node.children if c.type == "class_body"), None)
    if not body:
        return []

    for child in body.children:
        if child.type == "method_definition":
            name = _find_name(child, source_bytes)
            code = _node_text(child, source_bytes)
            method_chunks.append(CodeChunk(
                repo_id=repo_id,
                file_path=rel_path,
                language=language,
                chunk_type="method",
                name=name,
                code=code,
                start_line=child.start_point[0] + 1,
                end_line=child.end_point[0] + 1,
                imports=imports,
                parent_name=class_name,
            ))
    return method_chunks


def parse_js_file(
    file_path: Path,
    repo_root: Path,
    repo_id: str,
) -> List[CodeChunk]:
    """
    Parse a JS/TS/TSX file into CodeChunk objects using Tree-sitter.

    Falls back gracefully to the fallback parser if tree-sitter is unavailable.
    """
    from services.parser.fallback_parser import parse_fallback_file  # avoid circular

    rel_path = str(file_path.relative_to(repo_root))
    suffix = file_path.suffix.lower()

    if suffix in (".ts", ".tsx"):
        language = "typescript"
    else:
        language = "javascript"

    # ── Fallback if tree-sitter not available ──────────────────────────────
    if not _TS_AVAILABLE:
        logger.debug("Using fallback parser for JS/TS file", path=rel_path)
        return parse_fallback_file(file_path, repo_root, repo_id, language=language)

    try:
        source = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        logger.warning("Cannot read JS/TS file", path=rel_path, error=str(exc))
        return []

    source_bytes = source.encode("utf-8")
    lang = _get_language(language)

    parser = Parser(lang)
    tree = parser.parse(source_bytes)
    root = tree.root_node

    chunks: List[CodeChunk] = []
    imports = _collect_imports(root, source_bytes)

    # ── Import chunk ───────────────────────────────────────────────────────
    if imports:
        chunks.append(CodeChunk(
            repo_id=repo_id,
            file_path=rel_path,
            language=language,
            chunk_type="import",
            name=None,
            code="\n".join(imports),
            start_line=1,
            end_line=1,
            imports=imports,
        ))

    has_definitions = False

    for node in root.children:
        # ── Function declaration: function foo() {} ────────────────────────
        if node.type == "function_declaration":
            has_definitions = True
            name = _find_name(node, source_bytes)
            chunks.append(CodeChunk(
                repo_id=repo_id,
                file_path=rel_path,
                language=language,
                chunk_type="function",
                name=name,
                code=_node_text(node, source_bytes),
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                imports=imports,
            ))

        # ── Class declaration: class Foo {} ───────────────────────────────
        elif node.type == "class_declaration":
            has_definitions = True
            class_name = _find_name(node, source_bytes)
            chunks.append(CodeChunk(
                repo_id=repo_id,
                file_path=rel_path,
                language=language,
                chunk_type="class",
                name=class_name,
                code=_node_text(node, source_bytes),
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                imports=imports,
            ))
            # Extract methods
            chunks.extend(_walk_class_methods(
                node, source_bytes, repo_id, rel_path, language, imports, class_name
            ))

        # ── Export statement wrapping a function/class ─────────────────────
        elif node.type in ("export_statement", "lexical_declaration", "variable_declaration"):
            for child in node.children:
                if child.type == "function_declaration":
                    has_definitions = True
                    name = _find_name(child, source_bytes)
                    chunks.append(CodeChunk(
                        repo_id=repo_id,
                        file_path=rel_path,
                        language=language,
                        chunk_type="function",
                        name=name,
                        code=_node_text(child, source_bytes),
                        start_line=child.start_point[0] + 1,
                        end_line=child.end_point[0] + 1,
                        imports=imports,
                    ))
                elif child.type == "class_declaration":
                    has_definitions = True
                    class_name = _find_name(child, source_bytes)
                    chunks.append(CodeChunk(
                        repo_id=repo_id,
                        file_path=rel_path,
                        language=language,
                        chunk_type="class",
                        name=class_name,
                        code=_node_text(child, source_bytes),
                        start_line=child.start_point[0] + 1,
                        end_line=child.end_point[0] + 1,
                        imports=imports,
                    ))
                    chunks.extend(_walk_class_methods(
                        child, source_bytes, repo_id, rel_path, language, imports, class_name
                    ))

    # ── Fallback: no defs found ────────────────────────────────────────────
    if not has_definitions and source.strip():
        chunks.append(CodeChunk(
            repo_id=repo_id,
            file_path=rel_path,
            language=language,
            chunk_type="module",
            name=file_path.stem,
            code=source.rstrip(),
            start_line=1,
            end_line=source.count("\n") + 1,
            imports=imports,
        ))

    logger.debug("Parsed JS/TS file", path=rel_path, chunks=len(chunks))
    return chunks
