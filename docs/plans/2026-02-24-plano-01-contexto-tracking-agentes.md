# Plano 01 — Contexto e Tracking (LangChain/LangGraph End-to-End)

Data base: 24/02/2026

## 1) Objetivo
Padronizar contexto e observabilidade para agentes complexos com rastreabilidade completa de ponta a ponta, sem ambiguidade entre backend e frontend.

Resultado esperado: qualquer execução deve poder ser reconstruída por eventos e contexto versionado.

---

## 2) Mapa real de uso de frameworks no projeto

## 2.1 Fluxo `agent` (chat principal)
1. Entrada HTTP: `src/app/api/agent/chat/route.ts`
2. Modelo LangChain: `src/lib/agent/providers.ts` (`ChatVertexAI`, `ChatAnthropic`, `ChatOpenAI`, `ChatGoogleGenerativeAI`, `ChatOllama`)
3. Agente deepagents + backend de tools: `src/lib/agent/deep-agent-config.ts`
4. Checkpoint LangGraph/Postgres: `src/lib/db/postgres.ts` (`PostgresSaver`)
5. Streaming: `agent.stream(..., { streamMode: ["messages", "updates"] })`
6. Normalização de chunks LangChain: `src/lib/agent/chat-stream-normalizer.ts`
7. SSE para UI: `src/lib/agent/stream.ts`
8. Estado frontend: `src/hooks/use-agent-chat.ts` + `src/stores/agent-store.ts`

## 2.2 Fluxo `swarm` (grafo multiagente)
1. Criação de task: `src/app/api/swarm/route.ts`
2. Grafo LangGraph: `src/lib/swarm/graph.ts` (`StateGraph`, `START`, `END`)
3. Estado anotado LangGraph: `src/lib/swarm/state.ts` (`Annotation.Root`)
4. Nós com deepagents + LangChain messages:
   - `src/lib/swarm/coder.ts`
   - `src/lib/swarm/live-analyst.ts`
   - `src/lib/swarm/reviewer.ts`
   - `src/lib/swarm/orchestrator.ts` (nó determinístico)
5. Eventos e replay: `src/lib/swarm/notifier.ts` + `src/app/api/swarm/[taskId]/stream/route.ts`
6. Estado frontend: `src/hooks/use-swarm-stream.ts` + `src/stores/swarm-store.ts`

## 2.3 Tools LangChain usadas
1. Tool `search_web` no chat: `src/lib/agent/tools/search-web.ts` (`tool()` + `zod`)
2. Tools do coder/reviewer/analyst no swarm:
   - `src/lib/swarm/tools/coder-tools.ts`
   - `src/lib/swarm/tools/reviewer-tools.ts`
   - `src/lib/swarm/tools/analyst-tools.ts`

---

## 3) Problema atual de contexto/observabilidade
1. Existem dois modelos de evento (`StreamEvent` no agent e `NotificationEvent` no swarm) sem contrato único global.
2. Parte importante de estado ainda é in-memory (conversas/settings/registry), reduzindo reprodutibilidade.
3. O frontend mistura “estado renderizado” com “estado de auditoria”, dificultando replay confiável.

---

## 4) Contrato único de contexto (padrão obrigatório)

```json
{
  "trace_id": "uuid",
  "session_id": "uuid",
  "conversation_id": "uuid",
  "task_id": "uuid",
  "mode": "agent|swarm",
  "goal": "string",
  "constraints": ["string"],
  "acceptance_criteria": ["string"],
  "working_memory": {
    "current_plan": "string",
    "open_questions": ["string"],
    "latest_decisions": ["string"]
  },
  "tool_policy": {
    "allow": ["string"],
    "deny": ["string"]
  },
  "version": "v1",
  "updated_at": "ISO"
}
```

Regra: sempre atualizar `working_memory` após cada `TOOL_CALL_FINISHED`.

---

## 5) Contrato único de evento (padrão obrigatório)

```json
{
  "event_id": "uuid",
  "trace_id": "uuid",
  "task_id": "uuid",
  "agent_id": "orchestrator|coder|reviewer|agent",
  "event_type": "STATE_TRANSITION|TOOL_CALL_STARTED|TOOL_CALL_FINISHED|MODEL_TOKEN|...",
  "sequence": 0,
  "payload": {},
  "created_at": "ISO"
}
```

Tipos mínimos:
1. `TASK_CREATED`
2. `STATE_TRANSITION`
3. `MODEL_REQUESTED`
4. `MODEL_TOKEN`
5. `TOOL_CALL_STARTED`
6. `TOOL_CALL_FINISHED`
7. `DECISION_RECORDED`
8. `TASK_COMPLETED`
9. `TASK_FAILED`

---

## 6) Implementação recomendada

## 6.1 Backend
1. Criar `src/shared/events/contracts.ts` (Zod schemas).
2. Criar `src/shared/events/event-bus.ts` (publicação única para agent+swarm).
3. Criar `src/shared/events/event-repository.ts` (persistência SQL).
4. Rotas `app/api/*` só validam entrada e chamam casos de uso.
5. Remover emissão de eventos ad-hoc fora da camada de application.

## 6.2 Frontend
1. Separar store de `timeline de auditoria` da store de `UI render`.
2. Renderizar por `sequence`, não por ordem de chegada da rede.
3. Suportar replay por `Last-Event-ID` para ambos os modos.

---

## 7) Estrutura de pastas alvo (curto prazo)

```text
src/
  modules/
    agent/
      application/
      infrastructure/
      interface/
    swarm/
      application/
      infrastructure/
      interface/
  shared/
    events/
    llm/
    tools/
    observability/
    security/
    types/
  app/
    api/
```

Decisão: nesta fase inicial, evitar mover tudo para `domain` se ainda não houver regras de negócio maduras; começar por `application/infrastructure/interface`.

---

## 8) Critérios de aceite
1. Uma execução pode ser reconstruída do início ao fim só por eventos persistidos.
2. `agent` e `swarm` seguem o mesmo contrato de evento.
3. Reconexão frontend não perde histórico de execução.
4. Contexto permanece controlado (sem crescimento ilimitado de prompt).
