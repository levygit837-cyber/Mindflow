"""Memory data validation utilities."""

from typing import Any, Dict, List


def validate_memory_data(data: Dict[str, Any]) -> List[str]:
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


def validate_search_query(query: str) -> List[str]:
    """Validate search query and return list of errors."""
    errors = []
    
    if not query or not query.strip():
        errors.append("Search query cannot be empty")
    
    if len(query) > 1000:
        errors.append("Search query too long (max 1000 characters)")
    
    return errors


def validate_session_id(session_id: str) -> List[str]:
    """Validate session ID and return list of errors."""
    errors = []
    
    if not session_id or not session_id.strip():
        errors.append("Session ID cannot be empty")
    
    if len(session_id) > 64:
        errors.append("Session ID too long (max 64 characters)")
    
    return errors
