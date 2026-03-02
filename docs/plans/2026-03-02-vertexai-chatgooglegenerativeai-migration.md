# VertexAI -> ChatGoogleGenerativeAI (Gemini) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrar todo uso de `ChatVertexAI` para `ChatGoogleGenerativeAI` no provider `vertexai`, com suporte obrigatório a `vertexai=true`, `GOOGLE_GENAI_USE_VERTEXAI=true`, `project`, `location=global` para Gemini 3+, `include_thoughts=true`, `thinking_level` (`LOW|HIGH`) e captura de `reasoning_tokens`.

**Architecture:** O ponto único de criação de LLM continuará em `python/omnimind_backend/runtime/providers.py`, mas a construção do provider `vertexai` será feita exclusivamente com `langchain_google_genai`. O `thinking_level` será propagado desde os agentes/orquestrador para o provider, com normalização para `LOW|HIGH` para modelos Gemini. O streaming (`runtime/stream.py`) e a execução orquestrada (`orchestrator/graph.py`) passarão a extrair e emitir metadados de reasoning a partir de `usage_metadata`.

**Tech Stack:** Python 3.11, LangChain, `langchain-google-genai>=3.1.0`, FastAPI, pytest, uv.

**Related Skills:** @cpo-test-driven-development, @cpo-verification-before-completion, @cpo-systematic-debugging

---

### Task 1: Travar Dependência Mínima e Preparar Lock

**Files:**
- Modify: `python/tests/test_providers.py:1-120`
- Modify: `python/pyproject.toml:16-17`
- Modify: `python/uv.lock` (gerado automaticamente)

**Step 1: Write the failing test**

Adicionar um teste de guarda de versão em `python/tests/test_providers.py`:

```python
from pathlib import Path


def test_pyproject_requires_langchain_google_genai_3_1_plus() -> None:
    pyproject = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    assert 'langchain-google-genai>=3.1.0' in pyproject
```

**Step 2: Run test to verify it fails**

Run: `cd python && uv run pytest tests/test_providers.py::test_pyproject_requires_langchain_google_genai_3_1_plus -v`
Expected: FAIL because `pyproject.toml` currently has `langchain-google-genai>=2.0.0`.

**Step 3: Write minimal implementation**

Atualizar dependências:

```toml
# python/pyproject.toml
"langchain-google-genai>=3.1.0",
# remover dependência legada se não houver uso após migração:
# "langchain-google-vertexai>=2.0.0",
```

Atualizar lock:

Run: `cd python && uv lock`

**Step 4: Run test to verify it passes**

Run: `cd python && uv run pytest tests/test_providers.py::test_pyproject_requires_langchain_google_genai_3_1_plus -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add python/tests/test_providers.py python/pyproject.toml python/uv.lock
git commit -m "build: require langchain-google-genai >=3.1.0 for vertex tool-signature support"
```

---

### Task 2: Migrar Builders Vertex para ChatGoogleGenerativeAI

**Files:**
- Modify: `python/omnimind_backend/runtime/providers.py:36-106`
- Modify: `python/tests/test_providers.py:1-220`

**Step 1: Write the failing test**

Adicionar teste que valida kwargs obrigatórios para Vertex + Gemini:

```python
import sys
import types


def test_vertex_builder_uses_chatgooglegenerativeai_with_vertex_kwargs(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _FakeChatGoogleGenerativeAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setitem(
        sys.modules,
        "langchain_google_genai",
        types.SimpleNamespace(ChatGoogleGenerativeAI=_FakeChatGoogleGenerativeAI),
    )

    providers._build_vertex_service_account_model(
        model="gemini-3-flash-preview",
        project_id="demo-project",
        thinking_level="HIGH",
    )

    assert captured["model"] == "gemini-3-flash-preview"
    assert captured["vertexai"] is True
    assert captured["project"] == "demo-project"
    assert captured["location"] == "global"
    assert captured["include_thoughts"] is True
    assert captured["thinking_level"] == "HIGH"
```

**Step 2: Run test to verify it fails**

Run: `cd python && uv run pytest tests/test_providers.py::test_vertex_builder_uses_chatgooglegenerativeai_with_vertex_kwargs -v`
Expected: FAIL (builder atual usa `ChatVertexAI` e assinatura diferente).

**Step 3: Write minimal implementation**

Refatorar `providers.py` para usar apenas `ChatGoogleGenerativeAI` no provider `vertexai`:

```python
def _build_vertex_service_account_model(*, model: str, project_id: str | None, thinking_level: str | None):
    from langchain_google_genai import ChatGoogleGenerativeAI

    kwargs: dict[str, Any] = {
        "model": model,
        "vertexai": True,
        "location": _vertex_location(model),
    }
    if project_id:
        kwargs["project"] = project_id

    if _is_thinking_supported(model):
        kwargs["include_thoughts"] = True
        kwargs["thinking_level"] = _normalize_google_thinking_level(thinking_level)

    return ChatGoogleGenerativeAI(**kwargs)


def _build_vertex_api_key_model(*, model: str, api_key: str, project_id: str | None, thinking_level: str | None):
    from langchain_google_genai import ChatGoogleGenerativeAI

    kwargs: dict[str, Any] = {
        "model": model,
        "google_api_key": api_key,
        "vertexai": True,
        "location": _vertex_location(model),
    }
    if project_id:
        kwargs["project"] = project_id

    if _is_thinking_supported(model):
        kwargs["include_thoughts"] = True
        kwargs["thinking_level"] = _normalize_google_thinking_level(thinking_level)

    return ChatGoogleGenerativeAI(**kwargs)
```

Garantir `_ensure_vertex_env()` mantém:

```python
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"
```

**Step 4: Run test to verify it passes**

Run: `cd python && uv run pytest tests/test_providers.py::test_vertex_builder_uses_chatgooglegenerativeai_with_vertex_kwargs -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add python/omnimind_backend/runtime/providers.py python/tests/test_providers.py
git commit -m "refactor: migrate vertex builders from ChatVertexAI to ChatGoogleGenerativeAI"
```

---

### Task 3: Propagar thinking_level (LOW/HIGH) até o Provider

**Files:**
- Modify: `python/omnimind_backend/runtime/providers.py:176-258`
- Modify: `python/omnimind_backend/runtime/stream.py:115-205`
- Modify: `python/omnimind_backend/runtime/stream.py:245-367`
- Modify: `python/omnimind_backend/orchestrator/graph.py:135-193`
- Modify: `python/omnimind_backend/orchestrator/complexity.py:44-60`
- Modify: `python/omnimind_backend/orchestrator/decomposition/decomposer.py:48-54`
- Modify: `python/omnimind_backend/orchestrator/decomposition/resolver.py:28-66`
- Modify: `python/omnimind_backend/orchestrator/decomposition/synthesizer.py:35-41`
- Modify: `python/tests/test_providers.py:1-320`
- Modify: `python/tests/test_runtime_stream.py:1-220`

**Step 1: Write the failing test**

Adicionar testes de normalização e propagação:

```python
def test_normalize_google_thinking_level() -> None:
    assert providers._normalize_google_thinking_level("HIGH") == "HIGH"
    assert providers._normalize_google_thinking_level("LOW") == "LOW"
    assert providers._normalize_google_thinking_level("MEDIUM") == "LOW"
    assert providers._normalize_google_thinking_level("NONE") == "LOW"


def test_vertex_provider_forwards_thinking_level_to_builder(monkeypatch) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(providers, "_ensure_vertex_env", lambda: (None, "demo-project"))
    monkeypatch.setattr(
        providers,
        "get_settings",
        lambda: SimpleNamespace(
            google_api_key="api-key",
            google_application_credentials=None,
            vertexai_credentials_path=None,
            google_cloud_project="demo-project",
            anthropic_api_key=None,
            openai_api_key=None,
            ollama_base_url="http://localhost:11434",
        ),
    )

    def _fake_builder(**kwargs):
        captured.update(kwargs)
        return _FallbackModel()

    monkeypatch.setattr(providers, "_build_vertex_api_key_model", _fake_builder)

    providers.get_model_for_provider("vertexai", "gemini-3-flash-preview", thinking_level="MEDIUM")
    assert captured["thinking_level"] == "MEDIUM"
```

Adicionar teste de runtime direto:

```python
@pytest.mark.asyncio
async def test_direct_agent_passes_high_thinking_level(monkeypatch) -> None:
    calls = []

    def _fake_get_model(provider, model, **kwargs):
        calls.append(kwargs)
        return _DummyModel()

    monkeypatch.setattr("omnimind_backend.runtime.stream.get_model_for_provider", _fake_get_model)
    # monkeypatch de get_agent/create_default_registry para caminho direto com tools=[]
    ...
    assert calls[0]["thinking_level"] == "HIGH"
```

**Step 2: Run test to verify it fails**

Run: `cd python && uv run pytest tests/test_providers.py::test_normalize_google_thinking_level tests/test_providers.py::test_vertex_provider_forwards_thinking_level_to_builder tests/test_runtime_stream.py::test_direct_agent_passes_high_thinking_level -v`
Expected: FAIL (assinaturas atuais não propagam `thinking_level`).

**Step 3: Write minimal implementation**

1) Em `providers.py`, adicionar normalizador:

```python
def _normalize_google_thinking_level(value: str | None) -> str:
    if (value or "").upper() == "HIGH":
        return "HIGH"
    return "LOW"
```

2) Alterar assinatura de `get_model_for_provider`:

```python
def get_model_for_provider(..., thinking_level: str | None = None):
```

3) Encaminhar `thinking_level` para `_build_vertex_api_key_model` e `_build_vertex_service_account_model`.

4) Atualizar callsites principais:

```python
# runtime/stream.py (direct)
llm = get_model_for_provider(provider, model, thinking_level=agent.thinking_level.value)

# runtime/stream.py (legacy)
llm = get_model_for_provider(provider, model, thinking_level="LOW")

# orchestrator/graph.py
llm = get_model_for_provider(provider, model, thinking_level=decision.thinking.value)
```

5) Para componentes sem decisão explícita (`complexity`, `decomposer`, `resolver`, `synthesizer`), passar `thinking_level="LOW"` por padrão.

**Step 4: Run test to verify it passes**

Run: `cd python && uv run pytest tests/test_providers.py tests/test_runtime_stream.py -v`
Expected: PASS para os testes novos e existentes desses módulos.

**Step 5: Commit**

```bash
git add python/omnimind_backend/runtime/providers.py \
        python/omnimind_backend/runtime/stream.py \
        python/omnimind_backend/orchestrator/graph.py \
        python/omnimind_backend/orchestrator/complexity.py \
        python/omnimind_backend/orchestrator/decomposition/decomposer.py \
        python/omnimind_backend/orchestrator/decomposition/resolver.py \
        python/omnimind_backend/orchestrator/decomposition/synthesizer.py \
        python/tests/test_providers.py \
        python/tests/test_runtime_stream.py
git commit -m "feat: propagate gemini thinking_level low/high across runtime and orchestrator"
```

---

### Task 4: Expor Reasoning Tokens e Thoughts via usage_metadata

**Files:**
- Modify: `python/omnimind_backend/runtime/stream.py:170-205`
- Modify: `python/omnimind_backend/runtime/stream.py:347-367`
- Modify: `python/omnimind_backend/orchestrator/graph.py:159-192`
- Modify: `python/tests/test_runtime_stream.py:14-120`

**Step 1: Write the failing test**

Expandir `_DummyModel` para incluir `usage_metadata`:

```python
class ChunkWithMetadata:
    def __init__(self, content, metadata=None, usage_metadata=None):
        self.content = content
        self.response_metadata = metadata or {}
        self.usage_metadata = usage_metadata or {}


yield ChunkWithMetadata(
    "",
    {"thought": "I am thinking about this"},
    {"output_token_details": {"reasoning": 17}},
)
```

Adicionar asserção:

```python
reasoning_events = [evt for evt in events if evt.type == "thought" and "reasoning_tokens" in evt.data]
assert reasoning_events
assert "17" in reasoning_events[0].data
```

**Step 2: Run test to verify it fails**

Run: `cd python && uv run pytest tests/test_runtime_stream.py::test_stream_contract_has_ordered_seq_and_run_linkage -v`
Expected: FAIL (código atual não lê `usage_metadata.output_token_details.reasoning`).

**Step 3: Write minimal implementation**

Adicionar helper e emissão de evento:

```python
def _extract_reasoning_tokens(chunk: object) -> int | None:
    usage = getattr(chunk, "usage_metadata", None) or {}
    details = usage.get("output_token_details") or {}
    value = details.get("reasoning")
    return int(value) if isinstance(value, int | float) else None


reasoning_tokens = _extract_reasoning_tokens(chunk)
if reasoning_tokens is not None:
    yield normalizer.thought_event(
        next_seq(),
        f"reasoning_tokens={reasoning_tokens}",
        run_id=run_id,
    )
```

No fluxo orquestrado (`orchestrator/graph.py`), emitir custom event equivalente para manter comportamento consistente:

```python
await adispatch_custom_event("agent_thought", {"thought": f"reasoning_tokens={reasoning_tokens}"})
```

**Step 4: Run test to verify it passes**

Run: `cd python && uv run pytest tests/test_runtime_stream.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add python/omnimind_backend/runtime/stream.py python/omnimind_backend/orchestrator/graph.py python/tests/test_runtime_stream.py
git commit -m "feat: emit gemini reasoning_tokens from usage metadata in stream events"
```

---

### Task 5: Alinhar Configuração/Docs e Validar Migração Completa

**Files:**
- Modify: `python/.env.example:23-35`
- Modify: `python/README.md:1-140`
- Modify: `python/tests/test_providers.py:1-360`

**Step 1: Write the failing test**

Adicionar teste de documentação de env:

```python
def test_python_env_example_has_vertex_genai_flag() -> None:
    env_example = (Path(__file__).resolve().parents[1] / ".env.example").read_text(encoding="utf-8")
    assert "GOOGLE_GENAI_USE_VERTEXAI=true" in env_example
```

**Step 2: Run test to verify it fails**

Run: `cd python && uv run pytest tests/test_providers.py::test_python_env_example_has_vertex_genai_flag -v`
Expected: FAIL (flag ainda não documentada no `python/.env.example`).

**Step 3: Write minimal implementation**

Atualizar `python/.env.example` com bloco explícito:

```dotenv
# Vertex via langchain-google-genai
GOOGLE_GENAI_USE_VERTEXAI=true
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
# Gemini 3+ usa location global (definido no runtime)
```

Atualizar `python/README.md` com exemplo oficial de inicialização:

```python
llm = ChatGoogleGenerativeAI(
    model="gemini-3-flash-preview",
    google_api_key=GOOGLE_API_KEY,
    project=GOOGLE_CLOUD_PROJECT,
    vertexai=True,
    location="global",
    include_thoughts=True,
    thinking_level="HIGH",
)
```

**Step 4: Run test to verify it passes**

Run: `cd python && uv run pytest tests/test_providers.py::test_python_env_example_has_vertex_genai_flag -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add python/.env.example python/README.md python/tests/test_providers.py
git commit -m "docs: document vertex genai env and gemini thinking settings"
```

---

### Task 6: Verificação Final (Evidence Before Assertions)

**Files:**
- Test: `python/tests/test_providers.py`
- Test: `python/tests/test_runtime_stream.py`
- Test: `python/tests/test_complexity_scorer.py`
- Test: `python/tests/test_orchestrator_graph.py`

**Step 1: Run focused test suite**

Run:

```bash
cd python
uv run pytest tests/test_providers.py tests/test_runtime_stream.py tests/test_complexity_scorer.py tests/test_orchestrator_graph.py -v
```

Expected: PASS total nesses módulos.

**Step 2: Run quality gates**

Run:

```bash
cd python
make lint
make typecheck
make test
```

Expected: sem erros de lint/type/test.

**Step 3: Run manual smoke for Vertex provider**

Run:

```bash
cd python
export GOOGLE_GENAI_USE_VERTEXAI=true
uv run python -c "from omnimind_backend.runtime.providers import get_model_for_provider; m=get_model_for_provider('vertexai','gemini-3-flash-preview',thinking_level='HIGH'); print(type(m).__name__)"
```

Expected: saída contendo `ChatGoogleGenerativeAI` (ou wrapper `_AinvokeFallbackModel` com modelo interno `ChatGoogleGenerativeAI`).

**Step 4: Manual stream smoke for reasoning tokens**

Run:

```bash
cd python
uv run omnimind-cli chat -m "Explique rapidamente o plano" --provider vertexai --model gemini-3-flash-preview
```

Expected: stream com eventos de pensamento e presença de `reasoning_tokens=` quando retornado pelo provider.

**Step 5: Commit (if needed)**

```bash
git add -A
git commit -m "chore: finalize vertex genai migration verification"
```

(Executar apenas se houver artefatos finais desta etapa.)
