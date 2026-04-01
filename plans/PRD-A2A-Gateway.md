# PRD: A2A Gateway — Interoperabilidade Externa via Agent-to-Agent Protocol

**Versão:** 1.0  
**Data:** 2026-04-01  
**Status:** Draft para aprovação  
**ADR relacionado:** `docs/adr/ADR-002-a2a-gateway.md`  

---

## 1. Sumário

Este documento especifica a implementação de um **A2A Gateway** sobre o backend MindFlow existente — uma camada de API padronizada que expõe os agentes MindFlow (Analyst, Coder, Researcher, Orchestrator) ao ecossistema externo de agentes de IA usando o protocolo Agent-to-Agent (Google, 2025). O gateway não altera a arquitetura interna; funciona como um adaptador que traduz requisições A2A para chamadas ao sistema SPADE/InternalBus já em produção.

---

## 2. Contatos

| Nome | Papel | Responsabilidade |
|------|-------|-----------------|
| Engineering Lead | Dono Técnico | Arquitetura do gateway, revisão de implementação |
| Product Manager | Dono do Produto | Priorização, alinhamento com stakeholders |
| Backend Team | Implementação | Rotas A2A, AgentCard, adaptadores |
| Platform Team | Infraestrutura | Autenticação, rate limiting, observabilidade |
| QA Lead | Qualidade | Testes de conformidade com spec A2A, testes de regressão |

---

## 3. Background

### Por que agora?

O protocolo A2A foi lançado por Google em abril de 2025 e rapidamente se tornou o padrão emergente de interoperabilidade entre sistemas multi-agente. LangGraph, CrewAI, Google ADK, Microsoft AutoGen e outros já publicaram compatibilidade A2A. O ecossistema está crescendo rápido.

### O problema atual

O MindFlow possui quatro agentes especializados (Analyst, Coder, Researcher, Orchestrator) com capacidades únicas — raciocínio profundo, execução de código, pesquisa, orquestração de equipes. Esses agentes hoje são **invisíveis para o ecossistema externo**:

- Não há forma padronizada de outro sistema descobrir que o MindFlow tem um agente de análise de código
- Integrações externas precisam conhecer nossa API proprietária (`/agent/chat/stream`)
- O MindFlow não consegue chamar agentes especializados externos (ex: um agente de busca web de terceiro)
- Ferramentas CLI, notebooks, workflows de CI/CD não conseguem chamar agentes MindFlow de forma interoperável

### O que mudou

O protocolo A2A resolve exatamente esse problema de fronteira externa, sem exigir mudanças na orquestração interna. Analisando o código do MindFlow, descobrimos que **80% das primitivas A2A já existem no codebase** sob diferentes nomes — basta criar a camada de tradução.

---

## 4. Objetivo

### Objetivo Principal

Tornar os agentes MindFlow **descobríveis e chamáveis por qualquer sistema A2A-compatível**, e permitir que agentes MindFlow **consumam capacidades de agentes externos A2A**, sem alterar a arquitetura interna.

### Por que isso importa

- **Para o time:** Reduz o esforço de integração com ferramentas externas de horas para minutos (AgentCard autodocumenta capacidades)
- **Para usuários avançados:** Permite usar agentes MindFlow dentro de workflows LangGraph, notebooks Jupyter com ADK, pipelines de CI/CD
- **Para o produto:** Posiciona MindFlow no ecossistema emergente de agentes interoperáveis

### Como se alinha com a estratégia

Segue a direção do PRD de Orquestração Distribuída (em `PRD-Distributed-Agent-Orchestration.md`) de aumentar autonomia e reduzir acoplamento. O A2A Gateway é o passo natural de abrir essa autonomia para o mundo externo.

### Métricas de Sucesso (OKRs)

| Resultado-Chave | Baseline | Target (3 meses) | Método |
|---|---|---|---|
| Agentes MindFlow chamáveis via A2A | 0 | 4 (Analyst, Coder, Researcher, Orchestrator) | Conformidade com spec A2A |
| Tempo para integrar sistema externo | ~8h (API customizada) | < 30min (AgentCard) | Medido em PoC com LangGraph |
| Compatibilidade A2A Task lifecycle | 0% | 100% (todos os estados) | Testes de integração |
| Overhead de latência do gateway | N/A | < 50ms P99 | Benchmarks |
| Regressão na API legada | 0 falhas | 0 falhas | Suite existente |

---

## 5. Segmentos de Mercado

### Segmento Primário: Desenvolvedores que constroem sistemas multi-agente

**Quem são:** Engenheiros e pesquisadores que usam LangGraph, CrewAI, Google ADK ou frameworks próprios para orquestrar múltiplos agentes de IA especializados.

**O trabalho deles:** Querem montar pipelines onde diferentes agentes especializados colaboram em tarefas complexas — um agente pesquisa, outro analisa código, outro executa. Hoje precisam escrever adaptadores custom para cada combinação de frameworks.

**Restrições:**
- Precisam de API estável e documentada
- Não querem gerenciar credenciais proprietárias por sistema
- Precisam de streaming para tarefas longas (não podem aguardar resposta síncrona)

### Segmento Secundário: Usuários power do MindFlow que usam CLI e automação

**Quem são:** Desenvolvedores que já usam o MindFlow CLI (`mindflow_cli`) e querem integrar agentes MindFlow em scripts, webhooks de GitHub Actions, ou ferramentas internas.

**O trabalho deles:** Automatizar tarefas repetitivas (code review, análise de PR, pesquisa de documentação) chamando agentes MindFlow de pipelines automatizados.

**Restrições:**
- Precisam de endpoints HTTP simples e previsíveis
- Não querem manter o frontend aberto para usar os agentes

---

## 6. Proposta de Valor

### O que os desenvolvedores ganham

**Antes do A2A Gateway:**
- Para chamar um agente MindFlow de um sistema externo: estudar a API proprietária, entender o formato de eventos SSE específico, implementar autenticação custom, descobrir manualmente quais agentes existem e o que fazem
- Para usar um agente externo dentro do MindFlow: impossível sem código custom no backend

**Depois do A2A Gateway:**
- Para chamar um agente MindFlow: `GET /.well-known/agent.json` revela tudo → enviar `POST /a2a/tasks/send` com a tarefa → receber resultado estruturado
- Para usar um agente externo: o `DelegationEngine` A2A Client chama qualquer agente A2A-compatível como se fosse nativo

### Problemas eliminados

- ❌ "Preciso ler o código do MindFlow para entender como integrar" → ✅ AgentCard autodocumenta
- ❌ "Não sei como tratar o streaming do MindFlow no meu sistema" → ✅ SSE padronizado A2A
- ❌ "Preciso manter a sessão aberta para tarefas longas" → ✅ Webhooks push notifications (Fase C)
- ❌ "Meu agente de busca externa não se conecta com MindFlow" → ✅ A2A Client no DelegationEngine

### Vantagem sobre alternativas

| Alternativa | Problema | Como A2A resolve |
|---|---|---|
| API proprietária atual | Requer conhecimento profundo do MindFlow | AgentCard = autodocumentação padronizada |
| OpenAPI genérica | Não expressa capacidades de agentes, sem streaming nativo | A2A = semântica de agente nativa |
| gRPC | Não interoperável entre vendors | A2A = protocolo aberto multi-vendor |
| AgentOS/Agno layer | Requer migração de arquitetura interna | A2A Gateway = zero impacto interno |

---

## 7. Solução

### 7.1 UX / Fluxo do Desenvolvedor

**Fluxo 1: Descoberta de agentes (Developer Experience)**

```
1. Desenvolvedor externo quer usar o Coder MindFlow em seu sistema LangGraph
2. GET https://mindflow.example.com/.well-known/agent.json
3. Recebe AgentCard: nome, descrição, skills, URL, auth requirements
4. Configura LangGraph para usar o endpoint A2A
5. Pronto — sem leitura de docs adicionais
```

**Fluxo 2: Execução de task com streaming**

```
1. Sistema externo envia POST /a2a/tasks/sendSubscribe
   Body: { "message": { "role": "user", "parts": [{ "text": "Analyze this PR..." }] } }
2. MindFlow abre SSE stream
3. Events chegam: TaskStatusUpdateEvent (working) → chunks de resposta → TaskArtifactUpdateEvent (completed)
4. Cliente recebe resultado estruturado com Artifact contendo análise
```

**Fluxo 3: Agente MindFlow chamando agente externo**

```
1. Orchestrator decide que precisa de busca web especializada
2. DelegationEngine A2A Client chama agente externo A2A (ex: Tavily Search Agent)
3. Resultado retorna como DelegationResult normal
4. Orchestrator integra no contexto como qualquer outra delegação
```

### 7.2 Funcionalidades por Fase

---

#### Fase A — AgentCard + Task Core (Semanas 1–2) — P0

**A1. AgentCard Registry**

Endpoint: `GET /.well-known/agent.json`  
Parâmetro opcional: `?agent=coder` (retorna card de agente específico)

O AgentCard é gerado dinamicamente a partir de `list_agent_runtime_policies()` — dados que já existem no sistema.

Estrutura do AgentCard para o Coder:
```json
{
  "name": "MindFlow Coder",
  "description": "Specialized software engineering agent. Writes, refactors, debugs and reviews code with tool access.",
  "url": "https://mindflow.example.com/a2a",
  "version": "1.0.0",
  "skills": [
    {
      "id": "coding_task",
      "name": "Code Generation & Execution",
      "description": "Write, refactor, debug and test code. Access to file system tools."
    },
    {
      "id": "bug_fix",
      "name": "Bug Investigation & Fix",
      "description": "Analyze stack traces, identify root cause, implement and validate fix."
    }
  ],
  "defaultInputModes": ["text/plain"],
  "defaultOutputModes": ["text/plain", "application/json"],
  "capabilities": {
    "streaming": true,
    "pushNotifications": false,
    "stateTransitionHistory": false
  },
  "authentication": {
    "schemes": ["bearer"]
  }
}
```

**Mapeamento de agentes → AgentCards:**
- `coder` → Coder Agent Card (skills: coding_task, bug_fix, code_review)
- `analyst` → Analyst Agent Card (skills: analysis, deep_investigation, security_audit)
- `researcher` → Researcher Agent Card (skills: research, comparison, web_search)
- `orchestrator` → Orchestrator Agent Card (skills: team_session, delegation, planning)

---

**A2. A2A Task Router**

Endpoints:
- `POST /a2a/tasks/send` — task síncrona (aguarda conclusão, retorna resultado)
- `POST /a2a/tasks/sendSubscribe` — task com SSE streaming
- `GET /a2a/tasks/{task_id}` — consulta status de task

**Mapeamento de estados (100% compatível com código existente):**

```
A2A Task Status    ←→    MindFlow DelegationStatus
─────────────────────────────────────────────────────
submitted          ←→    pending
working            ←→    in_progress
input-required     ←→    (novo — para multi-turn)
completed          ←→    completed
failed             ←→    failed
cancelled          ←→    cancelled
```

**Adaptação de formato:**

```python
# Entrada A2A → MindFlow
def a2a_task_to_delegation_task(a2a_message: A2AMessage) -> DelegationTask:
    return DelegationTask(
        objective=a2a_message.parts[0].text,
        agent=AgentType(a2a_message.target_agent),
        session_id=a2a_message.context_id,   # ← OrchestratorSession existente
        task_id=uuid4(),
    )

# MindFlow → Saída A2A
def delegation_result_to_a2a_artifact(result: DelegationResult) -> A2AArtifact:
    return A2AArtifact(
        parts=[
            TextPart(text=result.key_findings),      # ← já existe
            DataPart(data={"full_output": result.full_output,  # ← já existe
                           "confidence": result.confidence,
                           "tokens": result.tokens_consumed}),
        ]
    )
```

---

**A3. A2A Stream Adapter**

O MindFlow já emite SSE com `format_sse()`. O adapter envolve os eventos existentes no formato A2A:

```
MindFlow StreamEvent          →   A2A SSE Event
─────────────────────────────────────────────────────
type="agent_step"             →   TaskStatusUpdateEvent(status=working)
type="response" (chunk)       →   TaskArtifactUpdateEvent(artifact.append=true)
type="thinking"               →   TaskStatusUpdateEvent(status=working, message=thinking)
type="tool_call"              →   TaskStatusUpdateEvent(status=working, message=tool_use)
type="done"                   →   TaskStatusUpdateEvent(status=completed) + final Artifact
type="error"                  →   TaskStatusUpdateEvent(status=failed, error=...)
```

Reutiliza o `event_generator()` existente em `agent_controller.py` — apenas wrapping de formato, zero lógica nova.

---

#### Fase B — Multi-turn + Artifacts ricos (Semanas 3–4) — P1

**B1. Suporte a `input-required` (multi-turn)**

Quando um agente MindFlow precisa de mais informação durante a execução (ex: Coder precisa saber qual linguagem usar), a Task entra em `input-required`. O cliente pode enviar uma mensagem adicional para a mesma task sem criar uma nova.

Mapeamento: `OrchestratorSession.session_checkpoints` → `Task.history` A2A.

**B2. Artifacts ricos por tipo de agente**

| Agente | Artifact Adicional |
|---|---|
| Coder | `FilePart` com código gerado (quando agente escreve arquivo) |
| Analyst | `DataPart` com estrutura JSON da análise (gaps, symbols, files_analyzed) |
| Researcher | `DataPart` com fontes e referências |
| Orchestrator | `DataPart` com Mission DAG summary |

---

#### Fase C — Push Notifications + A2A Client (Mês 2–3) — P2

**C1. Push Notifications (Webhooks)**

Para Team Sessions longas (minutos), o cliente pode registrar uma URL de webhook no momento da criação da task. O MindFlow POSTa o resultado final na URL quando a task completa.

Caso de uso: GitHub Actions que inicia uma Team Session para code review — não precisa manter conexão SSE aberta.

**C2. A2A Client no DelegationEngine**

Permite ao Orchestrator delegar para agentes externos A2A-compatíveis como se fossem agentes nativos.

```python
# DelegationEngine detecta agente externo
if task.agent_id.startswith("a2a://"):
    result = await a2a_client.send_task(
        agent_url=task.agent_id,
        message=task.objective,
        context_id=session_id,
    )
    return DelegationResult.from_a2a_artifact(result)
```

Casos de uso imediatos:
- Researcher → chama agente Tavily (busca web)
- Coder → chama agente de sandboxed code execution (E2B, Modal)
- Analyst → chama agente de análise de segurança especializado

---

### 7.3 Tecnologia

**Dependências novas (mínimas):**
- `a2a-sdk-python` (SDK oficial Google A2A) — ou implementação direta do spec (leve, < 500 linhas)
- Nenhuma dependência de infraestrutura nova (zero Docker, zero servidores externos)

**Arquivos novos:**
```
python/mindflow_backend/
  api/
    v1/
      a2a.py                      ← Router FastAPI (/a2a/*)
    controllers/
      a2a_controller.py           ← Lógica de negócio do gateway
  communication/
    a2a/
      __init__.py
      agent_card_registry.py      ← AgentCard gerado de runtime_policy
      task_adapter.py             ← DelegationTask ↔ A2A Task
      stream_adapter.py           ← StreamEvent → A2A SSE events
      a2a_client.py               ← (Fase C) cliente para agentes externos
  schemas/
    a2a/
      __init__.py
      agent_card.py               ← Pydantic models para AgentCard
      task.py                     ← Pydantic models para A2A Task/Message/Artifact
```

**Arquivos modificados (mínimos):**
```
python/mindflow_backend/api/main.py       ← incluir router /a2a
python/mindflow_backend/api/main.py       ← servir /.well-known/agent.json
python/mindflow_backend/orchestrator/delegation/engine.py  ← (Fase C) A2A client hook
```

### 7.4 Premissas

| Premissa | Risco se falsa | Como validar |
|---|---|---|
| Spec A2A não mudará significativamente em 6 meses | Médio — retrabalho de schema | Versionar endpoint `/a2a/v1/*`, monitorar releases |
| `runtime_policy.py` contém metadados suficientes para AgentCard útil | Baixo — já tem CommRole e MissionGraphType | PoC: gerar AgentCard e validar contra spec |
| LangGraph aceita o AgentCard gerado como válido | Médio — risco de incompatibilidade | PoC de integração na Fase A antes de marcar done |
| SSE adapter não adiciona latência perceptível | Baixo — é só wrapping de strings | Benchmark: < 5ms de overhead |
| Equipe tem capacidade de 2 semanas para Fase A | — | Confirmar antes de iniciar |

---

## 8. Release

### Fase A — MVP (Semanas 1–2)
**Escopo:** AgentCard para todos os agentes + Task endpoint (send + sendSubscribe) + SSE stream adapter  
**Critério de done:** LangGraph consegue descobrir e chamar Coder MindFlow com sucesso  
**Risco:** Baixo — 80% reutiliza código existente

### Fase B — Completude (Semanas 3–4)
**Escopo:** Multi-turn (input-required), Artifacts ricos por tipo de agente, cancelamento de task  
**Critério de done:** 100% de conformidade com A2A spec v0.2+  
**Risco:** Baixo — extensão incremental do MVP

### Fase C — Poder Avançado (Mês 2–3)
**Escopo:** Push notifications (webhooks), A2A Client no DelegationEngine (agentes externos)  
**Critério de done:** Orchestrator consegue delegar para agente Tavily externo via A2A  
**Risco:** Médio — A2A Client exige gestão de credenciais externas e timeouts de rede

### O que fica fora do escopo (v1)
- ❌ OAuth2 completo — Bearer token existente é suficiente inicialmente
- ❌ Rate limiting específico por agente A2A — usar rate limiting global existente
- ❌ Interface de administração para gerenciar AgentCards
- ❌ Federação (múltiplas instâncias MindFlow descobríveis entre si)

---

## Apêndice A: Compatibilidade de Features A2A Extraídas para MindFlow

Esta tabela lista **todos os elementos do protocolo A2A** e avalia o que extrair para o MindFlow, com justificativa técnica baseada no código existente.

| Feature A2A | Extrair? | Justificativa |
|---|---|---|
| **AgentCard** | ✅ Sim — Fase A | `runtime_policy.py` já tem todos os metadados. Custo mínimo, valor máximo. |
| **Task lifecycle (6 estados)** | ✅ Sim — Fase A | `DelegationStatus` já tem 5/6 estados. Adicionar `input-required` é trivial. |
| **Message/Parts (text)** | ✅ Sim — Fase A | Mensagens texto são o caso de uso principal. Mapeamento direto. |
| **SSE Streaming** | ✅ Sim — Fase A | MindFlow já usa SSE. A2A usa mesmo formato. É apenas wrapping de eventos. |
| **context_id (multi-turn)** | ✅ Sim — Fase A | `session_id` já existe. Mapping trivial. |
| **Artifact (TextPart)** | ✅ Sim — Fase A | `DelegationResult.key_findings` → TextPart. Direto. |
| **Artifact (DataPart/JSON)** | ✅ Sim — Fase B | `DelegationResult.full_output`, `files_analyzed`, `confidence` → DataPart. |
| **Artifact (FilePart)** | ✅ Sim — Fase B | Coder já escreve arquivos. Expor como FilePart agrega valor para clientes externos. |
| **input-required state** | ✅ Sim — Fase B | Habilita multi-turn real. Mapeia para `OrchestratorSession.session_checkpoints`. |
| **Task history** | ✅ Sim — Fase B | `OrchestratorSession` já acumula checkpoints de sessão. |
| **Push notifications (webhooks)** | ✅ Sim — Fase C | Crítico para Team Sessions longas em pipelines automatizados. |
| **A2A Client (chamar externos)** | ✅ Sim — Fase C | Unlock estratégico: Researcher pode usar web search agents, Coder pode usar sandbox agents. |
| **stateTransitionHistory** | 🔴 Não — v1 | Overhead sem demanda clara. Reavaliar com usuários. |
| **AgentCard federation** | 🔴 Não — v1 | Complexidade alta, casos de uso internos não justificam. |
| **OAuth2 completo** | 🔴 Não — v1 | Bearer token existente suficiente. OAuth2 para Fase C quando houver clientes externos reais. |
| **Streaming para send (não subscribe)** | 🔴 Não — v1 | `tasks/send` retorna resultado síncrono. Streaming só via `sendSubscribe`. |

---

## Apêndice B: Estrutura de Testes

```
tests/
  integration/
    a2a/
      test_agent_card.py          ← AgentCard válido por spec, um por agente
      test_task_lifecycle.py      ← Todos os estados: submitted→working→completed
      test_sse_streaming.py       ← Chunks chegam em ordem, sem perda
      test_multi_turn.py          ← input-required → resposta → completed
      test_artifact_types.py      ← TextPart, DataPart por tipo de agente
      test_langraph_compat.py     ← PoC com LangGraph real
  unit/
    a2a/
      test_task_adapter.py        ← DelegationTask ↔ A2A Task
      test_stream_adapter.py      ← StreamEvent → A2A SSE events
      test_agent_card_registry.py ← AgentCard gerado de runtime_policy
```

---

**Autor:** Engineering Team / Claude  
**Revisão:** Pendente  
**Aprovação:** Pendente  
**Próximo passo:** Validar Fase A com PoC LangGraph (estimativa: 2 semanas)
