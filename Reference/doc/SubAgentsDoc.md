# SubAgentsDoc

> Camada: 2 — Arquitetura | Depende de: AgentsDoc, ToolsDoc | Referenciado por: OrquestradorDoc
> Stack: deepagents · LangGraph · LangChain · TypeScript

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
| **Promise.all** | Função TypeScript para executar Promises em paralelo e aguardar todas |
| **Send API** | API do LangGraph para distribuir trabalho para múltiplos nodes em paralelo |
| **Interrupt** | Ponto de pausa no grafo onde um humano (ou outro agente) pode intervir |

---

## C) Boas Práticas

### DO ✅

- **Dê um propósito único e bem definido a cada sub-agente** — "analisa código", "escreve testes", "revisa PR"
- **Passe apenas o contexto necessário** — sub-agente de revisão não precisa do histórico de 50 mensagens do agente pai
- **Use fan-out para tarefas independentes** — se análise e busca não dependem uma da outra, rode em paralelo
- **Limite o `recursionLimit` do sub-agente** — um sub-agente com loop infinito trava o agente pai
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
- [ ] `recursionLimit` definido (menor que o do pai — ex: 10)
- [ ] Tratamento de erro no pai caso o sub-agente falhe
- [ ] Teste isolado do sub-agente antes de integrar

### Padrão fan-out / fan-in

```
1. Agente pai recebe tarefa grande
2. Divide em N sub-tarefas independentes
3. Dispara N sub-agentes em paralelo (Promise.all ou LangGraph Send)
4. Aguarda todos terminarem
5. Consolidar resultados no agente pai
6. Agente pai produz resposta final
```

---

## E) Exemplos Práticos

### Exemplo 1 — Sub-agente como tool (padrão mais simples)

```typescript
// O agente pai invoca o sub-agente como se fosse uma tool
// Útil quando o sub-agente é bem definido e sempre retorna string
// Arquivo: src/server/swarm/reviewer.ts

import { tool } from "@langchain/core/tools";
import { z } from "zod";
import { getModelForProvider } from "@/server/agent/providers";
import { createOmniMindDeepAgent } from "@/server/agent/deep-agent-config";

function createReviewerSubagent() {
  const model = getModelForProvider({ provider: "anthropic", model: "claude-haiku-4-5-20251001" }); // modelo menor = mais barato
  return createOmniMindDeepAgent({
    model,
    systemPrompt:
      "Você é um revisor de código especializado. " +
      "Analise o código fornecido e retorne uma lista de problemas encontrados. " +
      "Seja objetivo e conciso. Formato: lista com bullets.",
  });
}

const reviewer = createReviewerSubagent();

const reviewCode = tool(
  async ({ code }: { code: string }): Promise<string> => {
    const result = await reviewer.invoke(
      { messages: [{ role: "user", content: `Revise este código:\n\n\`\`\`\n${code}\n\`\`\`` }] },
      { recursionLimit: 10 }
    );
    return result.messages[result.messages.length - 1].content as string;
  },
  {
    name: "review_code",
    description:
      "Revisa um trecho de código e retorna problemas encontrados. " +
      "Use quando o usuário pede revisão de código. " +
      "Retorna lista de issues ou 'Nenhum problema encontrado'.",
    schema: z.object({
      code: z.string().describe("Trecho de código a ser revisado"),
    }),
  }
);

// O agente pai registra reviewCode como tool normal
```

---

### Exemplo 2 — Sub-agente como subgraph (LangGraph nativo)

```typescript
import { Annotation, StateGraph, END } from "@langchain/langgraph";
import { BaseMessage } from "@langchain/core/messages";
import { ChatAnthropic } from "@langchain/anthropic";

// --- Sub-agente: Analisa código ---
const AnalystState = Annotation.Root({
  code: Annotation<string>(),
  analysis: Annotation<string>(),
});

const analystModel = new ChatAnthropic({ model: "claude-haiku-4-5-20251001" });

async function analystNode(state: typeof AnalystState.State) {
  const result = await analystModel.invoke([
    { role: "system", content: "Analise o código e identifique a complexidade e riscos." },
    { role: "user", content: state.code },
  ]);
  return { analysis: result.content as string };
}

const analystGraph = new StateGraph(AnalystState)
  .addNode("analyze", analystNode)
  .addEdge("__start__", "analyze")
  .addEdge("analyze", END);

const analystSubgraph = analystGraph.compile();

// --- Agente pai: usa o subgraph como node ---
const ParentState = Annotation.Root({
  messages: Annotation<BaseMessage[]>({
    reducer: (left, right) => left.concat(right),
  }),
  codeToReview: Annotation<string>(),
  analysisResult: Annotation<string>(),
});

async function runAnalyst(state: typeof ParentState.State) {
  // Invoca o subgraph com contexto reduzido
  const result = await analystSubgraph.invoke({ code: state.codeToReview });
  return { analysisResult: result.analysis };
}

const parentGraph = new StateGraph(ParentState)
  .addNode("analyst", runAnalyst);
// ... adicione outros nodes ...
```

---

### Exemplo 3 — Fan-out paralelo com Promise.all

```typescript
// Arquivo: src/server/swarm/orchestrator.ts

import { getModelForProvider } from "@/server/agent/providers";
import { createOmniMindDeepAgent } from "@/server/agent/deep-agent-config";

async function runParallelSubagents(task: string): Promise<Record<string, string>> {
  /**
   * Roda 3 sub-agentes em paralelo:
   * - Analista: identifica problemas
   * - Pesquisador: busca contexto externo
   * - Revisor: verifica qualidade
   */
  const modelFast = getModelForProvider({ provider: "anthropic", model: "claude-haiku-4-5-20251001" });

  const analyst = createOmniMindDeepAgent({ model: modelFast, systemPrompt: "Analise problemas no código." });
  const researcher = createOmniMindDeepAgent({ model: modelFast, systemPrompt: "Busque contexto relevante." });
  const reviewerAgent = createOmniMindDeepAgent({ model: modelFast, systemPrompt: "Revise a qualidade geral." });

  const config = { recursionLimit: 10 };
  const inputMsg = { messages: [{ role: "user" as const, content: task }] };

  // Executa todos em paralelo; falhas individuais não cancelam as demais
  const [analysisResult, researchResult, reviewResult] = await Promise.allSettled([
    analyst.invoke(inputMsg, config),
    researcher.invoke(inputMsg, config),
    reviewerAgent.invoke(inputMsg, config),
  ]);

  function safeExtract(result: PromiseSettledResult<{ messages: BaseMessage[] }>): string {
    if (result.status === "rejected") {
      return `[ERRO] Sub-agente falhou: ${result.reason}`;
    }
    const msgs = result.value.messages;
    return msgs[msgs.length - 1].content as string;
  }

  return {
    analysis: safeExtract(analysisResult),
    research: safeExtract(researchResult),
    review: safeExtract(reviewResult),
  };
}
```

---

### Exemplo 4 (RUIM → CORRIGIDO)

```typescript
// ❌ RUIM — sub-agente recebe contexto completo desnecessário

async function runReviewerBad(fullConversationHistory: BaseMessage[], code: string): Promise<string> {
  const reviewer = createOmniMindDeepAgent({ model: bigModel, systemPrompt: "Revise." });
  // Passa 50 mensagens de histórico que o revisor não precisa
  const result = await reviewer.invoke({
    messages: [
      ...fullConversationHistory,
      { role: "user", content: `Revise: ${code}` },
    ],
  });
  return result.messages[result.messages.length - 1].content as string;
}
```

**Problemas:**
1. Passa histórico completo — aumenta custo e confunde o sub-agente
2. Usa modelo grande para tarefa pequena
3. Sem `recursionLimit` — sub-agente pode loopear

```typescript
// ✅ CORRIGIDO — sub-agente com escopo mínimo
// Arquivo: src/server/swarm/reviewer.ts

async function runReviewer(code: string): Promise<string> {
  /** Sub-agente de revisão com contexto mínimo. */
  const modelSmall = getModelForProvider({ provider: "anthropic", model: "claude-haiku-4-5-20251001" });
  const reviewerAgent = createOmniMindDeepAgent({
    model: modelSmall,
    systemPrompt:
      "Você é um revisor de código. Analise o código e liste problemas. " +
      "Seja direto. Formato: bullets.",
  });
  try {
    const result = await reviewerAgent.invoke(
      { messages: [{ role: "user", content: `Revise:\n\`\`\`\n${code}\n\`\`\`` }] },
      { recursionLimit: 8 }
    );
    return result.messages[result.messages.length - 1].content as string;
  } catch (err: unknown) {
    return `[ERRO] Revisor falhou: ${(err as Error).message}`;
  }
}
```

---

## F) Confiabilidade / Anti-Alucinação

### Como validar sub-agentes

- **Teste cada sub-agente isoladamente** antes de integrar no pai — se ele falha sozinho, vai falhar no sistema
- **Valide o formato do output** — se o pai espera JSON, o sub-agente deve sempre retornar JSON válido
- **Monitore latência** — sub-agentes lentos travam o fan-in; adicione timeout
- **Use `Promise.allSettled()`** para que a falha de um não cancele os outros

### Quando perguntar vs assumir

- Sub-agente não deve pedir mais contexto ao usuário — ele deve trabalhar com o que recebeu ou retornar erro estruturado
- Se falta informação: retorne `JSON.stringify({ status: "incomplete", reason: "Código não fornecido" })` e deixe o pai decidir

### Incertezas desta documentação

- LangGraph Send API para fan-out tem sintaxe que pode variar entre versões. **(incerto)** — confirme em `@langchain/langgraph>=0.2` docs.
- `createOmniMindDeepAgent` pode não suportar tools custom diretamente — **(incerto)** verifique `src/server/agent/deep-agent-config.ts`.

---

## G) Analogia

Um sub-agente é como um **consultor especialista** contratado por um gerente de projetos. O gerente (agente pai) não sabe tudo sobre segurança de redes — então quando surge um problema de segurança, ele liga para o consultor de segurança (sub-agente), passa o contexto específico do problema, e aguarda o parecer.

O consultor não precisa saber do histórico completo da empresa — só o que é relevante para resolver o problema de segurança. E o gerente pode contratar vários consultores ao mesmo tempo (fan-out): o de segurança, o de performance e o de custo trabalham em paralelo, e o gerente consolida os pareceres (fan-in) antes de tomar a decisão final.

---

## H) Erros Comuns e Como Evitar

| Erro | Causa | Como evitar |
|---|---|---|
| Sub-agente loopeia e trava o pai | Sem `recursionLimit` | Defina `recursionLimit` menor que o do pai |
| Fan-out cancela tudo se um falha | `Promise.all` sem tratamento de rejeição | Use `Promise.allSettled()` |
| Sub-agente confuso por contexto excessivo | Histórico completo passado | Passe apenas o contexto específico da tarefa |
| Custo alto em sub-agentes simples | Modelo grande para tarefa pequena | Use modelo menor (Haiku) para sub-agentes de tarefas simples |
| Output do sub-agente não parseável | Formato livre, pai espera JSON | Instrua no system prompt a retornar formato específico |
| Race condition em estado compartilhado | Múltiplos sub-agentes escrevendo no mesmo objeto | Use estado imutável ou sincronização explícita |
| Debug impossível | Muitos níveis de aninhamento | Limite a 2–3 níveis; adicione logging por nível |

---

## I) Mini-Template Pronto

```typescript
// ============================================================
// TEMPLATE: Sub-agente como tool para o agente pai
// Arquivo: src/server/swarm/orchestrator.ts
// ============================================================

import { tool } from "@langchain/core/tools";
import { z } from "zod";
import { getModelForProvider } from "@/server/agent/providers";
import { createOmniMindDeepAgent } from "@/server/agent/deep-agent-config";
import { BaseMessage } from "@langchain/core/messages";

// --- Criação do sub-agente (instancia uma vez, reutiliza) ---
const subagentModel = getModelForProvider({ provider: "anthropic", model: "claude-haiku-4-5-20251001" });
const subagent = createOmniMindDeepAgent({
  model: subagentModel,
  systemPrompt:
    "Você é especialista em [ESPECIALIDADE]. " +
    "Receba [TIPO DE INPUT] e retorne [TIPO DE OUTPUT]. " +
    "Formato de saída: [bullets / JSON / texto livre]. " +
    "Seja conciso.",
});

export const invokeSpecialist = tool(
  async ({ taskDescription }: { taskDescription: string }): Promise<string> => {
    try {
      const result = await subagent.invoke(
        { messages: [{ role: "user", content: taskDescription }] },
        { recursionLimit: 10 }
      );
      return result.messages[result.messages.length - 1].content as string;
    } catch (err: unknown) {
      return `[ERRO] Especialista falhou: ${(err as Error).constructor.name}: ${(err as Error).message}`;
    }
  },
  {
    name: "invoke_specialist",
    description:
      "Invoca o especialista em [ESPECIALIDADE] para processar a tarefa. " +
      "Use quando [condição de uso]. " +
      "Retorna [descrição do output].",
    schema: z.object({
      taskDescription: z.string().describe("Descrição completa da tarefa para o especialista"),
    }),
  }
);


// ============================================================
// TEMPLATE: Fan-out paralelo
// ============================================================

async function runFanout(
  task: string,
  agents: Array<{ invoke: (input: unknown, config: unknown) => Promise<{ messages: BaseMessage[] }> }>
): Promise<string[]> {
  /**
   * Executa N sub-agentes em paralelo e retorna lista de resultados.
   * Falhas individuais não cancelam os demais.
   */
  const inputMsg = { messages: [{ role: "user" as const, content: task }] };
  const config = { recursionLimit: 10 };

  const results = await Promise.allSettled(
    agents.map((agent) => agent.invoke(inputMsg, config))
  );

  return results.map((r) => {
    if (r.status === "rejected") {
      return `[ERRO] ${r.reason}`;
    }
    const msgs = r.value.messages;
    return msgs[msgs.length - 1].content as string;
  });
}
```
