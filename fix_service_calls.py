import re

with open('python/mindflow_backend/services/orchestration/todo_planning_service.py', 'r') as f:
    content = f.read()

# Replace my previously injected try/except with simply `service = _get_session_runtime_state_service()`
old_call = """from mindflow_backend.services.core import get_session_runtime_state_service
        try:
            service = get_session_runtime_state_service()
        except Exception as exc:
            _logger.warning("todo_session_runtime_state_service_unavailable", error=str(exc))
            return"""
new_call = """service = _get_session_runtime_state_service()
        if service is None:
            return"""

content = content.replace(old_call, new_call)

with open('python/mindflow_backend/services/orchestration/todo_planning_service.py', 'w') as f:
    f.write(content)
