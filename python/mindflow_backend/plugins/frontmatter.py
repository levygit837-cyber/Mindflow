"""Utilities for parsing markdown files with YAML frontmatter."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def parse_markdown_file(file_path: Path) -> tuple[dict[str, Any], str]:
    """Parse a markdown file that may contain YAML frontmatter."""
    content = file_path.read_text(encoding="utf-8")
    return parse_markdown_content(content)


def parse_markdown_content(content: str) -> tuple[dict[str, Any], str]:
    """Parse raw markdown content with optional YAML frontmatter."""
    frontmatter: dict[str, Any] = {}
    body = content.strip()

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            parsed = yaml.safe_load(parts[1]) or {}
            if isinstance(parsed, dict):
                frontmatter = parsed
            body = parts[2].strip()

    return frontmatter, body


def normalize_string_list(value: Any) -> list[str]:
    """Normalize frontmatter string-or-list fields to a list of strings."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        if "," in value:
            parts = value.split(",")
        else:
            parts = value.split()
        return [part.strip() for part in parts if part.strip()]
    return [str(value).strip()]
