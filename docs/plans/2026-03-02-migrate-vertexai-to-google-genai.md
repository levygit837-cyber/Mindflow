# Migração de ChatVertexAI para ChatGoogleGenerativeAI (Vertex AI) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrar a inicialização dos modelos Vertex AI do componente deprecado `ChatVertexAI` para o novo `ChatGoogleGenerativeAI` do pacote `langchain-google-genai`, habilitando suporte nativo a modelos Gemini 3, "Thinking" (Reasoning) e extração de metadados de tokens de pensamento.

**Architecture:** A lógica de provedores em `runtime/providers.py` será refatorada para que, quando o provedor for `vertexai`, ele utilize `ChatGoogleGenerativeAI` com a flag `vertexai=True`. O processamento de stream em `runtime/stream.py` será atualizado para capturar `reasoning_tokens` dos novos metadados da LangChain.

**Tech Stack:** `langchain-google-genai >= 3.1.0`, `langchain-core`, Python 3.11.

---

### Task 1: Atualização de Dependências

**Files:**
- Modify: `python/pyproject.toml`

**Step 1: Atualizar versão do langchain-google-genai**

Modificar a linha da dependência para garantir a versão mínima 3.1.0.

```toml
"langchain-google-genai>=3.1.0",
```

**Step 2: Sincronizar dependências**

Executar o comando de instalação (assumindo uso de `uv` ou `pip`).

Run: `cd python && uv sync` (ou `pip install -e .`)

**Step 3: Commit**

```bash
git add python/pyproject.toml
git commit -m "build: upgrade langchain-google-genai to 3.1.0"
```

---

### Task 2: Refatoração do Provedor Vertex AI

**Files:**
- Modify: `python/omnimind_backend/runtime/providers.py`

**Step 1: Atualizar imports e lógica de inicialização**

Remover o uso de `ChatVertexAI` e substituir por `ChatGoogleGenerativeAI` configurado para Vertex.

```python
# Em _build_vertex_service_account_model ou similar:
from langchain_google_genai import ChatGoogleGenerativeAI

kwargs = {
    "model": model,
    "project": project_id,
    "location": "global" if "gemini-3" in model.lower() else "us-central1",
    "vertexai": True,
}

if _is_thinking_supported(model):
    kwargs["include_thoughts"] = True
    kwargs["thinking_level"] = "HIGH" # Ou conforme desejado
```

**Step 2: Garantir variável de ambiente**

Garantir que `os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"` seja definido antes da inicialização.

**Step 3: Testar inicialização (Mock)**

Criar um teste rápido para validar que `get_model_for_provider("vertexai", ...)` retorna a classe correta com os parâmetros esperados.

**Step 4: Commit**

```bash
git add python/omnimind_backend/runtime/providers.py
git commit -m "refactor: migrate vertexai provider to ChatGoogleGenerativeAI"
```

---

### Task 3: Captura de Reasoning Tokens no Stream

**Files:**
- Modify: `python/omnimind_backend/runtime/stream.py`

**Step 1: Atualizar extração de pensamentos e metadados**

Atualizar o loop `astream` para extrair os `reasoning` tokens conforme a nova estrutura da LangChain.

```python
# No loop astream de _stream_chat_direct_agent e _stream_chat_legacy
if hasattr(chunk, "usage_metadata") and chunk.usage_metadata:
    reasoning_tokens = chunk.usage_metadata.get("output_token_details", {}).get("reasoning", 0)
    # Log ou emitir evento se necessário
```

**Step 2: Atualizar captura de thoughts (pensamento textual)**

Verificar se o pensamento agora vem via `chunk.content` (se for uma lista de partes) ou se continua nos metadados. Para Gemini 3 via `langchain-google-genai`, o pensamento geralmente é uma parte da mensagem.

**Step 3: Commit**

```bash
git add python/omnimind_backend/runtime/stream.py
git commit -m "feat: extract reasoning tokens from usage metadata"
```

---

### Task 4: Validação e Testes E2E

**Files:**
- Create: `python/tests/test_vertexai_migration.py`

**Step 1: Criar teste de integração/unitário para o novo provedor**

Validar que as chamadas `ainvoke` e `astream` funcionam com o novo modelo (usando mocks para evitar chamadas reais se necessário, ou testes reais se houver credenciais).

**Step 2: Verificar assinaturas de ferramentas (Tool Call Signatures)**

Garantir que chamadas de ferramentas funcionam, pois o Gemini 3 é sensível a isso.

**Step 3: Executar todos os testes de runtime**

Run: `pytest python/tests/test_runtime_stream.py python/tests/test_providers.py`

**Step 4: Commit final**

```bash
git add python/tests/test_vertexai_migration.py
git commit -m "test: verify vertexai migration and reasoning extraction"
```
