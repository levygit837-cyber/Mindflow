# AgentsDoc

> Camada: 1 — Fundação | Depende de: ToolsDoc | Referenciado por: SubAgentsDoc, OrquestradorDoc, MemoryDoc, SystemPromptDoc
> Stack: deepagents · LangGraph · LangChain · Python

---

## A) Visão Geral

- Um **agente** é um loop onde um LLM raciocina, decide invocar tools, recebe os resultados e repete até ter uma resposta final.
- Diferente de uma chain (sequência fixa), o agente decide dinamicamente o que fazer a cada passo.
- LangGraph modela o agente como um **grafo de estados**: nodes (passos) conectados por edges (transições) com um estado compartilhado.
- deepagents é uma camada de abstração que cria esse grafo por baixo dos panos — você configura no alto nível e ele monta o LangGraph.
- O ciclo de vida de um agente é: `input → raciocínio (LLM) → tool call (opcional) → resultado → raciocínio → ... → resposta final`.
- Agentes podem ser simples (um único LLM com tools) ou compostos (múltiplos agentes em grafo — ver SubAgentsDoc e OrquestradorDoc).

---

## B) Conceitos Essenciais

| Termo | Definição |
|---|---|
| **Agent loop** | Ciclo de raciocínio → ação → observação que se repete até o agente decidir parar |
| **State** | Objeto que carrega o contexto do agente entre os nodes (mensagens, variáveis, histórico) |
| **Node** | Um passo no grafo LangGraph — pode ser uma chamada ao LLM, execução de tool, ou lógica custom |
| **Edge** | Conexão entre nodes — pode ser fixa ou condicional (o agente decide para onde ir) |
| **ReAct** | Padrão de agente: Reason (raciocinar) + Act (agir com tool) — o mais comum |
| **StateGraph** | Classe principal do LangGraph para definir um grafo de agente |
| **ToolNode** | Node pré-construído do LangGraph que executa tool calls do LLM automaticamente |
| **create_deep_agent** | Função do deepagents que cria um agente completo com LangGraph por baixo |
| **stream_mode** | Como o agente emite eventos durante a execução (messages, updates, values, debug) |
| **checkpointer** | Componente que salva o estado do agente entre execuções — habilita memória persistente |

---

## C) Boas Práticas

### DO ✅

- **Defina um propósito claro para cada agente** — um agente de coding faz coding; um de busca faz busca
- **Use o system prompt para definir personalidade e limites** — ver SystemPromptDoc
- **Passe apenas as tools necessárias** — tools irrelevantes confundem o LLM e aumentam o contexto
- **Use `stream_mode` adequado** — para UI em tempo real use `messages`; para debug use `debug`
- **Configure `thread_id` para memória por conversa** — permite o agente lembrar de sessões anteriores
- **Trate erros de tool no próprio agente** — o agente deve tentar outra abordagem se uma tool falhar
- **Limite o número de iterações** — use `recursion_limit` para evitar loops infinitos

### DON'T ❌

- **Não misture responsabilidades** — agente de chat não deve também orquestrar sub-agentes
- **Não passe todas as tools disponíveis** — escolha as relevantes para o propósito do agente
- **Não ignore o `recursion_limit`** — sem ele, bugs de lógica viram loops infinitos e custo infinito
- **Não hardcode o model** — use variável de configuração (ver Backends.md)
- **Não assuma que o agente sempre termina** — sempre tenha um timeout ou limite de steps

---

## D) Receitas Reutilizáveis

### Checklist para criar um novo agente

- [ ] Propósito definido em uma frase
- [ ] System prompt escrito (ver SystemPromptDoc)
- [ ] Lista de tools selecionadas (só as necessárias)
- [ ] Provider e model configurados via env vars
- [ ] `thread_id` configurado para isolamento de conversa
- [ ] `recursion_limit` definido (padrão LangGraph: 25)
- [ ] Stream mode escolhido para o contexto de uso
- [ ] Teste de integração básico (input → output esperado)

### Fluxo de decisão: deepagents vs LangGraph direto

```
Precisa de algo simples (chat, task)?
  └── Use create_deep_agent (deepagents)

Precisa de grafo custom (branching, paralelo, estados complexos)?
  └── Use StateGraph (LangGraph) diretamente

Precisa de múltiplos agentes coordenados?
  └── Ver SubAgentsDoc + OrquestradorDoc
```

---

## E) Exemplos Práticos

### Exemplo 1 — Agente simples com deepagents

```python
# Agente de chat básico — o caso mais comum no OmniMind

from omnimind_agents import (
    build_static_system_prompt,
    create_agent_chat_stream_normalizer,
    get_model_for_provider,
)
from omnimind_agents.deep_agent_config import create_omnimind_deep_agent

# 1. Modelo (provedor configurado via env vars)
model = get_model_for_provider(provider="anthropic", model="claude-sonnet-4-6")

# 2. Agente
agent = create_omnimind_deep_agent(
    model=model,
    system_prompt=build_static_system_prompt(),
)

# 3. Invocar com stream
async def chat(message: str, thread_id: str = "default"):
    async for chunk in agent.astream(
        {"messages": [{"role": "user", "content": message}]},
        config={
            "configurable": {"thread_id": thread_id},
            "recursion_limit": 25,
        },
        stream_mode=["messages", "updates"],
    ):
        yield chunk
```

---

### Exemplo 2 — Agente com LangGraph direto (grafo custom)

```python
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool

# 1. Estado do agente
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]  # add_messages = acumula, não substitui

# 2. Tool registrada
@tool
def read_file(path: str) -> str:
    """Lê um arquivo local."""
    try:
        return open(path).read()
    except FileNotFoundError:
        return f"[ERRO] Não encontrado: {path}"

tools = [read_file]

# 3. Modelo com tools vinculadas
model = ChatAnthropic(model="claude-sonnet-4-6").bind_tools(tools)

# 4. Nodes
def call_llm(state: AgentState) -> AgentState:
    response = model.invoke(state["messages"])
    return {"messages": [response]}

def should_continue(state: AgentState) -> str:
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return END

# 5. Grafo
graph = StateGraph(AgentState)
graph.add_node("llm", call_llm)
graph.add_node("tools", ToolNode(tools))
graph.set_entry_point("llm")
graph.add_conditional_edges("llm", should_continue)
graph.add_edge("tools", "llm")  # após tool, volta pro LLM

agent = graph.compile()
```

---

### Exemplo 3 — Agente com checkpointer (memória persistente)

```python
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph

# MemorySaver = em memória (dev/teste)
# SqliteSaver = persiste em arquivo (produção leve)
# PostgresSaver = persiste em banco (produção real) — (incerto) confirme disponibilidade

checkpointer = MemorySaver()

graph = StateGraph(AgentState)
# ... adicione nodes e edges ...
agent = graph.compile(checkpointer=checkpointer)

# thread_id isola a memória por conversa
config = {"configurable": {"thread_id": "conversa-123"}}
result = agent.invoke({"messages": [{"role": "user", "content": "Olá"}]}, config=config)
```

---

### Exemplo 4 (RUIM → CORRIGIDO)

```python
# ❌ RUIM — agente genérico sem limites

from deepagents import create_deep_agent
from all_tools import ALL_TOOLS_EVER_CREATED  # todas as tools do projeto

agent = create_deep_agent(
    model=model,
    system_prompt="Você é um assistente.",  # system prompt vago
    tools=ALL_TOOLS_EVER_CREATED,           # 40 tools registradas
    name="agent",
)
# Sem recursion_limit → loop infinito possível
# Sem thread_id → sem memória de conversa
```

**Problemas:**
1. System prompt vago — o agente não sabe seus limites
2. 40 tools — contexto sobrecarregado, LLM escolhe errado com frequência
3. Sem `recursion_limit` — um bug de lógica vira custo infinito

```python
# ✅ CORRIGIDO

from deepagents import create_deep_agent
from omnimind_agents.prompts.base import BASE_PROMPT
from my_tools import read_file, search_web  # só as necessárias

agent = create_deep_agent(
    model=model,
    system_prompt=BASE_PROMPT,
    tools=[read_file, search_web],  # 2 tools relevantes
    name="research-agent",
)

config = {
    "configurable": {"thread_id": "user-456-session-1"},
    "recursion_limit": 20,
}
result = await agent.ainvoke({"messages": [...]}, config=config)
```

---

## F) Confiabilidade / Anti-Alucinação

### Como validar comportamento do agente

- **Teste com inputs extremos** — mensagem vazia, mensagem muito longa, pedido ambíguo
- **Verifique o `stream_mode`** — em modo `debug`, você vê cada decisão do LLM; use em desenvolvimento
- **Inspecione tool calls** — o agente está chamando as tools corretas com os argumentos corretos?
- **Cheque o estado final** — `state["messages"]` deve conter o histórico completo da execução

### Quando falta informação

- Se o agente não sabe como responder: o system prompt deve instruí-lo a dizer "não sei" ou pedir mais contexto (ver SystemPromptDoc)
- Se uma tool falha: o agente deve tentar abordagem alternativa, não inventar um resultado
- Se o contexto estiver cheio: ver ContextoDoc para estratégias de compressão

### Incertezas desta documentação

- `PostgresSaver` para checkpointing em produção — **(incerto)** verifique disponibilidade em `langgraph-checkpoint-postgres`
- Compatibilidade exata entre versões de `deepagents` e `langgraph` — **(incerto)** confirme em `python/requirements.txt` ou `pyproject.toml`

---

## G) Analogia

Um agente é como um detetive investigando um caso. O detetive não sabe a resposta de antemão — ele faz perguntas (tool calls), analisa evidências (tool results), e vai refinando sua hipótese (raciocínio) até chegar a uma conclusão (resposta final). A cada nova evidência, ele pode mudar de direção.

O LangGraph é o mapa do escritório do detetive: define quais salas ele pode visitar (nodes), quais portas levam a onde (edges), e o que ele carrega na pasta (state). O deepagents é um assistente que já montou o escritório básico pra você — você só precisa dar as ferramentas certas e as instruções iniciais.

---

## H) Erros Comuns e Como Evitar

| Erro | Causa | Como evitar |
|---|---|---|
| Loop infinito | Sem `recursion_limit` | Sempre defina `recursion_limit` (recomendado: 20–30) |
| Agente esquece o contexto | Sem `thread_id` configurado | Sempre passe `thread_id` no config |
| Tool errada escolhida | Tools demais registradas | Passe apenas as tools relevantes para o agente |
| Agente para sem responder | Edge condicional mal configurada | Verifique se `END` é acessível de todos os estados finais |
| Custo explodindo | Muitas iterações desnecessárias | Limite tools, melhore o system prompt, adicione `recursion_limit` |
| Memória vaza entre usuários | `thread_id` fixo ou ausente | Use `thread_id` único por usuário/conversa |
| Erros de stream | `stream_mode` incompatível com o provider | Teste com `stream_mode=["messages"]` primeiro |

---

## I) Mini-Template Pronto

```python
# ============================================================
# TEMPLATE: Agente com deepagents (caso mais comum)
# Copie, renomeie e adapte
# ============================================================

from omnimind_agents import get_model_for_provider
from omnimind_agents.deep_agent_config import create_omnimind_deep_agent
from langchain_core.tools import tool
import os

# --- 1. Tools (importe as suas) ---
@tool
def minha_tool(param: str) -> str:
    """Descrição da tool. Use quando [condição]."""
    return f"resultado: {param}"

# --- 2. Modelo ---
model = get_model_for_provider(
    provider=os.getenv("LLM_PROVIDER", "anthropic"),
    model=os.getenv("LLM_MODEL", "claude-sonnet-4-6"),
)

# --- 3. Agente ---
agent = create_omnimind_deep_agent(
    model=model,
    system_prompt="[Seu system prompt aqui — ver SystemPromptDoc]",
    # tools=[minha_tool],  # descomente se deepagents aceitar tools custom
)

# --- 4. Invocação ---
async def run(message: str, thread_id: str) -> str:
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 25,
    }
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": message}]},
        config=config,
    )
    return result["messages"][-1].content


# ============================================================
# TEMPLATE: Agente com LangGraph direto (grafo custom)
# ============================================================

from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

class State(TypedDict):
    messages: Annotated[list, add_messages]

tools = [minha_tool]
llm_with_tools = model.bind_tools(tools)

def agent_node(state: State) -> State:
    return {"messages": [llm_with_tools.invoke(state["messages"])]}

def router(state: State) -> str:
    last = state["messages"][-1]
    return "tools" if getattr(last, "tool_calls", None) else END

builder = StateGraph(State)
builder.add_node("agent", agent_node)
builder.add_node("tools", ToolNode(tools))
builder.set_entry_point("agent")
builder.add_conditional_edges("agent", router)
builder.add_edge("tools", "agent")

graph = builder.compile(checkpointer=MemorySaver())
```
