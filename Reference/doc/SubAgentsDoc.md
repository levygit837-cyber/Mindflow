# SubAgentsDoc

> Camada: 2 — Arquitetura | Depende de: AgentsDoc, ToolsDoc | Referenciado por: OrquestradorDoc
> Stack: deepagents · LangGraph · LangChain · Python

---

## A) Visão Geral

- Um **sub-agente** é um agente invocado por outro agente — ele aparece como uma tool para o agente chamador, mas por dentro é um agente completo com seu próprio loop de raciocínio.
- Sub-agentes permitem **dividir tarefas complexas** em especialistas independentes: um agente de análise, um de escrita, um de revisão.
- LangGraph suporta sub-agentes nativamente como **subgraphs** — grafos dentro de grafos.
- O padrão **fan-out / fan-in** executa múltiplos sub-agentes em paralelo e consolida os resultados.
- Sub-agentes têm escopo reduzido: recebem apenas o contexto necessário para sua tarefa, não o histórico completo do agente pai.
- A comunicação entre sub-agentes é feita via **estado compartilhado**, **mensagens passadas como argumento**, ou **eventos emitidos**.

---

## B) Conceitos Essenciais

| Termo | Definição |
|---|---|
| **Sub-agente** | Agente invocado por outro agente como se fosse uma tool especializada |
| **Subgraph** | Grafo LangGraph compilado e inserido como node dentro de um grafo maior |
| **Fan-out** | Disparar múltiplos sub-agentes em paralelo para tarefas independentes |
| **Fan-in** | Coletar e consolidar os resultados dos sub-agentes paralelos |
| **Scoped context** | Contexto reduzido enviado ao sub-agente — só o necessário para sua tarefa |
| **Parent agent** | O agente que invoca o sub-agente |
| **Handoff** | Transferência de controle do agente pai para o sub-agente |
| **asyncio.gather** | Função Python para executar coroutines em paralelo e aguardar todas |
| **Send API** | API do LangGraph para distribuir trabalho para múltiplos nodes em paralelo |
| **Interrupt** | Ponto de pausa no grafo onde um humano (ou outro agente) pode intervir |

---

## C) Boas Práticas

### DO ✅

- **Dê um propósito único e bem definido a cada sub-agente** — "analisa código", "escreve testes", "revisa PR"
- **Passe apenas o contexto necessário** — sub-agente de revisão não precisa do histórico de 50 mensagens do agente pai
- **Use fan-out para tarefas independentes** — se análise e busca não dependem uma da outra, rode em paralelo
- **Limite o `recursion_limit` do sub-agente** — um sub-agente com loop infinito trava o agente pai
- **Retorne resultado estruturado** — o agente pai precisa processar o output; use JSON ou formato previsível
- **Trate falhas de sub-agente no pai** — se o sub-agente falhar, o pai deve ter fallback

### DON'T ❌

- **Não crie sub-agente para tarefas simples** — uma tool direta é mais rápido e mais barato
- **Não compartilhe estado mutável sem sincronização** — sub-agentes paralelos escrevendo no mesmo objeto causam race conditions
- **Não passe o histórico completo do pai para o sub-agente** — aumenta custo e confunde o sub-agente
- **Não ignore timeouts** — sub-agentes lentos ou travados devem ter timeout explícito
- **Não anninhe sub-agentes demais** — mais de 3 níveis de profundidade torna debug impossível

---

## D) Receitas Reutilizáveis

### Checklist para criar um sub-agente

- [ ] Propósito único definido em uma frase
- [ ] System prompt específico para a tarefa do sub-agente (não o system prompt do pai)
- [ ] Input bem definido: o que o pai envia para o sub-agente
- [ ] Output bem definido: o que o sub-agente retorna para o pai
- [ ] `recursion_limit` definido (menor que o do pai — ex: 10)
- [ ] Tratamento de erro no pai caso o sub-agente falhe
- [ ] Teste isolado do sub-agente antes de integrar

### Padrão fan-out / fan-in

```
1. Agente pai recebe tarefa grande
2. Divide em N sub-tarefas independentes
3. Dispara N sub-agentes em paralelo (asyncio.gather ou LangGraph Send)
4. Aguarda todos terminarem
5. Consolidar resultados no agente pai
6. Agente pai produz resposta final
```

---

## E) Exemplos Práticos

### Exemplo 1 — Sub-agente como tool (padrão mais simples)

```python
# O agente pai invoca o sub-agente como se fosse uma tool
# Útil quando o sub-agente é bem definido e sempre retorna string

from langchain_core.tools import tool
from omnimind_agents import get_model_for_provider
from omnimind_agents.deep_agent_config import create_omnimind_deep_agent

def create_reviewer_subagent():
    model = get_model_for_provider("anthropic", "claude-haiku-4-5-20251001")  # modelo menor = mais barato
    return create_omnimind_deep_agent(
        model=model,
        system_prompt=(
            "Você é um revisor de código especializado. "
            "Analise o código fornecido e retorne uma lista de problemas encontrados. "
            "Seja objetivo e conciso. Formato: lista com bullets."
        ),
    )

reviewer = create_reviewer_subagent()

@tool
async def review_code(code: str) -> str:
    """Revisa um trecho de código e retorna problemas encontrados.
    Use quando o usuário pede revisão de código.
    Retorna lista de issues ou 'Nenhum problema encontrado'.
    """
    result = await reviewer.ainvoke({
        "messages": [{"role": "user", "content": f"Revise este código:\n\n```\n{code}\n```"}]
    }, config={"recursion_limit": 10})
    return result["messages"][-1].content

# O agente pai registra review_code como tool normal
```

---

### Exemplo 2 — Sub-agente como subgraph (LangGraph nativo)

```python
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

# --- Sub-agente: Analisa código ---
class AnalystState(TypedDict):
    code: str
    analysis: str

def analyst_node(state: AnalystState) -> AnalystState:
    result = analyst_model.invoke([
        {"role": "system", "content": "Analise o código e identifique a complexidade e riscos."},
        {"role": "user", "content": state["code"]},
    ])
    return {"analysis": result.content}

analyst_graph = StateGraph(AnalystState)
analyst_graph.add_node("analyze", analyst_node)
analyst_graph.set_entry_point("analyze")
analyst_graph.add_edge("analyze", END)
analyst_subgraph = analyst_graph.compile()

# --- Agente pai: usa o subgraph como node ---
class ParentState(TypedDict):
    messages: Annotated[list, add_messages]
    code_to_review: str
    analysis_result: str

def run_analyst(state: ParentState) -> ParentState:
    # Invoca o subgraph com contexto reduzido
    result = analyst_subgraph.invoke({"code": state["code_to_review"]})
    return {"analysis_result": result["analysis"]}

parent_graph = StateGraph(ParentState)
parent_graph.add_node("analyst", run_analyst)
# ... adicione outros nodes ...
```

---

### Exemplo 3 — Fan-out paralelo com asyncio.gather

```python
import asyncio
from omnimind_agents import get_model_for_provider
from omnimind_agents.deep_agent_config import create_omnimind_deep_agent

async def run_parallel_subagents(task: str) -> dict:
    """
    Roda 3 sub-agentes em paralelo:
    - Analista: identifica problemas
    - Pesquisador: busca contexto externo
    - Revisor: verifica qualidade
    """
    model_fast = get_model_for_provider("anthropic", "claude-haiku-4-5-20251001")

    analyst = create_omnimind_deep_agent(model=model_fast, system_prompt="Analise problemas no código.")
    researcher = create_omnimind_deep_agent(model=model_fast, system_prompt="Busque contexto relevante.")
    reviewer = create_omnimind_deep_agent(model=model_fast, system_prompt="Revise a qualidade geral.")

    config = {"recursion_limit": 10}
    input_msg = {"messages": [{"role": "user", "content": task}]}

    # Executa todos em paralelo
    results = await asyncio.gather(
        analyst.ainvoke(input_msg, config=config),
        researcher.ainvoke(input_msg, config=config),
        reviewer.ainvoke(input_msg, config=config),
        return_exceptions=True,  # não cancela tudo se um falhar
    )

    # Processa resultados (trata falhas individualmente)
    analysis_result, research_result, review_result = results

    def safe_extract(result) -> str:
        if isinstance(result, Exception):
            return f"[ERRO] Sub-agente falhou: {result}"
        return result["messages"][-1].content

    return {
        "analysis": safe_extract(analysis_result),
        "research": safe_extract(research_result),
        "review": safe_extract(review_result),
    }
```

---

### Exemplo 4 (RUIM → CORRIGIDO)

```python
# ❌ RUIM — sub-agente recebe contexto completo desnecessário

async def run_reviewer(full_conversation_history: list, code: str) -> str:
    reviewer = create_omnimind_deep_agent(model=big_model, system_prompt="Revise.")
    # Passa 50 mensagens de histórico que o revisor não precisa
    result = await reviewer.ainvoke({
        "messages": full_conversation_history + [
            {"role": "user", "content": f"Revise: {code}"}
        ]
    })
    return result["messages"][-1].content
```

**Problemas:**
1. Passa histórico completo — aumenta custo e confunde o sub-agente
2. Usa modelo grande para tarefa pequena
3. Sem `recursion_limit` — sub-agente pode loopear

```python
# ✅ CORRIGIDO — sub-agente com escopo mínimo

async def run_reviewer(code: str) -> str:
    """Sub-agente de revisão com contexto mínimo."""
    model_small = get_model_for_provider("anthropic", "claude-haiku-4-5-20251001")
    reviewer = create_omnimind_deep_agent(
        model=model_small,
        system_prompt=(
            "Você é um revisor de código. Analise o código e liste problemas. "
            "Seja direto. Formato: bullets."
        ),
    )
    try:
        result = await reviewer.ainvoke(
            {"messages": [{"role": "user", "content": f"Revise:\n```\n{code}\n```"}]},
            config={"recursion_limit": 8},
        )
        return result["messages"][-1].content
    except Exception as e:
        return f"[ERRO] Revisor falhou: {e}"
```

---

## F) Confiabilidade / Anti-Alucinação

### Como validar sub-agentes

- **Teste cada sub-agente isoladamente** antes de integrar no pai — se ele falha sozinho, vai falhar no sistema
- **Valide o formato do output** — se o pai espera JSON, o sub-agente deve sempre retornar JSON válido
- **Monitore latência** — sub-agentes lentos travam o fan-in; adicione timeout
- **Use `return_exceptions=True`** no `asyncio.gather` para que a falha de um não cancele os outros

### Quando perguntar vs assumir

- Sub-agente não deve pedir mais contexto ao usuário — ele deve trabalhar com o que recebeu ou retornar erro estruturado
- Se falta informação: retorne `{"status": "incomplete", "reason": "Código não fornecido"}` e deixe o pai decidir

### Incertezas desta documentação

- LangGraph Send API para fan-out tem sintaxe que pode variar entre versões. **(incerto)** — confirme em `langgraph>=0.2` docs.
- `create_omnimind_deep_agent` pode não suportar tools custom diretamente — **(incerto)** verifique `deep_agent_config.py`.

---

## G) Analogia

Um sub-agente é como um **consultor especialista** contratado por um gerente de projetos. O gerente (agente pai) não sabe tudo sobre segurança de redes — então quando surge um problema de segurança, ele liga para o consultor de segurança (sub-agente), passa o contexto específico do problema, e aguarda o parecer.

O consultor não precisa saber do histórico completo da empresa — só o que é relevante para resolver o problema de segurança. E o gerente pode contratar vários consultores ao mesmo tempo (fan-out): o de segurança, o de performance e o de custo trabalham em paralelo, e o gerente consolida os pareceres (fan-in) antes de tomar a decisão final.

---

## H) Erros Comuns e Como Evitar

| Erro | Causa | Como evitar |
|---|---|---|
| Sub-agente loopeia e trava o pai | Sem `recursion_limit` | Defina `recursion_limit` menor que o do pai |
| Fan-out cancela tudo se um falha | `asyncio.gather` sem `return_exceptions` | Use `return_exceptions=True` |
| Sub-agente confuso por contexto excessivo | Histórico completo passado | Passe apenas o contexto específico da tarefa |
| Custo alto em sub-agentes simples | Modelo grande para tarefa pequena | Use modelo menor (Haiku) para sub-agentes de tarefas simples |
| Output do sub-agente não parseável | Formato livre, pai espera JSON | Instrua no system prompt a retornar formato específico |
| Race condition em estado compartilhado | Múltiplos sub-agentes escrevendo no mesmo dict | Use estado imutável ou sincronização explícita |
| Debug impossível | Muitos níveis de aninhamento | Limite a 2–3 níveis; adicione logging por nível |

---

## I) Mini-Template Pronto

```python
# ============================================================
# TEMPLATE: Sub-agente como tool para o agente pai
# ============================================================

import asyncio
from langchain_core.tools import tool
from omnimind_agents import get_model_for_provider
from omnimind_agents.deep_agent_config import create_omnimind_deep_agent

# --- Criação do sub-agente (instancia uma vez, reutiliza) ---
_subagent_model = get_model_for_provider("anthropic", "claude-haiku-4-5-20251001")
_subagent = create_omnimind_deep_agent(
    model=_subagent_model,
    system_prompt=(
        "Você é especialista em [ESPECIALIDADE]. "
        "Receba [TIPO DE INPUT] e retorne [TIPO DE OUTPUT]. "
        "Formato de saída: [bullets / JSON / texto livre]. "
        "Seja conciso."
    ),
)

@tool
async def invoke_specialist(task_description: str) -> str:
    """Invoca o especialista em [ESPECIALIDADE] para processar a tarefa.
    Use quando [condição de uso].
    Retorna [descrição do output].
    """
    try:
        result = await _subagent.ainvoke(
            {"messages": [{"role": "user", "content": task_description}]},
            config={"recursion_limit": 10},
        )
        return result["messages"][-1].content
    except Exception as e:
        return f"[ERRO] Especialista falhou: {type(e).__name__}: {e}"


# ============================================================
# TEMPLATE: Fan-out paralelo
# ============================================================

async def run_fanout(task: str, subagents: list) -> list[str]:
    """
    Executa N sub-agentes em paralelo e retorna lista de resultados.
    Falhas individuais não cancelam os demais.
    """
    input_msg = {"messages": [{"role": "user", "content": task}]}
    config = {"recursion_limit": 10}

    results = await asyncio.gather(
        *[agent.ainvoke(input_msg, config=config) for agent in subagents],
        return_exceptions=True,
    )

    def extract(r) -> str:
        if isinstance(r, Exception):
            return f"[ERRO] {r}"
        return r["messages"][-1].content

    return [extract(r) for r in results]
```
