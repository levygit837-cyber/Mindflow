# OmniMind Phase 3 Roadmap — Tool Registry & DT

**Goal:** Deliver a fully functional Tool Registry and Decomposition Thinking (DT) pipeline.

## Phase 3.1 — Tool Registry & DeepAgents
- [ ] **Task 3.1.1:** Implement `ToolRegistry` class in `agents/tools/__init__.py`.
- [ ] **Task 3.1.2:** Integrate `deepagents` file system tools (read, write, list) into the registry.
- [ ] **Task 3.1.3:** Implement `filesystem.py` and `shell.py` wrappers with sandbox support.
- [ ] **Task 3.1.4:** Define tool scopes for each agent personality.
- [ ] **Validation:** Verify tool access and execution via `AgentRegistry`.

## Phase 3.2 — DT Infrastructure
- [ ] **Task 3.2.1:** Create `schemas/decomposition.py` for DT models (session, components).
- [ ] **Task 3.2.2:** Add Alembic migration for DT persistence.
- [ ] **Task 3.2.3:** Implement `orchestrator/complexity.py` (Complexity Scorer).
- [ ] **Validation:** Verify complexity scoring and DT triggering logic.

## Phase 3.3 — DT Pipeline Development
- [ ] **Task 3.3.1:** Implement `orchestrator/decomposition/decomposer.py` (DAG generation).
- [ ] **Task 3.3.2:** Implement `orchestrator/decomposition/scheduler.py` (Topological sort).
- [ ] **Task 3.3.3:** Implement `orchestrator/decomposition/resolver.py` (Task execution).
- [ ] **Task 3.3.4:** Implement `orchestrator/decomposition/synthesizer.py` (Result synthesis).
- [ ] **Validation:** E2E test of the DT pipeline on a complex multi-step task.

## Phase 3.4 — Hardening & Observability
- [ ] **Task 3.4.1:** Add DT progress events to SSE stream.
- [ ] **Task 3.4.2:** Implement error handling and fallback for DT failure.
- [ ] **Task 3.4.3:** Add comprehensive unit and integration tests for all Phase 3 modules.
- [ ] **Validation:** 85%+ code coverage and zero regressions.

## Milestones
- **M1:** Tool Registry & Core Tools operational.
- **M2:** DT Infrastructure & Scorer ready.
- **M3:** DT Pipeline end-to-end functionality.
- **M4:** Final Verification & Hardening complete.
