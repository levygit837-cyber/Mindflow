"""Validation utilities for MindFlow backend.

Common validation functions and sanitizers used across the system.
"""

from .validators import (
    validate_memory_data,
    validate_search_query,
    validate_session_id,
    validate_email,
    validate_uuid,
    validate_json_schema,
    validate_url,
    validate_phone_number,
    validate_date_string,
)


def validate_task_dependencies(components: list) -> list[str]:
    """Check for cyclic dependencies in task components. Returns list of error messages."""
    errors: list[str] = []
    id_map = {c.task_id: c for c in components}
    visited: set = set()

    def has_cycle(task_id, path: set) -> bool:
        if task_id in path:
            return True
        if task_id in visited:
            return False
        path.add(task_id)
        component = id_map.get(task_id)
        if component:
            for dep_id in component.dependencies:
                if has_cycle(dep_id, path):
                    return True
        path.discard(task_id)
        visited.add(task_id)
        return False

    for component in components:
        if has_cycle(component.task_id, set()):
            errors.append(f"Cyclic dependency detected involving task: {component.title}")

    return errors

from .sanitizers import (
    sanitize_input,
    sanitize_html,
    sanitize_filename,
    sanitize_json_data,
    sanitize_sql_input,
    sanitize_phone_number,
    sanitize_url,
    limit_string_length,
    normalize_whitespace,
    extract_safe_filename,
)

__all__ = [
    # Task validation
    "validate_task_dependencies",
    # Validators
    "validate_memory_data",
    "validate_search_query",
    "validate_session_id",
    "validate_email",
    "validate_uuid",
    "validate_json_schema",
    "validate_url",
    "validate_phone_number",
    "validate_date_string",
    
    # Sanitizers
    "sanitize_input",
    "sanitize_html",
    "sanitize_filename",
    "sanitize_json_data",
    "sanitize_sql_input",
    "sanitize_phone_number",
    "sanitize_url",
    "limit_string_length",
    "normalize_whitespace",
    "extract_safe_filename",
]
