"""Main penetration testing framework.

Provides automated security scanning with multiple scanners.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mindflow_backend.infra.logging import get_logger

from .config import PEN_TEST_CONFIG, PenTestFinding, PenTestResult, PenTestSeverity
from .scanners import (
    CommandInjectionScanner,
    SecretLeakScanner,
    SQLInjectionScanner,
    XSSScanner,
)

_logger = get_logger(__name__)


class PenTestFramework:
    """Automated penetration testing framework.

    Features:
    - Multiple security scanners
    - Configurable severity threshold
    - Multiple output formats (Markdown, JSON, SARIF)
    - CI/CD integration
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize penetration testing framework.

        Args:
            config: Custom configuration (default: use PEN_TEST_CONFIG)
        """
        self.config = config or PEN_TEST_CONFIG
        self._scanners = {
            "sql_injection": SQLInjectionScanner(),
            "command_injection": CommandInjectionScanner(),
            "xss": XSSScanner(),
            "secret_leak": SecretLeakScanner(),
        }

    def scan_codebase(
        self,
        codebase_path: str,
        scanners: list[str] | None = None,
    ) -> PenTestResult:
        """Scan codebase for security issues.

        Args:
            codebase_path: Path to codebase to scan
            scanners: List of scanner names to use (default: from config)

        Returns:
            PenTestResult with findings
        """
        start_time = time.time()
        codebase = Path(codebase_path)

        if not codebase.exists():
            raise ValueError(f"Codebase path does not exist: {codebase_path}")

        # Determine which scanners to use
        scanner_names = scanners or self.config.get("scanners", [])
        findings: list[PenTestFinding] = []
        files_scanned = 0

        # Run each scanner
        for scanner_name in scanner_names:
            scanner = self._scanners.get(scanner_name)
            if not scanner:
                _logger.warning("scanner_not_found", scanner=scanner_name)
                continue

            try:
                _logger.info("running_scanner", scanner=scanner_name)
                scanner_findings, files = scanner.scan(codebase)
                findings.extend(scanner_findings)
                files_scanned = max(files_scanned, files)
            except Exception as e:
                _logger.error(
                    "scanner_error",
                    scanner=scanner_name,
                    error=str(e),
                )

        # Filter by severity threshold
        threshold = self.config.get("severity_threshold", "high")
        severity_order = ["critical", "high", "medium", "low", "info"]
        threshold_index = severity_order.index(threshold)

        filtered_findings = [
            f
            for f in findings
            if severity_order.index(f.severity.value) <= threshold_index
        ]

        # Limit findings
        max_findings = self.config.get("max_findings", 100)
        if len(filtered_findings) > max_findings:
            filtered_findings = filtered_findings[:max_findings]
            _logger.warning(
                "findings_limited",
                total=len(findings),
                limited=max_findings,
            )

        scan_duration = time.time() - start_time

        result = PenTestResult(
            findings=filtered_findings,
            scan_duration_seconds=scan_duration,
            files_scanned=files_scanned,
            timestamp=datetime.now(UTC).isoformat(),
        )

        _logger.info(
            "scan_complete",
            findings_count=len(result.findings),
            files_scanned=files_scanned,
            duration_seconds=scan_duration,
        )

        return result

    def scan_file(self, file_path: str) -> list[PenTestFinding]:
        """Scan a single file for security issues.

        Args:
            file_path: Path to file to scan

        Returns:
            List of findings
        """
        file = Path(file_path)
        if not file.exists():
            raise ValueError(f"File does not exist: {file_path}")

        findings: list[PenTestFinding] = []
        scanner_names = self.config.get("scanners", [])

        for scanner_name in scanner_names:
            scanner = self._scanners.get(scanner_name)
            if not scanner:
                continue

            try:
                scanner_findings, _ = scanner.scan_file(file)
                findings.extend(scanner_findings)
            except Exception as e:
                _logger.error(
                    "scanner_file_error",
                    scanner=scanner_name,
                    file=file_path,
                    error=str(e),
                )

        return findings

    def generate_report(
        self,
        result: PenTestResult,
        format: str = "markdown",
    ) -> str:
        """Generate security report.

        Args:
            result: PenTestResult to report on
            format: Report format (markdown, json, sarif)

        Returns:
            Report string
        """
        if format == "json":
            from .reporters.json_reporter import JSONReporter

            reporter = JSONReporter()
            return reporter.generate(result)
        elif format == "sarif":
            from .reporters.sarif_reporter import SARIFReporter

            reporter = SARIFReporter()
            return reporter.generate(result)
        else:  # markdown
            from .reporters.markdown_reporter import MarkdownReporter

            reporter = MarkdownReporter()
            return reporter.generate(result)
