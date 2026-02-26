# OrquestradorDoc

> Camada: 2 — Arquitetura | Depende de: SubAgentsDoc, AgentsDoc | Referenciado por: SkillsDoc, Backends
> Stack: deepagents · LangGraph · LangChain · Python

---

## A) Visão Geral

- O **orquestrador** é o agente responsável por decidir **quem faz o quê** — ele coordena outros agentes/sub-agentes sem executar as tarefas diretamente.
- No OmniMind, o orquestrador vive em `python/omnimind_agents/runtime/swarm_runner.py` — é o ponto de entrada do sistema swarm.
- Existem três padrões principais: **supervisor** (um coordena vários), **pipeline** (sequência fixa de passos) e **reactive** (eventos disparam agentes).
- O orquestrador recebe uma tarefa de alto nível, a decompõe, distribui para especialistas, monitora o progresso e consolida o resultado final.
- Roteamento de tarefas pode ser estático (regras fixas) ou dinâmico (o próprio LLM decide para onde rotear).
- Falhas devem ser tratadas com retry, fallback para agente alternativo, ou escalada para o humano.

---

## B) Conceitos Essenciais

| Termo | Definição |
|---|---|
| **Orquestrador** | Agente de coordenação que delega tarefas sem executá-las diretamente |
| **Supervisor pattern** | Um agente central decide para qual sub-agente rotear cada tarefa |
| **Pipeline pattern** | Tarefas fluem por uma sequência predefinida de agentes (A → B → C) |
| **Reactive pattern** | Eventos disparam agentes específicos — sem coordenador central fixo |
| **Router** | Componente que decide para qual agente enviar uma tarefa com base em regras ou LLM |
| **Dead letter** | Tarefa que falhou em todos os agentes disponíveis — precisa de intervenção humana |
| **Retry** | Tentar novamente a mesma tarefa com o mesmo ou diferente agente |
| **Fallback** | Agente substituto quando o agente principal falha |
| **AGENT_STATE_CHANGE** | Tipo de evento emitido pelo swarm quando um agente muda de estado (ver swarm_runner.py) |
| **PLAN_UPDATE** | Tipo de evento emitido quando o plano de execução avança (ver swarm_runner.py) |

---

## C) Boas Práticas

### DO ✅

- **Orquestrador não executa tarefas** — ele só coordena; execução fica nos sub-agentes
- **Emita eventos de estado** — o frontend precisa saber o que está acontecendo (AGENT_STATE_CHANGE, PLAN_UPDATE)
- **Defina timeouts por sub-agente** — um agente travado não deve paralisar o sistema
- **Implemente fallback** — se o sub-agente preferido falha, tente o alternativo antes de desistir
- **Registre o plano antes de executar** — emita o plano para o frontend antes de começar os sub-agentes
- **Use modelo mais capaz para o orquestrador** — ele toma decisões; vale investir em modelo melhor
- **Use modelo menor para sub-agentes simples** — execução é mais barata com Haiku ou similar

### DON'T ❌

- **Não misture orquestração e execução** — orquestrador que também codifica é difícil de testar e manter
- **Não crie orquestradores com lógica de negócio** — regras de domínio ficam nos sub-agentes ou tools
- **Não ignore falhas de sub-agentes** — erros silenciosos levam a resultados incompletos sem aviso
- **Não crie pipeline fixo para tarefas variáveis** — use supervisor pattern com LLM router para flexibilidade
- **Não emita eventos sem estrutura** — o frontend depende de formato consistente (ver swarm_runner.py)

---

## D) Receitas Reutilizáveis

### Checklist para criar um orquestrador

- [ ] Propósito definido: quais tipos de tarefa ele gerencia
- [ ] Lista de sub-agentes disponíveis com suas especialidades
- [ ] Estratégia de roteamento: estático (if/else) ou dinâmico (LLM decide)
- [ ] Formato de eventos definido (AGENT_STATE_CHANGE, PLAN_UPDATE, etc.)
- [ ] Timeout por sub-agente configurado
- [ ] Fallback definido para cada sub-agente crítico
- [ ] Dead letter policy: o que fazer quando tudo falha
- [ ] Testes de integração: tarefa de ponta a ponta

### Fluxo de decisão: qual pattern usar

```
Tarefas sempre seguem a mesma sequência?
  └── Pipeline (A → B → C)

Um coordenador central decide quem faz o quê?
  └── Supervisor (LLM ou regras fixas)

Eventos externos disparam agentes diferentes?
  └── Reactive (event bus)

Mistura de tudo?
  └── Supervisor + sub-pipelines por especialidade
```

---

## E) Exemplos Práticos

### Exemplo 1 — Supervisor com LLM router (LangGraph)

```python
from typing import Annotated, Literal, TypedDict
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel

# Sub-agentes disponíveis
AGENTS = ["coder", "analyst", "reviewer", "researcher"]

# Schema de decisão do supervisor
class RouterDecision(BaseModel):
    next_agent: Literal["coder", "analyst", "reviewer", "researcher", "FINISH"]
    reason: str

class OrchestratorState(TypedDict):
    messages: Annotated[list, add_messages]
    task: str
    results: dict
    next_agent: str

supervisor_model = ChatAnthropic(model="claude-sonnet-4-6").with_structured_output(RouterDecision)

SUPERVISOR_PROMPT = """Você é um orquestrador. Dado o estado atual da tarefa,
decida qual agente especialista deve agir a seguir.

Agentes disponíveis:
- coder: implementa código
- analyst: analisa requisitos e arquitetura
- reviewer: revisa código e qualidade
- researcher: busca informações externas

Se a tarefa estiver completa, responda FINISH."""

def supervisor_node(state: OrchestratorState) -> OrchestratorState:
    context = f"Tarefa: {state['task']}\nResultados até agora: {state['results']}"
    decision = supervisor_model.invoke([
        {"role": "system", "content": SUPERVISOR_PROMPT},
        {"role": "user", "content": context},
    ])
    return {"next_agent": decision.next_agent}

def route_to_agent(state: OrchestratorState) -> str:
    return state["next_agent"]

def coder_node(state: OrchestratorState) -> OrchestratorState:
    # sub-agente de coding...
    result = run_coder_subagent(state["task"])
    return {"results": {**state.get("results", {}), "coder": result}}

# Grafo
builder = StateGraph(OrchestratorState)
builder.add_node("supervisor", supervisor_node)
builder.add_node("coder", coder_node)
# ... outros nodes ...
builder.set_entry_point("supervisor")
builder.add_conditional_edges(
    "supervisor",
    route_to_agent,
    {"coder": "coder", "analyst": "analyst", "FINISH": END},
)
builder.add_edge("coder", "supervisor")  # volta pro supervisor após execução

orchestrator = builder.compile()
```

---

### Exemplo 2 — Pipeline sequencial simples

```python
# Para tarefas que sempre seguem a mesma ordem:
# análise → implementação → revisão → entrega

from langgraph.graph import StateGraph, END
from typing import TypedDict

class PipelineState(TypedDict):
    task: str
    analysis: str
    code: str
    review: str
    final_output: str

async def analyze(state: PipelineState) -> PipelineState:
    result = await analyst_agent.ainvoke(
        {"messages": [{"role": "user", "content": f"Analise: {state['task']}"}]},
        config={"recursion_limit": 10},
    )
    return {"analysis": result["messages"][-1].content}

async def implement(state: PipelineState) -> PipelineState:
    prompt = f"Tarefa: {state['task']}\nAnálise: {state['analysis']}\nImplemente."
    result = await coder_agent.ainvoke(
        {"messages": [{"role": "user", "content": prompt}]},
        config={"recursion_limit": 15},
    )
    return {"code": result["messages"][-1].content}

async def review(state: PipelineState) -> PipelineState:
    result = await reviewer_agent.ainvoke(
        {"messages": [{"role": "user", "content": f"Revise:\n{state['code']}"}]},
        config={"recursion_limit": 10},
    )
    return {"review": result["messages"][-1].content, "final_output": state["code"]}

builder = StateGraph(PipelineState)
builder.add_node("analyze", analyze)
builder.add_node("implement", implement)
builder.add_node("review", review)
builder.set_entry_point("analyze")
builder.add_edge("analyze", "implement")
builder.add_edge("implement", "review")
builder.add_edge("review", END)

pipeline = builder.compile()
```

---

### Exemplo 3 — Como o swarm_runner.py do OmniMind emite eventos

```python
# Padrão real do projeto — ver python/omnimind_agents/runtime/swarm_runner.py
import json, sys

def emit(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()

# 1. Orquestrador muda de estado
emit({
    "kind": "event",
    "event_type": "AGENT_STATE_CHANGE",
    "agent_id": "orchestrator",
    "payload": {
        "old_state": "pending",
        "new_state": "planning",
        "detail": "Decompondo tarefa em sub-tarefas",
    },
})

# 2. Plano atualizado
emit({
    "kind": "event",
    "event_type": "PLAN_UPDATE",
    "agent_id": "orchestrator",
    "payload": {
        "plan_step": "coding",
        "status": "started",
        "detail": "Agente coder iniciou implementação",
    },
})

# 3. Status geral
emit({"kind": "status", "status": "coding"})
```

---

### Exemplo 4 (RUIM → CORRIGIDO)

```python
# ❌ RUIM — orquestrador que também executa tarefas

async def orchestrate_and_code(task: str) -> str:
    # Decide E implementa — mistura responsabilidades
    if "bug" in task:
        return await fix_bug_directly(task)   # orquestrador executando
    elif "feature" in task:
        return await add_feature(task)         # orquestrador executando
    # Sem tratamento de falha
    # Sem emissão de eventos
    # Sem timeout
```

```python
# ✅ CORRIGIDO — orquestrador puro + sub-agentes especializados

import asyncio

async def orchestrate(task: str, emit_fn) -> str:
    emit_fn({"kind": "status", "status": "planning"})

    # Decide quem executa (não executa ele mesmo)
    agent_type = classify_task(task)  # "bugfix" ou "feature"

    emit_fn({
        "kind": "event",
        "event_type": "AGENT_STATE_CHANGE",
        "agent_id": "orchestrator",
        "payload": {"new_state": "dispatching", "detail": f"Enviando para {agent_type}"},
    })

    try:
        # Timeout explícito
        result = await asyncio.wait_for(
            dispatch_to_agent(agent_type, task),
            timeout=120.0,
        )
        emit_fn({"kind": "status", "status": "done"})
        return result
    except asyncio.TimeoutError:
        emit_fn({"kind": "error", "message": f"Timeout: agente {agent_type} não respondeu em 120s"})
        # Fallback
        return await dispatch_to_agent("fallback_agent", task)
    except Exception as e:
        emit_fn({"kind": "error", "message": f"Falha no orquestrador: {e}"})
        raise

def classify_task(task: str) -> str:
    if any(word in task.lower() for word in ["bug", "erro", "fix", "corrigir"]):
        return "bugfix"
    return "feature"
```

---

## F) Confiabilidade / Anti-Alucinação

### Como validar o orquestrador

- **Teste o roteamento isolado** — dado input X, o orquestrador roteia para o agente correto?
- **Simule falha de sub-agente** — o orquestrador ativa o fallback corretamente?
- **Verifique eventos emitidos** — o frontend recebe todos os estados esperados?
- **Monitore tarefas em dead letter** — quantas tarefas precisaram de intervenção humana?

### Incertezas desta documentação

- LangGraph supervisor pattern pode ter atualizações na API `langgraph-supervisor` (pacote separado). **(incerto)** — confirme disponibilidade e API atual.
- `asyncio.wait_for` + LangGraph async pode ter comportamento específico por versão. **(incerto)** — teste em seu ambiente.

---

## G) Analogia

O orquestrador é como o **maestro de uma orquestra**. Ele não toca nenhum instrumento diretamente — sua função é garantir que cada músico (sub-agente) toque na hora certa, no tempo certo, e que o resultado final seja harmonioso. O maestro decide quando o violino entra, quando a flauta para, e quando toda a orquestra toca junto.

Se um músico erra uma nota (sub-agente falha), o maestro não substitui o músico — ele dá a deixa para o músico tentar novamente ou passa a parte para outro instrumento (fallback). O público (o usuário/frontend) não precisa saber dos detalhes internos — só ouve a música final.

---

## H) Erros Comuns e Como Evitar

| Erro | Causa | Como evitar |
|---|---|---|
| Orquestrador executa tarefas | Mistura responsabilidades | Orquestrador só coordena; sub-agentes executam |
| Sub-agente trava o sistema | Sem timeout | Use `asyncio.wait_for` com timeout explícito |
| Frontend não sabe o que acontece | Sem eventos de estado | Emita AGENT_STATE_CHANGE e PLAN_UPDATE |
| Falha silenciosa | Exceção não propagada | Sempre emita evento de erro antes de fazer fallback |
| Roteamento errado | LLM router sem exemplos | Adicione exemplos no prompt do supervisor (few-shot) |
| Dead letter acumula | Sem política de escalada | Defina: após N falhas, escalada para humano |
| Custos altos | Modelo caro para todos os agentes | Use modelo forte no orquestrador, leve nos sub-agentes |

---

## I) Mini-Template Pronto

```python
# ============================================================
# TEMPLATE: Orquestrador supervisor (LangGraph)
# ============================================================

import asyncio
import json
import sys
from typing import Annotated, Literal, TypedDict
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from pydantic import BaseModel

# --- Tipos de agentes disponíveis ---
AgentName = Literal["agent_a", "agent_b", "FINISH"]

class RouterDecision(BaseModel):
    next: AgentName
    reason: str

class OrchestratorState(TypedDict):
    messages: Annotated[list, add_messages]
    task: str
    results: dict

# --- Emit helper ---
def emit(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()

# --- Supervisor node ---
def supervisor(state: OrchestratorState) -> OrchestratorState:
    decision = router_model.invoke([
        {"role": "system", "content": "Decida qual agente age a seguir ou FINISH."},
        {"role": "user", "content": f"Tarefa: {state['task']}\nResultados: {state['results']}"},
    ])
    emit({"kind": "event", "event_type": "PLAN_UPDATE", "agent_id": "supervisor",
          "payload": {"next": decision.next, "reason": decision.reason}})
    return {"messages": [{"role": "assistant", "content": f"→ {decision.next}: {decision.reason}"}]}

# --- Sub-agente placeholder ---
async def agent_a(state: OrchestratorState) -> OrchestratorState:
    try:
        result = await asyncio.wait_for(
            run_subagent_a(state["task"]),
            timeout=60.0,
        )
        return {"results": {**state.get("results", {}), "agent_a": result}}
    except asyncio.TimeoutError:
        emit({"kind": "error", "message": "agent_a timeout"})
        return {"results": {**state.get("results", {}), "agent_a": "[TIMEOUT]"}}

# --- Grafo ---
def build_orchestrator():
    builder = StateGraph(OrchestratorState)
    builder.add_node("supervisor", supervisor)
    builder.add_node("agent_a", agent_a)
    # builder.add_node("agent_b", agent_b)
    builder.set_entry_point("supervisor")
    builder.add_conditional_edges(
        "supervisor",
        lambda s: s["messages"][-1].content.split("→")[1].split(":")[0].strip()
            if "→" in str(s["messages"][-1].content) else "FINISH",
        {"agent_a": "agent_a", "FINISH": END},
    )
    builder.add_edge("agent_a", "supervisor")
    return builder.compile()

orchestrator = build_orchestrator()
```
