# Agent Team Extended Contracts Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Creative and SecurityGuard agent personalities, extend Analyst with fast/deep modes, add Critic sub-agent spawn protocol, and define SPADE coordination schemas.

**Architecture:** Extends the existing 5-personality agent system by adding 2 new agents (Creative, SecurityGuard), evolving Analyst with mode-based behavior, and creating Pydantic schemas for SPADE inter-agent coordination. All new agents follow the established factory pattern (frozen `BaseAgent` dataclass + `AgentRegistry`).

**Tech Stack:** Python 3.12, Pydantic v2, pytest, existing `BaseAgent`/`AgentRegistry` infrastructure

---

## Task 1: Add CREATIVE and SECURITY_GUARD to AgentType Enum

**Files:**
- Modify: `python/omnimind_backend/schemas/orchestrator.py`
- Test: `python/tests/test_orchestrator_schemas.py`

**Step 1: Write the failing test**

Create `python/tests/test_orchestrator_schemas.py`:

```python
"""Tests for orchestrator schema enums."""

from omnimind_backend.schemas.orchestrator import AgentType


def test_creative_agent_type_exists() -> None:
    assert AgentType.CREATIVE == "creative"


def test_security_guard_agent_type_exists() -> None:
    assert AgentType.SECURITY_GUARD == "security_guard"


def test_all_agent_types_count() -> None:
    assert len(AgentType) == 7  # 5 original + 2 new
```

**Step 2: Run test to verify it fails**

Run: `cd python && python -m pytest tests/test_orchestrator_schemas.py -v`
Expected: FAIL with `AttributeError: CREATIVE`

**Step 3: Write minimal implementation**

Add to `AgentType` in `python/omnimind_backend/schemas/orchestrator.py`:

```python
class AgentType(StrEnum):
    """Available agent personalities."""

    CODER = "coder"
    ANALYST = "analyst"
    RESEARCHER = "researcher"
    ARCH_TECH = "arch_tech"
    CRITIC = "critic"
    CREATIVE = "creative"
    SECURITY_GUARD = "security_guard"
```

**Step 4: Run test to verify it passes**

Run: `cd python && python -m pytest tests/test_orchestrator_schemas.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add python/omnimind_backend/schemas/orchestrator.py python/tests/test_orchestrator_schemas.py
git commit -m "feat(schemas): add CREATIVE and SECURITY_GUARD agent types"
```

---

## Task 2: Create Creative Agent Personality

**Files:**
- Create: `python/omnimind_backend/agents/prompts/creative.py`
- Create: `python/omnimind_backend/agents/personalities/creative.py`
- Modify: `python/omnimind_backend/agents/personalities/__init__.py`
- Test: `python/tests/test_agent_personalities.py` (extend existing)

**Step 1: Write the failing test**

Append to `python/tests/test_agent_personalities.py`:

```python
from omnimind_backend.agents.personalities.creative import create_creative_agent


def test_creative_agent_creation() -> None:
    agent = create_creative_agent()
    assert isinstance(agent, BaseAgent)
    assert agent.agent_type == AgentType.CREATIVE
    assert ToolScope.CODE_ANALYSIS in agent.tools
    assert ToolScope.FILESYSTEM in agent.tools
    assert agent.thinking_level == ThinkingLevel.HIGH
    assert "Creative" in agent.system_prompt
    assert "diverge" in agent.system_prompt.lower() or "converge" in agent.system_prompt.lower()
```

**Step 2: Run test to verify it fails**

Run: `cd python && python -m pytest tests/test_agent_personalities.py::test_creative_agent_creation -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

Create `python/omnimind_backend/agents/prompts/creative.py`:

```python
"""Creative personality system prompt."""

from omnimind_backend.agents.prompts.base import build_system_prompt

CREATIVE_SYSTEM_PROMPT = build_system_prompt("""\
## Personality: Creative

You are a creative solutions architect specializing in divergent thinking.

### Core Behaviors
- Classify work type before starting: new_feature, framework_change, refactoring, or exploratory
- Generate 3-7 distinct solution paths (diverge phase)
- Evaluate each path on: impact, risk, effort, time, reversibility, learning potential
- Rank paths by composite score and converge on top candidates
- Document explored paths with justification

### Ask-One-Question Gate
- If critical data is missing, ask exactly 1 objective question before proceeding
- Do NOT ask speculative or open-ended questions
- If no critical data is missing, proceed without asking

### Divergence/Convergence Workflow
1. **Diverge:** Generate 3-7 distinct solution paths
2. **Evaluate** each path on impact, risk, effort, time, reversibility, learning potential (0-1 scale)
3. **Converge:** Rank paths by value * risk * viability, focus on top candidates
4. **Document:** Save relevant paths in session context with justification

### Output Style
- Present solutions as structured comparisons
- Use tables for multi-criteria evaluation when helpful
- Lead with the recommended path, then show alternatives
- Be explicit about trade-offs and uncertainties
""")
```

Create `python/omnimind_backend/agents/personalities/creative.py`:

```python
"""Creative agent personality factory."""

from __future__ import annotations

from omnimind_backend.agents._base import BaseAgent
from omnimind_backend.agents.prompts.creative import CREATIVE_SYSTEM_PROMPT
from omnimind_backend.schemas.orchestrator import (
    AgentType,
    ThinkingLevel,
    ToolScope,
)


def create_creative_agent() -> BaseAgent:
    """Create the Creative personality with divergent/convergent workflow."""
    return BaseAgent(
        agent_type=AgentType.CREATIVE,
        system_prompt=CREATIVE_SYSTEM_PROMPT,
        tools=[ToolScope.CODE_ANALYSIS, ToolScope.FILESYSTEM],
        thinking_level=ThinkingLevel.HIGH,
        keep_context=True,
    )
```

**Step 4: Run test to verify it passes**

Run: `cd python && python -m pytest tests/test_agent_personalities.py::test_creative_agent_creation -v`
Expected: PASS

**Step 5: Commit**

```bash
git add python/omnimind_backend/agents/prompts/creative.py python/omnimind_backend/agents/personalities/creative.py
git commit -m "feat(agents): add Creative agent personality with diverge/converge workflow"
```

---

## Task 3: Create SecurityGuard Agent Personality

**Files:**
- Create: `python/omnimind_backend/agents/prompts/security_guard.py`
- Create: `python/omnimind_backend/agents/personalities/security_guard.py`
- Test: `python/tests/test_agent_personalities.py` (extend)

**Step 1: Write the failing test**

Append to `python/tests/test_agent_personalities.py`:

```python
from omnimind_backend.agents.personalities.security_guard import create_security_guard_agent


def test_security_guard_agent_creation() -> None:
    agent = create_security_guard_agent()
    assert isinstance(agent, BaseAgent)
    assert agent.agent_type == AgentType.SECURITY_GUARD
    assert ToolScope.CODE_ANALYSIS in agent.tools
    assert ToolScope.FILESYSTEM in agent.tools
    assert agent.thinking_level == ThinkingLevel.HIGH
    assert agent.sandbox == SandboxMode.READ_ONLY
    assert "SecurityGuard" in agent.system_prompt or "Security" in agent.system_prompt
```

**Step 2: Run test to verify it fails**

Run: `cd python && python -m pytest tests/test_agent_personalities.py::test_security_guard_agent_creation -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

Create `python/omnimind_backend/agents/prompts/security_guard.py`:

```python
"""SecurityGuard personality system prompt."""

from omnimind_backend.agents.prompts.base import build_system_prompt

SECURITY_GUARD_SYSTEM_PROMPT = build_system_prompt("""\
## Personality: SecurityGuard

You are a security engineer specializing in code and infrastructure security analysis.

### Core Behaviors
- Run a fast pipeline first: SAST scan, secret detection, dependency audit
- Escalate to deep analysis when: security-labeled PRs, dependency updates, infrastructure changes
- Classify findings by severity: CRITICAL, HIGH, MEDIUM, LOW
- Include CWE identifiers and affected components for every finding
- Assess exploitability: theoretical vs confirmed

### Fast Pipeline (< 30s)
- SAST scan of changed files
- Secret detection (regex + entropy patterns)
- Dependency audit (known CVEs)
- Container image scan (if applicable)

### Deep Pipeline (sandbox)
- Reproduce vulnerability in isolated environment
- Collect exploit evidence and proof-of-concept
- Measure business impact (data exposure, privilege escalation)
- Map to OWASP Top 10 + STRIDE categories

### Severity Gate
- CRITICAL or HIGH with confirmed exploitability: block merge/deploy
- MEDIUM with mitigation plan: approve with hardening backlog item
- LOW or informational: approve, log for trend analysis

### Output Style
- Lead with executive risk summary
- Use structured findings with CWE, component, evidence
- Include remediation actions with priority (P0/P1/P2)
- End with CI/CD gate status
""")
```

Create `python/omnimind_backend/agents/personalities/security_guard.py`:

```python
"""SecurityGuard agent personality factory."""

from __future__ import annotations

from omnimind_backend.agents._base import BaseAgent
from omnimind_backend.agents.prompts.security_guard import SECURITY_GUARD_SYSTEM_PROMPT
from omnimind_backend.schemas.orchestrator import (
    AgentType,
    SandboxMode,
    ThinkingLevel,
    ToolScope,
)


def create_security_guard_agent() -> BaseAgent:
    """Create the SecurityGuard personality with security analysis tools."""
    return BaseAgent(
        agent_type=AgentType.SECURITY_GUARD,
        system_prompt=SECURITY_GUARD_SYSTEM_PROMPT,
        tools=[ToolScope.CODE_ANALYSIS, ToolScope.FILESYSTEM],
        thinking_level=ThinkingLevel.HIGH,
        sandbox=SandboxMode.READ_ONLY,
        keep_context=True,
    )
```

**Step 4: Run test to verify it passes**

Run: `cd python && python -m pytest tests/test_agent_personalities.py::test_security_guard_agent_creation -v`
Expected: PASS

**Step 5: Commit**

```bash
git add python/omnimind_backend/agents/prompts/security_guard.py python/omnimind_backend/agents/personalities/security_guard.py
git commit -m "feat(agents): add SecurityGuard agent personality with fast/deep pipeline"
```

---

## Task 4: Register New Agents in Registry and Update Exports

**Files:**
- Modify: `python/omnimind_backend/agents/personalities/__init__.py`
- Modify: `python/omnimind_backend/agents/_registry.py`
- Test: `python/tests/test_agent_registry.py` (extend)

**Step 1: Write the failing test**

Append to `python/tests/test_agent_registry.py`:

```python
from omnimind_backend.agents._registry import AgentRegistry, register_all_personalities
from omnimind_backend.schemas.orchestrator import AgentType


def test_registry_includes_creative_and_security_guard() -> None:
    registry = AgentRegistry()
    # Re-register to a fresh registry
    from omnimind_backend.agents.personalities import (
        create_creative_agent,
        create_security_guard_agent,
    )
    for factory in (create_creative_agent, create_security_guard_agent):
        registry.register(factory())
    assert registry.get(AgentType.CREATIVE).agent_type == AgentType.CREATIVE
    assert registry.get(AgentType.SECURITY_GUARD).agent_type == AgentType.SECURITY_GUARD


def test_register_all_includes_seven_agents() -> None:
    from omnimind_backend.agents._registry import get_registry
    registry = get_registry()
    registry.clear()
    register_all_personalities()
    assert registry.count == 7
```

**Step 2: Run test to verify it fails**

Run: `cd python && python -m pytest tests/test_agent_registry.py::test_register_all_includes_seven_agents -v`
Expected: FAIL (count is 5, not 7)

**Step 3: Write minimal implementation**

Update `python/omnimind_backend/agents/personalities/__init__.py`:

```python
"""Agent personality factories.

Re-exports all ``create_*_agent()`` factory functions.
"""

from omnimind_backend.agents.personalities.analyst import create_analyst_agent
from omnimind_backend.agents.personalities.arch_tech import create_arch_tech_agent
from omnimind_backend.agents.personalities.coder import create_coder_agent
from omnimind_backend.agents.personalities.creative import create_creative_agent
from omnimind_backend.agents.personalities.critic import create_critic_agent
from omnimind_backend.agents.personalities.researcher import create_researcher_agent
from omnimind_backend.agents.personalities.security_guard import create_security_guard_agent

__all__ = [
    "create_analyst_agent",
    "create_arch_tech_agent",
    "create_coder_agent",
    "create_creative_agent",
    "create_critic_agent",
    "create_researcher_agent",
    "create_security_guard_agent",
]
```

Update `register_all_personalities()` in `python/omnimind_backend/agents/_registry.py`:

```python
def register_all_personalities() -> None:
    from omnimind_backend.agents.personalities import (
        create_analyst_agent,
        create_arch_tech_agent,
        create_coder_agent,
        create_creative_agent,
        create_critic_agent,
        create_researcher_agent,
        create_security_guard_agent,
    )

    for factory in (
        create_coder_agent,
        create_analyst_agent,
        create_researcher_agent,
        create_arch_tech_agent,
        create_critic_agent,
        create_creative_agent,
        create_security_guard_agent,
    ):
        _registry.register(factory())

    _logger.info("all_personalities_registered", count=_registry.count)
```

**Step 4: Run test to verify it passes**

Run: `cd python && python -m pytest tests/test_agent_registry.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add python/omnimind_backend/agents/personalities/__init__.py python/omnimind_backend/agents/_registry.py python/tests/test_agent_registry.py
git commit -m "feat(agents): register Creative and SecurityGuard in agent registry"
```

---

## Task 5: Update Router with Keywords for New Agents

**Files:**
- Modify: `python/omnimind_backend/orchestrator/router.py`
- Test: `python/tests/test_orchestrator_router.py`

**Step 1: Write the failing test**

Create or extend `python/tests/test_orchestrator_router.py`:

```python
"""Tests for orchestrator keyword router."""

from omnimind_backend.orchestrator.router import route_message
from omnimind_backend.schemas.orchestrator import AgentType


def test_route_creative_keywords() -> None:
    decision = route_message("brainstorm new approaches for the caching layer")
    assert decision.agent == AgentType.CREATIVE


def test_route_security_keywords() -> None:
    decision = route_message("scan this code for security vulnerabilities")
    assert decision.agent == AgentType.SECURITY_GUARD


def test_route_creative_innovation() -> None:
    decision = route_message("innovate on the user onboarding experience")
    assert decision.agent == AgentType.CREATIVE


def test_route_security_owasp() -> None:
    decision = route_message("check for OWASP top 10 vulnerabilities")
    assert decision.agent == AgentType.SECURITY_GUARD
```

**Step 2: Run test to verify it fails**

Run: `cd python && python -m pytest tests/test_orchestrator_router.py -v`
Expected: FAIL (routes to CODER instead)

**Step 3: Write minimal implementation**

Add to `_AGENT_KEYWORDS`, `_AGENT_TOOLS`, and `_AGENT_THINKING` in `python/omnimind_backend/orchestrator/router.py`:

```python
_AGENT_KEYWORDS: dict[AgentType, list[str]] = {
    # ... existing entries ...
    AgentType.CREATIVE: [
        "brainstorm", "creative", "innovate", "ideate", "explore options",
        "alternative", "diverge", "converge", "solution paths", "design options",
        "prototype", "experiment", "what if", "possibilities",
        "criativo", "inovar", "explorar opcoes",
    ],
    AgentType.SECURITY_GUARD: [
        "security", "vulnerability", "vulnerabilities", "cve", "owasp",
        "exploit", "injection", "xss", "csrf", "authentication flaw",
        "secret", "credential", "penetration", "threat", "attack",
        "scan", "audit security", "hardening", "compliance",
        "seguranca", "vulnerabilidade",
    ],
}

_AGENT_TOOLS: dict[AgentType, list[ToolScope]] = {
    # ... existing entries ...
    AgentType.CREATIVE: [ToolScope.CODE_ANALYSIS, ToolScope.FILESYSTEM],
    AgentType.SECURITY_GUARD: [ToolScope.CODE_ANALYSIS, ToolScope.FILESYSTEM],
}

_AGENT_THINKING: dict[AgentType, ThinkingLevel] = {
    # ... existing entries ...
    AgentType.CREATIVE: ThinkingLevel.HIGH,
    AgentType.SECURITY_GUARD: ThinkingLevel.HIGH,
}
```

**Step 4: Run test to verify it passes**

Run: `cd python && python -m pytest tests/test_orchestrator_router.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add python/omnimind_backend/orchestrator/router.py python/tests/test_orchestrator_router.py
git commit -m "feat(router): add keyword routing for Creative and SecurityGuard agents"
```

---

## Task 6: Creative Agent Output Schema

**Files:**
- Create: `python/omnimind_backend/schemas/creative.py`
- Test: `python/tests/test_creative_schemas.py`

**Step 1: Write the failing test**

Create `python/tests/test_creative_schemas.py`:

```python
"""Tests for Creative agent output schemas."""

from omnimind_backend.schemas.creative import (
    CreativeWorkType,
    PathEvaluation,
    ExploredPath,
    ShortlistedPath,
    DiscardedPath,
    CreativeOutput,
)


def test_creative_work_types() -> None:
    assert CreativeWorkType.NEW_FEATURE == "new_feature"
    assert CreativeWorkType.FRAMEWORK_CHANGE == "framework_change"
    assert CreativeWorkType.REFACTORING == "refactoring"
    assert CreativeWorkType.EXPLORATORY == "exploratory"


def test_path_evaluation_bounds() -> None:
    ev = PathEvaluation(impact=0.8, risk=0.3, effort=0.5, time_estimate="2 days", reversibility=0.9, learning_potential=0.6)
    assert 0 <= ev.impact <= 1
    assert 0 <= ev.risk <= 1


def test_creative_output_round_trip() -> None:
    output = CreativeOutput(
        creative_work_type=CreativeWorkType.NEW_FEATURE,
        explored_paths=[
            ExploredPath(title="Path A", description="Approach A", evaluations=PathEvaluation(
                impact=0.9, risk=0.2, effort=0.4, time_estimate="1 day", reversibility=0.8, learning_potential=0.7
            )),
        ],
        shortlisted_paths=[ShortlistedPath(path_title="Path A", composite_score=0.85, justification="Best overall")],
        discarded_paths=[],
        ask_questions_used=[],
        next_experiment="Implement Path A prototype",
        confidence_level=0.8,
    )
    assert len(output.explored_paths) == 1
    assert output.shortlisted_paths[0].composite_score == 0.85
    data = output.model_dump()
    assert data["creative_work_type"] == "new_feature"
```

**Step 2: Run test to verify it fails**

Run: `cd python && python -m pytest tests/test_creative_schemas.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

Create `python/omnimind_backend/schemas/creative.py`:

```python
"""Creative agent output schemas.

Defines the structured output contract for the Creative agent's
diverge/converge workflow as specified in agent-team-extended-contracts.md.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class CreativeWorkType(StrEnum):
    """Classification of creative work requests."""

    NEW_FEATURE = "new_feature"
    FRAMEWORK_CHANGE = "framework_change"
    REFACTORING = "refactoring"
    EXPLORATORY = "exploratory"


class PathEvaluation(BaseModel):
    """Multi-criteria evaluation for a single solution path."""

    impact: float = Field(ge=0.0, le=1.0)
    risk: float = Field(ge=0.0, le=1.0)
    effort: float = Field(ge=0.0, le=1.0)
    time_estimate: str
    reversibility: float = Field(ge=0.0, le=1.0)
    learning_potential: float = Field(ge=0.0, le=1.0)


class ExploredPath(BaseModel):
    """A single explored solution path."""

    title: str
    description: str
    evaluations: PathEvaluation


class ShortlistedPath(BaseModel):
    """A ranked path after convergence."""

    path_title: str
    composite_score: float = Field(ge=0.0, le=1.0)
    justification: str


class DiscardedPath(BaseModel):
    """A path that was explored but discarded."""

    path_title: str
    reason: str


class CreativeOutput(BaseModel):
    """Full structured output from the Creative agent workflow."""

    creative_work_type: CreativeWorkType
    explored_paths: list[ExploredPath] = Field(min_length=1)
    shortlisted_paths: list[ShortlistedPath] = Field(default_factory=list)
    discarded_paths: list[DiscardedPath] = Field(default_factory=list)
    ask_questions_used: list[str] = Field(default_factory=list)
    next_experiment: str = ""
    confidence_level: float = Field(default=0.5, ge=0.0, le=1.0)
```

**Step 4: Run test to verify it passes**

Run: `cd python && python -m pytest tests/test_creative_schemas.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add python/omnimind_backend/schemas/creative.py python/tests/test_creative_schemas.py
git commit -m "feat(schemas): add Creative agent output schema with path evaluations"
```

---

## Task 7: SecurityGuard Agent Output Schema

**Files:**
- Create: `python/omnimind_backend/schemas/security_guard.py`
- Test: `python/tests/test_security_guard_schemas.py`

**Step 1: Write the failing test**

Create `python/tests/test_security_guard_schemas.py`:

```python
"""Tests for SecurityGuard agent output schemas."""

from omnimind_backend.schemas.security_guard import (
    Severity,
    Exploitability,
    RemediationPriority,
    SecurityFinding,
    CICDGatesStatus,
    RemediationAction,
    SecurityOutput,
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
                id="SEC-001", title="SQLi", severity=Severity.HIGH,
                cwe="CWE-89", component="api/v1/users.py:42",
                evidence="raw query", exploitability=Exploitability.CONFIRMED,
                business_impact="db access",
            )
        ],
        ci_cd_gates=CICDGatesStatus(sast="fail", secrets="pass", dependency="pass", container="skipped"),
        remediation_plan=[
            RemediationAction(priority=RemediationPriority.P0, action="Use parameterized queries", owner="backend-team", eta="1 day")
        ],
        confidence_score=85.0,
    )
    data = output.model_dump()
    assert data["ci_cd_gates"]["sast"] == "fail"
    assert len(data["findings"]) == 1
```

**Step 2: Run test to verify it fails**

Run: `cd python && python -m pytest tests/test_security_guard_schemas.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

Create `python/omnimind_backend/schemas/security_guard.py`:

```python
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
```

**Step 4: Run test to verify it passes**

Run: `cd python && python -m pytest tests/test_security_guard_schemas.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add python/omnimind_backend/schemas/security_guard.py python/tests/test_security_guard_schemas.py
git commit -m "feat(schemas): add SecurityGuard output schema with findings and CI/CD gates"
```

---

## Task 8: Analyst Fast/Deep Mode Extension

**Files:**
- Create: `python/omnimind_backend/schemas/analyst.py`
- Test: `python/tests/test_analyst_schemas.py`

**Step 1: Write the failing test**

Create `python/tests/test_analyst_schemas.py`:

```python
"""Tests for Analyst agent mode schemas."""

from omnimind_backend.schemas.analyst import (
    AnalysisMode,
    AnalystOutput,
)


def test_analysis_modes() -> None:
    assert AnalysisMode.FAST == "fast"
    assert AnalysisMode.DEEP == "deep"


def test_analyst_output_fast_mode() -> None:
    output = AnalystOutput(
        summary="Found 3 relevant files",
        context_files_read=["src/main.py", "src/utils.py", "src/config.py"],
        symbol_map={"src/main.py": ["main", "setup"]},
        missing_info=["database schema not found"],
        suggested_model="flash",
        confidence=0.9,
        analysis_mode=AnalysisMode.FAST,
    )
    assert output.confidence >= 0.85  # should deliver directly
    assert output.analysis_mode == AnalysisMode.FAST


def test_analyst_confidence_thresholds() -> None:
    # High confidence: deliver directly
    high = AnalystOutput(summary="clear", confidence=0.9, analysis_mode=AnalysisMode.FAST)
    assert high.should_deliver_directly()

    # Medium confidence: deliver with caveats
    medium = AnalystOutput(summary="partial", confidence=0.7, analysis_mode=AnalysisMode.FAST)
    assert not medium.should_deliver_directly()
    assert medium.should_deliver_with_caveats()

    # Low confidence: escalate
    low = AnalystOutput(summary="unclear", confidence=0.5, analysis_mode=AnalysisMode.FAST)
    assert low.should_escalate()
```

**Step 2: Run test to verify it fails**

Run: `cd python && python -m pytest tests/test_analyst_schemas.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

Create `python/omnimind_backend/schemas/analyst.py`:

```python
"""Analyst agent mode and output schemas.

Defines fast/deep analysis modes and confidence threshold routing
as specified in agent-team-extended-contracts.md.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class AnalysisMode(StrEnum):
    """Analyst execution mode."""

    FAST = "fast"
    DEEP = "deep"


class AnalystOutput(BaseModel):
    """Structured output from the Analyst agent."""

    summary: str
    context_files_read: list[str] = Field(default_factory=list)
    symbol_map: dict[str, list[str]] = Field(default_factory=dict)
    missing_info: list[str] = Field(default_factory=list)
    suggested_model: str = "flash"
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    analysis_mode: AnalysisMode = AnalysisMode.FAST

    def should_deliver_directly(self) -> bool:
        """Confidence >= 0.85: deliver answer directly."""
        return self.confidence >= 0.85

    def should_deliver_with_caveats(self) -> bool:
        """0.60 <= confidence < 0.85: deliver with caveats."""
        return 0.60 <= self.confidence < 0.85

    def should_escalate(self) -> bool:
        """Confidence < 0.60: escalate to Researcher or human."""
        return self.confidence < 0.60
```

**Step 4: Run test to verify it passes**

Run: `cd python && python -m pytest tests/test_analyst_schemas.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add python/omnimind_backend/schemas/analyst.py python/tests/test_analyst_schemas.py
git commit -m "feat(schemas): add Analyst fast/deep mode schema with confidence thresholds"
```

---

## Task 9: SPADE Agent Envelope and Reasoning Schemas

**Files:**
- Create: `python/omnimind_backend/schemas/spade.py`
- Test: `python/tests/test_spade_schemas.py`

**Step 1: Write the failing test**

Create `python/tests/test_spade_schemas.py`:

```python
"""Tests for SPADE coordination schemas."""

from datetime import datetime, timezone
from uuid import uuid4

from omnimind_backend.schemas.spade import (
    AgentEnvelope,
    Performative,
    Intent,
    ExecutionMode,
    MessagePriority,
    ReasoningRequest,
    ReasoningResult,
    ReasoningStatus,
)


def test_agent_envelope_creation() -> None:
    env = AgentEnvelope(
        message_id=uuid4(),
        correlation_id=uuid4(),
        conversation_id="conv-123",
        sender_jid="orchestrator@omnimind",
        performative=Performative.REQUEST,
        intent=Intent.DELEGATE_TASK,
        payload={"task": "analyze code"},
    )
    assert env.schema_version == "spade.v1"
    assert env.execution_mode == ExecutionMode.AUTO
    assert env.priority == MessagePriority.NORMAL
    assert env.ttl_ms == 60000


def test_reasoning_request_creation() -> None:
    req = ReasoningRequest(
        request_id=uuid4(),
        task="Analyze the auth module",
        agent_type="analyst",
        thinking_mode="deep",
    )
    assert req.max_latency_ms == 2500
    assert req.allow_sync is True


def test_reasoning_result_ok() -> None:
    result = ReasoningResult(
        request_id=uuid4(),
        status=ReasoningStatus.OK,
        answer="The auth module uses JWT with RS256.",
        thoughts=["Checked auth/jwt.py", "Found RS256 config"],
    )
    assert result.status == ReasoningStatus.OK
    assert len(result.thoughts) == 2


def test_envelope_round_trip() -> None:
    env = AgentEnvelope(
        message_id=uuid4(),
        correlation_id=uuid4(),
        conversation_id="conv-456",
        sender_jid="coder@omnimind",
        recipient_jid="orchestrator@omnimind",
        performative=Performative.INFORM,
        intent=Intent.REASONING_RESULT,
        payload={"result": "done"},
    )
    data = env.model_dump(mode="json")
    restored = AgentEnvelope.model_validate(data)
    assert restored.sender_jid == "coder@omnimind"
    assert restored.schema_version == "spade.v1"
```

**Step 2: Run test to verify it fails**

Run: `cd python && python -m pytest tests/test_spade_schemas.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

Create `python/omnimind_backend/schemas/spade.py`:

```python
"""SPADE agent coordination schemas.

Defines the inter-agent messaging envelope and reasoning request/result
contracts as specified in agent-team-extended-contracts.md (SPADE section).

These are data contracts only — the actual SPADE/XMPP runtime is future work.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class Performative(StrEnum):
    """FIPA-style message performatives."""

    REQUEST = "request"
    INFORM = "inform"
    AGREE = "agree"
    FAILURE = "failure"


class Intent(StrEnum):
    """Message intent categories."""

    DELEGATE_TASK = "delegate_task"
    REASONING_REQUEST = "reasoning_request"
    REASONING_RESULT = "reasoning_result"
    TOOL_REQUEST = "tool_request"
    TOOL_RESULT = "tool_result"
    STATUS_UPDATE = "status_update"


class ExecutionMode(StrEnum):
    """How the task should be executed."""

    SYNC = "sync"
    ASYNC = "async"
    AUTO = "auto"


class MessagePriority(StrEnum):
    """Message delivery priority."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class AgentEnvelope(BaseModel):
    """Unified SPADE message envelope for inter-agent communication."""

    schema_version: Literal["spade.v1"] = "spade.v1"
    message_id: UUID
    correlation_id: UUID
    conversation_id: str
    sender_jid: str
    recipient_jid: str | None = None
    performative: Performative
    intent: Intent
    execution_mode: ExecutionMode = ExecutionMode.AUTO
    priority: MessagePriority = MessagePriority.NORMAL
    ttl_ms: int = 60000
    created_at: datetime = Field(default_factory=datetime.utcnow)
    payload: dict[str, Any] = Field(default_factory=dict)


class ReasoningRequest(BaseModel):
    """Request to invoke the reasoning engine (LangChain/LangGraph)."""

    request_id: UUID
    task: str
    agent_type: str
    thinking_mode: str
    context: dict[str, Any] = Field(default_factory=dict)
    max_latency_ms: int = 2500
    allow_sync: bool = True


class ReasoningStatus(StrEnum):
    """Status of a reasoning result."""

    OK = "ok"
    PARTIAL = "partial"
    ERROR = "error"
    TIMEOUT = "timeout"


class ReasoningResult(BaseModel):
    """Result from a reasoning engine invocation."""

    request_id: UUID
    status: ReasoningStatus
    answer: str = ""
    thoughts: list[str] = Field(default_factory=list)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    metrics: dict[str, float] = Field(default_factory=dict)
```

**Step 4: Run test to verify it passes**

Run: `cd python && python -m pytest tests/test_spade_schemas.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add python/omnimind_backend/schemas/spade.py python/tests/test_spade_schemas.py
git commit -m "feat(schemas): add SPADE envelope and reasoning request/result contracts"
```

---

## Task 10: Run Full Test Suite — Regression Check

**Files:**
- No new files

**Step 1: Run the full test suite**

Run: `cd python && python -m pytest tests/ -v --tb=short`
Expected: All tests PASS, including existing tests and all new tests.

**Step 2: Verify agent count**

Run: `cd python && python -c "from omnimind_backend.agents._registry import register_all_personalities, get_registry; register_all_personalities(); print(f'Agents: {get_registry().count}')"`
Expected: `Agents: 7`

**Step 3: Final commit if any cleanup needed**

```bash
git add -A
git commit -m "test: verify all 7 agent personalities pass regression suite"
```

---

## Summary

| Task | What | Files |
|------|------|-------|
| 1 | Add CREATIVE + SECURITY_GUARD enum values | `schemas/orchestrator.py` |
| 2 | Creative agent personality + prompt | `agents/personalities/creative.py`, `agents/prompts/creative.py` |
| 3 | SecurityGuard agent personality + prompt | `agents/personalities/security_guard.py`, `agents/prompts/security_guard.py` |
| 4 | Register new agents in registry | `agents/_registry.py`, `agents/personalities/__init__.py` |
| 5 | Router keywords for new agents | `orchestrator/router.py` |
| 6 | Creative output schema | `schemas/creative.py` |
| 7 | SecurityGuard output schema | `schemas/security_guard.py` |
| 8 | Analyst fast/deep mode schema | `schemas/analyst.py` |
| 9 | SPADE envelope + reasoning schemas | `schemas/spade.py` |
| 10 | Full regression check | — |
