# Research: Orchestrator Todo and Task Planning

**Phase:** 06-orchestrator-todo-planning
**Goal:** Refactor and improve Orchestrator Todo, Task Planning, prompt application, and resolve documented technical debt.

## Current Architecture & State
The Orchestrator relies on an event-driven flow (`python/mindflow_backend/orchestrator/planning_flow.py`). It intercepts user intent, triggers a `PlannerAgent` to build a `.md` plan, which the user confirms. The confirmed plan is converted into `TodoItemContract` nodes mapped via `TodoPlanningService`. 
Prompts are dynamically composed from segments (e.g., `core/orchestrator.py` and `specialized/orchestrator_planning.py`). 

## Identified Concerns & Vulnerabilities
Based on the `.planning/codebase/CONCERNS.md`, the following issues require resolution:
1. **Context Window Exhaustion:** `PlannerAgent` injects raw, unsummarized context directly into planning prompts. This presents a critical vulnerability on large files.
2. **Circular Dependencies:** `TodoPlanningService` uses a lazy-loaded global variable `_session_runtime_state_service` which hides import errors and creates fragility.
3. **Hardcoded Language Triggers:** `should_trigger_planning` relies strictly on Portuguese string matches (e.g., "planejar"), which breaks for other languages.
4. **Error Masking & Infinite Loops:** The execution loop in `planning_flow.py` catches `ValueError` for missing todo lists but can spin infinitely up to its safety limit.
5. **Arbitrary Complexity Normalization:** `normalize_complexity_score` uses simplistic word-count metrics to calculate task difficulty.
6. **Static Iteration Limits:** `run_execution_loop` uses a magic constant `_SAFETY_ITERATION_LIMIT = 20`.

## Implementation Strategy
1. **Dependency Injection Refactor:** Implement a centralized registry or explicit DI for session runtime state to remove circular dependency hacks.
2. **Context Summarization Layer:** Introduce a token-aware summarization step before context injection in `PlannerAgent._build_planning_messages`.
3. **Intent-Based Routing:** Upgrade `should_trigger_planning` to use a fast LLM intent classifier or broader heuristic, discarding hardcoded Portuguese keywords.
4. **Execution Loop Hardening:** Refactor `run_execution_loop` to fail fast on state corruption (e.g., missing todo list) and implement a dynamic execution limit based on the generated plan size.
5. **Schema-Driven Complexity:** Replace arbitrary length checks in `normalize_complexity_score` with an explicit field evaluated by the planner or a robust heuristic.