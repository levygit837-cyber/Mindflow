# Vertex AI Gemini Integration and CLI Enhancements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fully integrate Vertex AI Gemini models with proper thinking/reasoning extraction and enhance the CLI to properly differentiate model messages and handle Vertex-specific outputs.

**Architecture:** 
1. Refactor `providers.py` to use `ChatVertexAI` from `langchain-google-vertexai` for the `vertexai` provider.
2. Update `AgentRuntime` to normalize Gemini outputs (thinking/content/tools).
3. Enhance `ChatStreamRenderer` in the CLI to ensure proper message separation and display.

**Tech Stack:** 
- langchain-google-vertexai
- langchain-google-genai
- rich (CLI rendering)
- FastAPI (backend)

---

### Task 1: Refactor Vertex AI Provider

**Files:**
- Modify: `python/omnimind_backend/runtime/providers.py`

**Step 1: Update imports and `_build_vertex_service_account_model`**
Switch from `ChatGoogleGenerativeAI` to `ChatVertexAI`.

```python
def _build_vertex_service_account_model(*, model: str, project_id: str | None):
    from langchain_google_vertexai import ChatVertexAI

    kwargs: dict[str, Any] = {
        "model_name": model,
        "location": _vertex_location(model),
    }
    if project_id:
        kwargs["project"] = project_id
        
    if _is_thinking_supported(model):
        kwargs["thinking_config"] = {"include_thoughts": True, "include_thoughts": True} # include_thoughts is often a direct param too
        # Update: ChatVertexAI has specific params for thinking in newer versions
        # We will use model_kwargs as fallback if direct params aren't available
        kwargs["include_thoughts"] = True
        
    return ChatVertexAI(**kwargs)
```

**Step 2: Update `_build_vertex_api_key_model`**
Vertex AI API key support is via `api_key` param in `ChatVertexAI`.

```python
def _build_vertex_api_key_model(*, model: str, api_key: str, project_id: str | None):
    from langchain_google_vertexai import ChatVertexAI

    kwargs: dict[str, Any] = {
        "model_name": model,
        "api_key": api_key,
        "location": _vertex_location(model),
    }
    if project_id:
        kwargs["project"] = project_id
    if _is_thinking_supported(model):
        kwargs["include_thoughts"] = True
        
    return ChatVertexAI(**kwargs)
```

**Step 3: Commit changes**

---

### Task 2: Normalize Gemini Outputs in AgentRuntime

**Files:**
- Modify: `python/omnimind_backend/runtime/stream.py`

**Step 1: Enhance `_stream_chat_direct_agent` thinking extraction**
Gemini 2.0/3.0 might return thoughts in different fields.

```python
                # Capture thoughts (Gemini)
                thought = ""
                if hasattr(chunk, "response_metadata"):
                    metadata = chunk.response_metadata
                    if "thought" in metadata:
                        thought = metadata["thought"]
                
                # Check additional_kwargs
                if not thought and hasattr(chunk, "additional_kwargs"):
                    thought = chunk.additional_kwargs.get("thought", "")
                
                # Check for thinking blocks in content if thinking enabled
                if not thought and isinstance(chunk.content, list):
                    for item in chunk.content:
                        if isinstance(item, dict) and item.get("type") == "thought":
                            thought = item.get("text", "")
```

**Step 2: Commit changes**

---

### Task 3: Enhance CLI Rendering

**Files:**
- Modify: `python/omnimind_cli/render/chat_stream.py`
- Modify: `python/omnimind_cli/commands/chat.py`

**Step 1: Fix `_render_response` in `chat_stream.py` to ensure newline**
Ensure it prints a newline if it's the first chunk of a response to separate from the "You:" prompt.

```python
    def _render_response(self, event: StreamEvent) -> None:
        if not self._response_open:
            # ...
            self.console.print() # Ensure we start on a new line
            self.console.print(Text.assemble(...))
```

**Step 2: Update theme to distinguish roles**
Ensure "agent" style is clearly different from user input.

**Step 3: Commit changes**

---

### Task 4: Verify with Test Script

**Files:**
- Create: `python/scripts/test_vertex_integration.py`

**Step 1: Write verification script**
Mock or use real credentials to verify the flow from provider to normalizer to CLI renderer.

**Step 2: Run verification**
`python python/scripts/test_vertex_integration.py`

**Step 3: Commit changes**
