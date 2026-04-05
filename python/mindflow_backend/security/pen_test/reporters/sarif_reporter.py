"""SARIF reporter for penetration test results.

SARIF (Static Analysis Results Interchange Format) for CI/CD integration.
"""

import json
from datetime import datetime

from ..config import PenTestResult, PenTestSeverity


class SARIFReporter:
    """Generate SARIF reports from penetration test results."""

    def __init__(self, tool_name: str = "MindFlow Security Scanner", tool_version: str = "1.0.0"):
        """Initialize SARIF reporter.

        Args:
            tool_name: Name of the scanning tool
            tool_version: Version of the scanning tool
        """
        self.tool_name = tool_name
        self.tool_version = tool_version

    def generate(self, result: PenTestResult) -> str:
        """Generate SARIF report.

        Args:
            result: PenTestResult to report on

        Returns:
            SARIF JSON string
        """
        sarif = {
            "version": "2.1.0",
            "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": self.tool_name,
                            "version": self.tool_version,
                            "informationUri": "https://github.com/mindflow/mindflow",
                            "rules": self._get_rules(),
                        }
                    },
                    "results": self._get_results(result),
                    "invocations": [
                        {
                            "startTimeUtc": result.timestamp,
                            "endTimeUtc": datetime.utcnow().isoformat() + "Z",
                            "exitCode": 1 if result.has_critical_or_high_findings() else 0,
                        }
                    ],
                }
            ],
        }

        return json.dumps(sarif, indent=2)

    def _get_rules(self) -> list[dict]:
        """Get SARIF rules for the scanner.

        Returns:
            List of rule definitions
        """
        return [
            {
                "id": "secret-leak",
                "name": "Secret Leak",
                "shortDescription": {"text": "Leaked secret detected in code"},
                "fullDescription": {
                    "text": "Hardcoded secrets detected in source code. Secrets should be stored in environment variables or secure storage."
                },
                "help": {"text": "Remove the secret and use environment variables or secure storage."},
                "properties": {"tags": ["security", "secrets"]},
            },
            {
                "id": "xss",
                "name": "XSS",
                "shortDescription": {"text": "Potential XSS vulnerability"},
                "fullDescription": {
                    "text": "Cross-site scripting (XSS) vulnerability detected. User input is not properly sanitized before being rendered."
                },
                "help": {"text": "Use proper output encoding and sanitization (e.g., html.escape, bleach.clean)."},
                "properties": {"tags": ["security", "xss"]},
            },
            {
                "id": "sql-injection",
                "name": "SQL Injection",
                "shortDescription": {"text": "Potential SQL injection vulnerability"},
                "fullDescription": {
                    "text": "SQL injection vulnerability detected. User input is concatenated into SQL queries without proper sanitization."
                },
                "help": {"text": "Use parameterized queries or ORM (e.g., SQLAlchemy, asyncpg)."},
                "properties": {"tags": ["security", "sql-injection"]},
            },
            {
                "id": "command-injection",
                "name": "Command Injection",
                "shortDescription": {"text": "Potential command injection vulnerability"},
                "fullDescription": {
                    "text": "Command injection vulnerability detected. User input is passed to shell commands without proper sanitization."
                },
                "help": {"text": "Use subprocess with list/tuple of arguments instead of shell=True, or use shlex.quote() for escaping."},
                "properties": {"tags": ["security", "command-injection"]},
            },
        ]

    def _get_results(self, result: PenTestResult) -> list[dict]:
        """Get SARIF results from findings.

        Args:
            result: PenTestResult

        Returns:
            List of SARIF result objects
        """
        sarif_results = []

        for finding in result.findings:
            rule_id = self._map_scanner_to_rule_id(finding.scanner_name)
            severity = self._map_severity(finding.severity)

            result_obj = {
                "ruleId": rule_id,
                "level": severity,
                "message": {
                    "text": finding.description,
                },
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": finding.file_path or "unknown"},
                            "region": {
                                "startLine": finding.line_number or 1,
                            },
                        }
                    }
                ],
                "codeFlows": [],
            }

            # Add code snippet if available
            if finding.code_snippet:
                result_obj["codeFlows"] = [
                    {
                        "threadFlows": [
                            {
                                "locations": [
                                    {
                                        "location": {
                                            "physicalLocation": {
                                                "artifactLocation": {
                                                    "uri": finding.file_path or "unknown"
                                                },
                                                "region": {
                                                    "startLine": finding.line_number or 1,
                                                    "snippet": {"text": finding.code_snippet},
                                                },
                                            }
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]

            sarif_results.append(result_obj)

        return sarif_results

    def _map_scanner_to_rule_id(self, scanner_name: str) -> str:
        """Map scanner name to SARIF rule ID.

        Args:
            scanner_name: Name of the scanner

        Returns:
            SARIF rule ID
        """
        if "SecretLeak" in scanner_name:
            return "secret-leak"
        elif "XSS" in scanner_name:
            return "xss"
        elif "SQLInjection" in scanner_name:
            return "sql-injection"
        elif "CommandInjection" in scanner_name:
            return "command-injection"
        else:
            return "security-issue"

    def _map_severity(self, severity: PenTestSeverity) -> str:
        """Map PenTestSeverity to SARIF level.

        Args:
            severity: PenTestSeverity

        Returns:
            SARIF level (error, warning, note)
        """
        if severity in [PenTestSeverity.CRITICAL, PenTestSeverity.HIGH]:
            return "error"
        elif severity == PenTestSeverity.MEDIUM:
            return "warning"
        else:
            return "note"
