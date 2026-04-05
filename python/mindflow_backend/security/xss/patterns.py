"""XSS attack patterns for detection and sanitization."""

import re
from typing import Pattern


# Script tag patterns
SCRIPT_TAG_PATTERNS = [
    r"<script[^>]*>.*?</script>",
    r"<script[^>]*>",
    r"</script>",
    r"javascript:",
    r"on\w+\s*=",
]

# HTML entity patterns
HTML_ENTITY_PATTERNS = [
    r"&lt;",
    r"&gt;",
    r"&amp;",
    r"&quot;",
    r"&apos;",
    r"&#x[0-9a-fA-F]+;",
    r"&#\d+;",
]

# Event handler patterns
EVENT_HANDLER_PATTERNS = [
    r"onerror\s*=",
    r"onload\s*=",
    r"onclick\s*=",
    r"onmouseover\s*=",
    r"onfocus\s*=",
    r"onblur\s*=",
]

# Data URI patterns
DATA_URI_PATTERNS = [
    r"data:text/html",
    r"data:application/javascript",
    r"data:image/svg\+xml",
]

# Combined XSS patterns
XSS_PATTERNS: list[Pattern] = [
    re.compile(pattern, re.IGNORECASE | re.DOTALL)
    for pattern in SCRIPT_TAG_PATTERNS + HTML_ENTITY_PATTERNS + EVENT_HANDLER_PATTERNS + DATA_URI_PATTERNS
]

# Whitelist of safe characters for plain text
SAFE_CHARS = re.compile(r"[a-zA-Z0-9\s.,;:!?\-_/]")

# HTML5 safe tags (tags that don't execute scripts)
SAFE_HTML_TAGS = {
    "div", "span", "p", "br", "hr", "h1", "h2", "h3", "h4", "h5", "h6",
    "strong", "em", "u", "b", "i", "code", "pre", "blockquote",
    "ul", "ol", "li", "dl", "dt", "dd",
    "table", "thead", "tbody", "tr", "th", "td",
    "a", "img", "figure", "figcaption",
}

# Safe HTML attributes (attributes that don't execute scripts)
SAFE_HTML_ATTRIBUTES = {
    "class", "id", "style", "href", "src", "alt", "title", "rel",
    "width", "height", "target",
}


def contains_xss(text: str) -> bool:
    """Check if text contains XSS patterns.

    Args:
        text: Text to check

    Returns:
        True if XSS patterns detected, False otherwise
    """
    for pattern in XSS_PATTERNS:
        if pattern.search(text):
            return True
    return False


def extract_xss_patterns(text: str) -> list[str]:
    """Extract XSS patterns from text.

    Args:
        text: Text to scan

    Returns:
        List of matched XSS patterns
    """
    matches = []
    for pattern in XSS_PATTERNS:
        for match in pattern.finditer(text):
            matches.append(match.group())
    return matches
