"""JSON utilities for MindFlow backend.

Advanced JSON serialization, deserialization, and manipulation utilities.
"""

import json
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID


class JSONEncoder(json.JSONEncoder):
    """Custom JSON encoder with support for additional types."""
    
    def default(self, obj):
        # Handle datetime objects
        if isinstance(obj, datetime):
            return obj.isoformat()
        
        # Handle Decimal objects
        elif isinstance(obj, Decimal):
            return float(obj)
        
        # Handle UUID objects
        elif isinstance(obj, UUID):
            return str(obj)
        
        # Handle bytes
        elif isinstance(obj, bytes):
            return obj.decode('utf-8', errors='replace')
        
        # Handle sets
        elif isinstance(obj, set):
            return list(obj)
        
        # Handle complex numbers
        elif isinstance(obj, complex):
            return {"real": obj.real, "imag": obj.imag}
        
        # Default to parent class
        return super().default(obj)


def to_json(
    obj: Any,
    indent: int | None = None,
    sort_keys: bool = False,
    ensure_ascii: bool = False,
    encoder: json.JSONEncoder | None = None,
) -> str:
    """Convert object to JSON string with enhanced encoding."""
    return json.dumps(
        obj,
        cls=encoder or JSONEncoder,
        indent=indent,
        sort_keys=sort_keys,
        ensure_ascii=ensure_ascii,
        default=str,
    )


def from_json(
    json_str: str,
    default: Any = None,
    raise_on_error: bool = False,
) -> Any:
    """Parse JSON string with error handling."""
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        if raise_on_error:
            raise
        return default


def from_json_file(
    file_path: str,
    default: Any = None,
    encoding: str = 'utf-8',
) -> Any:
    """Load JSON from file with error handling."""
    try:
        with open(file_path, encoding=encoding) as f:
            return json.load(f)
    except (OSError, FileNotFoundError, json.JSONDecodeError):
        return default


def to_json_file(
    obj: Any,
    file_path: str,
    indent: int = 2,
    sort_keys: bool = True,
    encoding: str = 'utf-8',
    create_dirs: bool = True,
) -> bool:
    """Save object to JSON file."""
    try:
        import os
        
        if create_dirs:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding=encoding) as f:
            json.dump(
                obj,
                f,
                cls=JSONEncoder,
                indent=indent,
                sort_keys=sort_keys,
                ensure_ascii=False,
                default=str,
            )
        
        return True
    
    except (OSError, TypeError):
        return False


def merge_json_objects(*objects: dict[str, Any]) -> dict[str, Any]:
    """Merge multiple JSON objects (dictionaries)."""
    result = {}
    
    for obj in objects:
        if isinstance(obj, dict):
            result.update(obj)
    
    return result


def deep_merge_json_objects(*objects: dict[str, Any]) -> dict[str, Any]:
    """Deep merge multiple JSON objects."""
    def _deep_merge(base: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                base[key] = _deep_merge(base[key], value)
            else:
                base[key] = value
        return base
    
    result = {}
    
    for obj in objects:
        if isinstance(obj, dict):
            result = _deep_merge(result, obj)
    
    return result


def get_json_path(data: dict[str, Any], path: str, default: Any = None) -> Any:
    """Get value from nested JSON using dot notation path."""
    keys = path.split('.')
    current = data
    
    try:
        for key in keys:
            if isinstance(current, dict):
                current = current[key]
            elif isinstance(current, list) and key.isdigit():
                current = current[int(key)]
            else:
                return default
        
        return current
    
    except (KeyError, IndexError, TypeError):
        return default


def set_json_path(data: dict[str, Any], path: str, value: Any) -> dict[str, Any]:
    """Set value in nested JSON using dot notation path."""
    keys = path.split('.')
    current = data
    
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    
    current[keys[-1]] = value
    return data


def delete_json_path(data: dict[str, Any], path: str) -> bool:
    """Delete value from nested JSON using dot notation path."""
    keys = path.split('.')
    current = data
    
    try:
        for key in keys[:-1]:
            current = current[key]
        
        if keys[-1] in current:
            del current[keys[-1]]
            return True
        
        return False
    
    except (KeyError, TypeError):
        return False


def flatten_json(data: dict[str, Any], separator: str = '.') -> dict[str, Any]:
    """Flatten nested JSON object."""
    def _flatten(obj: Any, parent_key: str = '') -> dict[str, Any]:
        items = []
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_key = f"{parent_key}{separator}{key}" if parent_key else key
                items.extend(_flatten(value, new_key).items())
        
        elif isinstance(obj, list):
            for i, value in enumerate(obj):
                new_key = f"{parent_key}{separator}{i}" if parent_key else str(i)
                items.extend(_flatten(value, new_key).items())
        
        else:
            items.append((parent_key, obj))
        
        return dict(items)
    
    return _flatten(data)


def unflatten_json(data: dict[str, Any], separator: str = '.') -> dict[str, Any]:
    """Unflatten JSON object."""
    result = {}
    
    for key, value in data.items():
        keys = key.split(separator)
        current = result
        
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        current[keys[-1]] = value
    
    return result


def filter_json_keys(data: dict[str, Any], keys: list[str], include: bool = True) -> dict[str, Any]:
    """Filter JSON object by keys."""
    if include:
        return {k: v for k, v in data.items() if k in keys}
    else:
        return {k: v for k, v in data.items() if k not in keys}


def filter_json_by_value(
    data: dict[str, Any],
    predicate: callable,
    deep: bool = True,
) -> dict[str, Any]:
    """Filter JSON object by value predicate."""
    def _filter(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: _filter(v) for k, v in obj.items() if predicate(v)}
        elif isinstance(obj, list):
            return [_filter(item) for item in obj if predicate(item)]
        else:
            return obj if predicate(obj) else None
    
    if deep:
        return _filter(data)
    else:
        return {k: v for k, v in data.items() if predicate(v)}


def find_json_values(data: dict[str, Any], key: str) -> list[Any]:
    """Find all values for a specific key in nested JSON."""
    values = []
    
    def _find(obj: Any):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == key:
                    values.append(v)
                _find(v)
        elif isinstance(obj, list):
            for item in obj:
                _find(item)
    
    _find(data)
    return values


def find_json_keys_by_value(data: dict[str, Any], value: Any) -> list[str]:
    """Find all keys that have a specific value in nested JSON."""
    keys = []
    
    def _find(obj: Any, path: str = ''):
        if isinstance(obj, dict):
            for k, v in obj.items():
                current_path = f"{path}.{k}" if path else k
                if v == value:
                    keys.append(current_path)
                _find(v, current_path)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                current_path = f"{path}[{i}]" if path else f"[{i}]"
                if item == value:
                    keys.append(current_path)
                _find(item, current_path)
    
    _find(data)
    return keys


def validate_json_schema(data: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    """Simple JSON schema validation."""
    errors = []
    
    # Check required fields
    required_fields = schema.get('required', [])
    for field in required_fields:
        if field not in data:
            errors.append(f"Required field '{field}' is missing")
    
    # Check field types
    properties = schema.get('properties', {})
    for field, field_schema in properties.items():
        if field in data:
            expected_type = field_schema.get('type')
            actual_value = data[field]
            
            if expected_type == 'string' and not isinstance(actual_value, str):
                errors.append(f"Field '{field}' must be a string")
            elif expected_type == 'number' and not isinstance(actual_value, (int, float)):
                errors.append(f"Field '{field}' must be a number")
            elif expected_type == 'integer' and not isinstance(actual_value, int):
                errors.append(f"Field '{field}' must be an integer")
            elif expected_type == 'boolean' and not isinstance(actual_value, bool):
                errors.append(f"Field '{field}' must be a boolean")
            elif expected_type == 'array' and not isinstance(actual_value, list):
                errors.append(f"Field '{field}' must be an array")
            elif expected_type == 'object' and not isinstance(actual_value, dict):
                errors.append(f"Field '{field}' must be an object")
            
            # Check enum values
            enum_values = field_schema.get('enum')
            if enum_values and actual_value not in enum_values:
                errors.append(f"Field '{field}' must be one of: {enum_values}")
            
            # Check minimum/maximum for numbers
            if isinstance(actual_value, (int, float)):
                minimum = field_schema.get('minimum')
                maximum = field_schema.get('maximum')
                
                if minimum is not None and actual_value < minimum:
                    errors.append(f"Field '{field}' must be >= {minimum}")
                if maximum is not None and actual_value > maximum:
                    errors.append(f"Field '{field}' must be <= {maximum}")
            
            # Check min/max length for strings
            if isinstance(actual_value, str):
                min_length = field_schema.get('minLength')
                max_length = field_schema.get('maxLength')
                
                if min_length is not None and len(actual_value) < min_length:
                    errors.append(f"Field '{field}' must have at least {min_length} characters")
                if max_length is not None and len(actual_value) > max_length:
                    errors.append(f"Field '{field}' must have at most {max_length} characters")
            
            # Check min/max items for arrays
            if isinstance(actual_value, list):
                min_items = field_schema.get('minItems')
                max_items = field_schema.get('maxItems')
                
                if min_items is not None and len(actual_value) < min_items:
                    errors.append(f"Field '{field}' must have at least {min_items} items")
                if max_items is not None and len(actual_value) > max_items:
                    errors.append(f"Field '{field}' must have at most {max_items} items")
    
    return errors


def json_patch(original: dict[str, Any], patch: list[dict[str, Any]]) -> dict[str, Any]:
    """Apply JSON Patch (RFC 6902) to object."""
    import copy
    
    result = copy.deepcopy(original)
    
    for operation in patch:
        op = operation.get('op')
        path = operation.get('path')
        value = operation.get('value')
        
        if op == 'add':
            set_json_path(result, path, value)
        elif op == 'remove':
            delete_json_path(result, path)
        elif op == 'replace':
            set_json_path(result, path, value)
        elif op == 'move':
            from_path = operation.get('from')
            from_value = get_json_path(result, from_path)
            if from_value is not None:
                delete_json_path(result, from_path)
                set_json_path(result, path, from_value)
        elif op == 'copy':
            from_path = operation.get('from')
            from_value = get_json_path(result, from_path)
            if from_value is not None:
                set_json_path(result, path, from_value)
        elif op == 'test':
            test_value = get_json_path(result, path)
            if test_value != value:
                raise ValueError(f"JSON Patch test failed at path {path}")
    
    return result


def json_diff(obj1: dict[str, Any], obj2: dict[str, Any]) -> list[dict[str, Any]]:
    """Generate JSON Patch representing differences between two objects."""
    # This is a simplified implementation
    patches = []
    
    # Find added/modified keys
    for key, value in obj2.items():
        if key not in obj1:
            patches.append({'op': 'add', 'path': f'/{key}', 'value': value})
        elif obj1[key] != value:
            patches.append({'op': 'replace', 'path': f'/{key}', 'value': value})
    
    # Find removed keys
    for key in obj1:
        if key not in obj2:
            patches.append({'op': 'remove', 'path': f'/{key}'})
    
    return patches


def compress_json(data: dict[str, Any]) -> str:
    """Compress JSON by removing whitespace and using shorter representations."""
    # Remove whitespace
    json_str = to_json(data, indent=None, sort_keys=True)
    
    # Simple compression: replace common patterns
    # (This is a very basic implementation)
    return json_str


def is_valid_json(json_str: str) -> bool:
    """Check if string is valid JSON."""
    try:
        json.loads(json_str)
        return True
    except json.JSONDecodeError:
        return False


def pretty_print_json(obj: Any, indent: int = 2) -> str:
    """Pretty print JSON object."""
    return to_json(obj, indent=indent, sort_keys=True)


def json_to_xml(data: dict[str, Any], root_name: str = 'root') -> str:
    """Convert JSON to simple XML format."""
    def _to_xml(obj: Any, name: str, indent: int = 0) -> str:
        spaces = '  ' * indent
        
        if isinstance(obj, dict):
            xml_parts = [f"{spaces}<{name}>"]
            for key, value in obj.items():
                xml_parts.append(_to_xml(value, key, indent + 1))
            xml_parts.append(f"{spaces}</{name}>")
            return '\n'.join(xml_parts)
        
        elif isinstance(obj, list):
            xml_parts = []
            for item in obj:
                xml_parts.append(_to_xml(item, name, indent))
            return '\n'.join(xml_parts)
        
        else:
            return f"{spaces}<{name}>{str(obj)}</{name}>"
    
    return _to_xml(data, root_name)


def json_to_yaml(data: dict[str, Any]) -> str:
    """Convert JSON to YAML format (basic implementation)."""
    def _to_yaml(obj: Any, indent: int = 0) -> str:
        spaces = '  ' * indent
        
        if isinstance(obj, dict):
            yaml_parts = []
            for key, value in obj.items():
                yaml_parts.append(f"{spaces}{key}: {_to_yaml(value, indent + 1)}")
            return '\n'.join(yaml_parts)
        
        elif isinstance(obj, list):
            yaml_parts = []
            for item in obj:
                yaml_parts.append(f"{spaces}- {_to_yaml(item, indent + 1)}")
            return '\n'.join(yaml_parts)
        
        elif isinstance(obj, str):
            return f'"{obj}"'
        
        else:
            return str(obj)
    
    return _to_yaml(data)
