"""
tests/test_repo_service.py — Unit tests for services/repo_service.py (Phase 2).

These tests run without any external services — they test pure Python logic.

Run with: pytest backend/tests/test_repo_service.py -v
"""

import shutil
import zipfile
from pathlib import Path

import pytest

from services.repo_service import (
    EXTENSION_LANGUAGES,
    FRAMEWORK_SIGNALS,
    extract_repo_metadata,
    extract_repo_name_from_url,
    validate_and_extract_zip,
    validate_github_url,
)


# ── validate_github_url ────────────────────────────────────────────────────────

@pytest.mark.parametrize("url", [
    "https://github.com/tiangolo/fastapi",
    "https://github.com/tiangolo/fastapi.git",
    "https://github.com/tiangolo/fastapi/",
    "http://github.com/owner/repo",
])
def test_validate_github_url_valid(url: str):
    """Valid GitHub URLs should pass without raising."""
    result = validate_github_url(url)
    assert "github.com" in result


@pytest.mark.parametrize("url", [
    "https://gitlab.com/owner/repo",
    "https://github.com/",
    "not-a-url",
    "",
    "https://github.com/only-owner",
])
def test_validate_github_url_invalid(url: str):
    """Invalid URLs should raise ValueError."""
    with pytest.raises(ValueError):
        validate_github_url(url)


# ── extract_repo_name_from_url ────────────────────────────────────────────────

def test_extract_repo_name():
    assert extract_repo_name_from_url("https://github.com/tiangolo/fastapi") == "tiangolo/fastapi"
    assert extract_repo_name_from_url("https://github.com/owner/my-repo.git") == "owner/my-repo"


# ── extract_repo_metadata ─────────────────────────────────────────────────────

@pytest.fixture
def sample_repo(tmp_path: Path) -> Path:
    """Create a minimal fake repository directory for metadata tests."""
    (tmp_path / "main.py").write_text("def hello(): pass")
    (tmp_path / "utils.py").write_text("import os")
    (tmp_path / "app.js").write_text("console.log('hi')")
    (tmp_path / "requirements.txt").write_text("fastapi")
    (tmp_path / "package.json").write_text('{"name":"app"}')
    (tmp_path / "README.md").write_text("# Hello")
    # Subdir
    sub = tmp_path / "src"
    sub.mkdir()
    (sub / "service.py").write_text("class Svc: pass")
    # Should be skipped
    skip = tmp_path / "node_modules"
    skip.mkdir()
    (skip / "ignored.js").write_text("// ignored")
    return tmp_path


def test_extract_repo_metadata_file_count(sample_repo: Path):
    meta = extract_repo_metadata(sample_repo)
    # node_modules should be skipped → 7 real files (py×3, js×1, md×1, json×1, txt×1)
    assert meta["total_files"] == 7


def test_extract_repo_metadata_languages(sample_repo: Path):
    meta = extract_repo_metadata(sample_repo)
    assert "python" in meta["languages"]
    assert "javascript" in meta["languages"]
    assert meta["primary_language"] == "python"  # most .py files


def test_extract_repo_metadata_frameworks(sample_repo: Path):
    meta = extract_repo_metadata(sample_repo)
    assert "python" in meta["frameworks"]
    assert "node" in meta["frameworks"]


def test_extract_repo_metadata_size(sample_repo: Path):
    meta = extract_repo_metadata(sample_repo)
    assert meta["total_bytes"] > 0
    assert "total_size_mb" in meta


# ── validate_and_extract_zip ──────────────────────────────────────────────────

@pytest.fixture
def sample_zip(tmp_path: Path) -> Path:
    """Create a valid ZIP file for extraction tests."""
    zip_path = tmp_path / "repo.zip"
    extract_dir = tmp_path / "content"
    extract_dir.mkdir()
    (extract_dir / "main.py").write_text("print('hello')")
    (extract_dir / "README.md").write_text("# Test")

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(extract_dir / "main.py", arcname="repo/main.py")
        zf.write(extract_dir / "README.md", arcname="repo/README.md")
    return zip_path


def test_extract_zip_valid(sample_zip: Path, tmp_path: Path):
    extract_to = tmp_path / "extracted"
    result = validate_and_extract_zip(sample_zip, extract_to)
    assert result.exists()
    # Should find a file somewhere in the extracted tree
    all_files = list(result.rglob("*.py"))
    assert len(all_files) >= 1


def test_extract_zip_slip_protection(tmp_path: Path):
    """A ZIP with a path traversal attempt should raise PermissionError."""
    evil_zip = tmp_path / "evil.zip"
    with zipfile.ZipFile(evil_zip, "w") as zf:
        zf.writestr("../../etc/passwd", "root:x:0:0")

    extract_to = tmp_path / "extracted"
    with pytest.raises(PermissionError, match="Zip-slip"):
        validate_and_extract_zip(evil_zip, extract_to)
