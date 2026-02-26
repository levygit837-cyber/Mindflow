# MemoryDoc

> Camada: 2 — Arquitetura | Depende de: AgentsDoc, ContextoDoc | Referenciado por: PromptGuide
> Stack: deepagents · LangGraph · LangChain · Python

---

## A) Visão Geral

- **Memória** é o mecanismo que permite ao agente lembrar informações além da janela de contexto atual.
- Existem quatro tipos: **working** (curto prazo, dentro da sessão), **episodic** (histórico de conversas), **semantic** (conhecimento factual persistente) e **procedural** (como executar tarefas — skills).
- LangGraph gerencia memória via **checkpointers** — componentes que salvam e restauram o estado do grafo entre execuções.
- deepagents usa `StateBackend` (memória de estado) e `FilesystemBackend` (persistência em arquivo) — ambos configurados em `deep_agent_config.py`.
- O `thread_id` é a chave de isolamento — cada conversa/usuário deve ter seu próprio `thread_id`.
- Saber **quando persistir vs quando descartar** é tão importante quanto saber como persistir.

---

## B) Conceitos Essenciais

| Termo | Definição |
|---|---|
| **Working memory** | Contexto atual da sessão — mensagens, tool results, raciocínio em andamento |
| **Episodic memory** | Histórico de conversas anteriores — o que foi dito em sessões passadas |
| **Semantic memory** | Conhecimento factual persistido — fatos, preferências, dados do usuário |
| **Procedural memory** | Como executar tarefas — skills, padrões, workflows aprendidos |
| **Checkpointer** | Componente LangGraph que salva/restaura o estado do grafo (MemorySaver, SqliteSaver) |
| **Thread ID** | Identificador único de uma conversa/sessão — isola memória entre usuários |
| **MemorySaver** | Checkpointer in-memory do LangGraph — dados somem ao reiniciar o processo |
| **SqliteSaver** | Checkpointer SQLite do LangGraph — persiste em arquivo local |
| **StateBackend** | Backend deepagents para armazenar estado estruturado em memória |
| **FilesystemBackend** | Backend deepagents para ler/escrever arquivos como memória persistente |

---

## C) Boas Práticas

### DO ✅

- **Sempre use `thread_id` por usuário/sessão** — sem isso, toda conversa compartilha o mesmo estado
- **Use `MemorySaver` em desenvolvimento, `SqliteSaver` em produção leve** — fácil de trocar
- **Persista só o que é realmente necessário** — memória grande aumenta latência de recuperação
- **Defina TTL (tempo de vida) para memórias episódicas** — conversas de 6 meses atrás raramente são relevantes
- **Separe memória por tipo** — histórico de conversa num lugar, preferências do usuário em outro
- **Comprima episodic memory regularmente** — resuma conversas antigas antes de persistir

### DON'T ❌

- **Não persista dados sensíveis em memória sem criptografia** — tokens, senhas, dados pessoais
- **Não use MemorySaver em produção** — dados somem ao reiniciar o processo
- **Não acumule episodic memory indefinidamente** — cresce sem limite e degrada performance
- **Não misture estado de diferentes usuários** — sempre isole por `thread_id`
- **Não confunda contexto com memória** — contexto é o que está na janela agora; memória é o que foi persistido

---

## D) Receitas Reutilizáveis

### Checklist para configurar memória

- [ ] Tipo de memória definido (working / episodic / semantic / procedural)
- [ ] Backend escolhido (MemorySaver / SqliteSaver / PostgreSQL / Redis / vector store)
- [ ] `thread_id` configurado e único por usuário/sessão
- [ ] TTL definido para dados episódicos
- [ ] Política de compressão definida (summarizar após N mensagens)
- [ ] Dados sensíveis identificados e protegidos
- [ ] Teste de isolamento entre threads (usuário A não vê dados do usuário B)

### Hierarquia de backends por cenário

```
Desenvolvimento / teste rápido
  └── MemorySaver (in-memory, sem dependências)

Produção leve / single-server
  └── SqliteSaver (arquivo local, persistente)

Produção com múltiplos servidores
  └── PostgreSQL (incerto — verifique langgraph-checkpoint-postgres)
      ou Redis (incerto — verifique disponibilidade)

Memória semântica (busca por similaridade)
  └── Vector store (Chroma, Pinecone, pgvector)
```

---

## E) Exemplos Práticos

### Exemplo 1 — Checkpointing com MemorySaver (desenvolvimento)

```python
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph

checkpointer = MemorySaver()
graph = build_agent_graph()  # seu grafo aqui
agent = graph.compile(checkpointer=checkpointer)

# Conversa 1 — thread isolado por usuário
config_user_a = {"configurable": {"thread_id": "user-001-session-1"}}
result1 = agent.invoke(
    {"messages": [{"role": "user", "content": "Meu nome é Alice"}]},
    config=config_user_a,
)

# Conversa 2 — mesmo usuário, agente lembra
result2 = agent.invoke(
    {"messages": [{"role": "user", "content": "Qual é meu nome?"}]},
    config=config_user_a,  # mesmo thread_id = lembra Alice
)
print(result2["messages"][-1].content)  # "Seu nome é Alice"

# Conversa 3 — thread diferente, agente NÃO lembra
config_user_b = {"configurable": {"thread_id": "user-002-session-1"}}
result3 = agent.invoke(
    {"messages": [{"role": "user", "content": "Qual é meu nome?"}]},
    config=config_user_b,  # thread diferente = sem memória do usuário A
)
```

---

### Exemplo 2 — SqliteSaver (produção leve)

```python
# SqliteSaver persiste em arquivo — sobrevive a reinicializações
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3

# Cria/abre o banco
conn = sqlite3.connect("memory/agent_checkpoints.db", check_same_thread=False)
checkpointer = SqliteSaver(conn)

graph = build_agent_graph()
agent = graph.compile(checkpointer=checkpointer)

# Uso idêntico ao MemorySaver — só muda o backend
config = {"configurable": {"thread_id": "user-001"}}
result = agent.invoke({"messages": [...]}, config=config)
```

---

### Exemplo 3 — Como deepagents usa StateBackend e FilesystemBackend

```python
# Padrão real do projeto — ver python/omnimind_agents/deep_agent_config.py

from deepagents import CompositeBackend, FilesystemBackend, StateBackend, create_deep_agent
import os

# FilesystemBackend: agente pode ler/escrever arquivos como memória
# StateBackend: estado em memória, acessível via path /memories/
backend = CompositeBackend(
    FilesystemBackend(root_dir=os.getcwd()),
    {
        "/memories/": StateBackend(state={}, store=None),
    },
)

agent = create_deep_agent(
    model=model,
    system_prompt=system_prompt,
    name="omnimind-agent",
    tools=[],
    backend=backend,
)

# O agente pode:
# - Ler arquivos do filesystem (FilesystemBackend)
# - Guardar/recuperar estado em /memories/ (StateBackend)
# Ex: agent pode salvar {"user_preference": "dark_mode"} em /memories/prefs
```

---

### Exemplo 4 (RUIM → CORRIGIDO)

```python
# ❌ RUIM — sem thread_id, sem persistência, memória vaza entre usuários

from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()
agent = graph.compile(checkpointer=checkpointer)

# Todos os usuários usam o mesmo thread — memória vaza!
def handle_request(message: str) -> str:
    result = agent.invoke(
        {"messages": [{"role": "user", "content": message}]},
        config={"configurable": {"thread_id": "global"}},  # ❌ thread único global
    )
    return result["messages"][-1].content
```

```python
# ✅ CORRIGIDO — thread_id por usuário, SqliteSaver para persistência

from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3
import uuid

conn = sqlite3.connect("memory/checkpoints.db", check_same_thread=False)
checkpointer = SqliteSaver(conn)
agent = graph.compile(checkpointer=checkpointer)

def handle_request(message: str, user_id: str, session_id: str | None = None) -> str:
    # thread_id = user_id + session_id = isolamento por usuário por sessão
    thread_id = f"{user_id}-{session_id or uuid.uuid4().hex}"

    result = agent.invoke(
        {"messages": [{"role": "user", "content": message}]},
        config={
            "configurable": {"thread_id": thread_id},
            "recursion_limit": 25,
        },
    )
    return result["messages"][-1].content, thread_id  # retorna thread_id para o cliente manter
```

---

## F) Confiabilidade / Anti-Alucinação

### Como validar memória

- **Teste de isolamento** — crie duas threads, verifique que informação de uma não aparece na outra
- **Teste de persistência** — reinicie o processo, verifique que SqliteSaver recupera o estado correto
- **Inspecione o checkpoint** — LangGraph permite `checkpointer.get(config)` para ver o estado salvo
- **Monitore tamanho da memória** — threads muito longas aumentam latência; defina limite

### Quando perguntar vs assumir

- Se a memória não contém a informação pedida: **pergunte ao usuário**, não invente
- Se o thread_id não existe (novo usuário): **comece com contexto vazio**, não use contexto de outro usuário

### Incertezas desta documentação

- `PostgresSaver` para produção multi-servidor — **(incerto)** verifique pacote `langgraph-checkpoint-postgres` e sua API atual.
- `StateBackend` do deepagents pode ter API diferente entre versões — **(incerto)** confirme em `python/omnimind_agents/deep_agent_config.py`.
- TTL automático no SqliteSaver não é nativo — **(incerto)** verifique se há extensão ou implemente manualmente.

---

## G) Analogia

Memória de agente é como a **mesa de trabalho + gaveta + arquivo morto** de um profissional.

A **mesa de trabalho** (working memory) é o que ele tem em mãos agora — o documento que está lendo, as anotações recentes. Quando a mesa fica cheia, ele precisa mover coisas para a gaveta.

A **gaveta** (episodic memory) guarda o histórico recente — conversas da semana passada, decisões tomadas. Ele abre quando precisa de contexto de curto prazo.

O **arquivo morto** (semantic memory) guarda conhecimento permanente — manuais, preferências do cliente, padrões da empresa. Raramente muda, mas sempre está disponível.

A diferença é que, diferente de um humano, o agente só "vê" o que está na mesa de trabalho (janela de contexto). Tudo o que está na gaveta ou no arquivo morto precisa ser **explicitamente trazido para a mesa** — e é aí que o checkpointer e as estratégias de recuperação entram.

---

## H) Erros Comuns e Como Evitar

| Erro | Causa | Como evitar |
|---|---|---|
| Memória vaza entre usuários | `thread_id` global ou ausente | Sempre use `thread_id` único por usuário/sessão |
| Dados somem ao reiniciar | MemorySaver em produção | Use SqliteSaver ou PostgreSQL em produção |
| Memória cresce sem limite | Sem TTL ou compressão | Defina limite de mensagens e comprima episodic memory |
| Agente "lembra" coisas erradas | Thread corrompido | Implemente reset de thread quando usuário pedir |
| Performance degradada | Thread com 1000+ mensagens | Aplique summarização após N mensagens |
| Dados sensíveis em memória | Sem filtro antes de persistir | Filtre tokens, senhas, dados pessoais antes de salvar |

---

## I) Mini-Template Pronto

```python
# ============================================================
# TEMPLATE: Agente com memória persistente por usuário
# ============================================================

import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph

# --- Setup do checkpointer (faça uma vez na inicialização) ---
def create_checkpointer(db_path: str = "memory/agent_memory.db") -> SqliteSaver:
    import os
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    return SqliteSaver(conn)

checkpointer = create_checkpointer()

# --- Compilação do agente com memória ---
graph = build_agent_graph()  # seu StateGraph aqui
agent = graph.compile(checkpointer=checkpointer)

# --- Invocação com isolamento por usuário ---
def get_thread_id(user_id: str, session_id: str) -> str:
    """Thread ID único por usuário + sessão."""
    return f"{user_id}::{session_id}"

async def chat_with_memory(
    message: str,
    user_id: str,
    session_id: str,
) -> str:
    thread_id = get_thread_id(user_id, session_id)
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 25,
    }
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": message}]},
        config=config,
    )
    return result["messages"][-1].content

# --- Recuperar histórico da thread ---
def get_conversation_history(user_id: str, session_id: str) -> list:
    thread_id = get_thread_id(user_id, session_id)
    config = {"configurable": {"thread_id": thread_id}}
    state = checkpointer.get(config)  # recupera último checkpoint
    if state:
        return state.values.get("messages", [])
    return []

# --- Resetar memória de um usuário ---
def reset_session(user_id: str, session_id: str) -> None:
    """Remove o checkpoint de uma sessão específica."""
    # SqliteSaver não tem delete nativo — implemente via SQL direto
    # (incerto) verifique API da versão instalada
    pass
```
