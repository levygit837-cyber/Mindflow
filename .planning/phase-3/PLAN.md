# Plan: Phase 3 — Tool Registry & Decomposition Thinking (DT)

## 1. Objectives
Implement a centralized Tool Registry using the `deepagents` framework and a multi-step Decomposition Thinking (DT) pipeline for complex task resolution.

## 2. Tasks

### Task 3.1: Tool Registry & Sandboxing
- [ ] **3.1.1: Implement `ToolRegistry`** in `omnimind_backend/agents/tools/__init__.py`.
  - Goal: Centralize tool management and scoped access per agent personality.
  - Dependencies: None.
- [ ] **3.1.2: Integrate `deepagents` FS tools.**
  - Goal: Expose `ls_info`, `read`, `write`, `edit`, `grep_raw`, `glob_info` as registry tools.
  - Normalization: Use keyword arguments and Pydantic models for output.
- [ ] **3.1.3: Implement `OmniMindSandbox`** in `omnimind_backend/agents/tools/sandbox.py`.
  - Goal: Mandatory background sandbox for shell execution (inherits `BaseSandbox`).
  - Security: Ensure process isolation or restricted execution.
- [ ] **3.1.4: Define Tool Scopes** in `omnimind_backend/agents/_registry.py`.
  - Goal: Assign tool sets to Coder, Analyst, Researcher, ArchTech, and Critic.

### Task 3.2: DT Infrastructure
- [ ] **3.2.1: Create DT Schemas** in `omnimind_backend/schemas/decomposition.py`.
  - Models: `DTSession`, `DTTask`, `DTStatus`, `DTResult`.
- [ ] **3.2.2: Implement DB Migrations.**
  - Create Alembic migration for `dt_sessions` and `dt_tasks` tables.
- [ ] **3.2.3: Implement Complexity Scorer** in `omnimind_backend/orchestrator/complexity.py`.
  - Logic: Heuristic + LLM evaluation (threshold 0.65).

### Task 3.3: DT Pipeline Development
- [ ] **3.3.1: Implement Decomposer** in `omnimind_backend/orchestrator/decomposition/decomposer.py`.
  - Goal: LLM prompt to generate a JSON DAG of sub-tasks.
- [ ] **3.3.2: Implement Scheduler** in `omnimind_backend/orchestrator/decomposition/scheduler.py`.
  - Goal: Topological sort for task execution order.
- [ ] **3.3.3: Implement Resolver** in `omnimind_backend/orchestrator/decomposition/resolver.py`.
  - Goal: Iterate through tasks, invoke agents, and manage state.
- [ ] **3.3.4: Implement Synthesizer** in `omnimind_backend/orchestrator/decomposition/synthesizer.py`.
  - Goal: Final LLM pass to consolidate all results.

### Task 3.4: Integration & Testing
- [ ] **3.4.1: Wire DT into Orchestrator Graph** in `omnimind_backend/orchestrator/graph.py`.
- [ ] **3.4.2: Add DT events to SSE stream** in `omnimind_backend/runtime/stream.py`.
- [ ] **3.4.3: Write Unit Tests** for Registry, Sandbox, Scorer, and DT Modules.
- [ ] **3.4.4: Write E2E Integration Test** for a complex decomposed task.

## 3. Verification Strategy
- **Unit Tests:** Each module in `tests/test_tool_registry.py`, `tests/test_complexity_scorer.py`, etc.
- **Contract Verification:** Ensure tool outputs match `deepagents` protocols.
- **E2E Validation:** CLI-driven test of a multi-file refactoring task to trigger DT.
- **Coverage:** Maintain ≥ 85% coverage in core modules.
