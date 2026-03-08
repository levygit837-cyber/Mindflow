"""String manipulation utilities for MindFlow backend.

Functions for formatting, parsing, and manipulating strings.
"""

import math
import re
import unicodedata
from typing import List, Optional, Union


def slugify(text: str) -> str:
    """Convert string to slug format."""
    # Normalize unicode characters
    text = unicodedata.normalize('NFKD', text)
    
    # Remove non-alphanumeric characters
    text = re.sub(r'[^\w\s-]', '', text)
    
    # Replace spaces and underscores with hyphens
    text = re.sub(r'[\s_]+', '-', text)
    
    # Remove multiple consecutive hyphens
    text = re.sub(r'-+', '-', text)
    
    # Remove leading/trailing hyphens
    text = text.strip('-')
    
    # Convert to lowercase
    return text.lower()


def truncate(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate string to maximum length."""
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def truncate_words(text: str, max_words: int, suffix: str = "...") -> str:
    """Truncate string to maximum number of words."""
    words = text.split()
    if len(words) <= max_words:
        return text
    
    return ' '.join(words[:max_words]) + suffix


def camel_case(text: str) -> str:
    """Convert string to camelCase."""
    # Remove non-alphanumeric characters and split by them
    words = re.split(r'[^a-zA-Z0-9]+', text)
    
    # Filter out empty strings and capitalize words except first
    words = [word for word in words if word]
    if not words:
        return ""
    
    first_word = words[0].lower()
    other_words = [word.capitalize() for word in words[1:]]
    
    return first_word + ''.join(other_words)


def pascal_case(text: str) -> str:
    """Convert string to PascalCase."""
    # Remove non-alphanumeric characters and split by them
    words = re.split(r'[^a-zA-Z0-9]+', text)
    
    # Filter out empty strings and capitalize all words
    words = [word.capitalize() for word in words if word]
    
    return ''.join(words)


def snake_case(text: str) -> str:
    """Convert string to snake_case."""
    # Convert camelCase and PascalCase to snake_case
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', text)
    s2 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1)
    
    # Replace non-alphanumeric characters with underscores
    s2 = re.sub(r'[^a-zA-Z0-9]+', '_', s2)
    
    # Convert to lowercase and remove multiple underscores
    s2 = re.sub(r'_+', '_', s2.lower())
    
    # Remove leading/trailing underscores
    return s2.strip('_')


def kebab_case(text: str) -> str:
    """Convert string to kebab-case."""
    # Convert to snake_case first
    snake = snake_case(text)
    
    # Replace underscores with hyphens
    return snake.replace('_', '-')


def title_case(text: str) -> str:
    """Convert string to title case."""
    return ' '.join(word.capitalize() for word in text.split())


def sentence_case(text: str) -> str:
    """Convert string to sentence case."""
    if not text:
        return text
    
    # Capitalize first letter and lowercase the rest
    return text[0].upper() + text[1:].lower()


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace in string."""
    # Replace all whitespace characters with single space
    text = re.sub(r'\s+', ' ', text)
    
    # Trim leading and trailing whitespace
    return text.strip()


def remove_html_tags(text: str) -> str:
    """Remove HTML tags from string."""
    # Remove script and style tags with content
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove HTML comments
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
    
    # Remove remaining HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    return text


def extract_text_from_html(html: str) -> str:
    """Extract plain text from HTML."""
    text = remove_html_tags(html)
    return normalize_whitespace(text)


def escape_html(text: str) -> str:
    """Escape HTML special characters."""
    html_escape_table = {
        "&": "&amp;",
        '"': "&quot;",
        "'": "&#x27;",
        ">": "&gt;",
        "<": "&lt;",
    }
    
    return "".join(html_escape_table.get(c, c) for c in text)


def unescape_html(text: str) -> str:
    """Unescape HTML special characters."""
    html_unescape_table = {
        "&amp;": "&",
        "&quot;": '"',
        "&#x27;": "'",
        "&gt;": ">",
        "&lt;": "<",
    }
    
    for entity, char in html_unescape_table.items():
        text = text.replace(entity, char)
    
    return text


def is_empty(text: Optional[str]) -> bool:
    """Check if string is empty or None."""
    return text is None or text.strip() == ""


def is_blank(text: Optional[str]) -> bool:
    """Check if string is blank (empty or only whitespace)."""
    return text is None or text.strip() == ""


def default_if_empty(text: Optional[str], default: str = "") -> str:
    """Return default value if string is empty."""
    return default if is_empty(text) else text


def default_if_blank(text: Optional[str], default: str = "") -> str:
    """Return default value if string is blank."""
    return default if is_blank(text) else text


def strip_prefix(text: str, prefix: str) -> str:
    """Remove prefix from string if present."""
    return text[len(prefix):] if text.startswith(prefix) else text


def strip_suffix(text: str, suffix: str) -> str:
    """Remove suffix from string if present."""
    return text[:-len(suffix)] if text.endswith(suffix) else text


def wrap_text(text: str, width: int = 80, indent: str = "") -> str:
    """Wrap text to specified width with optional indentation."""
    lines = []
    words = text.split()
    current_line = []
    current_length = len(indent)
    
    for word in words:
        if current_length + len(word) + (1 if current_line else 0) <= width:
            current_line.append(word)
            current_length += len(word) + (1 if current_line else 0)
        else:
            if current_line:
                lines.append(indent + ' '.join(current_line))
                current_line = [word]
                current_length = len(indent) + len(word)
            else:
                # Word is too long, add it anyway
                lines.append(indent + word)
                current_line = []
                current_length = len(indent)
    
    if current_line:
        lines.append(indent + ' '.join(current_line))
    
    return '\n'.join(lines)


def indent_text(text: str, indent: str, include_blank_lines: bool = False) -> str:
    """Indent all lines in text."""
    lines = text.split('\n')
    
    if include_blank_lines:
        return '\n'.join(indent + line for line in lines)
    else:
        return '\n'.join(indent + line if line.strip() else line for line in lines)


def dedent_text(text: str) -> str:
    """Remove common leading whitespace from all lines."""
    lines = text.split('\n')
    
    # Find minimum indentation (excluding empty lines)
    non_empty_lines = [line for line in lines if line.strip()]
    if not non_empty_lines:
        return text
    
    min_indent = min(len(line) - len(line.lstrip()) for line in non_empty_lines)
    
    # Remove that much indentation from all lines
    dedented_lines = [line[min_indent:] if len(line) >= min_indent else line for line in lines]
    
    return '\n'.join(dedented_lines)


def count_words(text: str) -> int:
    """Count words in text."""
    # Split on whitespace and filter out empty strings
    words = re.findall(r'\b\w+\b', text)
    return len(words)


def count_characters(text: str, include_spaces: bool = True) -> int:
    """Count characters in text."""
    if include_spaces:
        return len(text)
    else:
        return len(re.sub(r'\s', '', text))


def count_lines(text: str) -> int:
    """Count lines in text."""
    return len(text.split('\n'))


def find_words(text: str, min_length: int = 1) -> List[str]:
    """Find all words in text."""
    return re.findall(r'\b\w+\b', text)


def find_emails(text: str) -> List[str]:
    """Find all email addresses in text."""
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    return re.findall(email_pattern, text)


def find_urls(text: str) -> List[str]:
    """Find all URLs in text."""
    url_pattern = r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:\w*))?)?'
    return re.findall(url_pattern, text)


def find_phone_numbers(text: str) -> List[str]:
    """Find all phone numbers in text."""
    phone_patterns = [
        r'\+?1?[-.\s]?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})',  # US format
        r'\+?[\d\s\-\(\)]{10,}',  # General international format
    ]
    
    numbers = []
    for pattern in phone_patterns:
        matches = re.findall(pattern, text)
        numbers.extend(matches)
    
    return numbers


def mask_string(text: str, mask_char: str = "*", visible_chars: int = 4) -> str:
    """Mask string showing only first and last few characters."""
    if len(text) <= visible_chars:
        return text
    
    visible_start = visible_chars // 2
    visible_end = visible_chars - visible_start
    
    masked_middle = mask_char * (len(text) - visible_start - visible_end)
    
    return text[:visible_start] + masked_middle + text[-visible_end:]


def mask_email(email: str) -> str:
    """Mask email address."""
    if '@' not in email:
        return mask_string(email)
    
    local, domain = email.split('@', 1)
    
    if len(local) <= 2:
        masked_local = mask_string(local, "*", 1)
    else:
        masked_local = local[0] + mask_string(local[1:-1], "*") + local[-1]
    
    return f"{masked_local}@{domain}"


def mask_phone(phone: str) -> str:
    """Mask phone number."""
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)
    
    if len(digits) <= 4:
        return mask_string(phone, "*", 2)
    
    # Show last 4 digits
    return mask_string(phone, "*", len(phone) - 4)


def generate_random_string(length: int, chars: str = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789") -> str:
    """Generate random string."""
    import random
    return ''.join(random.choice(chars) for _ in range(length))


def generate_hex_string(length: int) -> str:
    """Generate random hexadecimal string."""
    return generate_random_string(length, "0123456789abcdef")


def is_palindrome(text: str) -> bool:
    """Check if string is a palindrome."""
    # Remove non-alphanumeric characters and convert to lowercase
    cleaned = re.sub(r'[^a-zA-Z0-9]', '', text.lower())
    return cleaned == cleaned[::-1]


def reverse_string(text: str) -> str:
    """Reverse string."""
    return text[::-1]


def shuffle_string(text: str) -> str:
    """Shuffle characters in string."""
    import random
    chars = list(text)
    random.shuffle(chars)
    return ''.join(chars)


def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]


def similarity_ratio(s1: str, s2: str) -> float:
    """Calculate similarity ratio between two strings (0-1)."""
    distance = levenshtein_distance(s1, s2)
    max_len = max(len(s1), len(s2))
    
    if max_len == 0:
        return 1.0
    
    return 1.0 - (distance / max_len)


def fuzzy_match(text: str, pattern: str, threshold: float = 0.8) -> bool:
    """Check if text fuzzy matches pattern."""
    ratio = similarity_ratio(text.lower(), pattern.lower())
    return ratio >= threshold


def extract_numbers(text: str) -> List[float]:
    """Extract all numbers from text."""
    numbers = []
    
    # Find integers and decimals
    matches = re.findall(r'-?\d+\.?\d*', text)
    
    for match in matches:
        try:
            if '.' in match:
                numbers.append(float(match))
            else:
                numbers.append(int(match))
        except ValueError:
            continue
    
    return numbers


def format_number(number: Union[int, float], decimals: int = 2) -> str:
    """Format number with thousands separator and decimals."""
    if isinstance(number, int):
        return f"{number:,}"
    else:
        return f"{number:,.{decimals}f}"


def pluralize(count: int, singular: str, plural: Optional[str] = None) -> str:
    """Return singular or plural form based on count."""
    if count == 1:
        return singular
    else:
        return plural or (singular + 's')


def ordinal(number: int) -> str:
    """Convert number to ordinal string (1st, 2nd, 3rd, etc.)."""
    if 11 <= number % 100 <= 13:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(number % 10, 'th')
    
    return f"{number}{suffix}"


def estimate_token_count(text: str) -> int:
    """Fast token estimate (~4 chars per token)."""
    if not text:
        return 0
    return max(1, math.ceil(len(text) / 4))
