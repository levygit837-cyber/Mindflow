# Phase 6: Orchestrator Todo and Task Planning

**Goal:** Refactor and improve Orchestrator Todo, Task Planning, prompt application, and resolve documented technical debt.

## Task Breakdown

### Task 1: Dependency Injection Refactor in TodoPlanningService
- **Description:** Remove the global lazy-loaded `_session_runtime_state_service` variable in `python/mindflow_backend/services/orchestration/todo_planning_service.py`. Implement a proper dependency injection mechanism or centralized registry.
- **Goal:** Eliminate the circular dependency hack and ensure reliable async state initialization.

### Task 2: Implement Token-Aware Context Summarization
- **Description:** Refactor `PlannerAgent._build_planning_messages` in `python/mindflow_backend/agents/planner_agent.py` to prevent context window exhaustion. Introduce a check on token limits and implement semantic summarization if `request.context` exceeds safety thresholds.
- **Goal:** Protect LLM calls from failing when operating on large files or extensive context gathered during mapping.

### Task 3: Execution Loop Hardening & Error Handling
- **Description:** Update `run_execution_loop` in `python/mindflow_backend/orchestrator/planning_flow.py`. Remove the magic `_SAFETY_ITERATION_LIMIT` and replace it with a dynamic limit based on the actual plan size. Fix the error masking by removing the naive `continue` block that swallows `ValueError` for missing todo lists.
- **Goal:** Prevent infinite loops and silent failures in the orchestrator's state machine.

### Task 4: Upgrade Planning Trigger Heuristics
- **Description:** Replace the hardcoded Portuguese string triggers (`"planejar"`, `"implementar"`) in `should_trigger_planning` (`python/mindflow_backend/orchestrator/planning_flow.py`) with a lightweight intent classification logic or multi-language routing logic.
- **Goal:** Make the orchestrator language-agnostic and more robust in deciding when to enter the planning state.

### Task 5: Enhance Task Complexity Normalization
- **Description:** Refactor `normalize_complexity_score` in `TodoPlanningService` to remove arbitrary word-count-based scoring. Rely on an explicit complexity field evaluated by the planner or a robust structural heuristic.
- **Goal:** Ensure accurate task prioritization and scheduling within the execution flow.

## Verification Protocol
1. **Dependency Verification:** Run the backend test suite to ensure no circular import errors exist upon initialization.
2. **Context Limits:** Introduce a mock massive context payload to `PlannerAgent` and assert that it correctly summarizes and completes without context exhaustion exceptions.
3. **Execution Loop Tests:** Unit test the `run_execution_loop` with a simulated corrupted state (e.g., missing todo list) and verify it raises a clean exception instead of infinitely looping.
4. **Intent Tests:** Test `should_trigger_planning` with multiple languages (English, Portuguese, Spanish) to ensure correct routing.
5. **Score Verification:** Validate that task generation outputs valid complexity floats without relying on string length.