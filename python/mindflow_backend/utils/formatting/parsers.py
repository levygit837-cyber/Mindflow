"""Parsing utilities for MindFlow backend.

Functions for parsing different data formats.
"""

import json
import re
from datetime import datetime
from typing import Any


def extract_json_from_response(content: str) -> str:
    """Strip markdown code fences from an LLM response and return the JSON string."""
    if "```json" in content:
        return content.split("```json")[1].split("```")[0].strip()
    if "```" in content:
        return content.split("```")[1].split("```")[0].strip()
    return content.strip()


def parse_csv(value: str) -> list[str]:
    """Parse CSV string into list of values."""
    return [part.strip() for part in value.split(",") if part.strip()]


def parse_json_safe(content: str, default: Any = None) -> Any:
    """Safely parse JSON content with fallback."""
    try:
        return json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return default


def parse_datetime_iso(dt_str: str) -> datetime | None:
    """Parse ISO datetime string."""
    try:
        return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    except ValueError:
        return None


def parse_date_string(date_str: str) -> datetime | None:
    """Parse various date string formats."""
    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    return None


def parse_url(url: str) -> dict[str, str]:
    """Parse URL into components."""
    import urllib.parse
    
    parsed = urllib.parse.urlparse(url)
    return {
        "scheme": parsed.scheme,
        "netloc": parsed.netloc,
        "path": parsed.path,
        "params": parsed.params,
        "query": parsed.query,
        "fragment": parsed.fragment,
    }


def parse_query_string(query: str) -> dict[str, list[str]]:
    """Parse query string into dictionary."""
    import urllib.parse
    
    return urllib.parse.parse_qs(query)


def parse_phone_number(phone: str) -> dict[str, str]:
    """Parse phone number into components."""
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)
    
    result = {
        "original": phone,
        "digits": digits,
        "country_code": "",
        "area_code": "",
        "local_number": "",
    }
    
    if len(digits) == 11 and digits[0] == '1':
        result["country_code"] = "1"
        result["area_code"] = digits[1:4]
        result["local_number"] = digits[4:]
    elif len(digits) == 10:
        result["area_code"] = digits[:3]
        result["local_number"] = digits[3:]
    
    return result


def parse_markdown_links(text: str) -> list[dict[str, str]]:
    """Parse markdown links from text."""
    pattern = r'\[([^\]]+)\]\(([^)]+)\)'
    matches = re.findall(pattern, text)
    
    return [
        {"text": match[0], "url": match[1]}
        for match in matches
    ]


def parse_hashtags(text: str) -> list[str]:
    """Parse hashtags from text."""
    return re.findall(r'#\w+', text)


def parse_mentions(text: str) -> list[str]:
    """Parse mentions (@username) from text."""
    return re.findall(r'@\w+', text)


def parse_file_size(size_str: str) -> int | None:
    """Parse file size string (e.g., "10MB", "1.5GB") into bytes."""
    size_str = size_str.upper().strip()
    
    # Match pattern: number + unit
    match = re.match(r'^(\d+(?:\.\d+)?)\s*([KMGT]?B?)$', size_str)
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


def parse_duration(duration_str: str) -> float | None:
    """Parse duration string (e.g., "1h 30m", "45s", "2.5h") into seconds."""
    if not duration_str:
        return None
    
    # Convert to lowercase and remove spaces
    duration_str = duration_str.lower().replace(' ', '')
    
    # Pattern to match number + unit
    pattern = r'(\d+(?:\.\d+)?)([smhd])'
    matches = re.findall(pattern, duration_str)
    
    total_seconds = 0
    multipliers = {
        's': 1,
        'm': 60,
        'h': 3600,
        'd': 86400,
    }
    
    for number_str, unit in matches:
        number = float(number_str)
        total_seconds += number * multipliers[unit]
    
    return total_seconds if total_seconds > 0 else None


def parse_version(version_str: str) -> list[int]:
    """Parse version string (e.g., "1.2.3") into list of integers."""
    return [int(part) for part in version_str.split('.') if part.isdigit()]


def parse_ip_address(ip_str: str) -> dict[str, Any] | None:
    """Parse IP address and return information about it."""
    import ipaddress
    
    try:
        ip = ipaddress.ip_address(ip_str)
        return {
            "address": str(ip),
            "version": ip.version,
            "is_private": ip.is_private,
            "is_loopback": ip.is_loopback,
            "is_multicast": ip.is_multicast,
            "is_global": ip.is_global,
        }
    except ValueError:
        return None


def parse_user_agent(user_agent: str) -> dict[str, str]:
    """Parse user agent string."""
    # Simple parsing - in production would use proper UA parser
    result = {"raw": user_agent}
    
    # Detect browser
    browsers = ["Chrome", "Firefox", "Safari", "Edge", "Opera"]
    for browser in browsers:
        if browser in user_agent:
            result["browser"] = browser
            break
    
    # Detect OS
    os_patterns = [
        ("Windows", r"Windows NT [\d.]+"),
        ("macOS", r"Mac OS X [\d_]+"),
        ("Linux", r"Linux"),
        ("iOS", r"iPhone OS [\d_]+"),
        ("Android", r"Android [\d.]+"),
    ]
    
    for os_name, pattern in os_patterns:
        if re.search(pattern, user_agent):
            result["os"] = os_name
            break
    
    return result


def parse_boolean(value: str | int | bool) -> bool:
    """Parse various boolean representations."""
    if isinstance(value, bool):
        return value
    
    if isinstance(value, int):
        return bool(value)
    
    if isinstance(value, str):
        truthy_values = ["true", "1", "yes", "on", "enabled", "y"]
        falsy_values = ["false", "0", "no", "off", "disabled", "n"]
        
        value_lower = value.lower().strip()
        if value_lower in truthy_values:
            return True
        elif value_lower in falsy_values:
            return False
    
    return bool(value)
