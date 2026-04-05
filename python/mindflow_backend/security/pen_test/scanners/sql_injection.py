"""SQL injection scanner.

Scans codebase for potential SQL injection vulnerabilities.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Tuple

from .base import BaseScanner
from ..config import PenTestFinding, PenTestSeverity


class SQLInjectionScanner(BaseScanner):
    """Scanner for detecting SQL injection vulnerabilities."""

    def __init__(self):
        """Initialize SQL injection scanner."""
        super().__init__()
        # Patterns for potential SQL injection vulnerabilities
        self.patterns = [
            # String concatenation in SQL queries
            (r"SELECT.*\+.*FROM", "String concatenation in SELECT query"),
            (r"INSERT.*\+.*INTO", "String concatenation in INSERT query"),
            (r"UPDATE.*\+.*SET", "String concatenation in UPDATE query"),
            (r"DELETE.*\+.*FROM", "String concatenation in DELETE query"),
            # f-strings with user input in SQL
            (rf'f["\'].*SELECT.*FROM.*\{{.*\}}', "f-string in SQL query"),
            (rf'f["\'].*INSERT.*INTO.*\{{.*\}}', "f-string in SQL query"),
            # .format() with user input in SQL
            (r'\.format\s*\([^)]*\).*SELECT', "String formatting in SQL query"),
            # Direct variable interpolation
            (r'"[^"]*\{[^}]*\}[^"]*".*SELECT', "Variable interpolation in SQL query"),
        ]

        # Safe patterns (parameterized queries, ORM)
        self.safe_patterns = [
            r"execute\s*\(\s*.*%\s*\)",  # Parameterized with %
            r"execute\s*\(\s*.*\?",  # Parameterized with ?
            r"Session\.query\s*\(",  # SQLAlchemy ORM
            r"Model\.select\(",  # SQLAlchemy ORM
            r"\.where\s*\(",  # ORM where clause
        ]

    def scan(self, codebase_path: Path) -> Tuple[list[PenTestFinding], int]:
        """Scan codebase for SQL injection vulnerabilities.

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
        """Scan a single file for SQL injection vulnerabilities.

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
                # Check for safe patterns first
                is_safe = any(re.search(pattern, line) for pattern in self.safe_patterns)
                if is_safe:
                    continue

                # Check for unsafe patterns
                for pattern, description in self.patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        finding = PenTestFinding(
                            scanner_name=self.name,
                            severity=PenTestSeverity.HIGH,
                            title="Potential SQL injection vulnerability",
                            description=description,
                            file_path=str(file_path),
                            line_number=line_number,
                            code_snippet=line.strip(),
                            recommendation="Use parameterized queries or ORM (e.g., SQLAlchemy, asyncpg)",
                            cwe_id="CWE-89",
                            references=[
                                "https://cwe.mitre.org/data/definitions/89.html",
                                "https://owasp.org/www-community/attacks/SQL_Injection",
                            ],
                        )
                        findings.append(finding)

        except Exception:
            pass

        return findings, len(lines)
