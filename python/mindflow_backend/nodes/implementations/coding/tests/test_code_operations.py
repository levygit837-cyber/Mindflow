"""Test suite for code operations utilities."""

import pytest
from pathlib import Path
import tempfile
import os


@pytest.mark.asyncio
async def test_read_file_safe_success():
    """Test successful file reading."""
    from mindflow_backend.nodes.implementations.coding.utils import read_file_safe

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.py"
        test_file.write_text("print('hello')", encoding="utf-8")

        content = await read_file_safe("test.py", tmpdir)

        assert content == "print('hello')"


@pytest.mark.asyncio
async def test_read_file_safe_not_found():
    """Test reading non-existent file."""
    from mindflow_backend.nodes.implementations.coding.utils import read_file_safe

    with tempfile.TemporaryDirectory() as tmpdir:
        content = await read_file_safe("nonexistent.py", tmpdir)

        assert content is None


@pytest.mark.asyncio
async def test_write_file_safe_success():
    """Test successful file writing."""
    from mindflow_backend.nodes.implementations.coding.utils import write_file_safe

    with tempfile.TemporaryDirectory() as tmpdir:
        result = await write_file_safe("test.py", "print('hello')", tmpdir)

        assert result["success"] is True
        assert result["file_path"] == str(Path(tmpdir) / "test.py")
        assert result["size"] == len("print('hello')")

        # Verify file was written
        test_file = Path(tmpdir) / "test.py"
        assert test_file.exists()
        assert test_file.read_text() == "print('hello')"


@pytest.mark.asyncio
async def test_write_file_safe_create_dirs():
    """Test writing file with directory creation."""
    from mindflow_backend.nodes.implementations.coding.utils import write_file_safe

    with tempfile.TemporaryDirectory() as tmpdir:
        result = await write_file_safe(
            "subdir/test.py", "print('hello')", tmpdir, create_dirs=True
        )

        assert result["success"] is True
        assert (Path(tmpdir) / "subdir" / "test.py").exists()


@pytest.mark.asyncio
async def test_detect_language_python():
    """Test language detection for Python."""
    from mindflow_backend.nodes.implementations.coding.utils import detect_language

    language = await detect_language("test.py")
    assert language == "python"


@pytest.mark.asyncio
async def test_detect_language_typescript():
    """Test language detection for TypeScript."""
    from mindflow_backend.nodes.implementations.coding.utils import detect_language

    language = await detect_language("test.ts")
    assert language == "typescript"

    language = await detect_language("test.tsx")
    assert language == "typescript"


@pytest.mark.asyncio
async def test_detect_language_javascript():
    """Test language detection for JavaScript."""
    from mindflow_backend.nodes.implementations.coding.utils import detect_language

    language = await detect_language("test.js")
    assert language == "javascript"


@pytest.mark.asyncio
async def test_detect_language_unknown():
    """Test language detection for unknown extension."""
    from mindflow_backend.nodes.implementations.coding.utils import detect_language

    language = await detect_language("test.unknown")
    assert language == "unknown"


@pytest.mark.asyncio
async def test_analyze_python_structure():
    """Test Python code structure analysis."""
    from mindflow_backend.nodes.implementations.coding.utils import (
        analyze_python_structure,
    )

    code = """
class MyClass:
    def __init__(self):
        self.value = 0

    def increment(self):
        self.value += 1

def helper_function():
    return "hello"
"""

    structure = await analyze_python_structure(code)

    assert "classes" in structure
    assert "functions" in structure
    assert "imports" in structure
    # The function returns structure with actual AST parsing
    assert len(structure["classes"]) >= 1 or len(structure["functions"]) >= 1


@pytest.mark.asyncio
async def test_validate_syntax_valid_python():
    """Test syntax validation for valid Python code."""
    from mindflow_backend.nodes.implementations.coding.utils import validate_syntax

    code = "print('hello')"
    result = await validate_syntax(code, "python")

    assert result["valid"] is True


@pytest.mark.asyncio
async def test_validate_syntax_invalid_python():
    """Test syntax validation for invalid Python code."""
    from mindflow_backend.nodes.implementations.coding.utils import validate_syntax

    code = "print('hello'"
    result = await validate_syntax(code, "python")

    assert result["valid"] is False
    assert "errors" in result


@pytest.mark.asyncio
async def test_extract_imports():
    """Test import extraction from Python code."""
    from mindflow_backend.nodes.implementations.coding.utils import extract_imports

    code = """
import os
import sys
from typing import List
from pathlib import Path
"""

    imports = await extract_imports(code, "python")

    assert isinstance(imports, list)
    assert len(imports) >= 4
    assert any("os" in imp for imp in imports)
    assert any("sys" in imp for imp in imports)
