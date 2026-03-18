# Architecture

**Analysis Date:** 2024-03-24

## Pattern Overview

**Overall:** Event-Driven Orchestration with Declarative Planning

**Key Characteristics:**
- **Stateful Task Execution:** Long-running orchestration goals are broken down into explicitly state-managed Todo Lists.
- **Human-in-the-Loop Confirmation:** High-complexity tasks mandate a user-confirmed `.md` planning artifact before generating actionable steps.
- **Delegated Complexity:** The Orchestrator does not generate plans directly but coordinates context gathering before delegating the `PlannerAgent` to generate a formalized plan.
- **Modular Prompts:** The LLM instruction architecture relies on compositing core personas with specialized trait segments (e.g., planning, reflection, chains).

## Layers

**Orchestration Flow Layer:**
- Purpose: Directs the lifecycle of an execution phase (Check intent -> Plan -> Confirm -> Execute tasks).
- Location: `python/mindflow_backend/orchestrator/planning_flow.py`
- Contains: Execution loop, task dispatching logic, and planning heuristics.
- Depends on: Services (`PlanningService`, `TodoPlanningService`), LangChain event dispatch.
- Used by: CLI and API entry points handling user requests.

**Planning & State Service Layer:**
- Purpose: Manages persistent data models for plan documents and execution todo lists.
- Location: `python/mindflow_backend/services/orchestration/`
- Contains: In-memory and disk-persisted state dictionaries, complexity scoring algorithms.
- Depends on: Domain schemas (`PlanDocument`, `TodoItemContract`), Session State Manager.
- Used by: Orchestrator flow, specific planning tools.

**Prompt Composition Layer:**
- Purpose: Builds contextually aware and modular LLM system prompts for specific agent configurations.
- Location: `python/mindflow_backend/agents/prompts/`
- Contains: Hardcoded Markdown prompt strings and composite builders.
- Depends on: Prompt templating logic (`build_system_prompt`).
- Used by: LLM generation endpoints initializing the `Orchestrator` or `PlannerAgent`.

## Data Flow

**Planning-Aware Execution Loop:**

1. **Trigger Evaluation:** Orchestrator evaluates user input in `planning_flow.py` via `should_trigger_planning`. If complexity score >= 0.6 or intent suggests "planejamento", planning is triggered.
2. **Context Gathering:** Orchestrator delegates to an `analyst` agent to read files and establish codebase context.
3. **Plan Generation:** Orchestrator calls the `create_plan` tool. `PlanningService` creates a `PlanDocument` stored as a `.md` file in `.plans/session_{id}/`. Status is set to `PENDING_CONFIRMATION`.
4. **Human Confirmation:** User reviews the `.md` summary. If confirmed via `confirm_plan`, the plan is sent to `TodoPlanningService`.
5. **Todo Conversion:** `TodoPlanningService` normalizes the plan tasks into a list of `TodoItemContract` elements, tracking complexity and dependencies.
6. **Execution Loop:** `run_execution_loop` iterates: finds the next `PENDING` item with satisfied dependencies, assigns an agent (`coder`, `researcher`, `analyst`), and runs `run_workflow_step`. Updates item status to `COMPLETED` or `FAILED`.
7. **Synthesis:** After all tasks reach a terminal state, `synthesize_final_response` formulates a holistic user response.

**State Management:**
- `PlanningService` maintains `PlanDocument` instances in memory (`_plans`) and backed by local `.md` files.
- `TodoPlanningService` handles granular execution state (`_lists`), computing a normalized `complexity_score` for dynamic sorting, and relies on `get_session_runtime_state_service` for session persistence.

## Key Abstractions

**Todo Item Contract:**
- Purpose: Represents an atomic execution node derived from a larger plan, enforcing dependencies and priority.
- Examples: `python/mindflow_backend/schemas/tools/planning.py` (`TodoItemContract`, `TodoItemStatus`)
- Pattern: State Machine (`PENDING` -> `IN_PROGRESS` -> `COMPLETED` / `FAILED` / `BLOCKED`).

**Plan Document:**
- Purpose: The human-readable manifestation of a proposed sequence of events, including file impact matrix and risk analysis.
- Examples: `python/mindflow_backend/schemas/orchestration/planning.py` (`PlanDocument`)
- Pattern: Memento/Snapshot (stored on disk for recovery/review).

## Entry Points

**Orchestrator Planning Trigger:**
- Location: `python/mindflow_backend/orchestrator/planning_flow.py`
- Triggers: Incoming user messages parsed by `should_trigger_planning`.
- Responsibilities: Decides whether to route to simple execution or the multi-phase planning workflow.

**Prompt Composites:**
- Location: `python/mindflow_backend/agents/prompts/composite/full_orchestrator.py`
- Triggers: Agent initialization.
- Responsibilities: Aggregates `core/orchestrator.py` with `specialized/orchestrator_planning.py` to give the LLM instructions on how to use planning tools.

## Error Handling

**Strategy:** Gradual degradation with blocking boundaries.

**Patterns:**
- **Task Failure Handling:** If a workflow step fails, the `TodoItemContract` status changes to `FAILED`, and the `notes` field is populated with the exception trace. The execution loop logs the error but may continue if subsequent tasks are not strictly dependent.
- **Dependency Blocking:** Tasks whose dependencies fail or aren't met remain `PENDING` or `BLOCKED`. The execution loop exits cleanly if no non-blocked items remain, notifying the user.

## Cross-Cutting Concerns

**Prompt Governance:** Orchestrator persona behavior is strictly segmented. Core identity is separated from planning rules, allowing dynamic injection of capabilities without cluttering a single monolith prompt.
**Session Persistence:** Both plans and todo lists track `session_id`. While `PlanningService` relies on flat `.md` files, `TodoPlanningService` injects JSON structures into the `session_runtime_state_service`.

---

*Architecture analysis: 2024-03-24*