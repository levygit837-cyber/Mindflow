# Codebase Concerns

**Analysis Date:** 2024-05-23

## Tech Debt

**Todo Planning Service Circular Dependency:**
- Issue: Uses a global `_session_runtime_state_service` variable and a lazy loading `try/except` inner import to break a circular dependency.
- Files: `python/mindflow_backend/services/orchestration/todo_planning_service.py`
- Impact: Creates fragile async state initialization and masks actual import errors behind a generic log warning, potentially leading to incomplete session states during planning.
- Fix approach: Refactor the dependency graph or use dependency injection via a registry instead of ad-hoc global lazy loading.

**Arbitrary Task Complexity Normalization:**
- Issue: `normalize_complexity_score` calculates task difficulty using hardcoded floats based on simplistic metrics like `len(description.split()) > 16` adding `0.06` to a base score.
- Files: `python/mindflow_backend/services/orchestration/todo_planning_service.py`
- Impact: Inaccurate complexity scores may cause the Orchestrator to bypass the planning phase when it's needed, or mis-prioritize tasks.
- Fix approach: Implement a more robust evaluation model (potentially using a quick LLM heuristic call or explicit schemas from the planner).

## Fragile Areas

**Hardcoded Language Triggers for Planning:**
- Files: `python/mindflow_backend/orchestrator/planning_flow.py`
- Why fragile: The `should_trigger_planning` function relies on a hardcoded list of Portuguese keywords (`"planejar", "plano", "implementar", "refatorar"`, etc.).
- Safe modification: Will break or fail to trigger if the user interacts in English or another language, bypassing the entire planning architecture.
- Test coverage: Needs internationalization or intent-classification (LLM routing) rather than strict string matching.

**Execution Loop Iteration Limits:**
- Files: `python/mindflow_backend/orchestrator/planning_flow.py`
- Why fragile: `run_execution_loop` relies on a magic constant `_SAFETY_ITERATION_LIMIT = 20`. 
- Safe modification: If a generated plan results in more than 20 tasks, the loop will silently abort.
- Test coverage: Implement dynamic limits based on the size of the plan or a robust state machine rather than a fixed while loop counter.

**Error Masking in Execution Loop:**
- Files: `python/mindflow_backend/orchestrator/planning_flow.py`
- Why fragile: If the `todo_list` is not found, the loop catches a `ValueError`, attempts to run `_convert_plan_to_todo`, and issues a `continue`. If the conversion fails or does not persist correctly, this becomes an infinite loop that spins rapidly until it hits the `_SAFETY_ITERATION_LIMIT`.
- Safe modification: Check the output of the conversion explicitly and raise/break if state cannot be recovered.

## Security Considerations

**Prompt Context Window Exhaustion (Vulnerability):**
- Risk: The `PlannerAgent` injects raw, unsummarized `request.context` directly into the planning prompt messages.
- Files: `python/mindflow_backend/agents/planner_agent.py`
- Current mitigation: None visible in `_build_planning_messages`.
- Recommendations: If the context gathered during Phase 1 (e.g., from the `analyst` agent) is massive (multiple large files read), this will blow out the context window, causing the LLM call to fail. Implement token counting and semantic summarization before injecting `request.context`.

---

*Concerns audit: 2024-05-23*