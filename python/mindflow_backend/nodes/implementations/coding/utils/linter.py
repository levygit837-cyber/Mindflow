"""Linter utilities for Coder nodes.

This module provides functions for code linting, type checking,
and code quality analysis.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


async def detect_linter(working_dir: str = ".") -> str:
    """Detect which linter is available.

    Args:
        working_dir: Working directory

    Returns:
        Linter name (ruff, flake8, eslint, etc.)
    """
    # Check for ruff (Python)
    try:
        result = subprocess.run(
            ["ruff", "--version"],
            capture_output=True,
            timeout=5,
        )
        if result.returncode == 0:
            return "ruff"
    except:
        pass

    # Check for flake8 (Python)
    try:
        result = subprocess.run(
            ["flake8", "--version"],
            capture_output=True,
            timeout=5,
        )
        if result.returncode == 0:
            return "flake8"
    except:
        pass

    # Check for eslint (JavaScript/TypeScript)
    if (Path(working_dir) / "package.json").exists():
        try:
            result = subprocess.run(
                ["npx", "eslint", "--version"],
                capture_output=True,
                timeout=10,
            )
            if result.returncode == 0:
                return "eslint"
        except:
            pass

    return "unknown"


async def run_ruff(
    file_path: str,
    working_dir: str = ".",
    fix: bool = False,
) -> dict[str, Any]:
    """Run ruff linter on Python files.

    Args:
        file_path: Path to the file
        working_dir: Working directory
        fix: Auto-fix issues

    Returns:
        Dictionary with linting results
    """
    try:
        cmd = ["ruff", "check", file_path]

        if fix:
            cmd.append("--fix")

        result = subprocess.run(
            cmd,
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=30,
        )

        output = result.stdout + result.stderr

        # Parse ruff output
        errors = []
        warnings = []

        for line in output.split("\n"):
            if line.strip():
                # Ruff format: file:line:col: CODE message
                match = re.match(
                    r".+:(\d+):(\d+):\s+(\w+)\s+(.+)",
                    line
                )
                if match:
                    error_info = {
                        "line": int(match.group(1)),
                        "col": int(match.group(2)),
                        "code": match.group(3),
                        "message": match.group(4).strip(),
                    }
                    if match.group(3).startswith("E"):
                        errors.append(error_info)
                    else:
                        warnings.append(error_info)

        _logger.info(
            "ruff_completed",
            file_path=file_path,
            errors=len(errors),
            warnings=len(warnings),
            return_code=result.returncode,
        )

        return {
            "success": result.returncode == 0,
            "errors": errors,
            "warnings": warnings,
            "total_issues": len(errors) + len(warnings),
            "output": output,
        }

    except subprocess.TimeoutExpired:
        _logger.error("ruff_timeout")
        return {
            "success": False,
            "error": "Linter timeout",
            "errors": [],
            "warnings": [],
        }
    except Exception as e:
        _logger.error("ruff_error", error=str(e))
        return {
            "success": False,
            "error": str(e),
            "errors": [],
            "warnings": [],
        }


async def run_flake8(
    file_path: str,
    working_dir: str = ".",
) -> dict[str, Any]:
    """Run flake8 linter on Python files.

    Args:
        file_path: Path to the file
        working_dir: Working directory

    Returns:
        Dictionary with linting results
    """
    try:
        cmd = ["flake8", file_path, "--max-line-length=120"]

        result = subprocess.run(
            cmd,
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=30,
        )

        output = result.stdout + result.stderr

        # Parse flake8 output
        issues = []

        for line in output.split("\n"):
            if line.strip():
                # Flake8 format: file:line:col: CODE message
                match = re.match(
                    r".+:(\d+):(\d+):\s+(\w+)\s+(.+)",
                    line
                )
                if match:
                    issues.append({
                        "line": int(match.group(1)),
                        "col": int(match.group(2)),
                        "code": match.group(3),
                        "message": match.group(4).strip(),
                    })

        _logger.info(
            "flake8_completed",
            file_path=file_path,
            issues=len(issues),
            return_code=result.returncode,
        )

        return {
            "success": result.returncode == 0,
            "errors": issues,
            "warnings": [],
            "total_issues": len(issues),
            "output": output,
        }

    except subprocess.TimeoutExpired:
        _logger.error("flake8_timeout")
        return {
            "success": False,
            "error": "Linter timeout",
            "errors": [],
            "warnings": [],
        }
    except Exception as e:
        _logger.error("flake8_error", error=str(e))
        return {
            "success": False,
            "error": str(e),
            "errors": [],
            "warnings": [],
        }


async def run_eslint(
    file_path: str,
    working_dir: str = ".",
    fix: bool = False,
) -> dict[str, Any]:
    """Run eslint on JavaScript/TypeScript files.

    Args:
        file_path: Path to the file
        working_dir: Working directory
        fix: Auto-fix issues

    Returns:
        Dictionary with linting results
    """
    try:
        cmd = ["npx", "eslint", file_path, "--format=json"]

        if fix:
            cmd.append("--fix")

        result = subprocess.run(
            cmd,
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=30,
        )

        output = result.stdout + result.stderr

        # Parse JSON output
        errors = []
        warnings = []

        try:
            import json
            eslint_output = json.loads(output)

            for result in eslint_output:
                for message in result.get("messages", []):
                    issue = {
                        "line": message.get("line", 0),
                        "col": message.get("column", 0),
                        "code": message.get("ruleId", "unknown"),
                        "message": message.get("message", ""),
                        "severity": message.get("severity", 1),
                    }
                    if message.get("severity", 1) == 2:
                        errors.append(issue)
                    else:
                        warnings.append(issue)

        except json.JSONDecodeError:
            # Fallback to simple parsing
            for line in output.split("\n"):
                if line.strip():
                    warnings.append({
                        "message": line.strip(),
                    })

        _logger.info(
            "eslint_completed",
            file_path=file_path,
            errors=len(errors),
            warnings=len(warnings),
            return_code=result.returncode,
        )

        return {
            "success": result.returncode == 0,
            "errors": errors,
            "warnings": warnings,
            "total_issues": len(errors) + len(warnings),
            "output": output,
        }

    except subprocess.TimeoutExpired:
        _logger.error("eslint_timeout")
        return {
            "success": False,
            "error": "Linter timeout",
            "errors": [],
            "warnings": [],
        }
    except Exception as e:
        _logger.error("eslint_error", error=str(e))
        return {
            "success": False,
            "error": str(e),
            "errors": [],
            "warnings": [],
        }


async def run_linter(
    file_path: str,
    working_dir: str = ".",
    fix: bool = False,
) -> dict[str, Any]:
    """Run linter with automatic detection.

    Args:
        file_path: Path to the file
        working_dir: Working directory
        fix: Auto-fix issues

    Returns:
        Dictionary with linting results
    """
    linter = await detect_linter(working_dir)
    file_ext = Path(file_path).suffix.lower()

    if linter == "ruff" and file_ext == ".py":
        return await run_ruff(file_path, working_dir, fix)
    elif linter == "flake8" and file_ext == ".py":
        return await run_flake8(file_path, working_dir)
    elif linter == "eslint" and file_ext in (".js", ".jsx", ".ts", ".tsx"):
        return await run_eslint(file_path, working_dir, fix)
    else:
        _logger.warning("unknown_linter", linter=linter, file_ext=file_ext)
        return {
            "success": False,
            "error": f"Could not detect appropriate linter for {file_ext}",
            "errors": [],
            "warnings": [],
        }


async def detect_type_checker(working_dir: str = ".") -> str:
    """Detect which type checker is available.

    Args:
        working_dir: Working directory

    Returns:
        Type checker name (mypy, tsc, etc.)
    """
    # Check for mypy (Python)
    try:
        result = subprocess.run(
            ["mypy", "--version"],
            capture_output=True,
            timeout=5,
        )
        if result.returncode == 0:
            return "mypy"
    except:
        pass

    # Check for tsc (TypeScript)
    try:
        result = subprocess.run(
            ["npx", "tsc", "--version"],
            capture_output=True,
            timeout=5,
        )
        if result.returncode == 0:
            return "tsc"
    except:
        pass

    return "unknown"


async def run_mypy(
    file_path: str,
    working_dir: str = ".",
) -> dict[str, Any]:
    """Run mypy type checker on Python files.

    Args:
        file_path: Path to the file
        working_dir: Working directory

    Returns:
        Dictionary with type checking results
    """
    try:
        cmd = ["mypy", file_path, "--no-error-summary"]

        result = subprocess.run(
            cmd,
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=30,
        )

        output = result.stdout + result.stderr

        # Parse mypy output
        errors = []

        for line in output.split("\n"):
            if line.strip() and ":" in line:
                # Mypy format: file:line: error: message
                match = re.match(
                    r".+:(\d+):\s+(error|warning|note):\s+(.+)",
                    line
                )
                if match:
                    errors.append({
                        "line": int(match.group(1)),
                        "severity": match.group(2),
                        "message": match.group(3).strip(),
                    })

        _logger.info(
            "mypy_completed",
            file_path=file_path,
            errors=len(errors),
            return_code=result.returncode,
        )

        return {
            "success": result.returncode == 0,
            "errors": errors,
            "total_errors": len(errors),
            "output": output,
        }

    except subprocess.TimeoutExpired:
        _logger.error("mypy_timeout")
        return {
            "success": False,
            "error": "Type checker timeout",
            "errors": [],
        }
    except Exception as e:
        _logger.error("mypy_error", error=str(e))
        return {
            "success": False,
            "error": str(e),
            "errors": [],
        }


async def run_tsc(
    file_path: str,
    working_dir: str = ".",
) -> dict[str, Any]:
    """Run tsc type checker on TypeScript files.

    Args:
        file_path: Path to the file
        working_dir: Working directory

    Returns:
        Dictionary with type checking results
    """
    try:
        cmd = ["npx", "tsc", "--noEmit", file_path]

        result = subprocess.run(
            cmd,
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=30,
        )

        output = result.stdout + result.stderr

        # Parse tsc output
        errors = []

        for line in output.split("\n"):
            if "error TS" in line:
                # TSC format: file(line,col): error TS####: message
                match = re.match(
                    r".+\((\d+),(\d+)\):\s+error\s+TS(\d+):\s+(.+)",
                    line
                )
                if match:
                    errors.append({
                        "line": int(match.group(1)),
                        "col": int(match.group(2)),
                        "code": f"TS{match.group(3)}",
                        "message": match.group(4).strip(),
                    })

        _logger.info(
            "tsc_completed",
            file_path=file_path,
            errors=len(errors),
            return_code=result.returncode,
        )

        return {
            "success": result.returncode == 0,
            "errors": errors,
            "total_errors": len(errors),
            "output": output,
        }

    except subprocess.TimeoutExpired:
        _logger.error("tsc_timeout")
        return {
            "success": False,
            "error": "Type checker timeout",
            "errors": [],
        }
    except Exception as e:
        _logger.error("tsc_error", error=str(e))
        return {
            "success": False,
            "error": str(e),
            "errors": [],
        }


async def run_type_checker(
    file_path: str,
    working_dir: str = ".",
) -> dict[str, Any]:
    """Run type checker with automatic detection.

    Args:
        file_path: Path to the file
        working_dir: Working directory

    Returns:
        Dictionary with type checking results
    """
    checker = await detect_type_checker(working_dir)
    file_ext = Path(file_path).suffix.lower()

    if checker == "mypy" and file_ext == ".py":
        return await run_mypy(file_path, working_dir)
    elif checker == "tsc" and file_ext in (".ts", ".tsx"):
        return await run_tsc(file_path, working_dir)
    else:
        _logger.warning("unknown_type_checker", checker=checker, file_ext=file_ext)
        return {
            "success": False,
            "error": f"Could not detect appropriate type checker for {file_ext}",
            "errors": [],
        }


async def quick_lint_check(
    file_path: str,
    working_dir: str = ".",
) -> dict[str, Any]:
    """Perform quick lint check (syntax + basic style).

    Args:
        file_path: Path to the file
        working_dir: Working directory

    Returns:
        Dictionary with quick check results
    """
    # First check syntax
    from mindflow_backend.nodes.implementations.coding.utils.code_operations import (
        detect_language,
        validate_syntax,
    )

    content = None
    try:
        content = Path(working_dir, file_path).read_text(encoding="utf-8")
    except Exception as e:
        return {
            "success": False,
            "error": f"Could not read file: {e}",
            "syntax_valid": False,
        }

    language = await detect_language(file_path)
    syntax_result = await validate_syntax(content, language)

    if not syntax_result["valid"]:
        return {
            "success": False,
            "syntax_valid": False,
            "syntax_errors": syntax_result["errors"],
            "style_errors": [],
        }

    # Quick style check (no auto-fix)
    lint_result = await run_linter(file_path, working_dir, fix=False)

    return {
        "success": lint_result["success"],
        "syntax_valid": True,
        "style_errors": lint_result["errors"],
        "style_warnings": lint_result["warnings"],
    }
