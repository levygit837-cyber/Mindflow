---
wave: 1
---
# Phase 5 Plan: Gemini Integration & DX (Developer Experience)

**Goal:** Fix the frontend message flow, integrate Gemini 3/2.0 with Vertex AI API keys, and normalize Gemini streaming/tool usage while enhancing observability.

## 5.1 — Model & Auth Integration
- [ ] **Task 5.1.1:** Update `omnimind_backend/runtime/providers.py` to use `ChatVertexAI` from `langchain-google-vertexai` for the `vertexai` provider.
- [ ] **Task 5.1.2:** Support `GOOGLE_API_KEY` with `ChatVertexAI` for Vertex AI provider.
- [ ] **Task 5.1.3:** Set `gemini-3-flash-preview` as the default model in `schemas/settings.py` and `infra/config.py`.
- [ ] **Task 5.1.4:** Map `gemini-3-flash-preview` to the appropriate Vertex AI model string if necessary.

## 5.2 — LangGraph Streaming & Normalization
- [ ] **Task 5.2.1:** Refactor `omnimind_backend/runtime/stream.py` to use `self._orchestrator_graph.astream_events(version="v2")` instead of `ainvoke`.
- [ ] **Task 5.2.2:** Update `AgentChatStreamNormalizer` to handle Gemini-specific event structures (e.g., `thinking` blocks).
- [ ] **Task 5.2.3:** Normalize `tool_call` and `tool_result` events for Gemini models.
- [ ] **Task 5.2.4:** Ensure `AgentRuntime` correctly yields events as they are received from the graph.

## 5.3 — Observability & Logs
- [ ] **Task 5.3.1:** Add structured log statements in `orchestrator/graph.py` for message routing, model execution, and tool calls.
- [ ] **Task 5.3.2:** Log incoming chat requests in `api/v1/agent.py` and `grpc/services/agent_runtime_service.py`.
- [ ] **Task 5.3.3:** Modify `start_dev.sh` to optionally tail logs or show them in the foreground during development.
- [ ] **Task 5.3.4:** Ensure `LOG_FORMAT=console` is active for dev environments to show colorized, structured logs.

## 5.4 — Validation & Testing
- [ ] **Task 5.4.1:** Verify frontend message flow (input should not disappear without a response).
- [ ] **Task 5.4.2:** Test Vertex AI API key authentication with a sample Gemini model.
- [ ] **Task 5.4.3:** Verify streaming of thinking blocks and tool calls in the frontend.
- [ ] **Task 5.4.4:** Run the full project test suite to ensure no regressions in orchestrator logic.

## Success Criteria
- [x] Frontend message flow is responsive and shows real-time updates.
- [x] Gemini models work via Vertex AI with API key authentication.
- [x] "Thinking" blocks and tool usage are normalized and visible in logs/UI.
- [x] `start_dev.sh` provides clear visibility into backend actions.
