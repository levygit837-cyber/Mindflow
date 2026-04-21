from __future__ import annotations

from typing import Any

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def _get_value(obj: Any, key: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def extract_chunk_parts(chunk: Any) -> tuple[str, list[str]]:
    """Extract thought text and visible text parts from model chunks/responses."""
    thought_parts: list[str] = []
    text_parts: list[str] = []

    content = _get_value(chunk, "content")
    if isinstance(content, str):
        text = content.strip()
        if text:
            text_parts.append(text)
    elif isinstance(content, list):
        for item in content:
            item_type = _as_text(_get_value(item, "type")).lower()
            if item_type in {"thinking", "thought"}:
                thought = _as_text(_get_value(item, "thinking")) or _as_text(_get_value(item, "text"))
                if thought.strip():
                    thought_parts.append(thought.strip())
                    _logger.debug("chunk_extract_thinking", thought_length=len(thought))
            elif item_type == "text":
                text = _as_text(_get_value(item, "text"))
                if text.strip():
                    text_parts.append(text.strip())
            elif isinstance(item, str):
                text = item.strip()
                if text:
                    text_parts.append(text)
    elif content is not None:
        text = _as_text(content).strip()
        if text:
            text_parts.append(text)

    response_metadata = _get_value(chunk, "response_metadata")
    if isinstance(response_metadata, dict):
        thought = _as_text(response_metadata.get("thought") or response_metadata.get("thinking"))
        if thought.strip():
            thought_parts.append(thought.strip())
            _logger.debug("chunk_extract_response_metadata_thinking", thought_length=len(thought))

    additional_kwargs = _get_value(chunk, "additional_kwargs")
    if isinstance(additional_kwargs, dict):
        thought = _as_text(additional_kwargs.get("thought") or additional_kwargs.get("thinking"))
        if thought.strip():
            thought_parts.append(thought.strip())
            _logger.debug("chunk_extract_additional_kwargs_thinking", thought_length=len(thought))

    unique_thoughts = [t for i, t in enumerate(thought_parts) if t and t not in thought_parts[:i]]
    result_thought = "\n".join(unique_thoughts).strip()
    
    if result_thought:
        _logger.debug("chunk_extract_result", thought_length=len(result_thought))
    
    return result_thought, [t for t in text_parts if t]
