import re

with open('python/mindflow_backend/services/orchestration/todo_planning_service.py', 'r') as f:
    content = f.read()

# Task 1: Refactor Dependency Injection
# Remove the global variables and logic around _session_runtime_state_service

content = re.sub(r"_session_runtime_state_service = None\n\n\ndef _get_session_runtime_state_service\(\).*?return _session_runtime_state_service\n", "", content, flags=re.DOTALL)

# Add it as a parameter to the service or explicitly resolve it within methods without caching globally
content = content.replace("service = _get_session_runtime_state_service()", """from mindflow_backend.services.core import get_session_runtime_state_service
        try:
            service = get_session_runtime_state_service()
        except Exception as exc:
            _logger.warning("todo_session_runtime_state_service_unavailable", error=str(exc))
            return""")

# Task 5: Enhance Task Complexity Normalization
new_normalize = """def normalize_complexity_score(
    raw_score: float | None = None,
    *,
    priority: str = "medium",
    owner_agent: str | None = None,
    dependencies_count: int = 0,
    description: str = "",
    artifacts_count: int = 0,
    overall_complexity: float | None = None,
) -> float:
    \"\"\"Normalize task complexity into the [0, 1] interval using runtime heuristics.\"\"\"
    if raw_score is not None:
        return min(max(raw_score, 0.0), 1.0)
        
    base = 0.35
    if overall_complexity is not None:
        base = max(base, min(max(overall_complexity, 0.0), 1.0) * 0.45)

    base += 0.08 * min(dependencies_count, 3)
    base += 0.04 * min(artifacts_count, 3)
    base += _OWNER_WEIGHT.get((owner_agent or "").lower(), 0.0)
    base += {1: 0.0, 2: 0.07, 3: 0.14}.get(_PRIORITY_WEIGHT.get(priority, 2), 0.07)

    # Note: Description word count removed as it was arbitrary and brittle.
    # We now strictly rely on structural heuristics (dependencies, artifacts, priority, owner).

    return round(min(max(base, 0.0), 1.0), 3)"""

old_normalize = r"def normalize_complexity_score\(.*?return round\(min\(max\(base, 0\.0\), 1\.0\), 3\)"
content = re.sub(old_normalize, new_normalize, content, flags=re.DOTALL)

with open('python/mindflow_backend/services/orchestration/todo_planning_service.py', 'w') as f:
    f.write(content)
