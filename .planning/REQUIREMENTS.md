# OmniMind Phase 3 — Tool Registry & Decomposition Thinking (DT)

## 1. Overview
Implement the centralized Tool Registry and the multi-step Decomposition Thinking (DT) pipeline to enable OmniMind to handle high-complexity tasks with autonomous task breakdown and execution.

## 2. Requirements

### 2.1 Tool Registry Implementation
- **Central Registry:** A `ToolRegistry` class in `omnimind_backend/agents/tools/__init__.py` to manage available tools.
- **DeepAgents Integration:** Use `deepagents` framework for core file system tools (read, write, list).
- **Tool Scopes:** Assign tools to specific agent personalities (Coder, Analyst, etc.) as defined in `ARCHITECTURE_PLAN.md`.
- **Sandbox Support:** Shell tools must execute in a background sandbox environment.
- **Verification:** All tools must be accessible via the registry and correctly authorized by agent scope.

### 2.2 Decomposition Thinking (DT) Pipeline
- **Complexity Scorer:** A heuristic or LLM-based module in `orchestrator/complexity.py` to assess task complexity.
- **Threshold Gate:** Trigger DT if `complexity_score >= 0.65` (configurable).
- **DT Schemas:** Pydantic models in `schemas/decomposition.py` for DT sessions and sub-tasks (DAG).
- **DT Pipeline Modules:**
  - **Decomposer:** Break complex tasks into a Directed Acyclic Graph (DAG) of sub-tasks.
  - **Scheduler:** Determine execution order based on dependencies and priority.
  - **Resolver:** Execute each sub-task through appropriate agents.
  - **Synthesizer:** Consolidate results into a final response.
- **Persistence:** Store DT session states, components, and results in PostgreSQL.

### 2.3 Integration & Security
- **No Circular Imports:** Ensure `agents` does not depend on `orchestrator`.
- **Streaming:** DT execution progress must be streamed back to the user via existing SSE infrastructure.
- **Auth & Rate Limiting:** Apply Phase 1.5 security standards to all new endpoints and LLM calls.

## 3. Acceptance Criteria
- [ ] `ToolRegistry` is functional and manages `deepagents` tools.
- [ ] Shell commands execute exclusively in a background sandbox.
- [ ] Task complexity is correctly scored, and DT is triggered at the specified threshold.
- [ ] Decomposed tasks form a valid DAG without cycles.
- [ ] Final synthesis correctly integrates results from all sub-tasks.
- [ ] All Phase 3 tests pass, and code coverage is maintained.
- [ ] No regression in Phase 1, 1.5, or 2 functionality.
