# OrquestradorDoc

> Camada: 2 — Arquitetura | Depende de: SubAgentsDoc, AgentsDoc | Referenciado por: SkillsDoc, Backends
> Stack: deepagents · LangGraph · LangChain · TypeScript

---

## A) Visão Geral

- O **orquestrador** é o agente responsável por decidir **quem faz o quê** — ele coordena outros agentes/sub-agentes sem executar as tarefas diretamente.
- No OmniMind, o orquestrador vive em `src/server/swarm/orchestrator.ts` — é o ponto de entrada do sistema swarm.
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
| **AGENT_STATE_CHANGE** | Tipo de evento emitido pelo swarm quando um agente muda de estado (ver orchestrator.ts) |
| **PLAN_UPDATE** | Tipo de evento emitido quando o plano de execução avança (ver orchestrator.ts) |

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
- **Não emita eventos sem estrutura** — o frontend depende de formato consistente (ver orchestrator.ts)

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

```typescript
import { Annotation, StateGraph, END } from "@langchain/langgraph";
import { ChatAnthropic } from "@langchain/anthropic";
import { z } from "zod";

// Sub-agentes disponíveis
const AGENTS = ["coder", "analyst", "reviewer", "researcher"] as const;
type AgentName = typeof AGENTS[number] | "FINISH";

// Schema de decisão do supervisor (Zod em vez de Pydantic)
const RouterDecisionSchema = z.object({
  next_agent: z.enum(["coder", "analyst", "reviewer", "researcher", "FINISH"]),
  reason: z.string(),
});

// Estado do orquestrador via Annotation.Root (padrão do projeto)
const OrchestratorAnnotation = Annotation.Root({
  messages: Annotation<{ role: string; content: string }[]>({
    reducer: (a, b) => [...a, ...b],
    default: () => [],
  }),
  task: Annotation<string>({ default: () => "" }),
  results: Annotation<Record<string, unknown>>({ default: () => ({}) }),
  next_agent: Annotation<string>({ default: () => "" }),
});

type OrchestratorState = typeof OrchestratorAnnotation.State;

const supervisorModel = new ChatAnthropic({ model: "claude-sonnet-4-6" }).withStructuredOutput(
  RouterDecisionSchema
);

const SUPERVISOR_PROMPT = `Você é um orquestrador. Dado o estado atual da tarefa,
decida qual agente especialista deve agir a seguir.

Agentes disponíveis:
- coder: implementa código
- analyst: analisa requisitos e arquitetura
- reviewer: revisa código e qualidade
- researcher: busca informações externas

Se a tarefa estiver completa, responda FINISH.`;

async function supervisorNode(state: OrchestratorState): Promise<Partial<OrchestratorState>> {
  const context = `Tarefa: ${state.task}\nResultados até agora: ${JSON.stringify(state.results)}`;
  const decision = await supervisorModel.invoke([
    { role: "system", content: SUPERVISOR_PROMPT },
    { role: "user", content: context },
  ]);
  return { next_agent: decision.next_agent };
}

function routeToAgent(state: OrchestratorState): string {
  return state.next_agent;
}

async function coderNode(state: OrchestratorState): Promise<Partial<OrchestratorState>> {
  // sub-agente de coding...
  const result = await runCoderSubagent(state.task);
  return { results: { ...state.results, coder: result } };
}

// Grafo
const builder = new StateGraph(OrchestratorAnnotation);
builder.addNode("supervisor", supervisorNode);
builder.addNode("coder", coderNode);
// ... outros nodes ...
builder.setEntryPoint("supervisor");
builder.addConditionalEdges("supervisor", routeToAgent, {
  coder: "coder",
  analyst: "analyst",
  FINISH: END,
});
builder.addEdge("coder", "supervisor"); // volta pro supervisor após execução

const orchestrator = builder.compile();
```

---

### Exemplo 2 — Pipeline sequencial simples

```typescript
// Para tarefas que sempre seguem a mesma ordem:
// análise → implementação → revisão → entrega

import { Annotation, StateGraph, END } from "@langchain/langgraph";

const PipelineAnnotation = Annotation.Root({
  task: Annotation<string>({ default: () => "" }),
  analysis: Annotation<string>({ default: () => "" }),
  code: Annotation<string>({ default: () => "" }),
  review: Annotation<string>({ default: () => "" }),
  final_output: Annotation<string>({ default: () => "" }),
});

type PipelineState = typeof PipelineAnnotation.State;

async function analyze(state: PipelineState): Promise<Partial<PipelineState>> {
  const result = await analystAgent.invoke(
    { messages: [{ role: "user", content: `Analise: ${state.task}` }] },
    { recursionLimit: 10 }
  );
  return { analysis: result.messages.at(-1)?.content as string };
}

async function implement(state: PipelineState): Promise<Partial<PipelineState>> {
  const prompt = `Tarefa: ${state.task}\nAnálise: ${state.analysis}\nImplemente.`;
  const result = await coderAgent.invoke(
    { messages: [{ role: "user", content: prompt }] },
    { recursionLimit: 15 }
  );
  return { code: result.messages.at(-1)?.content as string };
}

async function review(state: PipelineState): Promise<Partial<PipelineState>> {
  const result = await reviewerAgent.invoke(
    { messages: [{ role: "user", content: `Revise:\n${state.code}` }] },
    { recursionLimit: 10 }
  );
  return {
    review: result.messages.at(-1)?.content as string,
    final_output: state.code,
  };
}

const builder = new StateGraph(PipelineAnnotation);
builder.addNode("analyze", analyze);
builder.addNode("implement", implement);
builder.addNode("review", review);
builder.setEntryPoint("analyze");
builder.addEdge("analyze", "implement");
builder.addEdge("implement", "review");
builder.addEdge("review", END);

const pipeline = builder.compile();
```

---

### Exemplo 3 — Como o orchestrator.ts do OmniMind emite eventos

```typescript
// Padrão real do projeto — ver src/server/swarm/orchestrator.ts

function emit(payload: Record<string, unknown>): void {
  process.stdout.write(JSON.stringify(payload) + "\n");
}

// 1. Orquestrador muda de estado
emit({
  kind: "event",
  event_type: "AGENT_STATE_CHANGE",
  agent_id: "orchestrator",
  payload: {
    old_state: "pending",
    new_state: "planning",
    detail: "Decompondo tarefa em sub-tarefas",
  },
});

// 2. Plano atualizado
emit({
  kind: "event",
  event_type: "PLAN_UPDATE",
  agent_id: "orchestrator",
  payload: {
    plan_step: "coding",
    status: "started",
    detail: "Agente coder iniciou implementação",
  },
});

// 3. Status geral
emit({ kind: "status", status: "coding" });
```

---

### Exemplo 4 (RUIM → CORRIGIDO)

```typescript
// ❌ RUIM — orquestrador que também executa tarefas

async function orchestrateAndCode(task: string): Promise<string> {
  // Decide E implementa — mistura responsabilidades
  if (task.includes("bug")) {
    return fixBugDirectly(task);   // orquestrador executando
  } else if (task.includes("feature")) {
    return addFeature(task);       // orquestrador executando
  }
  // Sem tratamento de falha
  // Sem emissão de eventos
  // Sem timeout
  return "";
}
```

```typescript
// ✅ CORRIGIDO — orquestrador puro + sub-agentes especializados

async function orchestrate(
  task: string,
  emitFn: (payload: Record<string, unknown>) => void
): Promise<string> {
  emitFn({ kind: "status", status: "planning" });

  // Decide quem executa (não executa ele mesmo)
  const agentType = classifyTask(task); // "bugfix" ou "feature"

  emitFn({
    kind: "event",
    event_type: "AGENT_STATE_CHANGE",
    agent_id: "orchestrator",
    payload: { new_state: "dispatching", detail: `Enviando para ${agentType}` },
  });

  try {
    // Timeout explícito com Promise.race
    const result = await Promise.race([
      dispatchToAgent(agentType, task),
      new Promise<never>((_, reject) =>
        setTimeout(() => reject(new Error("Timeout")), 120_000)
      ),
    ]);
    emitFn({ kind: "status", status: "done" });
    return result;
  } catch (err) {
    if (err instanceof Error && err.message === "Timeout") {
      emitFn({ kind: "error", message: `Timeout: agente ${agentType} não respondeu em 120s` });
      // Fallback
      return dispatchToAgent("fallback_agent", task);
    }
    emitFn({ kind: "error", message: `Falha no orquestrador: ${String(err)}` });
    throw err;
  }
}

function classifyTask(task: string): string {
  const lower = task.toLowerCase();
  if (["bug", "erro", "fix", "corrigir"].some((w) => lower.includes(w))) {
    return "bugfix";
  }
  return "feature";
}
```

---

## F) Confiabilidade / Anti-Alucinação

### Como validar o orquestrador

- **Teste o roteamento isolado** — dado input X, o orquestrador roteia para o agente correto?
- **Simule falha de sub-agente** — o orquestrador ativa o fallback corretamente?
- **Verifique eventos emitidos** — o frontend recebe todos os estados esperados?
- **Monitore tarefas em dead letter** — quantas tarefas precisaram de intervenção humana?

### Incertezas desta documentação

- LangGraph supervisor pattern pode ter atualizações na API `@langchain/langgraph` (pacote ativo). **(incerto)** — confirme disponibilidade e API atual.
- `Promise.race` com timeout + LangGraph async pode ter comportamento específico por versão. **(incerto)** — teste em seu ambiente.

---

## G) Analogia

O orquestrador é como o **maestro de uma orquestra**. Ele não toca nenhum instrumento diretamente — sua função é garantir que cada músico (sub-agente) toque na hora certa, no tempo certo, e que o resultado final seja harmonioso. O maestro decide quando o violino entra, quando a flauta para, e quando toda a orquestra toca junto.

Se um músico erra uma nota (sub-agente falha), o maestro não substitui o músico — ele dá a deixa para o músico tentar novamente ou passa a parte para outro instrumento (fallback). O público (o usuário/frontend) não precisa saber dos detalhes internos — só ouve a música final.

---

## H) Erros Comuns e Como Evitar

| Erro | Causa | Como evitar |
|---|---|---|
| Orquestrador executa tarefas | Mistura responsabilidades | Orquestrador só coordena; sub-agentes executam |
| Sub-agente trava o sistema | Sem timeout | Use `Promise.race` com timeout explícito |
| Frontend não sabe o que acontece | Sem eventos de estado | Emita AGENT_STATE_CHANGE e PLAN_UPDATE |
| Falha silenciosa | Exceção não propagada | Sempre emita evento de erro antes de fazer fallback |
| Roteamento errado | LLM router sem exemplos | Adicione exemplos no prompt do supervisor (few-shot) |
| Dead letter acumula | Sem política de escalada | Defina: após N falhas, escalada para humano |
| Custos altos | Modelo caro para todos os agentes | Use modelo forte no orquestrador, leve nos sub-agentes |

---

## I) Mini-Template Pronto

```typescript
// ============================================================
// TEMPLATE: Orquestrador supervisor (LangGraph TypeScript)
// ============================================================

import { Annotation, StateGraph, END } from "@langchain/langgraph";
import { z } from "zod";

// --- Tipos de agentes disponíveis ---
const AgentNameSchema = z.enum(["agent_a", "agent_b", "FINISH"]);
type AgentName = z.infer<typeof AgentNameSchema>;

const RouterDecisionSchema = z.object({
  next: AgentNameSchema,
  reason: z.string(),
});

// --- Estado via Annotation.Root ---
const OrchestratorAnnotation = Annotation.Root({
  messages: Annotation<{ role: string; content: string }[]>({
    reducer: (a, b) => [...a, ...b],
    default: () => [],
  }),
  task: Annotation<string>({ default: () => "" }),
  results: Annotation<Record<string, unknown>>({ default: () => ({}) }),
});

type OrchestratorState = typeof OrchestratorAnnotation.State;

// --- Emit helper ---
function emit(payload: Record<string, unknown>): void {
  process.stdout.write(JSON.stringify(payload) + "\n");
}

// --- Supervisor node ---
async function supervisor(
  state: OrchestratorState
): Promise<Partial<OrchestratorState>> {
  const decision = await routerModel.invoke([
    { role: "system", content: "Decida qual agente age a seguir ou FINISH." },
    {
      role: "user",
      content: `Tarefa: ${state.task}\nResultados: ${JSON.stringify(state.results)}`,
    },
  ]);
  emit({
    kind: "event",
    event_type: "PLAN_UPDATE",
    agent_id: "supervisor",
    payload: { next: decision.next, reason: decision.reason },
  });
  return {
    messages: [{ role: "assistant", content: `→ ${decision.next}: ${decision.reason}` }],
  };
}

// --- Sub-agente placeholder ---
async function agentA(
  state: OrchestratorState
): Promise<Partial<OrchestratorState>> {
  try {
    const result = await Promise.race([
      runSubagentA(state.task),
      new Promise<never>((_, reject) =>
        setTimeout(() => reject(new Error("Timeout")), 60_000)
      ),
    ]);
    return { results: { ...state.results, agent_a: result } };
  } catch {
    emit({ kind: "error", message: "agent_a timeout" });
    return { results: { ...state.results, agent_a: "[TIMEOUT]" } };
  }
}

// --- Grafo ---
function buildOrchestrator() {
  const builder = new StateGraph(OrchestratorAnnotation);
  builder.addNode("supervisor", supervisor);
  builder.addNode("agent_a", agentA);
  // builder.addNode("agent_b", agentB);
  builder.setEntryPoint("supervisor");
  builder.addConditionalEdges(
    "supervisor",
    (s) => {
      const last = s.messages.at(-1)?.content ?? "";
      const match = last.match(/→ (\w+):/);
      return match ? match[1] : "FINISH";
    },
    { agent_a: "agent_a", FINISH: END }
  );
  builder.addEdge("agent_a", "supervisor");
  return builder.compile();
}

const orchestrator = buildOrchestrator();
```
