"""Formatting utilities for MindFlow backend.

Functions for formatting different types of data.
"""

import re
from datetime import datetime, timedelta
from typing import Any


def format_sse(data: Any, event_id: str | int | None = None) -> str:
    """Format data for Server-Sent Events."""
    import json
    
    payload = data if isinstance(data, str) else json.dumps(data, ensure_ascii=True)
    if event_id is None:
        return f"data: {payload}\n\n"
    return f"id: {event_id}\ndata: {payload}\n\n"


def format_bytes(bytes_count: int) -> str:
    """Format bytes into human readable format."""
    if bytes_count == 0:
        return "0 B"
    
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    unit_index = 0
    
    while bytes_count >= 1024 and unit_index < len(units) - 1:
        bytes_count /= 1024
        unit_index += 1
    
    return f"{bytes_count:.1f} {units[unit_index]}"


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human readable format."""
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds:.0f}s"
    else:
        hours = int(seconds // 3600)
        remaining_minutes = int((seconds % 3600) // 60)
        return f"{hours}h {remaining_minutes}m"


def format_currency(amount: float, currency: str = "USD") -> str:
    """Format currency amount."""
    currency_symbols = {
        "USD": "$",
        "EUR": "€",
        "GBP": "£",
        "JPY": "¥",
        "BRL": "R$",
    }
    
    symbol = currency_symbols.get(currency, currency)
    
    if currency == "JPY":  # No decimal places for JPY
        return f"{symbol}{int(amount):,}"
    else:
        return f"{symbol}{amount:,.2f}"


def format_percentage(value: float, decimal_places: int = 1) -> str:
    """Format value as percentage."""
    return f"{value:.{decimal_places}f}%"


def format_number(value: int | float, decimal_places: int = 0) -> str:
    """Format number with thousands separator."""
    if isinstance(value, int) or decimal_places == 0:
        return f"{int(value):,}"
    else:
        return f"{value:,.{decimal_places}f}"


def format_datetime_iso(dt: datetime) -> str:
    """Format datetime in ISO format."""
    return dt.isoformat()


def format_datetime_human(dt: datetime) -> str:
    """Format datetime in human readable format."""
    now = datetime.now(dt.tzinfo)
    diff = now - dt
    
    if diff < timedelta(minutes=1):
        return "just now"
    elif diff < timedelta(hours=1):
        minutes = int(diff.total_seconds() // 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif diff < timedelta(days=1):
        hours = int(diff.total_seconds() // 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif diff < timedelta(days=7):
        days = diff.days
        return f"{days} day{'s' if days != 1 else ''} ago"
    else:
        return dt.strftime("%b %d, %Y")


def format_list(items: list, max_items: int = 5, separator: str = ", ") -> str:
    """Format list with truncation if too many items."""
    if len(items) <= max_items:
        return separator.join(str(item) for item in items)
    else:
        shown = separator.join(str(item) for item in items[:max_items])
        return f"{shown}... and {len(items) - max_items} more"


def format_key_value(pairs: dict, indent: int = 0) -> str:
    """Format dictionary as key-value pairs."""
    lines = []
    prefix = "  " * indent
    
    for key, value in pairs.items():
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            lines.append(format_key_value(value, indent + 1))
        elif isinstance(value, list):
            lines.append(f"{prefix}{key}: [{', '.join(str(v) for v in value)}]")
        else:
            lines.append(f"{prefix}{key}: {value}")
    
    return "\n".join(lines)


def format_code_block(code: str, language: str = "") -> str:
    """Format code as markdown code block."""
    if language:
        return f"```{language}\n{code}\n```"
    else:
        return f"```\n{code}\n```"


def format_error_message(error: Exception, include_traceback: bool = False) -> str:
    """Format error message for logging."""
    import traceback
    
    msg = f"{error.__class__.__name__}: {str(error)}"
    
    if include_traceback:
        msg += f"\n{''.join(traceback.format_tb(error.__traceback__))}"
    
    return msg


def format_phone_number(phone: str, country_code: str = "US") -> str:
    """Format phone number for specified country."""
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)
    
    if country_code == "US" and len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    elif country_code == "US" and len(digits) == 11 and digits[0] == '1':
        return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
    else:
        # Return original if can't format
        return phone


def format_url_safe(text: str) -> str:
    """Format text to be URL-safe."""
    # Convert to lowercase and replace spaces with hyphens
    text = text.lower().strip()
    text = re.sub(r'\s+', '-', text)
    
    # Remove non-alphanumeric characters except hyphens
    text = re.sub(r'[^a-z0-9-]', '', text)
    
    # Remove multiple consecutive hyphens
    text = re.sub(r'-+', '-', text)
    
    # Remove leading/trailing hyphens
    text = text.strip('-')
    
    return text


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format."""
    return format_bytes(size_bytes)


def format_memory_usage(bytes_used: int, bytes_total: int) -> str:
    """Format memory usage as percentage and absolute values."""
    percentage = (bytes_used / bytes_total) * 100 if bytes_total > 0 else 0
    return f"{format_bytes(bytes_used)} / {format_bytes(bytes_total)} ({percentage:.1f}%)"
