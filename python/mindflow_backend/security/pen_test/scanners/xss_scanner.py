"""XSS scanner.

Scans codebase for potential XSS vulnerabilities.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Tuple

from .base import BaseScanner
from ..config import PenTestFinding, PenTestSeverity


class XSSScanner(BaseScanner):
    """Scanner for detecting XSS vulnerabilities."""

    def __init__(self):
        """Initialize XSS scanner."""
        super().__init__()
        # Patterns for potential XSS vulnerabilities
        self.patterns = [
            # Direct HTML output without sanitization
            (r"response\.write\s*\(\s*.*\)", "Direct HTML output without sanitization"),
            (r"print\s*\(\s*.*\)", "Direct print without sanitization"),
            # Template rendering without autoescape
            (r"render_template\s*\([^)]*autoescape\s*=\s*False", "Template rendering with autoescape disabled"),
            # Unsafe innerHTML
            (r"\.innerHTML\s*=\s*", "Unsafe innerHTML assignment"),
            # Unsafe outerHTML
            (r"\.outerHTML\s*=\s*", "Unsafe outerHTML assignment"),
            # eval() with user input
            (r"eval\s*\(\s*.*\)", "Use of eval() function"),
            # document.write with user input
            (r"document\.write\s*\(\s*.*\)", "Use of document.write()"),
        ]

    def scan(self, codebase_path: Path) -> Tuple[list[PenTestFinding], int]:
        """Scan codebase for XSS vulnerabilities.

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
        """Scan a single file for XSS vulnerabilities.

        Args:
            file_path: Path to file

        Returns:
            Tuple of (findings, lines_scanned)
        """
        findings: list[PenTestFinding] = []

        try:
            with open(file_path, "r") as f:
                lines = f.readlines()

            for line_number, line in enumerate(lines, start=1):
                for pattern, description in self.patterns:
                    if re.search(pattern, line):
                        finding = PenTestFinding(
                            scanner_name=self.name,
                            severity=PenTestSeverity.HIGH,
                            title="Potential XSS vulnerability",
                            description=description,
                            file_path=str(file_path),
                            line_number=line_number,
                            code_snippet=line.strip(),
                            recommendation="Use proper output encoding and sanitization (e.g., html.escape, bleach.clean)",
                            cwe_id="CWE-79",
                            references=[
                                "https://cwe.mitre.org/data/definitions/79.html",
                                "https://owasp.org/www-community/attacks/xss/",
                            ],
                        )
                        findings.append(finding)

        except Exception:
            pass

        return findings, len(lines)
