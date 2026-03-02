# Phase 5 Research: Gemini Integration & DX (Developer Experience)

## 1. Vertex AI via API Key with LangGraph

Google Cloud now supports using API keys with Vertex AI. This allows easier integration without full IAM/Service Account setup in some environments.

### LangChain Implementation
The `langchain-google-vertexai` package (v2.0.0+) supports `api_key`.
```python
from langchain_google_vertexai import ChatVertexAI

llm = ChatVertexAI(
    model="gemini-1.5-flash", # or gemini-2.0-flash-exp
    api_key="YOUR_VERTEX_API_KEY",
    project="YOUR_PROJECT_ID",
    location="us-central1"
)
```

### Integration in OmniMind
We need to update `omnimind_backend/runtime/providers.py` to:
- Use `ChatVertexAI` for the `vertexai` provider.
- Correctly handle `GOOGLE_API_KEY` when the provider is `vertexai`.
- Support `gemini-3-flash-preview` (as requested by the user) by mapping it to the correct Vertex AI model string if it's a custom alias, or ensuring the location is set to "global" if applicable.

## 2. Gemini Streaming & Tool Normalization

Gemini models (especially Gemini 2.0) introduce `thinking` blocks and have specific tool call formats.

### Streaming Normalization
- **Thinking Blocks**: Gemini 2.0 Flash/Pro returns thinking content in separate parts. We must capture these and emit `thought` events via SSE.
- **LangGraph Events**: Using `graph.astream_events(version="v2")` is the best way to capture fine-grained events from nodes and LLM calls.

### Tool Normalization
- Gemini's `tool_calls` might differ from OpenAI's in terms of naming or argument serialization.
- We should ensure `llm.bind_tools(tools)` works consistently across providers.
- Normalize the `tool_call` and `tool_result` SSE events so the frontend can render them uniformly regardless of the underlying model.

## 3. Frontend Message Issue Diagnosis

**Cause**: The `AgentRuntime._stream_chat_orchestrated` method uses `self._orchestrator_graph.ainvoke(graph_input)`.
**Effect**: `ainvoke` is an atomic call. It waits for the entire graph (routing, execution, response formatting) to finish before returning the final state. During this time, the SSE stream remains open but silent.
**Fix**: Refactor to use `astream_events`. This will allow emitting `thought`, `tool_call`, and `response` events as they happen within the graph nodes.

## 4. Structured Logs in `start_dev.sh`

The user wants to see "actions, message sending, return of messages" in the logs.

### Backend Logging Improvements
- Add `_logger.info("llm_call_started", ...)` and `_logger.info("llm_call_completed", ...)` in `execute_node`.
- Log tool execution start/end in the tool registry or nodes.
- Log incoming chat requests in the FastAPI route and gRPC service.

### `start_dev.sh` Enhancement
- Use `tail -f` to multiplex logs into the main terminal, or provide a command to view combined logs.
- Ensure `LOG_FORMAT=console` is set by default in dev to leverage `structlog`'s `ConsoleRenderer` for readability.
