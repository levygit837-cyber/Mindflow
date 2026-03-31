"""Common validation utilities for MindFlow backend.

Generic validation functions that can be reused across the system.
"""

from typing import Any


def validate_memory_data(data: dict[str, Any]) -> list[str]:
    """Validate memory data and return list of errors."""
    errors = []
    
    # Validate required fields
    if not data.get("session_id"):
        errors.append("session_id is required")
    
    if not data.get("agent_id"):
        errors.append("agent_id is required")
    
    if not data.get("content"):
        errors.append("content is required")
    
    # Validate data types
    if "token_count" in data and not isinstance(data["token_count"], int):
        errors.append("token_count must be an integer")
    
    if "role" in data and data["role"] not in ["user", "assistant", "system"]:
        errors.append("role must be one of: user, assistant, system")
    
    return errors


def validate_search_query(query: str) -> list[str]:
    """Validate search query and return list of errors."""
    errors = []
    
    if not query or not query.strip():
        errors.append("Search query cannot be empty")
    
    if len(query) > 1000:
        errors.append("Search query too long (max 1000 characters)")
    
    return errors


def validate_session_id(session_id: str) -> list[str]:
    """Validate session ID and return list of errors."""
    errors = []
    
    if not session_id or not session_id.strip():
        errors.append("Session ID cannot be empty")
    
    if len(session_id) > 64:
        errors.append("Session ID too long (max 64 characters)")
    
    return errors


def validate_email(email: str) -> bool:
    """Validate email format."""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_uuid(uuid_str: str) -> bool:
    """Validate UUID format."""
    import uuid
    try:
        uuid.UUID(uuid_str)
        return True
    except ValueError:
        return False


def validate_json_schema(data: dict, schema: dict) -> list[str]:
    """Validate data against a JSON schema and return list of errors."""
    errors = []
    
    # Simple validation - in production would use jsonschema library
    required_fields = schema.get("required", [])
    for field in required_fields:
        if field not in data:
            errors.append(f"Required field '{field}' is missing")
    
    # Type validation
    properties = schema.get("properties", {})
    for field, prop_schema in properties.items():
        if field in data:
            expected_type = prop_schema.get("type")
            if expected_type == "string" and not isinstance(data[field], str):
                errors.append(f"Field '{field}' must be a string")
            elif expected_type == "integer" and not isinstance(data[field], int):
                errors.append(f"Field '{field}' must be an integer")
            elif expected_type == "array" and not isinstance(data[field], list):
                errors.append(f"Field '{field}' must be an array")
            elif expected_type == "object" and not isinstance(data[field], dict):
                errors.append(f"Field '{field}' must be an object")
    
    return errors


def validate_url(url: str) -> bool:
    """Validate URL format."""
    import re
    pattern = r'^https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:\w*))?)?$'
    return bool(re.match(pattern, url))


def validate_phone_number(phone: str) -> bool:
    """Validate phone number format (international)."""
    import re
    pattern = r'^\+?[\d\s\-\(\)]{10,}$'
    return bool(re.match(pattern, phone))


def validate_date_string(date_str: str) -> bool:
    """Validate ISO date string format."""
    from datetime import datetime
    try:
        datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return True
    except ValueError:
        return False
