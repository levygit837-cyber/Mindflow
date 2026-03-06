"""Tests for SecurityGuard agent output schemas."""

from mindflow_backend.schemas.security_guard import (
    CICDGatesStatus,
    Exploitability,
    RemediationAction,
    RemediationPriority,
    SecurityFinding,
    SecurityOutput,
    Severity,
)


def test_severity_levels() -> None:
    assert Severity.CRITICAL == "CRITICAL"
    assert Severity.HIGH == "HIGH"
    assert Severity.MEDIUM == "MEDIUM"
    assert Severity.LOW == "LOW"


def test_finding_creation() -> None:
    finding = SecurityFinding(
        id="SEC-001",
        title="SQL Injection in user search",
        severity=Severity.HIGH,
        cwe="CWE-89",
        component="api/v1/users.py:42",
        evidence="Unsanitized user input in SQL query",
        exploitability=Exploitability.CONFIRMED,
        business_impact="Full database read access",
    )
    assert finding.severity == Severity.HIGH
    assert finding.exploitability == Exploitability.CONFIRMED


def test_security_output_round_trip() -> None:
    output = SecurityOutput(
        summary="1 HIGH finding detected",
        attack_surface=["api/v1/users.py"],
        findings=[
            SecurityFinding(
                id="SEC-001",
                title="SQLi",
                severity=Severity.HIGH,
                cwe="CWE-89",
                component="api/v1/users.py:42",
                evidence="raw query",
                exploitability=Exploitability.CONFIRMED,
                business_impact="db access",
            )
        ],
        ci_cd_gates=CICDGatesStatus(
            sast="fail", secrets="pass", dependency="pass", container="skipped"
        ),
        remediation_plan=[
            RemediationAction(
                priority=RemediationPriority.P0,
                action="Use parameterized queries",
                owner="backend-team",
                eta="1 day",
            )
        ],
        confidence_score=85.0,
    )
    data = output.model_dump()
    assert data["ci_cd_gates"]["sast"] == "fail"
    assert len(data["findings"]) == 1
