# AgentsDoc

> Camada: 1 — Fundação | Depende de: ToolsDoc | Referenciado por: SubAgentsDoc, OrquestradorDoc, MemoryDoc, SystemPromptDoc
> Stack: deepagents · LangGraph · LangChain · TypeScript

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
| **createDeepAgent** | Função do deepagents que cria um agente completo com LangGraph por baixo |
| **streamMode** | Como o agente emite eventos durante a execução (messages, updates, values, debug) |
| **checkpointer** | Componente que salva o estado do agente entre execuções — habilita memória persistente |

---

## C) Boas Práticas

### DO ✅

- **Defina um propósito claro para cada agente** — um agente de coding faz coding; um de busca faz busca
- **Use o system prompt para definir personalidade e limites** — ver SystemPromptDoc
- **Passe apenas as tools necessárias** — tools irrelevantes confundem o LLM e aumentam o contexto
- **Use `streamMode` adequado** — para UI em tempo real use `messages`; para debug use `debug`
- **Configure `threadId` para memória por conversa** — permite o agente lembrar de sessões anteriores
- **Trate erros de tool no próprio agente** — o agente deve tentar outra abordagem se uma tool falhar
- **Limite o número de iterações** — use `recursionLimit` para evitar loops infinitos

### DON'T ❌

- **Não misture responsabilidades** — agente de chat não deve também orquestrar sub-agentes
- **Não passe todas as tools disponíveis** — escolha as relevantes para o propósito do agente
- **Não ignore o `recursionLimit`** — sem ele, bugs de lógica viram loops infinitos e custo infinito
- **Não hardcode o model** — use variável de configuração (ver Backends.md)
- **Não assuma que o agente sempre termina** — sempre tenha um timeout ou limite de steps

---

## D) Receitas Reutilizáveis

### Checklist para criar um novo agente

- [ ] Propósito definido em uma frase
- [ ] System prompt escrito (ver SystemPromptDoc)
- [ ] Lista de tools selecionadas (só as necessárias)
- [ ] Provider e model configurados via env vars
- [ ] `threadId` configurado para isolamento de conversa
- [ ] `recursionLimit` definido (padrão LangGraph: 25)
- [ ] Stream mode escolhido para o contexto de uso
- [ ] Teste de integração básico (input → output esperado)

### Fluxo de decisão: deepagents vs LangGraph direto

```
Precisa de algo simples (chat, task)?
  └── Use createDeepAgent (deepagents)

Precisa de grafo custom (branching, paralelo, estados complexos)?
  └── Use StateGraph (LangGraph) diretamente

Precisa de múltiplos agentes coordenados?
  └── Ver SubAgentsDoc + OrquestradorDoc
```

---

## E) Exemplos Práticos

### Exemplo 1 — Agente simples com deepagents

```typescript
// Agente de chat básico — o caso mais comum no OmniMind
// Arquivo: src/server/agent/stream.ts

import { getModelForProvider } from "@/server/agent/providers";
import { buildStaticSystemPrompt } from "@/server/agent/prompts/base";
import { createOmniMindDeepAgent } from "@/server/agent/deep-agent-config";

// 1. Modelo (provedor configurado via env vars)
const model = getModelForProvider({ provider: "anthropic", model: "claude-sonnet-4-6" });

// 2. Agente
const agent = createOmniMindDeepAgent({
  model,
  systemPrompt: buildStaticSystemPrompt(),
});

// 3. Invocar com stream
async function* chat(message: string, threadId = "default") {
  const stream = agent.streamEvents(
    { messages: [{ role: "user", content: message }] },
    {
      configurable: { thread_id: threadId },
      recursionLimit: 25,
      streamMode: ["messages", "updates"],
    }
  );
  for await (const chunk of stream) {
    yield chunk;
  }
}
```

---

### Exemplo 2 — Agente com LangGraph direto (grafo custom)

```typescript
import { Annotation, StateGraph, END } from "@langchain/langgraph";
import { ToolNode } from "@langchain/langgraph/prebuilt";
import { ChatAnthropic } from "@langchain/anthropic";
import { tool } from "@langchain/core/tools";
import { z } from "zod";
import { readFileSync } from "fs";
import { BaseMessage } from "@langchain/core/messages";

// 1. Estado do agente
const AgentState = Annotation.Root({
  messages: Annotation<BaseMessage[]>({
    reducer: (left, right) => left.concat(right), // acumula, não substitui
  }),
});

// 2. Tool registrada
const readFileTool = tool(
  async ({ path }: { path: string }): Promise<string> => {
    try {
      return readFileSync(path, "utf-8");
    } catch {
      return `[ERRO] Não encontrado: ${path}`;
    }
  },
  {
    name: "read_file",
    description: "Lê um arquivo local.",
    schema: z.object({ path: z.string() }),
  }
);

const tools = [readFileTool];

// 3. Modelo com tools vinculadas
const model = new ChatAnthropic({ model: "claude-sonnet-4-6" }).bindTools(tools);

// 4. Nodes
function callLlm(state: typeof AgentState.State) {
  const response = model.invoke(state.messages);
  return { messages: [response] };
}

function shouldContinue(state: typeof AgentState.State): string {
  const last = state.messages[state.messages.length - 1];
  if ("tool_calls" in last && Array.isArray((last as any).tool_calls) && (last as any).tool_calls.length > 0) {
    return "tools";
  }
  return END;
}

// 5. Grafo
const graph = new StateGraph(AgentState)
  .addNode("llm", callLlm)
  .addNode("tools", new ToolNode(tools))
  .addEdge("__start__", "llm")
  .addConditionalEdges("llm", shouldContinue)
  .addEdge("tools", "llm"); // após tool, volta pro LLM

const agent = graph.compile();
```

---

### Exemplo 3 — Agente com checkpointer (memória persistente)

```typescript
import { MemorySaver } from "@langchain/langgraph";
import { StateGraph } from "@langchain/langgraph";

// MemorySaver = em memória (dev/teste)
// PostgresSaver via @langchain/langgraph-checkpoint-postgres = persiste em banco (produção real) — (incerto) confirme disponibilidade

const checkpointer = new MemorySaver();

const graph = new StateGraph(AgentState);
// ... adicione nodes e edges ...
const agent = graph.compile({ checkpointer });

// threadId isola a memória por conversa
const config = { configurable: { thread_id: "conversa-123" } };
const result = await agent.invoke(
  { messages: [{ role: "user", content: "Olá" }] },
  config
);
```

---

### Exemplo 4 (RUIM → CORRIGIDO)

```typescript
// ❌ RUIM — agente genérico sem limites

import { createDeepAgent } from "deepagents";
import { ALL_TOOLS_EVER_CREATED } from "./allTools"; // todas as tools do projeto

const agent = createDeepAgent({
  model,
  systemPrompt: "Você é um assistente.", // system prompt vago
  tools: ALL_TOOLS_EVER_CREATED,         // 40 tools registradas
  name: "agent",
});
// Sem recursionLimit → loop infinito possível
// Sem threadId → sem memória de conversa
```

**Problemas:**
1. System prompt vago — o agente não sabe seus limites
2. 40 tools — contexto sobrecarregado, LLM escolhe errado com frequência
3. Sem `recursionLimit` — um bug de lógica vira custo infinito

```typescript
// ✅ CORRIGIDO

import { createDeepAgent } from "deepagents";
import { BASE_PROMPT } from "@/server/agent/prompts/base";
import { readFileTool, searchWebTool } from "@/server/agent/prompts/tools"; // só as necessárias

const agent = createDeepAgent({
  model,
  systemPrompt: BASE_PROMPT,
  tools: [readFileTool, searchWebTool], // 2 tools relevantes
  name: "research-agent",
});

const config = {
  configurable: { thread_id: "user-456-session-1" },
  recursionLimit: 20,
};
const result = await agent.invoke({ messages: [...] }, config);
```

---

## F) Confiabilidade / Anti-Alucinação

### Como validar comportamento do agente

- **Teste com inputs extremos** — mensagem vazia, mensagem muito longa, pedido ambíguo
- **Verifique o `streamMode`** — em modo `debug`, você vê cada decisão do LLM; use em desenvolvimento
- **Inspecione tool calls** — o agente está chamando as tools corretas com os argumentos corretos?
- **Cheque o estado final** — `state.messages` deve conter o histórico completo da execução

### Quando falta informação

- Se o agente não sabe como responder: o system prompt deve instruí-lo a dizer "não sei" ou pedir mais contexto (ver SystemPromptDoc)
- Se uma tool falha: o agente deve tentar abordagem alternativa, não inventar um resultado
- Se o contexto estiver cheio: ver ContextoDoc para estratégias de compressão

### Incertezas desta documentação

- `PostgresSaver` para checkpointing em produção — **(incerto)** verifique disponibilidade em `@langchain/langgraph-checkpoint-postgres`
- Compatibilidade exata entre versões de `deepagents` e `@langchain/langgraph` — **(incerto)** confirme em `package.json`

---

## G) Analogia

Um agente é como um detetive investigando um caso. O detetive não sabe a resposta de antemão — ele faz perguntas (tool calls), analisa evidências (tool results), e vai refinando sua hipótese (raciocínio) até chegar a uma conclusão (resposta final). A cada nova evidência, ele pode mudar de direção.

O LangGraph é o mapa do escritório do detetive: define quais salas ele pode visitar (nodes), quais portas levam a onde (edges), e o que ele carrega na pasta (state). O deepagents é um assistente que já montou o escritório básico pra você — você só precisa dar as ferramentas certas e as instruções iniciais.

---

## H) Erros Comuns e Como Evitar

| Erro | Causa | Como evitar |
|---|---|---|
| Loop infinito | Sem `recursionLimit` | Sempre defina `recursionLimit` (recomendado: 20–30) |
| Agente esquece o contexto | Sem `threadId` configurado | Sempre passe `threadId` no config |
| Tool errada escolhida | Tools demais registradas | Passe apenas as tools relevantes para o agente |
| Agente para sem responder | Edge condicional mal configurada | Verifique se `END` é acessível de todos os estados finais |
| Custo explodindo | Muitas iterações desnecessárias | Limite tools, melhore o system prompt, adicione `recursionLimit` |
| Memória vaza entre usuários | `threadId` fixo ou ausente | Use `threadId` único por usuário/conversa |
| Erros de stream | `streamMode` incompatível com o provider | Teste com `streamMode: ["messages"]` primeiro |

---

## I) Mini-Template Pronto

```typescript
// ============================================================
// TEMPLATE: Agente com deepagents (caso mais comum)
// Copie, renomeie e adapte
// Arquivo: src/server/agent/stream.ts
// ============================================================

import { getModelForProvider } from "@/server/agent/providers";
import { createOmniMindDeepAgent } from "@/server/agent/deep-agent-config";
import { tool } from "@langchain/core/tools";
import { z } from "zod";

// --- 1. Tools (importe as suas) ---
const minhaTool = tool(
  async ({ param }: { param: string }): Promise<string> => {
    return `resultado: ${param}`;
  },
  {
    name: "minha_tool",
    description: "Descrição da tool. Use quando [condição].",
    schema: z.object({ param: z.string() }),
  }
);

// --- 2. Modelo ---
const model = getModelForProvider({
  provider: process.env.LLM_PROVIDER ?? "anthropic",
  model: process.env.LLM_MODEL ?? "claude-sonnet-4-6",
});

// --- 3. Agente ---
const agent = createOmniMindDeepAgent({
  model,
  systemPrompt: "[Seu system prompt aqui — ver SystemPromptDoc]",
  // tools: [minhaTool],  // descomente se deepagents aceitar tools custom
});

// --- 4. Invocação ---
async function run(message: string, threadId: string): Promise<string> {
  const config = {
    configurable: { thread_id: threadId },
    recursionLimit: 25,
  };
  const result = await agent.invoke(
    { messages: [{ role: "user", content: message }] },
    config
  );
  return result.messages[result.messages.length - 1].content as string;
}


// ============================================================
// TEMPLATE: Agente com LangGraph direto (grafo custom)
// ============================================================

import { Annotation, StateGraph, END } from "@langchain/langgraph";
import { ToolNode } from "@langchain/langgraph/prebuilt";
import { MemorySaver } from "@langchain/langgraph";
import { BaseMessage } from "@langchain/core/messages";

const State = Annotation.Root({
  messages: Annotation<BaseMessage[]>({
    reducer: (left, right) => left.concat(right),
  }),
});

const tools = [minhaTool];
const llmWithTools = model.bindTools(tools);

function agentNode(state: typeof State.State) {
  return { messages: [llmWithTools.invoke(state.messages)] };
}

function router(state: typeof State.State): string {
  const last = state.messages[state.messages.length - 1];
  const toolCalls = (last as any).tool_calls;
  return toolCalls && toolCalls.length > 0 ? "tools" : END;
}

const builder = new StateGraph(State)
  .addNode("agent", agentNode)
  .addNode("tools", new ToolNode(tools))
  .addEdge("__start__", "agent")
  .addConditionalEdges("agent", router)
  .addEdge("tools", "agent");

const compiledGraph = builder.compile({ checkpointer: new MemorySaver() });
```
