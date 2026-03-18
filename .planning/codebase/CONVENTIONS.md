# Coding Conventions

**Analysis Date:** 2026-03-17

## Naming Patterns

**Files:**
- `snake_case` for Python modules (e.g., `orchestrator_planning.py`, `todo_planning_service.py`).

**Functions:**
- `snake_case` for functions and methods. Private methods use leading underscore (e.g., `_ensure_session_loaded`, `_persist_session_state`).
- Builder functions used for prompts (e.g., `build_orchestrator_planning_prompt`).

**Variables:**
- `snake_case` for local variables and parameters.
- Constants and exported prompts are `UPPER_SNAKE_CASE` (e.g., `_OPEN_STATUSES`, `ORCHESTRATOR_PLANNING_PROMPT`).

**Types:**
- `PascalCase` for classes, Pydantic models, and TypedDicts (e.g., `PlanningFlowState`, `TodoItemContract`).

## Code Style

**Formatting:**
- Modern Python features like `from __future__ import annotations`.
- Extensive use of type hints (`dict[str, Any]`, `list`, `str | None`).
- Pydantic models are the standard for data structures and contracts, utilizing methods like `model_copy(deep=True)`, `model_dump(mode="json")`, and `model_validate`.

## Import Organization

**Order:**
1. `from __future__ import annotations` (must be first)
2. Standard library imports (e.g., `import asyncio`, `from typing import Any`)
3. Third-party library imports (e.g., `from langchain_core.callbacks.manager import adispatch_custom_event`)
4. Local project imports (e.g., `from mindflow_backend.infra.logging import get_logger`)
5. Local type-checking only imports (inside `if TYPE_CHECKING:` block) to avoid circular dependencies.

## Prompt Engineering Patterns

**Definition:**
- Prompts are defined as large markdown-formatted string variables (e.g., in `python/mindflow_backend/agents/prompts/specialized/orchestrator_planning.py`).
- Clear structural sections using markdown headers (`### Planning Mode`, `#### Planning Workflow`, `#### Example Flow`).

**Encapsulation:**
- Prompt strings are wrapped by a builder function (e.g., `build_system_prompt()`) that appends standard system preambles.
- The compiled prompt is exported as a constant.

## Error Handling

**Patterns:**
- Extensive use of structural logging for exceptions rather than crashing, especially for non-critical side effects (e.g., session state persistence).
- Uses `try/except` to catch generic `Exception` when recovering from or ignoring errors is safe.
- Propagates custom or meaningful `ValueError` when validation fails.

## Logging

**Framework:** `mindflow_backend.infra.logging.get_logger(__name__)`

**Patterns:**
- Structured logging with explicit event names and contextual `kwargs`.
- Example: `_logger.warning("todo_session_state_load_failed", session_id=session_id, error=str(exc))`
- `info` used for major state changes (`"todo_list_replaced"`), `warning` and `error` used for exceptions.

## Architecture & Module Design

**Dependency Injection:**
- Services are accessed via getter functions acting as service locators/singletons (e.g., `get_todo_planning_service()`, `get_session_runtime_state_service()`).
- Avoids circular imports by importing getter functions lazily within functions.

**Event Dispatching:**
- The orchestrator communicates progress to the UI using LangChain's event system.
- `adispatch_custom_event("agent_thought", {"thought": "..."})` is heavily utilized to surface UX information like planning stages and task executions.

---

*Convention analysis: 2026-03-17*