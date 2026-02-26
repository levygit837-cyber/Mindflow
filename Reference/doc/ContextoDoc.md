# ContextoDoc

> Camada: 1 — Fundação | Depende de: AgentsDoc | Referenciado por: MemoryDoc, PromptGuide, SystemPromptDoc
> Stack: deepagents · LangGraph · LangChain · TypeScript

---

## A) Visão Geral

- **Contexto** é tudo que o LLM consegue "ver" durante uma execução: mensagens, resultados de tools, system prompt, histórico — tudo junto dentro da janela de tokens.
- A janela de contexto é finita — quando enche, informação é cortada ou o modelo erra por sobrecarga.
- Controlar contexto é a habilidade mais crítica para agentes confiáveis e baratos.
- Existem quatro tipos de conteúdo no contexto: **instrução** (system prompt), **histórico** (mensagens), **evidências** (tool results) e **raciocínio** (thinking/chain-of-thought).
- O OmniMind gerencia contexto via `src/server/agent/stream.ts` e `src/client/hooks/use-agent-chat.ts` — esses arquivos são a implementação real do que este doc descreve.
- Estratégias de controle: summarização, sliding window, seleção por relevância, compressão de tool results.

---

## B) Conceitos Essenciais

| Termo | Definição |
|---|---|
| **Janela de contexto** | Número máximo de tokens que o modelo processa de uma vez (ex: 200k para Claude, 128k para GPT-4) |
| **Token** | Unidade de texto que o modelo processa (~0.75 palavras em inglês, ~0.5 em português) |
| **Context window overflow** | Quando o total de tokens excede o limite — causa erro ou truncamento silencioso |
| **Sliding window** | Estratégia de manter apenas as N mensagens mais recentes no contexto |
| **Summarization** | Comprimir mensagens antigas em um resumo curto antes de removê-las do contexto |
| **Relevance filtering** | Selecionar apenas as partes do histórico relevantes para a pergunta atual |
| **Tool result compression** | Truncar ou resumir resultados de tools que são muito longos |
| **System prompt tokens** | Tokens consumidos pelo system prompt — ficam no contexto em TODAS as mensagens |
| **Thinking tokens** | Tokens usados para raciocínio interno (chain-of-thought) — visíveis no stream mas não enviados de volta ao modelo em todos os casos |
| **StreamEvent** | Evento emitido pelo OmniMind durante execução — contém type, data, mode, meta |

---

## C) Boas Práticas

### DO ✅

- **Monitore o tamanho do contexto** — conte tokens antes de enviar (use `@anthropic-ai/sdk` para Claude com `client.messages.countTokens()`)
- **Comprima tool results longos** — se uma tool retorna 10.000 tokens, resuma para os 500 mais relevantes antes de inserir no contexto
- **Use sliding window para chats longos** — mantenha as últimas 10–20 mensagens + um resumo das anteriores
- **Separe raciocínio de resposta** — thinking tokens não precisam voltar para o contexto nas iterações seguintes
- **Priorize o system prompt enxuto** — cada token no system prompt é cobrado em TODAS as mensagens
- **Filtre tool results irrelevantes** — se a tool retornou 50 resultados mas apenas 3 importam, passe só os 3

### DON'T ❌

- **Não insira tool results crus no contexto** — um resultado de busca web de 20.000 tokens vai explodir a janela
- **Não acumule histórico indefinidamente** — sem estratégia de sliding window, o agente vai falhar em conversas longas
- **Não repita o system prompt dentro do histórico** — já está no início, não precisa estar em cada mensagem
- **Não ignore erros de context overflow** — eles causam comportamento imprevisível, não apenas lentidão
- **Não use modelos com janela pequena para tarefas de código** — código é verboso em tokens

---

## D) Receitas Reutilizáveis

### Checklist de controle de contexto

- [ ] Calcule os tokens do system prompt (deve ser < 20% da janela total)
- [ ] Defina estratégia para histórico: sliding window (N mensagens) ou summarização
- [ ] Comprima tool results acima de 2.000 tokens antes de inserir
- [ ] Monitore uso de tokens em produção (log por request)
- [ ] Teste com conversas longas (50+ mensagens) para verificar comportamento
- [ ] Configure `recursionLimit` para limitar também o volume de tool calls por sessão

### Estratégias de compressão (ordem de preferência)

```
1. Truncar com aviso     → "... [resultado truncado após 500 chars] ..."
2. Resumir com LLM       → peça ao modelo para resumir antes de inserir
3. Extrair campos chave  → de um JSON de 5000 tokens, extraia só os 3 campos relevantes
4. Sliding window        → remove mensagens antigas, mantém resumo
5. Relevance filter      → embeddings para selecionar trechos mais próximos da query
```

### Cálculo de tokens (aproximação rápida)

```typescript
// Aproximação: 1 token ≈ 4 caracteres em inglês, ≈ 3 em português
function estimateTokens(text: string, lang: "pt" | "en" = "pt"): number {
  const charsPerToken = lang === "pt" ? 3 : 4;
  return Math.floor(text.length / charsPerToken);
}

// Para contar exato com Anthropic SDK:
// const response = await client.messages.countTokens({ model, messages, system });
// response.input_tokens → retorna número exato de tokens
```

---

## E) Exemplos Práticos

### Exemplo 1 — Sliding window simples

```typescript
import { BaseMessage, SystemMessage } from "@langchain/core/messages";

function applySlidingWindow(
  messages: BaseMessage[],
  maxMessages = 20,
): BaseMessage[] {
  if (messages.length <= maxMessages) {
    return messages;
  }

  const recent = messages.slice(-maxMessages);

  // Adiciona aviso de que histórico foi truncado
  const truncationNote = new SystemMessage(
    `[Contexto: ${messages.length - maxMessages} mensagens anteriores foram removidas para manter o contexto gerenciável.]`
  );

  return [truncationNote, ...recent];
}
```

---

### Exemplo 2 — Compressão de tool result longo

```typescript
function compressToolResult(result: string, maxChars = 2000): string {
  /**
   * Trunca tool results longos com aviso explícito.
   * Use antes de inserir resultados de busca, leitura de arquivos grandes, etc.
   */
  if (result.length <= maxChars) {
    return result;
  }

  const truncated = result.slice(0, maxChars);
  const originalLen = result.length;

  return (
    `${truncated}\n\n` +
    `... [RESULTADO TRUNCADO: ${originalLen} chars totais, ` +
    `exibindo primeiros ${maxChars}. ` +
    `Se precisar de mais, use uma query mais específica.]`
  );
}
```

---

### Exemplo 3 — Como o OmniMind emite eventos de contexto

```typescript
// src/server/agent/stream.ts e src/shared/types/agent.ts fazem isso internamente
// Este é o padrão de StreamEvent do projeto (ver src/shared/types/agent.ts)

import type { StreamEvent } from "@/shared/types/agent";

// Evento de pensamento (não retorna pro contexto do LLM nas iterações)
const thoughtEvent: StreamEvent = {
  id: "evt-001",
  seq: 1,
  type: "thought",       // raciocínio interno
  mode: "messages",
  data: "Vou verificar o arquivo antes de editar.",
  meta: { agentId: "omnimind-agent" },
};

// Evento de tool call (vai pro contexto como "o agente fez X")
const toolCallEvent: StreamEvent = {
  id: "evt-002",
  seq: 2,
  type: "tool_call",
  mode: "updates",
  data: JSON.stringify({ tool: "read_file", args: { path: "src/server/agent/stream.ts" } }),
  meta: { toolName: "read_file" },
};

// Evento de resposta final (vai pro contexto como resposta do assistente)
const responseEvent: StreamEvent = {
  id: "evt-003",
  seq: 3,
  type: "response",
  mode: "messages",
  data: "O arquivo tem 200 linhas. Aqui está o resumo...",
  meta: {},
};
```

---

### Exemplo 4 (RUIM → CORRIGIDO)

```typescript
// ❌ RUIM — insere resultado bruto de busca no contexto

import { tool } from "@langchain/core/tools";
import { z } from "zod";

const searchDocsBad = tool(
  async ({ query }: { query: string }): Promise<string> => {
    const results = await searchEngine.search(query);
    // Retorna TUDO — pode ser 50.000 tokens
    return JSON.stringify(results, null, 2);
  },
  {
    name: "search_docs",
    description: "Busca na documentação.",
    schema: z.object({ query: z.string() }),
  }
);
```

```typescript
// ✅ CORRIGIDO — filtra e comprime antes de retornar

import { tool } from "@langchain/core/tools";
import { z } from "zod";

interface SearchResult {
  title: string;
  url: string;
  content: string;
  score: number;
}

const searchDocs = tool(
  async ({ query }: { query: string }): Promise<string> => {
    const results: SearchResult[] = await searchEngine.search(query, { maxResults: 10 });

    // Filtra os 3 mais relevantes por score
    const top3 = [...results].sort((a, b) => b.score - a.score).slice(0, 3);

    const output = top3.map((r) => {
      const snippet = r.content.length > 200
        ? r.content.slice(0, 200) + "..."
        : r.content;
      return `**${r.title}** (${r.url})\n${snippet}`;
    });

    return output.length > 0 ? output.join("\n\n") : "[Nenhum resultado encontrado]";
  },
  {
    name: "search_docs",
    description:
      "Busca na documentação. Retorna os 3 resultados mais relevantes, " +
      "com título, URL e trecho de 200 chars cada.",
    schema: z.object({ query: z.string().describe("Termo de busca") }),
  }
);
```

---

## F) Confiabilidade / Anti-Alucinação

### Como detectar problemas de contexto

- **O agente "esquece" coisas ditas no início da conversa** → janela de tokens muito curta ou sliding window muito agressiva
- **O agente começa a alucinar fatos** → contexto sobrecarregado, modelo começa a preencher lacunas
- **Erros de `context_length_exceeded`** → overflow — reduza histórico ou comprima tool results
- **Respostas ficam genéricas no meio da conversa longa** → modelo perdeu o fio após compressão ruim

### Como validar

```typescript
// Monitore o uso de tokens por request usando o Anthropic SDK
import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic();
// Após cada invocação, verifique usage na resposta:
// response.usage.input_tokens   → tokens enviados
// response.usage.output_tokens  → tokens gerados
// Alerte se input_tokens > 80% da janela do modelo

function checkContextUsage(inputTokens: number, modelLimit: number): void {
  const ratio = inputTokens / modelLimit;
  if (ratio > 0.8) {
    console.warn(`[CONTEXTO] Uso em ${(ratio * 100).toFixed(1)}% da janela — considere comprimir.`);
  }
}
```

### Quando perguntar vs assumir

- Se o contexto foi truncado e a informação pode estar ausente: **o agente deve perguntar** ("Não encontrei X no contexto. Você pode fornecer?")
- Se o resultado de tool está truncado: **o agente deve informar** ("O arquivo é grande, vi apenas os primeiros 2000 chars. Quer que eu continue?")

---

## G) Analogia

Imagine que o LLM é um detetive com uma **mesa de trabalho de tamanho fixo**. Ele só consegue analisar o que está na mesa — não consegue ver o que está no arquivo ou na gaveta. Cada nova pista (tool result), mensagem ou instrução ocupa espaço na mesa. Quando a mesa enche, você precisa tirar coisas antigas para colocar as novas.

Controlar o contexto é decidir **o que fica na mesa**. Deixar tudo lá é tentador, mas em pouco tempo a mesa fica tão bagunçada que o detetive não consegue mais raciocinar com clareza. A arte está em manter na mesa apenas o que é relevante para o caso atual — e guardar o resto em um resumo organizado na gaveta (memória persistente).

---

## H) Erros Comuns e Como Evitar

| Erro | Causa | Como evitar |
|---|---|---|
| Context overflow em produção | Tool results crus + histórico longo | Comprima tool results, use sliding window |
| Agente "esquece" instruções | System prompt muito longo empurra histórico para fora | Enxugue o system prompt; mova instruções pouco usadas para tool descriptions |
| Alucinação em conversas longas | Janela cheia, modelo preenche lacunas | Adicione summarização ou relevance filtering |
| Custo explodindo | Contexto grande em cada request | Monitore tokens por request; aplique compressão |
| Truncamento silencioso | Alguns providers truncam sem avisar | Conte tokens antes de enviar; valide que input < 90% do limite |
| Thinking tokens não gerenciados | Raciocínio interno acumula no contexto | Configure corretamente o streamMode; separe thinking de history |

---

## I) Mini-Template Pronto

```typescript
// ============================================================
// TEMPLATE: Gerenciador de contexto para agentes OmniMind
// Arquivo: src/server/agent/stream.ts
// ============================================================

import { BaseMessage, SystemMessage, HumanMessage, AIMessage } from "@langchain/core/messages";

// --- Constantes ---
const MAX_HISTORY_MESSAGES = 20;      // mensagens recentes a manter
const MAX_TOOL_RESULT_CHARS = 2000;   // chars máx por tool result
const CONTEXT_WARNING_THRESHOLD = 0.8; // alerta se > 80% da janela usada

// --- Sliding window ---
function trimHistory(
  messages: BaseMessage[],
  maxMsgs = MAX_HISTORY_MESSAGES
): BaseMessage[] {
  /** Mantém as últimas `maxMsgs` mensagens. Preserva SystemMessage. */
  const system = messages.filter((m) => m._getType() === "system");
  const others = messages.filter((m) => m._getType() !== "system");

  if (others.length > maxMsgs) {
    const note = new SystemMessage(
      `[${others.length - maxMsgs} mensagens anteriores omitidas]`
    );
    return [...system, note, ...others.slice(-maxMsgs)];
  }

  return [...system, ...others];
}

// --- Compressão de tool result ---
function compressResult(result: string, maxChars = MAX_TOOL_RESULT_CHARS): string {
  /** Trunca resultado longo com aviso. */
  if (result.length <= maxChars) return result;
  return (
    result.slice(0, maxChars) +
    `\n... [truncado: ${result.length} chars totais, exibindo ${maxChars}]`
  );
}

// --- Estimativa de tokens ---
function estimateTokensPt(text: string): number {
  /** Estimativa rápida para português (~3 chars/token). */
  return Math.floor(text.length / 3);
}

// Uso no pipeline:
// const messages = trimHistory(state.messages);
// const toolOutput = compressResult(rawToolOutput);
// const tokensUsed = estimateTokensPt(JSON.stringify(messages));
```
