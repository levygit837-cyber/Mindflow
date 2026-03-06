"""SecurityGuard agent output schemas.

Defines the structured output contract for security analysis pipelines
as specified in agent-team-extended-contracts.md.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class Severity(StrEnum):
    """Security finding severity levels."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Exploitability(StrEnum):
    """Whether a vulnerability is theoretical or confirmed exploitable."""

    THEORETICAL = "theoretical"
    CONFIRMED = "confirmed"


class RemediationPriority(StrEnum):
    """Remediation urgency classification."""

    P0 = "P0"
    P1 = "P1"
    P2 = "P2"


class SecurityFinding(BaseModel):
    """A single security finding with evidence."""

    id: str
    title: str
    severity: Severity
    cwe: str
    component: str
    evidence: str
    exploitability: Exploitability
    business_impact: str


class CICDGatesStatus(BaseModel):
    """Status of CI/CD security gates."""

    sast: str = "skipped"
    secrets: str = "skipped"
    dependency: str = "skipped"
    container: str = "skipped"


class RemediationAction(BaseModel):
    """A single remediation action with ownership."""

    priority: RemediationPriority
    action: str
    owner: str
    eta: str


class SecurityOutput(BaseModel):
    """Full structured output from the SecurityGuard agent."""

    summary: str
    attack_surface: list[str] = Field(default_factory=list)
    findings: list[SecurityFinding] = Field(default_factory=list)
    ci_cd_gates: CICDGatesStatus = Field(default_factory=CICDGatesStatus)
    remediation_plan: list[RemediationAction] = Field(default_factory=list)
    confidence_score: float = Field(default=0.0, ge=0.0, le=100.0)
