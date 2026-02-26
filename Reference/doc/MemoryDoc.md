# MemoryDoc

> Camada: 2 — Arquitetura | Depende de: AgentsDoc, ContextoDoc | Referenciado por: PromptGuide
> Stack: deepagents · LangGraph · LangChain · TypeScript

---

## A) Visão Geral

- **Memória** é o mecanismo que permite ao agente lembrar informações além da janela de contexto atual.
- Existem quatro tipos: **working** (curto prazo, dentro da sessão), **episodic** (histórico de conversas), **semantic** (conhecimento factual persistente) e **procedural** (como executar tarefas — skills).
- LangGraph gerencia memória via **checkpointers** — componentes que salvam e restauram o estado do grafo entre execuções.
- deepagents usa `StateBackend` (memória de estado) e `FilesystemBackend` (persistência em arquivo) — ambos configurados em `src/server/agent/deep-agent-config.ts`.
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
| **Checkpointer** | Componente LangGraph que salva/restaura o estado do grafo (MemorySaver) |
| **Thread ID** | Identificador único de uma conversa/sessão — isola memória entre usuários |
| **MemorySaver** | Checkpointer in-memory do `@langchain/langgraph` — dados somem ao reiniciar o processo |
| **SqliteSaver** | Checkpointer SQLite (Python) — sem equivalente direto em TS; use `MemorySaver` para dev **(incerto)** |
| **StateBackend** | Backend deepagents para armazenar estado estruturado em memória |
| **FilesystemBackend** | Backend deepagents para ler/escrever arquivos como memória persistente |

---

## C) Boas Práticas

### DO ✅

- **Sempre use `thread_id` por usuário/sessão** — sem isso, toda conversa compartilha o mesmo estado
- **Use `MemorySaver` em desenvolvimento** — fácil de configurar; para produção, avalie alternativas persistentes **(incerto)**
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
- [ ] Backend escolhido (MemorySaver / PostgreSQL / Redis / vector store)
- [ ] `thread_id` configurado e único por usuário/sessão
- [ ] TTL definido para dados episódicos
- [ ] Política de compressão definida (summarizar após N mensagens)
- [ ] Dados sensíveis identificados e protegidos
- [ ] Teste de isolamento entre threads (usuário A não vê dados do usuário B)

### Hierarquia de backends por cenário

```
Desenvolvimento / teste rápido
  └── MemorySaver (in-memory, sem dependências — @langchain/langgraph)

Produção leve / single-server
  └── (incerto) — SqliteSaver não tem equivalente direto em TS;
      verifique @langchain/langgraph-checkpoint-sqlite ou implemente via better-sqlite3

Produção com múltiplos servidores
  └── PostgreSQL (incerto — verifique @langchain/langgraph-checkpoint-postgres)
      ou Redis (incerto — verifique disponibilidade)

Memória semântica (busca por similaridade)
  └── Vector store (Chroma, Pinecone, pgvector)
```

---

## E) Exemplos Práticos

### Exemplo 1 — Checkpointing com MemorySaver (desenvolvimento)

```typescript
import { MemorySaver } from "@langchain/langgraph";

const checkpointer = new MemorySaver();
const graph = buildAgentGraph(); // seu grafo aqui
const agent = graph.compile({ checkpointer });

// Conversa 1 — thread isolado por usuário
const configUserA = { configurable: { thread_id: "user-001-session-1" } };
const result1 = await agent.invoke(
  { messages: [{ role: "user", content: "Meu nome é Alice" }] },
  configUserA
);

// Conversa 2 — mesmo usuário, agente lembra
const result2 = await agent.invoke(
  { messages: [{ role: "user", content: "Qual é meu nome?" }] },
  configUserA // mesmo thread_id = lembra Alice
);
console.log(result2.messages.at(-1)?.content); // "Seu nome é Alice"

// Conversa 3 — thread diferente, agente NÃO lembra
const configUserB = { configurable: { thread_id: "user-002-session-1" } };
const result3 = await agent.invoke(
  { messages: [{ role: "user", content: "Qual é meu nome?" }] },
  configUserB // thread diferente = sem memória do usuário A
);
```

---

### Exemplo 2 — Backend persistente (produção leve)

```typescript
// (incerto) — SqliteSaver não tem equivalente direto em @langchain/langgraph para TypeScript.
// Sugestão: use MemorySaver para desenvolvimento e avalie
// @langchain/langgraph-checkpoint-postgres ou uma solução customizada para produção.

// Exemplo conceitual com MemorySaver (funcional hoje):
import { MemorySaver } from "@langchain/langgraph";

const checkpointer = new MemorySaver();
const graph = buildAgentGraph();
const agent = graph.compile({ checkpointer });

// Uso idêntico independente do backend
const config = { configurable: { thread_id: "user-001" } };
const result = await agent.invoke({ messages: [{ role: "user", content: "Olá" }] }, config);
```

---

### Exemplo 3 — Como deepagents usa StateBackend e FilesystemBackend

```typescript
// Padrão real do projeto — ver src/server/agent/deep-agent-config.ts

import { CompositeBackend, FilesystemBackend, StateBackend, createDeepAgent } from "deepagents";

// FilesystemBackend: agente pode ler/escrever arquivos como memória
// StateBackend: estado em memória, acessível via path /memories/
const backend = new CompositeBackend(
  new FilesystemBackend({ rootDir: process.cwd() }),
  {
    "/memories/": new StateBackend({ state: {}, store: null }),
  }
);

const agent = createDeepAgent({
  model,
  systemPrompt,
  name: "omnimind-agent",
  tools: [],
  backend,
});

// O agente pode:
// - Ler arquivos do filesystem (FilesystemBackend)
// - Guardar/recuperar estado em /memories/ (StateBackend)
// Ex: agent pode salvar { user_preference: "dark_mode" } em /memories/prefs
```

---

### Exemplo 4 (RUIM → CORRIGIDO)

```typescript
// ❌ RUIM — sem thread_id, sem persistência, memória vaza entre usuários

import { MemorySaver } from "@langchain/langgraph";

const checkpointer = new MemorySaver();
const agent = graph.compile({ checkpointer });

// Todos os usuários usam o mesmo thread — memória vaza!
async function handleRequest(message: string): Promise<string> {
  const result = await agent.invoke(
    { messages: [{ role: "user", content: message }] },
    { configurable: { thread_id: "global" } } // ❌ thread único global
  );
  return result.messages.at(-1)?.content as string;
}
```

```typescript
// ✅ CORRIGIDO — thread_id por usuário, MemorySaver por ora (trocar por backend persistente em produção)

import { MemorySaver } from "@langchain/langgraph";
import { randomUUID } from "crypto";

const checkpointer = new MemorySaver();
const agent = graph.compile({ checkpointer });

async function handleRequest(
  message: string,
  userId: string,
  sessionId?: string
): Promise<{ content: string; threadId: string }> {
  // thread_id = userId + sessionId = isolamento por usuário por sessão
  const threadId = `${userId}-${sessionId ?? randomUUID().replace(/-/g, "")}`;

  const result = await agent.invoke(
    { messages: [{ role: "user", content: message }] },
    {
      configurable: { thread_id: threadId },
      recursionLimit: 25,
    }
  );
  return {
    content: result.messages.at(-1)?.content as string,
    threadId, // retorna threadId para o cliente manter
  };
}
```

---

## F) Confiabilidade / Anti-Alucinação

### Como validar memória

- **Teste de isolamento** — crie duas threads, verifique que informação de uma não aparece na outra
- **Teste de persistência** — reinicie o processo, verifique que o backend persistente recupera o estado correto
- **Inspecione o checkpoint** — LangGraph permite `checkpointer.get(config)` para ver o estado salvo **(incerto — confirme API da versão instalada)**
- **Monitore tamanho da memória** — threads muito longas aumentam latência; defina limite

### Quando perguntar vs assumir

- Se a memória não contém a informação pedida: **pergunte ao usuário**, não invente
- Se o thread_id não existe (novo usuário): **comece com contexto vazio**, não use contexto de outro usuário

### Incertezas desta documentação

- Equivalente TypeScript ao `PostgresSaver` para produção multi-servidor — **(incerto)** verifique pacote `@langchain/langgraph-checkpoint-postgres` e sua API atual.
- `StateBackend` do deepagents pode ter API diferente entre versões — **(incerto)** confirme em `src/server/agent/deep-agent-config.ts`.
- TTL automático no checkpointer TypeScript não é nativo — **(incerto)** verifique se há extensão ou implemente manualmente.

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
| Dados somem ao reiniciar | MemorySaver em produção | Use backend persistente (PostgreSQL ou similar) em produção |
| Memória cresce sem limite | Sem TTL ou compressão | Defina limite de mensagens e comprima episodic memory |
| Agente "lembra" coisas erradas | Thread corrompido | Implemente reset de thread quando usuário pedir |
| Performance degradada | Thread com 1000+ mensagens | Aplique summarização após N mensagens |
| Dados sensíveis em memória | Sem filtro antes de persistir | Filtre tokens, senhas, dados pessoais antes de salvar |

---

## I) Mini-Template Pronto

```typescript
// ============================================================
// TEMPLATE: Agente com memória persistente por usuário
// ============================================================

import { MemorySaver } from "@langchain/langgraph";
import { randomUUID } from "crypto";

// --- Setup do checkpointer (faça uma vez na inicialização) ---
// Para desenvolvimento: MemorySaver
// Para produção: substitua por backend persistente (incerto — verifique disponibilidade)
function createCheckpointer(): MemorySaver {
  return new MemorySaver();
}

const checkpointer = createCheckpointer();

// --- Compilação do agente com memória ---
const graph = buildAgentGraph(); // seu StateGraph aqui
const agent = graph.compile({ checkpointer });

// --- Invocação com isolamento por usuário ---
function getThreadId(userId: string, sessionId: string): string {
  /** Thread ID único por usuário + sessão. */
  return `${userId}::${sessionId}`;
}

async function chatWithMemory(
  message: string,
  userId: string,
  sessionId: string
): Promise<string> {
  const threadId = getThreadId(userId, sessionId);
  const config = {
    configurable: { thread_id: threadId },
    recursionLimit: 25,
  };
  const result = await agent.invoke(
    { messages: [{ role: "user", content: message }] },
    config
  );
  return result.messages.at(-1)?.content as string;
}

// --- Recuperar histórico da thread ---
async function getConversationHistory(
  userId: string,
  sessionId: string
): Promise<{ role: string; content: string }[]> {
  const threadId = getThreadId(userId, sessionId);
  const config = { configurable: { thread_id: threadId } };
  // (incerto) — confirme API exata do checkpointer na versão instalada
  const state = await checkpointer.get(config);
  if (state) {
    return (state.values as Record<string, unknown>)?.messages as { role: string; content: string }[] ?? [];
  }
  return [];
}

// --- Resetar memória de um usuário ---
function resetSession(userId: string, sessionId: string): void {
  /**
   * Remove o checkpoint de uma sessão específica.
   * MemorySaver não expõe delete nativo — inicie nova instância ou
   * use um novo thread_id para a próxima sessão.
   * (incerto) verifique API da versão instalada para backends persistentes.
   */
}
```
