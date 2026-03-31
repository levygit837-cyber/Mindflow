"""Data sanitization utilities for MindFlow backend.

Functions to clean and sanitize user input and data.
"""

import re
from typing import Any


def sanitize_input(text: str) -> str:
    """Sanitize input text by removing potentially harmful content."""
    if not text:
        return ""
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove potentially harmful characters
    text = re.sub(r'[<>"\'\&]', '', text)
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def sanitize_html(text: str) -> str:
    """Sanitize HTML content by removing dangerous tags and attributes."""
    if not text:
        return ""
    
    # Remove script tags
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    
    # Remove dangerous attributes
    text = re.sub(r'on\w+\s*=\s*["\'][^"\']*["\']', '', text, flags=re.IGNORECASE)
    
    # Remove javascript: URLs
    text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
    
    return text


def sanitize_filename(filename: str) -> str:
    """Sanitize filename by removing dangerous characters."""
    if not filename:
        return ""
    
    # Remove path traversal characters
    filename = filename.replace('..', '').replace('/', '').replace('\\', '')
    
    # Remove dangerous characters
    filename = re.sub(r'[<>:"|?*]', '', filename)
    
    # Remove control characters
    filename = re.sub(r'[\x00-\x1f\x7f]', '', filename)
    
    # Limit length
    if len(filename) > 255:
        filename = filename[:255]
    
    return filename.strip()


def sanitize_json_data(data: Any, path: str = "") -> list[str]:
    """Recursively sanitize JSON data and return list of issues found."""
    issues = []
    
    if isinstance(data, dict):
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key
            if isinstance(key, str) and any(char in key for char in ['<', '>', '"', "'", '&']):
                issues.append(f"Potentially unsafe key at {current_path}")
            
            issues.extend(sanitize_json_data(value, current_path))
    
    elif isinstance(data, list):
        for i, item in enumerate(data):
            current_path = f"{path}[{i}]" if path else f"[{i}]"
            issues.extend(sanitize_json_data(item, current_path))
    
    elif isinstance(data, str):
        if any(pattern in data.lower() for pattern in [
            '<script', 'javascript:', 'vbscript:', 'onload=', 'onerror=', 'onclick='
        ]):
            issues.append(f"Potentially unsafe content at {path}")
    
    return issues


def sanitize_sql_input(text: str) -> str:
    """Sanitize SQL input to prevent injection."""
    if not text:
        return ""
    
    # Remove SQL injection patterns
    dangerous_patterns = [
        r'union\s+select',
        r'drop\s+table',
        r'insert\s+into',
        r'delete\s+from',
        r';\s*(drop|alter|truncate|exec)',
        r'--',
        r'/\*.*\*/',
    ]
    
    for pattern in dangerous_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    return text.strip()


def sanitize_phone_number(phone: str) -> str:
    """Sanitize phone number by keeping only digits and + symbol."""
    if not phone:
        return ""
    
    # Keep only digits and + at the beginning
    phone = re.sub(r'[^\d+]', '', phone)
    
    # Ensure + is only at the beginning
    if '+' in phone[1:]:
        phone = '+' + phone.replace('+', '')
    
    return phone


def sanitize_url(url: str) -> str:
    """Sanitize URL by removing dangerous components."""
    if not url:
        return ""
    
    # Remove javascript: and data: URLs
    url = re.sub(r'^(javascript|data|vbscript):', '', url, flags=re.IGNORECASE)
    
    # Ensure URL starts with http:// or https://
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    return url


def limit_string_length(text: str, max_length: int = 1000) -> str:
    """Limit string length and add ellipsis if truncated."""
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - 3] + "..."


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace in text."""
    if not text:
        return ""
    
    # Replace multiple whitespace with single space
    text = re.sub(r'\s+', ' ', text)
    
    # Trim leading and trailing whitespace
    return text.strip()


def extract_safe_filename(filename: str) -> str:
    """Extract safe filename from potentially dangerous input."""
    if not filename:
        return "unnamed"
    
    # Get filename without path
    filename = filename.split('/')[-1].split('\\')[-1]
    
    # Remove extension if dangerous
    dangerous_exts = ['.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js']
    for ext in dangerous_exts:
        if filename.lower().endswith(ext):
            filename = filename[:-len(ext)] + '.txt'
    
    return sanitize_filename(filename) or "unnamed"
