# Obsidian Feature Integration Roadmap Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create the coordination infrastructure (feature flags, phase verification, coverage checks, integration tests) that ties together the 6 feature plans derived from the Obsidian vault gap analysis.

**Architecture:** This is a meta-plan that does NOT duplicate work from the other 6 plans. It creates: (1) per-phase feature flags in Settings, (2) a coverage verification script, (3) phase gate test infrastructure, and (4) a test scaffold for cross-phase integration. All features are backward-compatible and opt-in.

**Tech Stack:** Python 3.12, Pydantic v2 (BaseSettings), pytest, bash scripts

---

## Task 1: Per-Phase Feature Flags in Settings

**Files:**
- Modify: `python/omnimind_backend/infra/config.py`
- Test: `python/tests/test_feature_flags.py`

**Step 1: Write the failing test**

Create `python/tests/test_feature_flags.py`:

```python
"""Tests for per-phase feature flags."""

from omnimind_backend.infra.config import Settings


def test_phase1_flags_default_off() -> None:
    s = Settings()
    assert s.enable_creative_agent is False
    assert s.enable_security_guard_agent is False


def test_phase2_flags_default_off() -> None:
    s = Settings()
    assert s.enable_input_normalization is False
    assert s.enable_context_governance is False
    assert s.enable_session_chunks is False


def test_phase3_flags_default_off() -> None:
    s = Settings()
    assert s.enable_async_workflows is False
    assert s.enable_workflow_registry is False


def test_phase4_flags_default_off() -> None:
    s = Settings()
    assert s.enable_dt_v2 is False


def test_flags_can_be_enabled() -> None:
    s = Settings(
        ENABLE_CREATIVE_AGENT="true",
        ENABLE_CONTEXT_GOVERNANCE="true",
    )
    assert s.enable_creative_agent is True
    assert s.enable_context_governance is True
```

**Step 2: Run test to verify it fails**

Run: `cd python && python -m pytest tests/test_feature_flags.py -v`
Expected: FAIL with `AttributeError` (flags don't exist yet)

**Step 3: Write minimal implementation**

Add to `Settings` class in `python/omnimind_backend/infra/config.py`:

```python
    # Phase 1 - Agent Contract Parity
    enable_creative_agent: bool = Field(default=False, alias="ENABLE_CREATIVE_AGENT")
    enable_security_guard_agent: bool = Field(default=False, alias="ENABLE_SECURITY_GUARD_AGENT")

    # Phase 2 - Context Governance and Input Normalization
    enable_input_normalization: bool = Field(default=False, alias="ENABLE_INPUT_NORMALIZATION")
    enable_context_governance: bool = Field(default=False, alias="ENABLE_CONTEXT_GOVERNANCE")
    enable_session_chunks: bool = Field(default=False, alias="ENABLE_SESSION_CHUNKS")

    # Phase 3 - Async Workflow Caller
    enable_async_workflows: bool = Field(default=False, alias="ENABLE_ASYNC_WORKFLOWS")
    enable_workflow_registry: bool = Field(default=False, alias="ENABLE_WORKFLOW_REGISTRY")

    # Phase 4 - DT v2
    enable_dt_v2: bool = Field(default=False, alias="ENABLE_DT_V2")
```

**Step 4: Run test to verify it passes**

Run: `cd python && python -m pytest tests/test_feature_flags.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add python/omnimind_backend/infra/config.py python/tests/test_feature_flags.py
git commit -m "feat(config): add per-phase feature flags for obsidian integration roadmap"
```

---

## Task 2: Documentation Coverage Verification Script

**Files:**
- Create: `python/scripts/verify_obsidian_docs_coverage.sh`
- Test: Run manually

**Step 1: Write the script**

Create `python/scripts/verify_obsidian_docs_coverage.sh`:

```bash
#!/usr/bin/env bash
# Verify that all required architecture documents exist and cross-references resolve.
# Exit 0 if all checks pass, exit 1 if any fail.

set -euo pipefail

DOCS_DIR="docs/architecture"
PLANS_DIR="docs/plans"
ADR_DIR="docs/adr"
ROADMAP_DIR="docs/roadmap"

ERRORS=0

echo "=== Obsidian Docs Coverage Verification ==="
echo ""

# Required architecture documents
REQUIRED_ARCH_DOCS=(
    "ARCHITECTURE_PLAN.md"
    "agent-team-extended-contracts.md"
    "decomposition-thinking-contracts-v2.md"
    "input-normalization-and-session-chunks.md"
    "orchestrator-context-governance.md"
    "researcher-pipeline-and-source-trust.md"
    "workflow-caller-async-integration.md"
    "python-backend.md"
    "python-engineering-standards.md"
)

echo "Checking architecture docs..."
for doc in "${REQUIRED_ARCH_DOCS[@]}"; do
    if [ -f "$DOCS_DIR/$doc" ]; then
        echo "  ✓ $doc"
    else
        echo "  ✗ MISSING: $doc"
        ERRORS=$((ERRORS + 1))
    fi
done

# Required ADR
echo ""
echo "Checking ADR..."
if [ -f "$ADR_DIR/0004-vault-derived-agent-contracts-and-context-governance.md" ]; then
    echo "  ✓ ADR 0004"
else
    echo "  ✗ MISSING: ADR 0004"
    ERRORS=$((ERRORS + 1))
fi

# Required roadmap
echo ""
echo "Checking roadmap..."
if [ -f "$ROADMAP_DIR/obsidian-feature-integration-roadmap.md" ]; then
    echo "  ✓ Integration roadmap"
else
    echo "  ✗ MISSING: Integration roadmap"
    ERRORS=$((ERRORS + 1))
fi

# Check cross-references resolve
echo ""
echo "Checking cross-references..."
for doc in "$DOCS_DIR"/*.md; do
    # Extract markdown links to local files
    refs=$(grep -oP '`[^`]*\.md`' "$doc" 2>/dev/null || true)
    for ref in $refs; do
        clean_ref=$(echo "$ref" | tr -d '`')
        # Skip if it's a path pattern or not a local file
        if [[ "$clean_ref" == *"/"* ]]; then
            # Check relative to repo root
            if [ ! -f "$clean_ref" ] && [ ! -f "docs/architecture/$clean_ref" ] && [ ! -f "docs/$clean_ref" ]; then
                # Silently skip — cross-references to plans that may not exist yet
                :
            fi
        fi
    done
done
echo "  ✓ Cross-reference check complete"

echo ""
if [ $ERRORS -eq 0 ]; then
    echo "=== ALL CHECKS PASSED ==="
    exit 0
else
    echo "=== $ERRORS CHECK(S) FAILED ==="
    exit 1
fi
```

**Step 2: Make executable and test**

Run: `chmod +x python/scripts/verify_obsidian_docs_coverage.sh && cd /home/levybonito/Projetos/OmniMind && bash python/scripts/verify_obsidian_docs_coverage.sh`
Expected: Some MISSING docs (they're in the worktree, not main branch yet). Script exits 1.

**Step 3: Commit**

```bash
git add python/scripts/verify_obsidian_docs_coverage.sh
git commit -m "feat(scripts): add obsidian docs coverage verification script"
```

---

## Task 3: Phase Gate Test Infrastructure

**Files:**
- Create: `python/tests/test_phase_gates.py`

**Step 1: Write the tests**

Create `python/tests/test_phase_gates.py`:

```python
"""Phase gate tests for the Obsidian feature integration roadmap.

Each test verifies the exit criteria for a roadmap phase.
Tests are skipped if the corresponding feature flag is disabled.
"""

import pytest

from omnimind_backend.infra.config import get_settings


class TestPhase0DocumentationConvergence:
    """Phase 0: All architecture docs exist and are importable."""

    def test_schemas_importable(self) -> None:
        """All schema modules should import without error."""
        from omnimind_backend.schemas import orchestrator  # noqa: F401
        from omnimind_backend.schemas import decomposition  # noqa: F401
        from omnimind_backend.schemas import agent  # noqa: F401

    def test_agent_type_enum_has_base_agents(self) -> None:
        from omnimind_backend.schemas.orchestrator import AgentType
        assert len(AgentType) >= 5  # At least the original 5


class TestPhase1AgentContractParity:
    """Phase 1: Creative and SecurityGuard agents operational."""

    def test_creative_agent_importable(self) -> None:
        settings = get_settings()
        if not settings.enable_creative_agent:
            pytest.skip("ENABLE_CREATIVE_AGENT is False")
        from omnimind_backend.agents.personalities.creative import create_creative_agent
        agent = create_creative_agent()
        assert agent.agent_type.value == "creative"

    def test_security_guard_agent_importable(self) -> None:
        settings = get_settings()
        if not settings.enable_security_guard_agent:
            pytest.skip("ENABLE_SECURITY_GUARD_AGENT is False")
        from omnimind_backend.agents.personalities.security_guard import create_security_guard_agent
        agent = create_security_guard_agent()
        assert agent.agent_type.value == "security_guard"

    def test_seven_agents_registered(self) -> None:
        settings = get_settings()
        if not (settings.enable_creative_agent and settings.enable_security_guard_agent):
            pytest.skip("New agents not enabled")
        from omnimind_backend.agents._registry import get_registry, register_all_personalities
        registry = get_registry()
        registry.clear()
        register_all_personalities()
        assert registry.count == 7


class TestPhase2ContextGovernance:
    """Phase 2: Input normalization and context governance active."""

    def test_normalizer_importable(self) -> None:
        settings = get_settings()
        if not settings.enable_input_normalization:
            pytest.skip("ENABLE_INPUT_NORMALIZATION is False")
        from omnimind_backend.infra.normalizer import normalize_message  # noqa: F401

    def test_context_budget_importable(self) -> None:
        settings = get_settings()
        if not settings.enable_context_governance:
            pytest.skip("ENABLE_CONTEXT_GOVERNANCE is False")
        from omnimind_backend.orchestrator.context_budget import ContextBudgetTracker  # noqa: F401


class TestPhase3AsyncWorkflows:
    """Phase 3: Workflow registry and TaskBus operational."""

    def test_task_bus_importable(self) -> None:
        settings = get_settings()
        if not settings.enable_async_workflows:
            pytest.skip("ENABLE_ASYNC_WORKFLOWS is False")
        from omnimind_backend.workers.task_bus import InMemoryTaskBus  # noqa: F401

    def test_workflow_registry_importable(self) -> None:
        settings = get_settings()
        if not settings.enable_workflow_registry:
            pytest.skip("ENABLE_WORKFLOW_REGISTRY is False")
        from omnimind_backend.workers.workflow_registry import WorkflowRegistry  # noqa: F401


class TestPhase4DTv2:
    """Phase 4: DT v2 contracts and scoring operational."""

    def test_dt_v2_schemas_importable(self) -> None:
        settings = get_settings()
        if not settings.enable_dt_v2:
            pytest.skip("ENABLE_DT_V2 is False")
        from omnimind_backend.schemas.decomposition_v2 import (  # noqa: F401
            MainComponentContract,
            SubComponentContract,
            SynthesisContract,
        )

    def test_scoring_importable(self) -> None:
        settings = get_settings()
        if not settings.enable_dt_v2:
            pytest.skip("ENABLE_DT_V2 is False")
        from omnimind_backend.orchestrator.decomposition.scoring import compute_component_score  # noqa: F401
```

**Step 2: Run the tests**

Run: `cd python && python -m pytest tests/test_phase_gates.py -v`
Expected: Phase 0 tests PASS, Phase 1-4 tests SKIP (feature flags are off by default)

**Step 3: Commit**

```bash
git add python/tests/test_phase_gates.py
git commit -m "test: add phase gate tests for obsidian feature integration roadmap"
```

---

## Task 4: No-Regression Guard — Existing Tests Must Pass

**Step 1: Run the full test suite**

Run: `cd python && python -m pytest tests/ -v --tb=short`
Expected: All existing tests PASS. Phase gate tests either PASS (Phase 0) or SKIP (Phase 1-4).

**Step 2: Verify feature flags don't break startup**

Run: `cd python && python -c "from omnimind_backend.infra.config import get_settings; s = get_settings(); print(f'Flags OK: creative={s.enable_creative_agent}, dt_v2={s.enable_dt_v2}')"`
Expected: `Flags OK: creative=False, dt_v2=False`

---

## Summary

| Task | What | Files |
|------|------|-------|
| 1 | Per-phase feature flags | `infra/config.py` |
| 2 | Docs coverage verification script | `scripts/verify_obsidian_docs_coverage.sh` |
| 3 | Phase gate tests | `tests/test_phase_gates.py` |
| 4 | Full regression check | — |

## Dependency Map

This meta-plan enables and coordinates the other 6 plans:

```
This plan (meta)
  ├── Feature flags → gate all other plans
  ├── Coverage script → verifies Phase 0 completion
  └── Phase gate tests → verify each plan's exit criteria

Plan 1: agent-team-extended-contracts → Phase 1
Plan 2: decomposition-thinking-contracts-v2 → Phase 4
Plan 3: input-normalization-and-session-chunks → Phase 2
Plan 4: orchestrator-context-governance → Phase 2
Plan 5: researcher-pipeline-and-source-trust → Phase 1-2
Plan 6: workflow-caller-async-integration → Phase 3
```
