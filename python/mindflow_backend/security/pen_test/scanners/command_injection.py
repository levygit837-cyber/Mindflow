"""Command injection scanner.

Scans codebase for potential command injection vulnerabilities.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Tuple

from .base import BaseScanner
from ..config import PenTestFinding, PenTestSeverity


class CommandInjectionScanner(BaseScanner):
    """Scanner for detecting command injection vulnerabilities."""

    def __init__(self):
        """Initialize command injection scanner."""
        super().__init__()
        # Unsafe functions
        self.unsafe_functions = [
            r"os\.system\s*\(",
            r"subprocess\.call\s*\(\s*shell\s*=\s*True",
            r"subprocess\.run\s*\(\s*shell\s*=\s*True",
            r"subprocess\.Popen\s*\(\s*shell\s*=\s*True",
            r"commands\.getoutput\s*\(",
            r"commands\.getstatusoutput\s*\(",
            r"eval\s*\(",
            r"exec\s*\(",
        ]

        # Safe patterns (using list/tuple for args)
        self.safe_patterns = [
            r"subprocess\.call\s*\(\s*\[",  # List of args
            r"subprocess\.run\s*\(\s*\[",  # List of args
            r"subprocess\.Popen\s*\(\s*\[",  # List of args
            r"subprocess\.call\s*\(\s*\(",  # Tuple of args (no shell=True)
            r"subprocess\.run\s*\(\s*\(",  # Tuple of args (no shell=True)
            r"subprocess\.Popen\s*\(\s*\(",  # Tuple of args (no shell=True)
        ]

    def scan(self, codebase_path: Path) -> Tuple[list[PenTestFinding], int]:
        """Scan codebase for command injection vulnerabilities.

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
        """Scan a single file for command injection vulnerabilities.

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
                for pattern in self.unsafe_functions:
                    if re.search(pattern, line):
                        finding = PenTestFinding(
                            scanner_name=self.name,
                            severity=PenTestSeverity.HIGH,
                            title="Potential command injection vulnerability",
                            description=f"Use of unsafe function: {pattern}",
                            file_path=str(file_path),
                            line_number=line_number,
                            code_snippet=line.strip(),
                            recommendation="Use subprocess with list/tuple of arguments instead of shell=True, or use shlex.quote() for escaping",
                            cwe_id="CWE-78",
                            references=[
                                "https://cwe.mitre.org/data/definitions/78.html",
                                "https://owasp.org/www-community/attacks/Command_Injection",
                            ],
                        )
                        findings.append(finding)

        except Exception:
            pass

        return findings, len(lines)
