"""Penetration testing configuration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class PenTestSeverity(Enum):
    """Penetration test finding severity."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class PenTestFinding:
    """A single penetration test finding."""

    scanner_name: str
    severity: PenTestSeverity
    title: str
    description: str
    file_path: str | None = None
    line_number: int | None = None
    code_snippet: str | None = None
    recommendation: str = ""
    cwe_id: str | None = None  # CWE identifier
    references: list[str] = None

    def __post_init__(self) -> None:
        if self.references is None:
            self.references = []

    def to_dict(self) -> dict[str, Any]:
        """Convert finding to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "scanner": self.scanner_name,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "code_snippet": self.code_snippet,
            "recommendation": self.recommendation,
            "cwe_id": self.cwe_id,
            "references": self.references,
        }


@dataclass
class PenTestResult:
    """Result of a penetration test scan."""

    findings: list[PenTestFinding]
    scan_duration_seconds: float
    files_scanned: int
    timestamp: str

    def get_findings_by_severity(self, severity: PenTestSeverity) -> list[PenTestFinding]:
        """Get findings filtered by severity.

        Args:
            severity: Severity level to filter by

        Returns:
            List of findings with specified severity
        """
        return [f for f in self.findings if f.severity == severity]

    def get_critical_findings(self) -> list[PenTestFinding]:
        """Get all critical findings."""
        return self.get_findings_by_severity(PenTestSeverity.CRITICAL)

    def get_high_findings(self) -> list[PenTestFinding]:
        """Get all high findings."""
        return self.get_findings_by_severity(PenTestSeverity.HIGH)

    def get_summary(self) -> dict[str, int]:
        """Get summary of findings by severity.

        Returns:
            Dictionary with count per severity
        """
        summary = {severity.value: 0 for severity in PenTestSeverity}
        for finding in self.findings:
            summary[finding.severity.value] += 1
        return summary

    def has_critical_or_high_findings(self) -> bool:
        """Check if there are critical or high findings.

        Returns:
            True if critical or high findings exist
        """
        return (
            len(self.get_critical_findings()) > 0
            or len(self.get_high_findings()) > 0
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "findings": [f.to_dict() for f in self.findings],
            "scan_duration_seconds": self.scan_duration_seconds,
            "files_scanned": self.files_scanned,
            "timestamp": self.timestamp,
            "summary": self.get_summary(),
        }


# Penetration test configuration
PEN_TEST_CONFIG = {
    "mode": "quick",  # quick, full, custom
    "scanners": [
        "sql_injection",
        "command_injection",
        "xss",
        "secret_leak",
    ],
    "severity_threshold": "high",  # Report only high+ severity
    "exclude_patterns": ["tests/", "migrations/", ".venv/", "__pycache__/"],
    "max_findings": 100,
    "timeout_seconds": 300,  # 5 minutes
}
