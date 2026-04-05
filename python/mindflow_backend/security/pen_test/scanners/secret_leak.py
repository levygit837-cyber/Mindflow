"""Secret leak scanner.

Scans codebase for exposed secrets using the existing SecretScanner.
"""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

from mindflow_backend.security.secrets import SecretScanner

from .base import BaseScanner
from ..config import PenTestFinding, PenTestSeverity


class SecretLeakScanner(BaseScanner):
    """Scanner for detecting leaked secrets in code."""

    def __init__(self):
        """Initialize secret leak scanner."""
        super().__init__()
        self.secret_scanner = SecretScanner()

    def scan(self, codebase_path: Path) -> Tuple[list[PenTestFinding], int]:
        """Scan codebase for leaked secrets.

        Args:
            codebase_path: Path to codebase

        Returns:
            Tuple of (findings, files_scanned)
        """
        findings: list[PenTestFinding] = []
        files_scanned = 0

        exclude_patterns = [
            "tests/",
            "migrations/",
            ".venv/",
            "__pycache__/",
            ".git/",
        ]

        # Scan Python files
        for file_path in codebase_path.rglob("*.py"):
            if self._should_exclude_file(file_path, exclude_patterns):
                continue

            file_findings, _ = self.scan_file(file_path)
            findings.extend(file_findings)
            files_scanned += 1

        return findings, files_scanned

    def scan_file(self, file_path: Path) -> Tuple[list[PenTestFinding], int]:
        """Scan a single file for leaked secrets.

        Args:
            file_path: Path to file

        Returns:
            Tuple of (findings, lines_scanned)
        """
        findings: list[PenTestFinding] = []

        try:
            with open(file_path, "r") as f:
                content = f.read()

            # Use SecretScanner to detect secrets
            matches = self.secret_scanner.scan_content(content)

            for match in matches:
                finding = PenTestFinding(
                    scanner_name=self.name,
                    severity=PenTestSeverity.CRITICAL,
                    title=f"Leaked {match.description}",
                    description=f"Detected {match.description} in code",
                    file_path=str(file_path),
                    line_number=match.line_number,
                    code_snippet=match.matched_text,
                    recommendation="Remove the secret and use environment variables or secure storage",
                    cwe_id="CWE-798",
                    references=[
                        "https://cwe.mitre.org/data/definitions/798.html",
                        "https://docs.github.com/en/code-security/secret-scanning/about-secret-scanning",
                    ],
                )
                findings.append(finding)

        except Exception as e:
            _logger.error(
                "file_scan_failed",
                file_path=str(file_path),
                error=str(e),
            )
            pass  # Skip files that can't be read

        return findings, 0
