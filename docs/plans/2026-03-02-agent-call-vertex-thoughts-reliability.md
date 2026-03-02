# Agent Call + Vertex Thoughts Reliability Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Corrigir toda a cadeia de chamada de agentes (CLI/API/runtime/gRPC) para que o sistema sempre entregue `thoughts` e `mensagens` do modelo de forma confiável.

**Architecture:** A correção será guiada por TDD em camadas: contrato de payload (`AgentChatRequest`), bridge API↔runtime/gRPC, normalização de eventos de orquestração, extração de chunks Gemini (thinking/text), robustez de provider Vertex e validação live. O plano separa testes unitários, integração de stream SSE e smoke tests reais com Vertex AI para garantir que a parada só ocorre após receber `thoughts` e `messages` válidos.

**Tech Stack:** Python 3.13, FastAPI, Pydantic v2, LangChain, Vertex AI (Gemini), Typer CLI, pytest.

---

**Skills de execução recomendados:** @cpo-test-driven-development, @cpo-systematic-debugging, @cpo-verification-before-completion.

## Erros Confirmados na Exploração (chamada de agentes)
1. `python/omnimind_backend/api/v1/agent.py:33` chama `grpc_client.agent.stream_chat(...)`, mas o serviço expõe `StreamChat(...)`.
2. `python/omnimind_backend/grpc/proto/omnimind_backend.proto:5-10` não possui campos `orchestrate` e `agent_type`, enquanto `AgentRuntimeServiceImpl` tenta ler `request.orchestrate`.
3. `python/omnimind_backend/schemas/agent.py:15` define `agent_type` com alias apenas `agent`; payload com `agent_type` é ignorado.
4. `python/omnimind_backend/runtime/stream.py:470-471` usa `data[task]` e `data[status]` (keys sem aspas).
5. `python/omnimind_backend/runtime/stream.py:483` usa `chunk[name]` onde `name == "agent_tool_call"`, causando `KeyError`.
6. `python/omnimind_backend/orchestrator/complexity.py:72` aplica regex em `content` que pode vir como lista de blocos Gemini.
7. `python/omnimind_backend/runtime/stream.py` não extrai `thinking` quando chunk vem em `content=[{"type":"thinking",...}]`.
8. `python/omnimind_backend/runtime/providers.py` usa `ChatVertexAI` deprecado e repassa `api_key` com warning.
9. `python/omnimind_cli/client.py` encerra silenciosamente sem erro quando stream falha sem evento `done`.

---

### Task 1: Corrigir Contrato de Payload para Agent Calls

**Files:**
- Modify: `python/omnimind_backend/schemas/agent.py`
- Test: `python/tests/test_agent_request_schema.py`

**Step 1: Write the failing test**

```python
from omnimind_backend.schemas.agent import AgentChatRequest


def test_agent_request_accepts_agent_type_and_agent_alias() -> None:
    by_name = AgentChatRequest.model_validate({"message": "oi", "agent_type": "coder"})
    by_alias = AgentChatRequest.model_validate({"message": "oi", "agent": "coder"})
    assert by_name.agent_type == "coder"
    assert by_alias.agent_type == "coder"
```

**Step 2: Run test to verify it fails**

Run: `cd python && uv run pytest tests/test_agent_request_schema.py::test_agent_request_accepts_agent_type_and_agent_alias -v`
Expected: FAIL because `agent_type` is currently ignored.

**Step 3: Write minimal implementation**

```python
from pydantic import AliasChoices, ConfigDict, Field

class AgentChatRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    agent_type: str | None = Field(
        default=None,
        validation_alias=AliasChoices("agent_type", "agent"),
        serialization_alias="agent_type",
    )
```

**Step 4: Run test to verify it passes**

Run: `cd python && uv run pytest tests/test_agent_request_schema.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add python/omnimind_backend/schemas/agent.py python/tests/test_agent_request_schema.py
git commit -m "fix(schema): accept agent_type payload in agent chat requests"
```

---

### Task 2: Corrigir Bridge API → Runtime de Chat de Agentes

**Files:**
- Modify: `python/omnimind_backend/api/v1/agent.py`
- Modify: `python/omnimind_backend/grpc/client.py`
- Test: `python/tests/test_agent_stream_route.py`

**Step 1: Write the failing test**

```python
from fastapi.testclient import TestClient
from omnimind_backend.main import app


def test_stream_route_emits_response_and_done(monkeypatch):
    # mock InternalGrpcClient.stream_chat to emit thought/response/done
    client = TestClient(app)
    with client.stream("POST", "/v1/agent/chat/stream", json={"message": "oi"}) as resp:
        body = "".join(list(resp.iter_text()))
    assert "\"type\": \"response\"" in body
    assert "\"type\": \"done\"" in body
```

**Step 2: Run test to verify it fails**

Run: `cd python && uv run pytest tests/test_agent_stream_route.py::test_stream_route_emits_response_and_done -v`
Expected: FAIL with current `AttributeError` (`stream_chat` vs `StreamChat`).

**Step 3: Write minimal implementation**

```python
# grpc/client.py
class InternalGrpcClient:
    def __init__(self) -> None:
        self._service = AgentRuntimeServiceImpl()

    async def stream_chat(self, **kwargs):
        # call AgentRuntime directly (local fallback path)
        payload = AgentChatRequest(...)
        async for event in self._service.runtime.stream_chat(payload, kwargs["session_id"], run_id=kwargs.get("run_id")):
            yield event

# api/v1/agent.py
async for event in grpc_client.stream_chat(...):
    ...
```

**Step 4: Run test to verify it passes**

Run: `cd python && uv run pytest tests/test_agent_stream_route.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add python/omnimind_backend/api/v1/agent.py python/omnimind_backend/grpc/client.py python/tests/test_agent_stream_route.py
git commit -m "fix(api): restore agent stream bridge from route to runtime"
```

---

### Task 3: Alinhar Contrato gRPC da Chamada de Agentes

**Files:**
- Modify: `python/omnimind_backend/grpc/proto/omnimind_backend.proto`
- Modify: `python/omnimind_backend/grpc/services/agent_runtime_service.py`
- Modify: `python/omnimind_backend/grpc/generated/omnimind_backend_pb2.py`
- Modify: `python/omnimind_backend/grpc/generated/omnimind_backend_pb2_grpc.py`
- Test: `python/tests/test_grpc_agent_runtime_service.py`

**Step 1: Write the failing test**

```python
async def test_service_streamchat_handles_optional_fields_without_attribute_errors():
    request = SimpleNamespace(message="oi", provider="vertexai", model="gemini-3-flash-preview", session_id="s1", run_id="r1")
    svc = AgentRuntimeServiceImpl()
    events = [e async for e in svc.StreamChat(request, context=None)]
    assert events
```

**Step 2: Run test to verify it fails**

Run: `cd python && uv run pytest tests/test_grpc_agent_runtime_service.py::test_service_streamchat_handles_optional_fields_without_attribute_errors -v`
Expected: FAIL on `request.orchestrate` access.

**Step 3: Write minimal implementation**

```python
# proto: add fields
bool orchestrate = 6;
string agent_type = 7;
bool debug_steps = 8;

# service: safe attribute access
orchestrate=getattr(request, "orchestrate", False)
agent_type=getattr(request, "agent_type", None) or None
```

Regenerate bindings:

```bash
cd python
./scripts/gen_proto.sh
```

**Step 4: Run test to verify it passes**

Run: `cd python && uv run pytest tests/test_grpc_agent_runtime_service.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add python/omnimind_backend/grpc/proto/omnimind_backend.proto python/omnimind_backend/grpc/services/agent_runtime_service.py python/omnimind_backend/grpc/generated/omnimind_backend_pb2.py python/omnimind_backend/grpc/generated/omnimind_backend_pb2_grpc.py python/tests/test_grpc_agent_runtime_service.py
git commit -m "fix(grpc): align agent stream request contract with runtime payload"
```

---

### Task 4: Corrigir Eventos de Orquestração (`dt_step` e `agent_tool_call`)

**Files:**
- Modify: `python/omnimind_backend/runtime/stream.py`
- Test: `python/tests/test_runtime_orchestrated_events.py`

**Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_orchestrated_stream_maps_dt_step_and_tool_call_without_crashing(monkeypatch):
    # fake graph emits on_custom_event dt_step + agent_tool_call
    # assert stream has agent_step/thought and no error event
```

**Step 2: Run test to verify it fails**

Run: `cd python && uv run pytest tests/test_runtime_orchestrated_events.py::test_orchestrated_stream_maps_dt_step_and_tool_call_without_crashing -v`
Expected: FAIL (`NameError: task` or `KeyError: 'agent_tool_call'`).

**Step 3: Write minimal implementation**

```python
elif name == "dt_step":
    task_name = data.get("task", "unknown")
    status = data.get("status", "unknown")
    ... step_name=f"DT: {task_name}", detail=f"Status: {status}" ...

elif name == "agent_tool_call":
    chunk = data.get("chunk", {})
    tool_name = chunk.get("name")
    if tool_name:
        yield normalizer.thought_event(..., f"Calling tool: {tool_name}", ...)
```

**Step 4: Run test to verify it passes**

Run: `cd python && uv run pytest tests/test_runtime_orchestrated_events.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add python/omnimind_backend/runtime/stream.py python/tests/test_runtime_orchestrated_events.py
git commit -m "fix(stream): stabilize orchestrator custom event mapping"
```

---

### Task 5: Extrair `thoughts` e `messages` corretamente dos chunks Gemini

**Files:**
- Create: `python/omnimind_backend/runtime/chunk_extract.py`
- Modify: `python/omnimind_backend/runtime/stream.py`
- Modify: `python/omnimind_backend/orchestrator/complexity.py`
- Test: `python/tests/test_chunk_extract.py`
- Test: `python/tests/test_runtime_stream.py`

**Step 1: Write the failing test**

```python
def test_extract_chunk_parts_reads_thinking_and_text_from_list_content():
    chunk = DummyChunk(content=[
        {"type": "thinking", "thinking": "chain of thought"},
        {"type": "text", "text": "final answer"},
    ])
    thought, texts = extract_chunk_parts(chunk)
    assert "chain of thought" in thought
    assert texts == ["final answer"]
```

**Step 2: Run test to verify it fails**

Run: `cd python && uv run pytest tests/test_chunk_extract.py::test_extract_chunk_parts_reads_thinking_and_text_from_list_content -v`
Expected: FAIL because helper does not exist.

**Step 3: Write minimal implementation**

```python
def extract_chunk_parts(chunk) -> tuple[str, list[str]]:
    thought = ""
    texts: list[str] = []
    content = getattr(chunk, "content", None)
    if isinstance(content, list):
        for item in content:
            if item.get("type") in {"thinking", "thought"}:
                thought += item.get("thinking") or item.get("text") or ""
            elif item.get("type") == "text":
                texts.append(item.get("text", ""))
    ... # fallback metadata/additional_kwargs and str content
    return thought.strip(), [t for t in texts if t]
```

Use this helper in runtime stream paths and in `ComplexityScorer` before regex extraction.

**Step 4: Run test to verify it passes**

Run: `cd python && uv run pytest tests/test_chunk_extract.py tests/test_runtime_stream.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add python/omnimind_backend/runtime/chunk_extract.py python/omnimind_backend/runtime/stream.py python/omnimind_backend/orchestrator/complexity.py python/tests/test_chunk_extract.py python/tests/test_runtime_stream.py
git commit -m "fix(runtime): parse gemini thinking/text chunks consistently"
```

---

### Task 6: Hardening do Provider Vertex (depreciação + assinatura)

**Files:**
- Modify: `python/omnimind_backend/runtime/providers.py`
- Test: `python/tests/test_providers.py`

**Step 1: Write the failing test**

```python
def test_vertex_provider_uses_google_genai_vertex_mode(monkeypatch):
    captured = {}
    class FakeModel:
        def __init__(self, **kwargs):
            captured.update(kwargs)
    monkeypatch.setattr("omnimind_backend.runtime.providers.ChatGoogleGenerativeAI", FakeModel)
    providers.get_model_for_provider("vertexai", "gemini-3-flash-preview")
    assert captured["vertexai"] is True
    assert captured["model"] == "gemini-3-flash-preview"
```

**Step 2: Run test to verify it fails**

Run: `cd python && uv run pytest tests/test_providers.py::test_vertex_provider_uses_google_genai_vertex_mode -v`
Expected: FAIL because provider still uses `ChatVertexAI`.

**Step 3: Write minimal implementation**

```python
from langchain_google_genai import ChatGoogleGenerativeAI

return ChatGoogleGenerativeAI(
    model=model,
    vertexai=True,
    project=project_id,
    location=_vertex_location(model),
    include_thoughts=_is_thinking_supported(model),
    thinking_level="HIGH" if _is_thinking_supported(model) else None,
    google_api_key=google_api_key,
)
```

**Step 4: Run test to verify it passes**

Run: `cd python && uv run pytest tests/test_providers.py -v`
Expected: PASS with no `ChatVertexAI` deprecation warning path.

**Step 5: Commit**

```bash
git add python/omnimind_backend/runtime/providers.py python/tests/test_providers.py
git commit -m "refactor(vertex): migrate provider to google-genai vertex mode"
```

---

### Task 7: Falha de Stream deve quebrar CLI com erro explícito

**Files:**
- Modify: `python/omnimind_cli/client.py`
- Modify: `python/omnimind_cli/commands/chat.py`
- Test: `python/tests/test_cli_commands.py`

**Step 1: Write the failing test**

```python
def test_chat_command_fails_when_stream_has_no_done(monkeypatch):
    class DummyClient:
        def stream_chat(self, **kwargs):
            if False:
                yield
    monkeypatch.setattr("omnimind_cli.commands.chat.build_client", lambda _base_url: DummyClient())
    result = runner.invoke(app, ["chat", "--message", "oi"])
    assert result.exit_code == 1
    assert "no terminal done event" in result.output.lower()
```

**Step 2: Run test to verify it fails**

Run: `cd python && uv run pytest tests/test_cli_commands.py::test_chat_command_fails_when_stream_has_no_done -v`
Expected: FAIL because CLI currently exits `0` silently.

**Step 3: Write minimal implementation**

```python
# client.stream_chat or _stream_chat_once
seen_done = False
...
if event.type == "done":
    seen_done = True
...
if not seen_done:
    raise RuntimeError("No terminal done event in stream")
```

**Step 4: Run test to verify it passes**

Run: `cd python && uv run pytest tests/test_cli_commands.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add python/omnimind_cli/client.py python/omnimind_cli/commands/chat.py python/tests/test_cli_commands.py
git commit -m "fix(cli): fail fast when SSE stream terminates without done"
```

---

### Task 8: Testes Live de LLM (obrigatório para encerrar)

**Files:**
- Create: `python/tests/live/test_vertex_agent_stream_live.py`
- Create: `python/scripts/verify_vertex_stream.py`
- Modify: `python/README.md`

**Step 1: Write the failing live test**

```python
@pytest.mark.live
@pytest.mark.asyncio
async def test_live_vertex_stream_returns_model_thought_and_response():
    # call /v1/agent/chat/stream with {"agent_type":"coder","orchestrate":False}
    # assert at least one thought event from model and at least one response event
    # assert final done event
```

**Step 2: Run test to verify it fails**

Run: `cd python && RUN_LIVE_VERTEX_TESTS=1 uv run pytest tests/live/test_vertex_agent_stream_live.py -v -s`
Expected: FAIL until all previous tasks are fixed.

**Step 3: Write minimal implementation/support script**

```python
# scripts/verify_vertex_stream.py
# 1) start backend health check
# 2) send request
# 3) collect event types
# 4) print PASS only when thought>=1, response>=1, done==1
# 5) persist output in .logs/
```

**Step 4: Run live validation until PASS**

Run:
```bash
cd python
RUN_LIVE_VERTEX_TESTS=1 uv run pytest tests/live/test_vertex_agent_stream_live.py -v -s
uv run python scripts/verify_vertex_stream.py
```
Expected: PASS only when stream contains `thought` + `response` + `done` from end-to-end pipeline.

**Step 5: Commit**

```bash
git add python/tests/live/test_vertex_agent_stream_live.py python/scripts/verify_vertex_stream.py python/README.md
git commit -m "test(live): verify vertex agent stream returns thoughts and messages"
```

---

## Final Verification Gate (Do Not Skip)

Run full suite for touched areas:

```bash
cd python
uv run pytest tests/test_agent_request_schema.py \
  tests/test_agent_stream_route.py \
  tests/test_grpc_agent_runtime_service.py \
  tests/test_runtime_orchestrated_events.py \
  tests/test_chunk_extract.py \
  tests/test_runtime_stream.py \
  tests/test_providers.py \
  tests/test_cli_commands.py -v
```

Run live gate (mandatory):

```bash
cd python
RUN_LIVE_VERTEX_TESTS=1 uv run pytest tests/live/test_vertex_agent_stream_live.py -v -s
uv run python scripts/verify_vertex_stream.py
```

**Stop condition:** only stop planning/execution when the live gate proves `thoughts` and `messages` are both received correctly from the model, with terminal `done` event.
