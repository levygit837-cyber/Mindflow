"""Response parsing utilities for LLM providers.

Handles extraction and separation of thinking/text content from different LLM providers,
particularly Vertex AI which returns structured AIMessage objects.
"""

from typing import Any


def extract_ai_message_content(ai_message: Any, include_thinking: bool = False) -> dict[str, str]:
    """Extract and separate thinking/text content from AIMessage objects.
    
    Args:
        ai_message: Response object from LLM provider (AIMessage, string, etc.)
        include_thinking: Whether to include thinking content in result
        
    Returns:
        Dictionary with 'text' and optionally 'thinking' keys:
        {
            "text": "Final response text",
            "thinking": "Model reasoning (if include_thinking=True)"
        }
    """
    # Handle non-AIMessage objects (fallback to string conversion)
    if not hasattr(ai_message, 'content'):
        return {
            "text": str(ai_message),
            "thinking": ""
        }
    
    text_parts = []
    thinking_parts = []
    
    # Extract content from AIMessage structure
    content = ai_message.content
    if isinstance(content, list):
        for part in content:
            if isinstance(part, dict):
                if part.get('type') == 'text' and 'text' in part:
                    text_parts.append(part['text'])
                elif part.get('type') == 'thinking' and 'thinking' in part:
                    thinking_parts.append(part['thinking'])
            elif isinstance(part, str):
                # Direct string content
                text_parts.append(part)
    elif isinstance(content, str):
        # Simple string content
        text_parts.append(content)
    else:
        # Fallback for unexpected content types
        text_parts.append(str(content))
    
    result = {
        "text": " ".join(text_parts).strip()
    }
    
    if include_thinking:
        result["thinking"] = " ".join(thinking_parts).strip()
    
    return result


def extract_text_only(ai_message: Any) -> str:
    """Extract only the text content from an AI message.
    
    Args:
        ai_message: Response object from LLM provider
        
    Returns:
        Clean text string suitable for JSON parsing or processing
    """
    content = extract_ai_message_content(ai_message, include_thinking=False)
    return content["text"]


def extract_thinking_only(ai_message: Any) -> str:
    """Extract only the thinking content from an AI message.
    
    Args:
        ai_message: Response object from LLM provider
        
    Returns:
        Thinking/reasoning string for debugging or analysis
    """
    content = extract_ai_message_content(ai_message, include_thinking=True)
    return content["thinking"]


def has_thinking_content(ai_message: Any) -> bool:
    """Check if the AI message contains thinking content.
    
    Args:
        ai_message: Response object from LLM provider
        
    Returns:
        True if thinking content is present
    """
    if not hasattr(ai_message, 'content'):
        return False
    
    content = ai_message.content
    if isinstance(content, list):
        return any(
            isinstance(part, dict) and part.get('type') == 'thinking'
            for part in content
        )
    
    return False


def normalize_response_for_json(ai_message: Any) -> str:
    """Normalize AI message to string suitable for JSON parsing.
    
    This is particularly useful for components that expect plain string responses
    but receive structured AIMessage objects from Vertex AI.
    
    Args:
        ai_message: Response object from LLM provider
        
    Returns:
        Clean string that can be parsed as JSON
    """
    text = extract_text_only(ai_message)
    
    # Strip markdown JSON wrappers commonly used by LLMs
    if text.startswith('```json'):
        text = text[7:]  # Remove ```json
    elif text.startswith('```'):
        text = text[3:]   # Remove ```
    
    if text.endswith('```'):
        text = text[:-3]  # Remove trailing ```
    
    return text.strip()
