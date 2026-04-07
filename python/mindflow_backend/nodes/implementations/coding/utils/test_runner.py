"""Test runner utilities for Coder nodes.

This module provides functions for running tests, collecting results,
and handling test execution.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


async def detect_test_framework(working_dir: str = ".") -> str:
    """Detect which test framework is being used.

    Args:
        working_dir: Working directory

    Returns:
        Test framework name (pytest, unittest, jest, etc.)
    """
    # Check for pytest
    if (Path(working_dir) / "pytest.ini").exists():
        return "pytest"
    if (Path(working_dir) / "pyproject.toml").exists():
        content = (Path(working_dir) / "pyproject.toml").read_text()
        if "pytest" in content:
            return "pytest"

    # Check for unittest
    test_files = list(Path(working_dir).rglob("test_*.py"))
    if test_files:
        for test_file in test_files[:3]:  # Check first 3 files
            content = test_file.read_text()
            if "unittest" in content or "TestCase" in content:
                return "unittest"
            if "pytest" in content:
                return "pytest"

    # Check for JavaScript test frameworks
    if (Path(working_dir) / "package.json").exists():
        content = (Path(working_dir) / "package.json").read_text()
        if "jest" in content:
            return "jest"
        if "mocha" in content:
            return "mocha"
        if "vitest" in content:
            return "vitest"

    return "unknown"


async def run_python_tests(
    working_dir: str = ".",
    framework: str = "pytest",
    test_path: str | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """Run Python tests using detected framework.

    Args:
        working_dir: Working directory
        framework: Test framework (pytest, unittest)
        test_path: Specific test path to run
        verbose: Enable verbose output

    Returns:
        Dictionary with test results
    """
    try:
        if framework == "pytest":
            return await _run_pytest(working_dir, test_path, verbose)
        elif framework == "unittest":
            return await _run_unittest(working_dir, test_path, verbose)
        else:
            return {
                "success": False,
                "error": f"Unknown framework: {framework}",
                "tests_run": 0,
                "tests_failed": 0,
            }

    except Exception as e:
        _logger.error("test_execution_failed", framework=framework, error=str(e))
        return {
            "success": False,
            "error": str(e),
            "tests_run": 0,
            "tests_failed": 0,
        }


async def _run_pytest(
    working_dir: str,
    test_path: str | None,
    verbose: bool,
) -> dict[str, Any]:
    """Run tests using pytest.

    Args:
        working_dir: Working directory
        test_path: Specific test path
        verbose: Verbose output

    Returns:
        Dictionary with test results
    """
    cmd = ["python", "-m", "pytest"]

    if test_path:
        cmd.append(test_path)

    cmd.extend([
        "--tb=short",
        "--no-header",
        "-q",
    ])

    if verbose:
        cmd.append("-v")

    # Add JSON output for parsing
    cmd.extend(["--json-report", "--json-report-file=/tmp/pytest_report.json"])

    try:
        result = subprocess.run(
            cmd,
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=300,
        )

        # Parse output
        passed = 0
        failed = 0
        skipped = 0
        errors = []

        # Try to parse pytest output
        output = result.stdout + result.stderr
        summary_match = re.search(r"(\d+)\s+passed", output)
        if summary_match:
            passed = int(summary_match.group(1))

        failed_match = re.search(r"(\d+)\s+failed", output)
        if failed_match:
            failed = int(failed_match.group(1))

        skipped_match = re.search(r"(\d+)\s+skipped", output)
        if skipped_match:
            skipped = int(skipped_match.group(1))

        # Try to read JSON report if available
        try:
            with open("/tmp/pytest_report.json", "r") as f:
                json_report = json.load(f)
                if "summary" in json_report:
                    passed = json_report["summary"].get("passed", 0)
                    failed = json_report["summary"].get("failed", 0)
                    skipped = json_report["summary"].get("skipped", 0)
        except:
            pass

        _logger.info(
            "pytest_completed",
            passed=passed,
            failed=failed,
            skipped=skipped,
            return_code=result.returncode,
        )

        return {
            "success": result.returncode == 0,
            "tests_run": passed + failed + skipped,
            "tests_passed": passed,
            "tests_failed": failed,
            "tests_skipped": skipped,
            "output": output,
            "return_code": result.returncode,
        }

    except subprocess.TimeoutExpired as e:
        _logger.error("pytest_timeout")
        # Kill the process to prevent zombie processes
        try:
            import signal
            import os
            os.killpg(os.getpgid(e.pid), signal.SIGTERM)
        except:
            pass
        return {
            "success": False,
            "error": "Test execution timeout",
            "tests_run": 0,
            "tests_failed": 0,
        }
    except Exception as e:
        _logger.error("pytest_error", error=str(e))
        return {
            "success": False,
            "error": str(e),
            "tests_run": 0,
            "tests_failed": 0,
        }


async def _run_unittest(
    working_dir: str,
    test_path: str | None,
    verbose: bool,
) -> dict[str, Any]:
    """Run tests using unittest.

    Args:
        working_dir: Working directory
        test_path: Specific test path
        verbose: Verbose output

    Returns:
        Dictionary with test results
    """
    cmd = ["python", "-m", "unittest"]

    if verbose:
        cmd.append("-v")

    if test_path:
        cmd.append(test_path)
    else:
        cmd.append("discover")

    try:
        result = subprocess.run(
            cmd,
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=300,
        )

        output = result.stdout + result.stderr

        # Parse unittest output
        passed = 0
        failed = 0
        errors = []

        # Simple parsing
        if "OK" in output:
            # Extract number from "Ran X tests in ... OK"
            match = re.search(r"Ran (\d+) tests", output)
            if match:
                passed = int(match.group(1))

        if "FAILED" in output:
            failed_match = re.search(r"FAILED \((\w+)\)", output)
            if failed_match:
                failed = 1  # Simplified

        _logger.info(
            "unittest_completed",
            passed=passed,
            failed=failed,
            return_code=result.returncode,
        )

        return {
            "success": result.returncode == 0,
            "tests_run": passed + failed,
            "tests_passed": passed,
            "tests_failed": failed,
            "output": output,
            "return_code": result.returncode,
        }

    except subprocess.TimeoutExpired as e:
        _logger.error("unittest_timeout")
        # Kill the process to prevent zombie processes
        try:
            import signal
            import os
            os.killpg(os.getpgid(e.pid), signal.SIGTERM)
        except:
            pass
        return {
            "success": False,
            "error": "Test execution timeout",
            "tests_run": 0,
            "tests_failed": 0,
        }
    except Exception as e:
        _logger.error("unittest_error", error=str(e))
        return {
            "success": False,
            "error": str(e),
            "tests_run": 0,
            "tests_failed": 0,
        }


async def run_javascript_tests(
    working_dir: str = ".",
    framework: str = "jest",
    test_path: str | None = None,
) -> dict[str, Any]:
    """Run JavaScript/TypeScript tests.

    Args:
        working_dir: Working directory
        framework: Test framework (jest, mocha, vitest)
        test_path: Specific test path

    Returns:
        Dictionary with test results
    """
    try:
        if framework == "jest":
            cmd = ["npm", "test", "--", "--json"]
        elif framework == "vitest":
            cmd = ["npx", "vitest", "run", "--json"]
        elif framework == "mocha":
            cmd = ["npm", "test"]
        else:
            return {
                "success": False,
                "error": f"Unknown framework: {framework}",
                "tests_run": 0,
                "tests_failed": 0,
            }

        if test_path:
            cmd.append(test_path)

        result = subprocess.run(
            cmd,
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=300,
        )

        output = result.stdout + result.stderr

        # Parse JSON output if available
        passed = 0
        failed = 0

        try:
            # Try to extract JSON from output
            json_match = re.search(r'\{.*\}', output, re.DOTALL)
            if json_match:
                json_data = json.loads(json_match.group())
                if "testResults" in json_data:
                    for test in json_data["testResults"]:
                        passed += len([t for t in test.get("assertionResults", []) if t.get("status") == "passed"])
                        failed += len([t for t in test.get("assertionResults", []) if t.get("status") == "failed"])
        except:
            # Fallback to simple parsing
            passed_match = re.search(r"(\d+)\s+passing", output, re.IGNORECASE)
            if passed_match:
                passed = int(passed_match.group(1))

            failed_match = re.search(r"(\d+)\s+failing", output, re.IGNORECASE)
            if failed_match:
                failed = int(failed_match.group(1))

        _logger.info(
            "js_test_completed",
            framework=framework,
            passed=passed,
            failed=failed,
            return_code=result.returncode,
        )

        return {
            "success": result.returncode == 0,
            "tests_run": passed + failed,
            "tests_passed": passed,
            "tests_failed": failed,
            "output": output,
            "return_code": result.returncode,
        }

    except subprocess.TimeoutExpired:
        _logger.error("js_test_timeout")
        return {
            "success": False,
            "error": "Test execution timeout",
            "tests_run": 0,
            "tests_failed": 0,
        }
    except Exception as e:
        _logger.error("js_test_error", error=str(e))
        return {
            "success": False,
            "error": str(e),
            "tests_run": 0,
            "tests_failed": 0,
        }


async def run_tests(
    working_dir: str = ".",
    test_path: str | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """Run tests with automatic framework detection.

    Args:
        working_dir: Working directory
        test_path: Specific test path
        verbose: Verbose output

    Returns:
        Dictionary with test results
    """
    framework = await detect_test_framework(working_dir)

    if framework in ("pytest", "unittest"):
        return await run_python_tests(working_dir, framework, test_path, verbose)
    elif framework in ("jest", "mocha", "vitest"):
        return await run_javascript_tests(working_dir, framework, test_path)
    else:
        _logger.warning("unknown_test_framework", framework=framework)
        return {
            "success": False,
            "error": f"Could not detect test framework",
            "tests_run": 0,
            "tests_failed": 0,
        }


async def get_test_coverage(
    working_dir: str = ".",
    framework: str = "pytest",
) -> dict[str, Any]:
    """Get test coverage report.

    Args:
        working_dir: Working directory
        framework: Test framework

    Returns:
        Dictionary with coverage information
    """
    try:
        if framework == "pytest":
            cmd = ["python", "-m", "pytest", "--cov=.", "--cov-report=json", "--cov-report=term"]
        else:
            return {
                "success": False,
                "error": f"Coverage not supported for {framework}",
            }

        result = subprocess.run(
            cmd,
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=300,
        )

        # Try to read coverage.json
        coverage_file = Path(working_dir) / "coverage.json"
        if coverage_file.exists():
            try:
                with open(coverage_file) as f:
                    coverage_data = json.load(f)
                    return {
                        "success": True,
                        "coverage": coverage_data.get("totals", {}).get("percent_covered", 0),
                        "files": coverage_data.get("files", {}),
                    }
            except:
                pass

        # Fallback: parse terminal output
        output = result.stdout + result.stderr
        match = re.search(r"TOTAL\s+(\d+)%", output)
        if match:
            return {
                "success": True,
                "coverage": float(match.group(1)),
            }

        return {
            "success": False,
            "error": "Could not parse coverage report",
        }

    except Exception as e:
        _logger.error("coverage_error", error=str(e))
        return {
            "success": False,
            "error": str(e),
        }
