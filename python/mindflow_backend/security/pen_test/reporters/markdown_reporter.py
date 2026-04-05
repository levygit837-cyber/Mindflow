"""Markdown reporter for penetration test results."""

from ..config import PenTestResult


class MarkdownReporter:
    """Generate Markdown reports from penetration test results."""

    def generate(self, result: PenTestResult) -> str:
        """Generate Markdown report.

        Args:
            result: PenTestResult to report on

        Returns:
            Markdown report string
        """
        lines = [
            "# Security Scan Report",
            "",
            f"**Timestamp:** {result.timestamp}",
            f"**Duration:** {result.scan_duration_seconds:.2f}s",
            f"**Files Scanned:** {result.files_scanned}",
            "",
            "## Summary",
            "",
        ]

        # Summary table
        summary = result.get_summary()
        lines.append("| Severity | Count |")
        lines.append("|----------|-------|")
        for severity, count in summary.items():
            lines.append(f"| {severity.title()} | {count} |")
        lines.append("")

        # Findings by severity
        severity_order = ["critical", "high", "medium", "low", "info"]
        for severity in severity_order:
            findings = result.get_findings_by_severity(
                type("Severity", (), {"value": severity})()
            )
            if findings:
                lines.append(f"## {severity.title()} Findings")
                lines.append("")
                for finding in findings:
                    lines.append(f"### {finding.title}")
                    lines.append("")
                    lines.append(f"**File:** `{finding.file_path}:{finding.line_number}`")
                    lines.append(f"**CWE:** {finding.cwe_id}")
                    lines.append("")
                    lines.append(f"**Description:** {finding.description}")
                    lines.append("")
                    lines.append(f"**Code:**")
                    lines.append("```")
                    lines.append(finding.code_snippet or "N/A")
                    lines.append("```")
                    lines.append("")
                    lines.append(f"**Recommendation:** {finding.recommendation}")
                    lines.append("")
                    if finding.references:
                        lines.append("**References:**")
                        for ref in finding.references:
                            lines.append(f"- {ref}")
                        lines.append("")

        return "\n".join(lines)
