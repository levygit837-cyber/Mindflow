"""Code operations utilities for Coder nodes.

This module provides reusable functions for code file operations,
pattern detection, and code manipulation.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


async def read_file_safe(file_path: str, working_dir: str = ".") -> str | None:
    """Safely read a file with error handling.

    Note: Marked as async for compatibility with async contexts, but uses
    synchronous I/O. Consider using aiofiles for true async I/O in production.

    Args:
        file_path: Path to the file
        working_dir: Working directory for relative paths

    Returns:
        File content or None if error
    """
    try:
        full_path = Path(working_dir) / file_path
        if not full_path.exists():
            _logger.warning("file_not_found", file_path=file_path)
            return None

        content = full_path.read_text(encoding="utf-8")
        _logger.debug("file_read_success", file_path=file_path, size=len(content))
        return content

    except Exception as e:
        _logger.error("file_read_failed", file_path=file_path, error=str(e))
        return None


async def write_file_safe(
    file_path: str,
    content: str,
    working_dir: str = ".",
    create_dirs: bool = True,
) -> dict[str, Any]:
    """Safely write a file with error handling.

    Note: Marked as async for compatibility with async contexts, but uses
    synchronous I/O. Consider using aiofiles for true async I/O in production.

    Args:
        file_path: Path to the file
        content: Content to write
        working_dir: Working directory for relative paths
        create_dirs: Create parent directories if they don't exist

    Returns:
        Dictionary with success status and metadata
    """
    try:
        full_path = Path(working_dir) / file_path

        if create_dirs:
            full_path.parent.mkdir(parents=True, exist_ok=True)

        full_path.write_text(content, encoding="utf-8")

        _logger.info("file_write_success", file_path=file_path, size=len(content))
        return {
            "success": True,
            "file_path": str(full_path),
            "size": len(content),
        }

    except Exception as e:
        _logger.error("file_write_failed", file_path=file_path, error=str(e))
        return {
            "success": False,
            "error": str(e),
            "file_path": str(full_path) if "full_path" in locals() else file_path,
        }


async def detect_language(file_path: str) -> str:
    """Detect programming language from file extension.

    Args:
        file_path: Path to the file

    Returns:
        Language identifier (python, typescript, javascript, etc.)
    """
    ext = Path(file_path).suffix.lower()

    language_map = {
        ".py": "python",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".js": "javascript",
        ".jsx": "javascript",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
        ".kt": "kotlin",
        ".rb": "ruby",
        ".php": "php",
        ".cpp": "cpp",
        ".c": "c",
        ".h": "c",
        ".hpp": "cpp",
    }

    return language_map.get(ext, "unknown")


async def analyze_python_structure(content: str) -> dict[str, Any]:
    """Analyze Python code structure using AST.

    Args:
        content: Python code content

    Returns:
        Dictionary with structure information
    """
    try:
        tree = ast.parse(content)

        classes = []
        functions = []
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append({
                    "name": node.name,
                    "lineno": node.lineno,
                    "methods": [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                })
            elif isinstance(node, ast.FunctionDef):
                functions.append({
                    "name": node.name,
                    "lineno": node.lineno,
                    "args": [arg.arg for arg in node.args.args]
                })
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    imports.extend([alias.name for alias in node.names])
                else:
                    imports.append(f"from {node.module}")

        return {
            "classes": classes,
            "functions": functions,
            "imports": imports,
            "total_classes": len(classes),
            "total_functions": len(functions),
        }

    except SyntaxError as e:
        _logger.error("python_syntax_error", error=str(e))
        return {
            "error": "syntax_error",
            "message": str(e),
        }


async def detect_code_patterns(content: str, language: str) -> dict[str, Any]:
    """Detect common code patterns.

    Args:
        content: Code content
        language: Programming language

    Returns:
        Dictionary with detected patterns
    """
    patterns = {
        "async_functions": 0,
        "class_definitions": 0,
        "decorators": 0,
        "type_hints": 0,
        "docstrings": 0,
        "comments": 0,
    }

    if language == "python":
        # Count async functions
        patterns["async_functions"] = len(re.findall(r"async\s+def\s+\w+", content))
        # Count class definitions
        patterns["class_definitions"] = len(re.findall(r"class\s+\w+", content))
        # Count decorators
        patterns["decorators"] = len(re.findall(r"@\w+", content))
        # Count type hints (basic detection)
        patterns["type_hints"] = len(re.findall(r":\s*\w+\[?", content))
        # Count docstrings (triple quotes)
        patterns["docstrings"] = len(re.findall(r'""".*?"""', content, re.DOTALL))
        # Count comments
        patterns["comments"] = len(re.findall(r"#.*$", content, re.MULTILINE))

    elif language in ("typescript", "javascript"):
        # Count async functions
        patterns["async_functions"] = len(re.findall(r"async\s+(function\s+)?\w+", content))
        # Count class definitions
        patterns["class_definitions"] = len(re.findall(r"class\s+\w+", content))
        # Count decorators (TS)
        patterns["decorators"] = len(re.findall(r"@\w+", content))
        # Count type hints (TS)
        patterns["type_hints"] = len(re.findall(r":\s*\w+", content))
        # Count comments
        patterns["comments"] = len(re.findall(r"//.*$", content, re.MULTILINE))
        patterns["comments"] += len(re.findall(r"/\*.*?\*/", content, re.DOTALL))

    return patterns


async def validate_syntax(content: str, language: str) -> dict[str, Any]:
    """Validate code syntax.

    Args:
        content: Code content
        language: Programming language

    Returns:
        Dictionary with validation results
    """
    if language == "python":
        try:
            ast.parse(content)
            return {"valid": True, "errors": []}
        except SyntaxError as e:
            return {
                "valid": False,
                "errors": [{"line": e.lineno, "message": str(e)}]
            }

    # For other languages, basic validation
    if not content.strip():
        return {"valid": False, "errors": [{"message": "Empty file"}]}

    return {"valid": True, "errors": []}


async def extract_imports(content: str, language: str) -> list[str]:
    """Extract import statements from code.

    Args:
        content: Code content
        language: Programming language

    Returns:
        List of import statements
    """
    imports = []

    if language == "python":
        # Python imports
        imports.extend(re.findall(r"^import\s+(.+)$", content, re.MULTILINE))
        imports.extend(re.findall(r"^from\s+(\S+)\s+import", content, re.MULTILINE))

    elif language in ("typescript", "javascript"):
        # JS/TS imports
        imports.extend(re.findall(r"^import\s+.+from\s+['\"](.+?)['\"]", content, re.MULTILINE))
        imports.extend(re.findall(r"^require\(['\"](.+?)['\"]\)", content, re.MULTILINE))

    return imports


async def get_file_dependencies(
    file_path: str,
    working_dir: str = "."
) -> dict[str, Any]:
    """Get dependencies for a specific file.

    Args:
        file_path: Path to the file
        working_dir: Working directory

    Returns:
        Dictionary with dependencies information
    """
    content = await read_file_safe(file_path, working_dir)
    if not content:
        return {"error": "Could not read file"}

    language = await detect_language(file_path)
    imports = await extract_imports(content, language)

    return {
        "file_path": file_path,
        "language": language,
        "imports": imports,
        "total_imports": len(imports),
    }
