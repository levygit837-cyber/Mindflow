# Testing Patterns

**Analysis Date:** 2026-03-17

## Test Framework

**Runner:**
- `pytest` (configured via `pytest.ini`)
- Async support provided by `pytest-asyncio` plugin.

**Run Commands:**
```bash
pytest tests/              # Run all tests
pytest tests/unit/orchestrator/  # Run orchestrator unit tests
```

## Test File Organization

**Location:**
- Tests are completely separated from source code, residing in the `python/tests/` directory.
- Test directory structure mirrors the source structure (e.g., `python/tests/unit/orchestrator/`).

**Naming:**
- Files: `test_[module_name].py` (e.g., `test_todo_planning_service.py`).
- Functions: `test_[behavior_description]` (e.g., `test_todo_planning_service_replace_focus_and_stale`).

## Test Structure

**Suite Organization:**
```python
@pytest.mark.asyncio
async def test_todo_planning_service_isolated_by_session_and_task() -> None:
    from mindflow_backend.services.orchestration.todo_planning_service import TodoPlanningService

    # Arrange
    service = TodoPlanningService()
    
    # Act
    await service.replace_list(
        session_id="session-a",
        task_id="task-1",
        goal="A",
        source="planner",
        items=[{"item_id": "a1", "title": "A1"}],
    )
    
    # Assert
    task_lookup = await service.get_list_by_task_id("task-1")
    assert task_lookup.todo_list.goal == "A"
```

## Mocking

**Framework:** `pytest.MonkeyPatch`

**Patterns:**
```python
@pytest.mark.asyncio
async def test_todo_planning_service_persists_and_rehydrates_state(monkeypatch: pytest.MonkeyPatch) -> None:
    import mindflow_backend.services.orchestration.todo_planning_service as module
    
    # Create fake implementation
    fake_runtime_state = _FakeSessionRuntimeStateService()
    
    # Patch the service locator getter function
    monkeypatch.setattr(module, "_get_session_runtime_state_service", lambda: fake_runtime_state, raising=False)
```

**What to Mock:**
- External dependencies, I/O bound operations, and session runtime state services are mocked using custom fake classes (e.g., `_FakeSessionRuntimeStateService`).
- Service locators/getters are monkeypatched at the module level.

## Validation & Model Testing

**Patterns:**
- Pydantic models are extensively tested for default values and edge cases.
- `ValidationError` is expected and asserted using `with pytest.raises(ValidationError):`.
- Serialization cycles (`model_dump` -> `model_validate`) are validated for correctness.

```python
def test_orchestrator_decision_serialization_round_trips_specialist_identity() -> None:
    decision = OrchestratorDecision(agent=AgentType.CODER, specialist=SpecialistType.ARCH_TECH)
    data = decision.model_dump()
    restored = OrchestratorDecision.model_validate(data)
    assert restored == decision
```

## Coverage

**Requirements:**
- Configured in `pytest.ini` with `--cov-fail-under=80`.

**View Coverage:**
- The configuration already includes `--cov=mindflow_backend --cov-report=term-missing --cov-report=html`.

## Common Patterns

**Async Testing:**
- All asynchronous test functions are decorated with `@pytest.mark.asyncio`.
- Use `await asyncio.sleep(...)` for timing-related logic, such as testing stale conditions in caching mechanisms.

---

*Testing analysis: 2026-03-17*