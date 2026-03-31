"""Data conversion utilities for MindFlow backend.

Functions for converting between different data types and formats.
"""

import base64
import hashlib
import json
import uuid
from datetime import datetime
from typing import Any


def to_json(data: Any, indent: int | None = None, ensure_ascii: bool = False) -> str:
    """Convert data to JSON string."""
    return json.dumps(data, indent=indent, ensure_ascii=ensure_ascii, default=str)


def from_json(json_str: str, default: Any = None) -> Any:
    """Convert JSON string to data."""
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default


def to_bool(value: Any) -> bool:
    """Convert value to boolean."""
    if isinstance(value, bool):
        return value
    
    if isinstance(value, (int, float)):
        return value != 0
    
    if isinstance(value, str):
        truthy_values = ["true", "1", "yes", "on", "enabled", "y"]
        falsy_values = ["false", "0", "no", "off", "disabled", "n"]
        
        value_lower = value.lower().strip()
        if value_lower in truthy_values:
            return True
        elif value_lower in falsy_values:
            return False
    
    return bool(value)


def to_int(value: Any, default: int = 0) -> int:
    """Convert value to integer."""
    try:
        if isinstance(value, bool) or isinstance(value, (int, float)):
            return int(value)
        elif isinstance(value, str):
            # Handle common string formats
            value = value.strip().lower()
            if value == "true":
                return 1
            elif value == "false":
                return 0
            else:
                return int(float(value))
        else:
            return int(value)
    except (ValueError, TypeError):
        return default


def to_float(value: Any, default: float = 0.0) -> float:
    """Convert value to float."""
    try:
        if isinstance(value, bool) or isinstance(value, (int, float)):
            return float(value)
        elif isinstance(value, str):
            value = value.strip()
            if value == "":
                return default
            return float(value)
        else:
            return float(value)
    except (ValueError, TypeError):
        return default


def to_str(value: Any, default: str = "") -> str:
    """Convert value to string."""
    if value is None:
        return default
    
    if isinstance(value, str):
        return value
    
    if isinstance(value, bytes):
        try:
            return value.decode('utf-8')
        except UnicodeDecodeError:
            return value.decode('utf-8', errors='replace')
    
    return str(value)


def to_list(value: Any) -> list[Any]:
    """Convert value to list."""
    if value is None:
        return []
    
    if isinstance(value, list):
        return value
    
    if isinstance(value, (tuple, set)):
        return list(value)
    
    if isinstance(value, str):
        # Split by commas if it looks like a comma-separated list
        if ',' in value:
            return [item.strip() for item in value.split(',')]
        return [value]
    
    return [value]


def to_dict(value: Any) -> dict[str, Any]:
    """Convert value to dictionary."""
    if value is None:
        return {}
    
    if isinstance(value, dict):
        return value
    
    if isinstance(value, str):
        # Try to parse as JSON
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
    
    # Convert object to dict if it has __dict__
    if hasattr(value, '__dict__'):
        return value.__dict__
    
    return {}


def to_uuid(value: Any, default: str | None = None) -> str | None:
    """Convert value to UUID string."""
    if value is None:
        return default
    
    if isinstance(value, uuid.UUID):
        return str(value)
    
    if isinstance(value, str):
        try:
            # Try to parse as UUID
            uuid_obj = uuid.UUID(value)
            return str(uuid_obj)
        except ValueError:
            # Generate new UUID if string is not a valid UUID
            return str(uuid.uuid4())
    
    # Generate new UUID for other types
    return str(uuid.uuid4())


def to_datetime(value: Any, default: datetime | None = None) -> datetime | None:
    """Convert value to datetime."""
    if value is None:
        return default
    
    if isinstance(value, datetime):
        return value
    
    if isinstance(value, (int, float)):
        # Assume Unix timestamp
        try:
            return datetime.fromtimestamp(value)
        except (ValueError, OSError):
            return default
    
    if isinstance(value, str):
        # Try common datetime formats
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%d/%m/%Y",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        
        # Try ISO format
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            pass
    
    return default


def to_base64(data: str | bytes) -> str:
    """Convert data to base64 string."""
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    return base64.b64encode(data).decode('utf-8')


def from_base64(base64_str: str) -> bytes:
    """Convert base64 string to bytes."""
    return base64.b64decode(base64_str)


def to_hash(data: str | bytes, algorithm: str = "sha256") -> str:
    """Convert data to hash string."""
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    hash_obj = hashlib.new(algorithm)
    hash_obj.update(data)
    return hash_obj.hexdigest()


def to_snake_case(text: str) -> str:
    """Convert text to snake_case."""
    import re
    
    # Convert spaces and hyphens to underscores
    text = re.sub(r'[\s-]+', '_', text)
    
    # Add underscore before capital letters (except at start)
    text = re.sub(r'(?<!^)(?=[A-Z])', '_', text)
    
    # Convert to lowercase
    text = text.lower()
    
    # Remove multiple consecutive underscores
    text = re.sub(r'_+', '_', text)
    
    # Remove leading/trailing underscores
    text = text.strip('_')
    
    return text


def to_camel_case(text: str) -> str:
    """Convert text to camelCase."""
    
    # Convert to snake_case first
    snake = to_snake_case(text)
    
    # Split by underscores and capitalize each part except first
    parts = snake.split('_')
    if not parts:
        return ""
    
    first_part = parts[0]
    other_parts = [part.capitalize() for part in parts[1:]]
    
    return first_part + "".join(other_parts)


def to_pascal_case(text: str) -> str:
    """Convert text to PascalCase."""
    # Convert to snake_case first
    snake = to_snake_case(text)
    
    # Split by underscores and capitalize each part
    parts = snake.split('_')
    return "".join(part.capitalize() for part in parts if part)


def to_kebab_case(text: str) -> str:
    """Convert text to kebab-case."""
    # Convert to snake_case first
    snake = to_snake_case(text)
    
    # Replace underscores with hyphens
    return snake.replace('_', '-')


def to_slug(text: str) -> str:
    """Convert text to URL slug."""
    import re
    
    # Convert to lowercase and replace spaces with hyphens
    text = text.lower()
    text = re.sub(r'[\s_]+', '-', text)
    
    # Remove non-alphanumeric characters except hyphens
    text = re.sub(r'[^a-z0-9-]', '', text)
    
    # Remove multiple consecutive hyphens
    text = re.sub(r'-+', '-', text)
    
    # Remove leading/trailing hyphens
    text = text.strip('-')
    
    return text


def bytes_to_human(bytes_count: int) -> str:
    """Convert bytes to human readable format."""
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    unit_index = 0
    
    while bytes_count >= 1024 and unit_index < len(units) - 1:
        bytes_count /= 1024
        unit_index += 1
    
    return f"{bytes_count:.1f} {units[unit_index]}"


def human_to_bytes(human_str: str) -> int | None:
    """Convert human readable size to bytes."""
    import re
    
    # Match pattern: number + unit
    match = re.match(r'^(\d+(?:\.\d+)?)\s*([KMGT]?B?)$', human_str.upper())
    if not match:
        return None
    
    number = float(match.group(1))
    unit = match.group(2)
    
    multipliers = {
        'B': 1,
        'KB': 1024,
        'MB': 1024 ** 2,
        'GB': 1024 ** 3,
        'TB': 1024 ** 4,
        'K': 1024,
        'M': 1024 ** 2,
        'G': 1024 ** 3,
        'T': 1024 ** 4,
    }
    
    multiplier = multipliers.get(unit, 1)
    return int(number * multiplier)
