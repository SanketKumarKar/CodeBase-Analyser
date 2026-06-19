"""
tests/test_parser.py — Unit tests for the Phase 3 parsing engine.

Tests run without any external services — pure Python / filesystem only.

Run with: pytest backend/tests/test_parser.py -v
"""

import textwrap
from pathlib import Path

import pytest

from services.parser.chunk_schema import CodeChunk
from services.parser.fallback_parser import parse_fallback_file
from services.parser.python_parser import parse_python_file
from services.parser import parse_repository


# ── Fixtures ──────────────────────────────────────────────────────────────────

REPO_ID = "test-repo-123"


@pytest.fixture
def repo_root(tmp_path: Path) -> Path:
    """Minimal fake repository with Python, JS, and an unknown-lang file."""

    # ── Python files ───────────────────────────────────────────────────────
    py_dir = tmp_path / "backend"
    py_dir.mkdir()

    (py_dir / "auth.py").write_text(textwrap.dedent("""\
        import os
        from pathlib import Path

        class AuthService:
            def __init__(self, secret: str):
                self.secret = secret

            def verify_token(self, token: str) -> bool:
                return token == self.secret

        def login(username: str, password: str) -> str:
            return "jwt-token"
    """))

    (py_dir / "utils.py").write_text(textwrap.dedent("""\
        from typing import Any

        def flatten(lst: list) -> list:
            return [item for sub in lst for item in sub]
    """))

    # A script with no named defs → should produce a 'module' chunk
    (py_dir / "script.py").write_text("print('hello world')\n")

    # ── JS file ────────────────────────────────────────────────────────────
    js_dir = tmp_path / "frontend" / "src"
    js_dir.mkdir(parents=True)
    (js_dir / "api.js").write_text(textwrap.dedent("""\
        import axios from 'axios';

        function fetchUser(id) {
            return axios.get('/users/' + id);
        }

        class ApiClient {
            constructor(baseUrl) {
                this.baseUrl = baseUrl;
            }
        }
    """))

    # ── Unknown language ───────────────────────────────────────────────────
    (tmp_path / "Makefile").write_text("build:\n\techo done\n")

    # ── Files that should be skipped ──────────────────────────────────────
    (tmp_path / "package.lock").write_text("not parsed")
    skip_dir = tmp_path / "node_modules"
    skip_dir.mkdir()
    (skip_dir / "ignored.js").write_text("should be skipped")

    return tmp_path


# ── chunk_schema ──────────────────────────────────────────────────────────────

def test_chunk_schema_content_for_embedding():
    chunk = CodeChunk(
        repo_id="r1",
        file_path="src/auth.py",
        language="python",
        chunk_type="function",
        name="login",
        code="def login(): pass",
        start_line=10,
        end_line=10,
    )
    text = chunk.content_for_embedding()
    assert "[python]" in text
    assert "[function]" in text
    assert "login" in text
    assert "src/auth.py" in text
    assert "def login" in text


def test_chunk_schema_coarse_flag_default():
    chunk = CodeChunk(
        repo_id="r1", file_path="x.py", language="python",
        chunk_type="function", code="def f(): pass",
        start_line=1, end_line=1,
    )
    assert chunk.is_coarse is False


# ── python_parser ─────────────────────────────────────────────────────────────

def test_python_parser_class_and_methods(tmp_path: Path):
    src = tmp_path / "auth.py"
    src.write_text(textwrap.dedent("""\
        import os

        class AuthService:
            def __init__(self):
                pass

            def verify(self, token: str) -> bool:
                return bool(token)

        def login():
            return 'ok'
    """))

    chunks = parse_python_file(src, tmp_path, REPO_ID)
    types = {c.chunk_type for c in chunks}

    assert "import" in types
    assert "class" in types
    assert "method" in types
    assert "function" in types

    method_names = {c.name for c in chunks if c.chunk_type == "method"}
    assert "__init__" in method_names
    assert "verify" in method_names


def test_python_parser_function_names(tmp_path: Path):
    src = tmp_path / "utils.py"
    src.write_text("def foo(): pass\ndef bar(): pass\n")
    chunks = parse_python_file(src, tmp_path, REPO_ID)
    func_names = {c.name for c in chunks if c.chunk_type == "function"}
    assert "foo" in func_names
    assert "bar" in func_names


def test_python_parser_decorators(tmp_path: Path):
    src = tmp_path / "routes.py"
    src.write_text(textwrap.dedent("""\
        from fastapi import APIRouter
        router = APIRouter()

        @router.get('/users')
        def get_users():
            return []
    """))
    chunks = parse_python_file(src, tmp_path, REPO_ID)
    func_chunks = [c for c in chunks if c.chunk_type == "function"]
    assert len(func_chunks) >= 1
    assert any("get" in d for c in func_chunks for d in c.decorators)


def test_python_parser_script_no_defs(tmp_path: Path):
    """A script with no functions/classes should produce a module chunk."""
    src = tmp_path / "script.py"
    src.write_text("print('hello')\nx = 1 + 2\n")
    chunks = parse_python_file(src, tmp_path, REPO_ID)
    assert any(c.chunk_type == "module" for c in chunks)


def test_python_parser_syntax_error(tmp_path: Path):
    """A file with syntax errors should return an empty list, not raise."""
    src = tmp_path / "broken.py"
    src.write_text("def (: pass\n")  # intentional syntax error
    chunks = parse_python_file(src, tmp_path, REPO_ID)
    assert chunks == []


def test_python_parser_imports_propagated(tmp_path: Path):
    """Import names should be populated in function chunks."""
    src = tmp_path / "svc.py"
    src.write_text("import os\n\ndef do_thing(): os.getcwd()\n")
    chunks = parse_python_file(src, tmp_path, REPO_ID)
    func = next(c for c in chunks if c.chunk_type == "function")
    assert any("import os" in imp for imp in func.imports)


# ── fallback_parser ───────────────────────────────────────────────────────────

def test_fallback_parser_produces_coarse_chunk(tmp_path: Path):
    f = tmp_path / "Makefile"
    f.write_text("build:\n\techo done\n")
    chunks = parse_fallback_file(f, tmp_path, REPO_ID)
    assert len(chunks) == 1
    assert chunks[0].is_coarse is True
    assert chunks[0].chunk_type == "coarse"


def test_fallback_parser_empty_file(tmp_path: Path):
    f = tmp_path / "empty.go"
    f.write_text("")
    chunks = parse_fallback_file(f, tmp_path, REPO_ID)
    assert chunks == []


def test_fallback_parser_language_detection(tmp_path: Path):
    cases = {
        "app.go":   "go",
        "Main.java": "java",
        "lib.rs":   "rust",
        "query.sql": "sql",
    }
    for fname, expected_lang in cases.items():
        f = tmp_path / fname
        f.write_text(f"// {fname} content")
        chunks = parse_fallback_file(f, tmp_path, REPO_ID)
        assert chunks[0].language == expected_lang, f"{fname} → expected {expected_lang}"


def test_fallback_parser_truncates_large_file(tmp_path: Path):
    f = tmp_path / "huge.sh"
    f.write_text("x" * 20_000)
    chunks = parse_fallback_file(f, tmp_path, REPO_ID)
    assert len(chunks) == 1
    assert "[... truncated ...]" in chunks[0].code


# ── parse_repository (integration) ───────────────────────────────────────────

def test_parse_repository_returns_chunks(repo_root: Path):
    chunks = parse_repository(repo_root, REPO_ID)
    assert len(chunks) > 0


def test_parse_repository_skips_node_modules(repo_root: Path):
    chunks = parse_repository(repo_root, REPO_ID)
    paths = [c.file_path for c in chunks]
    assert not any("node_modules" in p for p in paths)


def test_parse_repository_skips_lock_files(repo_root: Path):
    chunks = parse_repository(repo_root, REPO_ID)
    paths = [c.file_path for c in chunks]
    assert not any(p.endswith(".lock") for p in paths)


def test_parse_repository_all_chunks_have_repo_id(repo_root: Path):
    chunks = parse_repository(repo_root, REPO_ID)
    assert all(c.repo_id == REPO_ID for c in chunks)


def test_parse_repository_python_files_parsed(repo_root: Path):
    chunks = parse_repository(repo_root, REPO_ID)
    python_chunks = [c for c in chunks if c.language == "python"]
    assert len(python_chunks) > 0
    # auth.py has a class + methods + function
    func_names = {c.name for c in python_chunks if c.chunk_type == "function"}
    assert "login" in func_names


def test_parse_repository_chunk_line_numbers_valid(repo_root: Path):
    chunks = parse_repository(repo_root, REPO_ID)
    for chunk in chunks:
        assert chunk.start_line >= 1, f"start_line < 1 in {chunk.file_path}"
        assert chunk.end_line >= chunk.start_line, f"end < start in {chunk.file_path}"
