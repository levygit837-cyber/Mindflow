# Migração Temporária para CLI Interativa Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Descontinuar temporariamente o frontend e migrar a experiência principal para uma CLI interativa e rica, conversando diretamente com modelos individuais do Vertex AI (Gemini 3 Flash Preview com thinking budget), sem passar pelo orquestrador.

**Architecture:** A CLI será a interface padrão. O comando `connect` passará a ser o padrão (ou a principal porta de entrada interativa). O cliente CLI será configurado para sempre enviar `orchestrate=False`, fixar o provider como `vertexai` e o modelo como `gemini-3-flash-preview`. O backend (via API/gRPC) deverá aceitar um parâmetro `agent_type` para direcionar a mensagem a uma personalidade específica, ignorando o orquestrador.

**Tech Stack:** Python, Typer, Rich (CLI), FastAPI, gRPC (Backend), Vertex AI (Gemini).

---

### Task 1: Atualizar o payload do Client CLI para suportar agent_type e orchestrate

**Files:**
- Modify: `python/omnimind_cli/client.py`

**Step 1: Update the stream_chat method signature and payload**

Update `stream_chat` to accept `agent_type` and `orchestrate`.

```python
    def stream_chat(
        self,
        *,
        message: str,
        provider: str | None = None,
        model: str | None = None,
        debug_steps: bool = False,
        agent_type: str | None = None,
        orchestrate: bool = False,
    ) -> Iterator[StreamEvent]:
        payload: dict[str, Any] = {
            "message": message,
            "debugSteps": debug_steps,
            "orchestrate": orchestrate,
        }
        if provider:
            payload["provider"] = provider
        if model:
            payload["model"] = model
        if agent_type:
            payload["agent_type"] = agent_type
        # ... resto do código igual ...
```

**Step 2: Commit**
```bash
git add python/omnimind_cli/client.py
git commit -m "feat(cli): add agent_type and orchestrate params to stream_chat"
```

---

### Task 2: Configurar o CLI para ser Interativo por padrão com seleção de Personalidade

**Files:**
- Modify: `python/omnimind_cli/commands/chat.py`
- Modify: `python/omnimind_cli/app.py`

**Step 1: Atualizar parâmetros do comando connect e torná-lo o fluxo principal**

Modificar o comando `connect` no `chat.py` para fixar os padrões do VertexAI e solicitar a personalidade.

```python
# Em python/omnimind_cli/commands/chat.py
# Modificar a assinatura do connect e a lógica inicial:

    @app.command("connect")
    def connect(
        agent: str = typer.Option("coder", "--agent", "-a", help="Personalidade do agente (coder, analyst, researcher, etc)"),
        provider: str = typer.Option("vertexai", "--provider", help="Provider override"),
        model: str = typer.Option("gemini-3-flash-preview", "--model", help="Model override"),
        debug_steps: bool = typer.Option(False, "--debug-steps", help="Enable debug-oriented stream flags"),
        base_url: str | None = typer.Option(
            None,
            "--base-url",
            envvar="OMNIMIND_API_URL",
            help="OmniMind backend base URL",
        ),
    ) -> None:
        # ...
        console.print(f"[green]Conexao estabelecida[/] (backend status: {status})")
        console.print(f"Modo: [bold]Agente Direto ({agent})[/] via {provider} / {model}")
        console.print("Comandos: /sair para encerrar, /reset para limpar contexto local.")

        # Na chamada do _stream_chat_once dentro do loop:
            assistant_text = _stream_chat_once(
                client=client,
                renderer=renderer,
                message=composed_message,
                provider=provider,
                model=model,
                debug_steps=debug_steps,
                agent_type=agent,
                orchestrate=False, # Forçar false
            )
```

E atualizar a função auxiliar `_stream_chat_once` no `chat.py` para aceitar esses parâmetros:

```python
def _stream_chat_once(
    *,
    client: OmniMindCliClient,
    renderer: ChatStreamRenderer,
    message: str,
    provider: str | None,
    model: str | None,
    debug_steps: bool,
    agent_type: str | None = None,
    orchestrate: bool = False,
) -> str:
    response_chunks: list[str] = []
    for event in client.stream_chat(
        message=message,
        provider=provider,
        model=model,
        debug_steps=debug_steps,
        agent_type=agent_type,
        orchestrate=orchestrate,
    ):
        # ...
```

**Step 2: Fazer o app invocar connect por padrão (Opcional mas recomendado)**

No `python/omnimind_cli/app.py`:
Trocar `no_args_is_help=True` para `invoke_without_command=True`.

```python
app = typer.Typer(help="OmniMind terminal-first CLI", invoke_without_command=True)

@app.callback()
def main(ctx: typer.Context):
    """OmniMind CLI - Modo interativo por padrão"""
    if ctx.invoked_subcommand is None:
        from omnimind_cli.commands.chat import register_chat_commands
        # Um hack simples é invocar o connect via sistema caso não passe nada
        pass
        # Ou orientar o usuário a rodar 'omnimind connect' por enquanto para manter a estrutura do typer limpa.
```
*Vamos apenas manter o foco no `connect` como o comando interativo primário e orientar o uso.*

**Step 3: Commit**
```bash
git add python/omnimind_cli/commands/chat.py python/omnimind_cli/app.py
git commit -m "feat(cli): enhance connect command to support direct agent chat with vertexai"
```

---

### Task 3: Atualizar API e gRPC do Backend para propagar agent_type e orchestrate

**Files:**
- Modify: `python/omnimind_backend/api/v1/agent.py`
- Modify: `python/omnimind_backend/grpc/client.py`
- Modify: (se necessário) os arquivos proto e gerados (pular edição direta de proto se a struct já suporta os kwargs kwargs ou se pudermos passar via metadados, mas assumiremos que `agent_type` pode ser passado).

**Step 1: Atualizar `v1/agent.py`**

```python
# Em python/omnimind_backend/api/v1/agent.py (linha ~39)
        async for event in grpc_client.agent.stream_chat(
            session_id=session_id,
            message=payload.message,
            provider=payload.provider,
            model=payload.model,
            run_id=run_id,
            orchestrate=payload.orchestrate,
            agent_type=payload.agent_type, # Adicionar repasse
        ):
```

**Step 2: Atualizar `grpc/client.py` (StreamChat)**

```python
# Adicione agent_type a assinatura
    async def stream_chat(
        self,
        *,
        session_id: str,
        message: str,
        provider: str | None = None,
        model: str | None = None,
        run_id: str | None = None,
        orchestrate: bool = True,
        agent_type: str | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        # Configurar o payload gRPC para incluir o agent_type, 
        # dependendo de como a mensagem protobuf foi definida.
        pass
```

*(Nota para o executor: verificar a definição do protobuf `StreamChatRequest` em `python/omnimind_backend/grpc/protos/agent.proto`. Se não tiver `agent_type`, será necessário adicioná-lo e rodar `make gen-proto` ou o script equivalente. Se o protobuf já tiver, apenas mapear o campo.)*

**Step 3: Commit**
```bash
git add python/omnimind_backend/api/v1/agent.py python/omnimind_backend/grpc/client.py
git commit -m "feat(api): pass agent_type to grpc client"
```

---

### Task 4: Atualizar o Worker/Servicer para instanciar o Agente Específico

**Files:**
- Modify: `python/omnimind_backend/workers/agent_servicer.py` ou equivalente que implemente o gRPC.
- Modify: `python/omnimind_backend/runtime/stream.py`

**Step 1: Modificar a lógica de fallback do Orquestrador**

Quando `orchestrate=False`, o backend deve olhar para `agent_type`. Se fornecido, buscar da `AgentRegistry`.

```python
# Em python/omnimind_backend/workers/agent_servicer.py (ou onde o Graph é invocado)
from omnimind_backend.agents._registry import get_agent

# Lógica condicional:
if not request.orchestrate and request.agent_type:
    # Invocar diretamente o LangGraph/Runtime do agente individual
    agent = get_agent(request.agent_type)
    # Lógica para executar agent.build_graph() em vez do orquestrador
```

**Step 2: Garantir que o Provider inclua o Thinking Budget**

O VertexAI exige que para os modelos Gemini (como gemini-3-flash-preview e thinking models) passemos configurações específicas na inicialização do LLM (no Langchain/VertexAI wrapper).
Revisar `python/omnimind_backend/runtime/providers.py` na função de criação do VertexAI:

```python
# Em python/omnimind_backend/runtime/providers.py
def _create_vertexai_model(model_name: str, ...):
    # Assegurar kwargs de thinking budget
    # model_kwargs={"thinking_config": {"thinking_budget": 1024}} # ou conforme a doc da API do Vertex
    pass
```

**Step 3: Commit**
```bash
git add python/omnimind_backend/workers/agent_servicer.py python/omnimind_backend/runtime/providers.py
git commit -m "feat(backend): direct agent routing and thinking budget for vertexai"
```
