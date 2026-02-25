# OmniMind — Arquitetura do Agente

> Documentação técnica completa de como o agente funciona, suas tools, lógica de decisão e fluxo de dados.

---

## Índice

1. [Visão Geral](#1-visão-geral)
2. [Fluxo Completo de uma Mensagem](#2-fluxo-completo-de-uma-mensagem)
3. [Componentes do Agente](#3-componentes-do-agente)
4. [Tools do Agente](#4-tools-do-agente)
5. [Lógica de Decisão — Quando Chamar Tools](#5-lógica-de-decisão--quando-chamar-tools)
6. [SafeBackend — Camada de Segurança](#6-safebackend--camada-de-segurança)
7. [Provedores LLM](#7-provedores-llm)
8. [Sistema de Streaming](#8-sistema-de-streaming)
9. [Normalização de Eventos (ChatStreamNormalizer)](#9-normalização-de-eventos-chatstreaamnormalizer)
10. [Camada de UI — Estado e Renderização](#10-camada-de-ui--estado-e-renderização)
11. [Persistência e Memória](#11-persistência-e-memória)
12. [ContentParts — Timeline de Mensagens](#12-contentparts--timeline-de-mensagens)
13. [Ciclo de Vida Completo (Exemplo)](#13-ciclo-de-vida-completo-exemplo)

---

## 1. Visão Geral

O OmniMind é um **Deep Agent** baseado em LangGraph que possui:
- Acesso ao **filesystem** (leitura, escrita, edição de arquivos)
- **Busca na web** via SearXNG (self-hosted, privado)
- **Execução de shell** com guardrails de segurança
- **Planejamento de tarefas** com todo list
- **Memória persistente** via PostgreSQL (checkpointing LangGraph)
- **Suporte a múltiplos provedores** de LLM

```
┌─────────────────────────────────────────────────────────────────────┐
│                        OMNIMIND AGENT                               │
│                                                                     │
│   ┌───────────┐    ┌──────────────┐    ┌────────────────────────┐  │
│   │  Browser  │    │  Next.js API │    │     LangGraph Agent    │  │
│   │   (UI)    │◄──►│  /api/agent  │◄──►│  (deepagents library)  │  │
│   └───────────┘    └──────────────┘    └────────────────────────┘  │
│        SSE                                       │                  │
│   (streaming)         ┌──────────────────────────┘                 │
│                       ▼                                             │
│   ┌────────────────────────────────────────────────────────────┐   │
│   │                    TOOLS + BACKENDS                         │   │
│   │                                                             │   │
│   │  ls  read_file  write_file  edit_file  glob  grep          │   │
│   │  search_web  write_todos  execute                          │   │
│   │                                                             │   │
│   │  ┌─────────────────────────────────────────────────────┐  │   │
│   │  │ SafeBackend (guardrail)                              │  │   │
│   │  │   └── CompositeBackend                               │  │   │
│   │  │         ├── FilesystemBackend (arquivos reais)       │  │   │
│   │  │         └── StateBackend (/memories/ - scratchpad)   │  │   │
│   │  └─────────────────────────────────────────────────────┘  │   │
│   └────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Fluxo Completo de uma Mensagem

```
USUÁRIO DIGITA E ENVIA MENSAGEM
              │
              ▼
┌─────────────────────────────────┐
│  ChatInput.handleSend(text)     │
│  → onSend(text) callback        │
└───────────────┬─────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│  useAgentChat.sendMessage()     │
│  1. addUserMessage(text)        │
│  2. setLoading(true)            │
│  3. startAssistantMessage()     │
│     ↳ cria ThinkingPart vazio   │
│       (isStreaming: true)       │
└───────────────┬─────────────────┘
                │
                │ POST /api/agent/chat
                │ { message, provider, model, conversationId }
                ▼
┌─────────────────────────────────────────────────────────────────┐
│  route.ts (Next.js API)                                         │
│                                                                 │
│  ┌──────────────────────┐                                       │
│  │ SSE Response criada  │◄──── retorna IMEDIATAMENTE ao browser │
│  │ (stream aberto)      │                                       │
│  └──────────────────────┘                                       │
│                                                                 │
│  [async, em background]:                                        │
│  1. ensureDbInitialized()      → PostgresSaver.setup()          │
│  2. createOmniMindAgent()      → monta o agente                 │
│  3. agent.stream(messages, { streamMode: ["messages","updates"]})│
│  4. for await chunk:                                            │
│       normalizer.process(chunk)                                 │
│       → emite StreamEvents via SSE                              │
│       → publica no logBus                                       │
│  5. normalizer.flush()                                          │
│  6. emit("done")                                                │
│  7. close()                                                     │
└───────────────┬─────────────────────────────────────────────────┘
                │
                │ SSE eventos fluindo...
                ▼
┌─────────────────────────────────┐
│  useAgentChat (SSE reader loop) │
│  parse "data: {...}" lines      │
│  dispatch ao store por tipo:    │
│                                 │
│  "thought"     → appendThought  │
│  "response"    → appendToAsst.  │
│  "tool_call"   → addToolCall    │
│  "tool_result" → updateToolRes. │
│  "agent_step"  → addAgentStep   │
│  "done"        → finishAsst.    │
└───────────────┬─────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│  agent-store (Zustand)          │
│  mutações no contentParts[]     │
│  → React re-renders automático  │
└───────────────┬─────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│  ChatInterface (UI)             │
│  ContentPartRenderer dispatch:  │
│  "thinking"   → ThinkingBlock   │
│  "tool_call"  → ToolCallBlock   │
│  "text"       → ResponseBlock   │
│  "agent_step" → AgentStepsBlock │
│  "notifier"   → inline badge    │
└─────────────────────────────────┘
```

---

## 3. Componentes do Agente

```
createOmniMindAgent(provider, model)
         │
         ├── getModelForProvider(provider, model)
         │         │
         │         └── retorna BaseChatModel (LangChain)
         │
         └── createOmniMindDeepAgent({ model, systemPrompt })
                   │
                   ├── checkpointer = getCheckpointer()
                   │         └── PostgresSaver (LangGraph)
                   │
                   ├── tools = [searchWebTool]
                   │
                   └── backend = SafeBackend(
                               CompositeBackend(
                                 FilesystemBackend({ rootDir: cwd }),
                                 { "/memories/": StateBackend({}) }
                               )
                             )

┌────────────────────────────────────────────────────┐
│              CAMADAS DO BACKEND                    │
│                                                    │
│  ┌─────────────────────────────────────────────┐   │
│  │  SafeBackend (intercepta execute())         │   │
│  │  └── bloqueia 30+ padrões perigosos         │   │
│  │                                             │   │
│  │  ┌────────────────────────────────────────┐ │   │
│  │  │  CompositeBackend                      │ │   │
│  │  │  ├── FilesystemBackend                 │ │   │
│  │  │  │   (rootDir = process.cwd())         │ │   │
│  │  │  │   → ls, read_file, write_file,      │ │   │
│  │  │  │     edit_file, glob, grep, execute  │ │   │
│  │  │  │                                     │ │   │
│  │  │  └── StateBackend ("/memories/")       │ │   │
│  │  │      → key-value scratchpad in-memory  │ │   │
│  │  │        para estado de sessão           │ │   │
│  │  └────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────┘
```

---

## 4. Tools do Agente

O agente tem **9 tools** disponíveis:

```
┌─────────────────────────────────────────────────────────────────────┐
│                        9 TOOLS DO AGENTE                            │
├───────────────┬─────────────────────────────────────────────────────┤
│  TOOL         │  O QUE FAZ                                          │
├───────────────┼─────────────────────────────────────────────────────┤
│  ls           │  Lista arquivos/diretórios                          │
│               │  → built-in do FilesystemBackend                    │
├───────────────┼─────────────────────────────────────────────────────┤
│  read_file    │  Lê conteúdo de arquivos (paginado, 100 linhas)     │
│               │  → built-in do FilesystemBackend                    │
├───────────────┼─────────────────────────────────────────────────────┤
│  write_file   │  Cria NOVOS arquivos (não modifica existentes)      │
│               │  → built-in do FilesystemBackend                    │
├───────────────┼─────────────────────────────────────────────────────┤
│  edit_file    │  Modifica arquivos existentes (string replace)      │
│               │  → built-in do FilesystemBackend                    │
├───────────────┼─────────────────────────────────────────────────────┤
│  glob         │  Busca arquivos por padrão (*.ts, **/*.tsx)         │
│               │  → built-in do FilesystemBackend                    │
├───────────────┼─────────────────────────────────────────────────────┤
│  grep         │  Busca texto em arquivos com números de linha       │
│               │  → built-in do FilesystemBackend                    │
├───────────────┼─────────────────────────────────────────────────────┤
│  search_web   │  Busca na web via SearXNG (self-hosted)             │
│               │  → tool customizada (src/lib/agent/tools/search-web)│
│               │  → top 10 resultados, timeout 15s                   │
├───────────────┼─────────────────────────────────────────────────────┤
│  write_todos  │  Gerencia lista de tarefas (para tarefas 3+ passos) │
│               │  → built-in do deepagents                          │
├───────────────┼─────────────────────────────────────────────────────┤
│  execute      │  Executa comandos shell (LAST RESORT)               │
│               │  → interceptado pelo SafeBackend                    │
│               │  → 30+ padrões bloqueados                           │
└───────────────┴─────────────────────────────────────────────────────┘
```

### Como a `search_web` funciona internamente:

```
search_web(query: string)
         │
         ▼
  fetch(`${SEARXNG_URL}/search?q=<query>&format=json`)
         │
         │ SearXNG = meta-search engine self-hosted
         │ SEARXNG_URL default: http://localhost:8080
         │ Timeout: 15 segundos
         ▼
  SearXNGResponse { results[], suggestions[], query }
         │
         ▼
  formatResults()
  → top 10 resultados
  → "N. **title**\n   URL: ...\n   snippet (≤300 chars)"
         │
         ▼
  retorna string formatada → LLM usa como contexto
```

---

## 5. Lógica de Decisão — Quando Chamar Tools

O agente segue **regras estritas** definidas no System Prompt:

### Hierarquia de Prioridade de Tools

```
PERGUNTA: "Qual tool devo usar?"
              │
              ▼
    Preciso listar arquivos?
    ├── SIM → ls (NUNCA execute("ls"))
    │
    Preciso ler arquivo?
    ├── SIM → ls primeiro → read_file (NUNCA execute("cat"))
    │
    Preciso criar arquivo NOVO?
    ├── SIM → ls (verificar parent) → write_file
    │
    Preciso MODIFICAR arquivo?
    ├── SIM → ls → read_file → edit_file (NUNCA write_file)
    │
    Preciso buscar arquivos por padrão?
    ├── SIM → glob (NUNCA execute("find"))
    │
    Preciso buscar texto em arquivos?
    ├── SIM → grep (NUNCA execute("grep"))
    │
    Preciso de informação externa/atual?
    ├── SIM → search_web (ÚNICA fonte externa)
    │
    Tarefa tem 3+ passos?
    ├── SIM → write_todos (planejamento)
    │
    Nenhuma tool cobre a necessidade?
    └── execute (LAST RESORT, com restrições)
```

### Workflow Obrigatório para Edição de Arquivos

```
OBRIGATÓRIO: ls → read_file → edit_file

Passo 1: ls(path="/diretório")
         ↓
         Confirma que arquivo existe
         Descobre nome exato
         ↓
Passo 2: read_file(file_path="/caminho/exato")
         ↓
         Obtém conteúdo atual com números de linha
         Identifica exatamente o que substituir
         ↓
Passo 3: edit_file(old_string="...", new_string="...")
         ↓
         Realiza substituição exata de string
```

### Quando o Agente Decide Usar `search_web`

```
TRIGGERS para search_web:
  ├── Documentação atual (ex: "como usar Next.js 16 app router")
  ├── Mensagens de erro desconhecidas
  ├── APIs de pacotes (ex: "parâmetros do langchain ChatAnthropic")
  ├── Boas práticas atuais
  ├── Notícias/eventos recentes
  └── Qualquer dado além do knowledge cutoff do LLM

NÃO usa search_web quando:
  ├── A resposta está no filesystem local
  ├── É conhecimento estável (algoritmos, conceitos básicos)
  └── Pode resolver com outras tools
```

---

## 6. SafeBackend — Camada de Segurança

```
┌─────────────────────────────────────────────────────────────────────┐
│                     DOIS NÍVEIS DE SEGURANÇA                        │
│                                                                     │
│  Nível 1: System Prompt (Advisory)                                  │
│  ─────────────────────────────────                                  │
│  → LLM é INSTRUÍDO a não chamar comandos proibidos                  │
│  → Depende da conformidade do modelo                                │
│  → Pode ser bypassado por um modelo mal-comportado                  │
│                                                                     │
│  Nível 2: SafeBackend (Enforcement)                                 │
│  ──────────────────────────────────                                 │
│  → Verifica TODOS os execute() ANTES de chegar ao shell             │
│  → Regex blocklist, case-insensitive                                │
│  → IMPOSSÍVEL de bypassar pelo LLM                                  │
│  → Retorna { exitCode: 1, stderr: "BLOCKED: ..." }                  │
│  → Loga warning no console do servidor                              │
└─────────────────────────────────────────────────────────────────────┘

SafeBackend usa JS Proxy:

┌───────────────────────────────────────────┐
│  new Proxy(this, {                        │
│    get(target, prop) {                    │
│      if (prop === "execute") {            │
│        return target.execute.bind(target) │  ← INTERCEPTA
│      }                                    │
│      return innerBackend[prop]            │  ← PASSA TRANSPARENTE
│    }                                      │
│  })                                       │
└───────────────────────────────────────────┘

Categorias de Comandos Bloqueados (30+ padrões):

  DELEÇÃO DE ARQUIVOS:  rm, rmdir, del, find -delete, xargs rm
  OPERAÇÕES DE DISCO:   mkfs, fdisk, dd
  PERMISSÕES:           chmod, chown
  CONTROLE DE PROC.:    kill, killall, pkill
  SISTEMA:              shutdown, reboot, halt, poweroff
  FIREWALL:             iptables, ufw, firewall-cmd
  USUÁRIOS:             useradd, userdel, passwd, usermod
  MONTAGEM:             mount, umount
  SERVIÇOS:             systemctl, service
  ESCALONAMENTO:        sudo, su, doas
  ACESSO REMOTO:        ssh, scp, rsync @
  HTTP MUTANTE:         curl -X POST/PUT/DELETE, wget --post
  INJEÇÃO:              | bash, | sh, eval
  GIT DESTRUTIVO:       git push --force, git reset --hard, git clean -f
  CONTAINERS:           docker rm, docker rmi
  SQL DESTRUTIVO:       DROP TABLE, DELETE FROM, TRUNCATE
  BG PROCESSES:         nohup, disown
  FORK BOMBS:           :(){ :|:& };:
```

---

## 7. Provedores LLM

```
┌──────────────────────────────────────────────────────────────────┐
│                   PROVEDORES SUPORTADOS                          │
├──────────────┬───────────────────────┬──────────────────────────┤
│  PROVIDER    │  MODELO PADRÃO        │  CONFIGURAÇÃO ESPECIAL   │
├──────────────┼───────────────────────┼──────────────────────────┤
│  vertexai    │  gemini-3-flash-prev. │  reasoningEffort: "high" │
│  (DEFAULT)   │                       │  serviceAccountVertex.json│
│              │                       │  location: "global"      │
├──────────────┼───────────────────────┼──────────────────────────┤
│  google      │  gemini-2.0-flash     │  thinkingLevel: "HIGH"   │
│              │                       │  includeThoughts: true   │
├──────────────┼───────────────────────┼──────────────────────────┤
│  anthropic   │  claude-sonnet-4      │  thinking: "adaptive"    │
│              │                       │  (Sonnet 4 / Opus 4)     │
├──────────────┼───────────────────────┼──────────────────────────┤
│  openai      │  gpt-4o               │  configuração padrão     │
├──────────────┼───────────────────────┼──────────────────────────┤
│  ollama      │  llama3.1:8b          │  baseUrl: localhost:11434 │
└──────────────┴───────────────────────┴──────────────────────────┘

Gemini/VertexAI:   usa <think>...</think> tags no stream
Anthropic:         usa additional_kwargs.thinking
OpenAI:            usa additional_kwargs.tool_calls
```

---

## 8. Sistema de Streaming

### SSE Stream (Server-Sent Events)

```
SERVIDOR                                CLIENTE (Browser)
   │                                          │
   │ POST /api/agent/chat                     │
   │◄─────────────────────────────────────────┤
   │                                          │
   │ HTTP 200 text/event-stream               │
   ├─────────────────────────────────────────►│
   │                                          │
   │ data: {"type":"thought","data":"..."}    │
   ├─────────────────────────────────────────►│
   │                                          │
   │ data: {"type":"tool_call","data":"..."}  │
   ├─────────────────────────────────────────►│
   │                                          │
   │ data: {"type":"tool_result","data":"..."}│
   ├─────────────────────────────────────────►│
   │                                          │
   │ data: {"type":"response","data":"..."}   │
   ├─────────────────────────────────────────►│  (chunk a chunk)
   │                                          │
   │ data: {"type":"done","data":""}          │
   ├─────────────────────────────────────────►│
   │                                          │
   │ [stream fecha]                           │
   ├─────────────────────────────────────────►│

Formato de cada evento SSE:

StreamEvent {
  id:   string      // UUID único do evento
  seq:  number      // número de sequência (ordenação garantida)
  type: StreamEventType  // thought | tool_call | tool_result |
                         // response | step | agent_step |
                         // done | error | notifier
  mode: StreamModeName   // messages | updates | custom
  data: string           // payload (JSON string ou texto)
  meta?: {
    runId?:     string   // ID do run LangGraph
    node?:      string   // nó do grafo (ex: "agent", "tools")
    toolCallId?: string  // ID da tool call
    provider?:  LLMProvider
    model?:     string
    status?:    "start" | "update" | "end"
    path?:      string[] // caminho no subgraph
  }
}
```

---

## 9. Normalização de Eventos (ChatStreamNormalizer)

O `ChatStreamNormalizer` traduz o raw output do LangGraph para `StreamEvent`s uniformes.

```
LangGraph emite streams em 3 modos diferentes:
    │
    ├── "messages" → [chunk, metadata] pairs (streaming em tempo real)
    ├── "updates"  → { nodeName: nodeUpdate } (estado após cada nó)
    └── "custom"   → eventos customizados do grafo

PROBLEMA: cada provider LLM usa formatos diferentes!
    │
    ├── Anthropic: { additional_kwargs: { thinking: "..." } }
    ├── Gemini:    texto com <think>...</think> tags
    ├── OpenAI:    { additional_kwargs: { tool_calls: [...] } }
    └── Ollama:    formatos variáveis

SOLUÇÃO: ChatStreamNormalizer abstrai tudo!
```

### Parser de `<think>` Tags (Gemini/VertexAI)

```
Gemini envia pensamentos inline no texto como:
"<think>Vou analisar o problema...</think>A resposta é..."

O ThinkTagParser resolve boundary splits:
  Chunk 1: "Vou analisar o <thi"
  Chunk 2: "nk>conteúdo do pensam"
  Chunk 3: "ento</think>Resposta"

  Buffer mantém 7 chars no final para detectar <think> parcial
  Buffer mantém 8 chars no final para detectar </think> parcial

  Resultado:
    emit("thought", "conteúdo do pensamento")
    emit("response", "Resposta")
```

### Deduplicação de Tool Calls

```
┌─────────────────────────────────────────────────────────────────┐
│  PROBLEMA: LangGraph emite a mesma tool call em DOIS modos      │
│  (messages E updates) → duplicatas no UI                        │
│                                                                 │
│  SOLUÇÃO: seenToolCalls Set                                     │
│                                                                 │
│  seenToolCalls = new Set<string>()  // IDs já emitidos          │
│  seenToolResults = new Set<string>() // resultados já emitidos  │
│                                                                 │
│  pendingTools = new Map<id, {name, args}>  // aguardando result │
│  pendingByName = new Map<name, id[]>       // FIFO por nome     │
│                                                                 │
│  Matching de resultado quando toolCallId está ausente:          │
│  1. Tenta por toolCallId direto                                 │
│  2. Tenta por toolName via FIFO queue                           │
│  3. Gera fallback ID aleatório                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 10. Camada de UI — Estado e Renderização

### Zustand Store (agent-store)

```
Estado global (agent-store):

{
  messages:       ChatMessage[]    // todas as mensagens da sessão
  isLoading:      boolean          // true durante streaming
  provider:       LLMProvider      // "vertexai" (default)
  model:          string           // "gemini-3-flash-preview"
  conversationId: string           // "session-{timestamp}-{random}"
  noteContext:    string[]         // IDs de notas injetadas como contexto
}

Estrutura de cada mensagem assistente:

ChatMessage {
  id:           string
  role:         "assistant"
  contentParts: ContentPart[]   ← PRINCIPAL: timeline ordenada
  isStreaming:  boolean
  // + campos legado: content, thoughts, toolCalls
}
```

### ContentPart — Timeline da Mensagem

```
contentParts[] representa a TIMELINE ORDENADA de uma resposta:

Exemplo após uma interação completa:

  contentParts = [
    ┌──────────────────────────────────────────────────────┐
    │ ThinkingPart { isStreaming: false }                   │
    │ "Preciso verificar quais arquivos existem em /src..." │
    │ [▶ Thought  42 tokens]                               │
    └──────────────────────────────────────────────────────┘
    ┌──────────────────────────────────────────────────────┐
    │ ToolCallPart { status: "success" }                   │
    │ name: "ls"  args: { path: "/src" }                   │
    │ ● ls /src  0.3s  [expandir ▼]                        │
    └──────────────────────────────────────────────────────┘
    ┌──────────────────────────────────────────────────────┐
    │ ThinkingPart { isStreaming: false }                   │
    │ "Agora que sei os arquivos, vou ler o principal..."  │
    │ [▶ Thought  28 tokens]                               │
    └──────────────────────────────────────────────────────┘
    ┌──────────────────────────────────────────────────────┐
    │ ToolCallPart { status: "success" }                   │
    │ name: "read_file"  args: { file_path: "/src/app.ts" }│
    │ ● read_file /src/app.ts  0.8s  [expandir ▼]         │
    └──────────────────────────────────────────────────────┘
    ┌──────────────────────────────────────────────────────┐
    │ TextPart { content: "..." }                          │
    │ O arquivo `app.ts` contém...                         │
    │ [markdown renderizado]                               │
    └──────────────────────────────────────────────────────┘
  ]
```

### ContentPartRenderer

```
ChatInterface → ContentPartRenderer (dispatch switch)

part.type === "thinking"   → <ThinkingBlock>
                              ├── isStreaming=true: pulsing dot + token count
                              └── isStreaming=false: collapsible section

part.type === "tool_call"  → <ToolCallBlock>
                              ├── status="running": Loader2 spinning + ElapsedTimer
                              └── status="success": static time + expand/collapse
                                  (mostra args e result em JSON)

part.type === "text"       → <ResponseBlock>
                              ├── ReactMarkdown + remarkGfm + rehypeHighlight
                              └── isStreaming=true: cursor piscando no fim

part.type === "agent_step" → <AgentStepsBlock>
                              ├── status="running": indicador de progresso
                              └── status="completed": checkmark + duração

part.type === "notifier"   → <span> badge inline
```

---

## 11. Persistência e Memória

```
┌─────────────────────────────────────────────────────────────────────┐
│                   DOIS SISTEMAS DE PERSISTÊNCIA                     │
│                                                                     │
│  1. PostgreSQL (LangGraph Checkpointer)                             │
│  ─────────────────────────────────────                              │
│  → Persiste o ESTADO INTERNO DO GRAFO LANGGRAPH                     │
│  → thread_id = conversationId (da sessão)                           │
│  → Sobrevive a reinicializações do servidor                         │
│  → Usado para: memória multi-turno do agente                        │
│  → Schema: tabelas do PostgresSaver (@langchain/langgraph-*)        │
│                                                                     │
│  pg.Pool {                                                          │
│    max: 10,                                                         │
│    idleTimeoutMillis: 30000,                                        │
│    connectionTimeoutMillis: 5000                                    │
│  }                                                                  │
│                                                                     │
│  2. In-Memory Maps (Conversation Store)                             │
│  ──────────────────────────────────────                             │
│  → conversationStore: Map<string, Conversation>                     │
│  → messageStore: Map<string, Message[]>                             │
│  → EPHEMERAL: perdido no restart do servidor                        │
│  → Usado para: lista de conversas na sidebar da UI                  │
│  → TODO: migrar para PostgreSQL (comentário no código)              │
│                                                                     │
│  3. StateBackend (/memories/)                                       │
│  ────────────────────────────                                       │
│  → key-value store in-memory dentro do agente                       │
│  → O agente pode ler/gravar em /memories/qualquer-chave             │
│  → Scratchpad de sessão para estado temporário                      │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                    LogBus (Event Bus)                               │
│                                                                     │
│  Singleton process-wide pub/sub:                                    │
│  ├── Ring buffer: 500 eventos mais recentes                         │
│  ├── Cada evento SSE também é publicado aqui                        │
│  ├── Novos subscribers recebem histórico imediatamente              │
│  └── Usado para debug/monitoring dashboards                         │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 12. ContentParts — Timeline de Mensagens

### Ciclo de Vida de um ContentPart

```
STREAMING COMEÇA:
  startAssistantMessage()
  → contentParts = [ThinkingPart { isStreaming: true, content: "" }]

  UI mostra: ● Thinking... (0 tokens)

──────────────────────────────────────────
EVENTO "thought" recebido:
  appendThought(msgId, "Vou verificar...")
  → ThinkingPart.content += "Vou verificar..."

  UI mostra: ● Thinking... (4 tokens)

──────────────────────────────────────────
EVENTO "tool_call" recebido:
  cancelEmptyThinking(msgId)  → sela ThinkingPart vazio (se content="")
  addToolCall(msgId, { id, name:"ls", args:{ path:"/src" } })
  → ThinkingPart.isStreaming = false
  → contentParts.push(ToolCallPart { status: "running", startedAt: now })

  UI mostra:
    [▶ Thought 4 tokens]
    [⟳ ls /src  0.0s]

──────────────────────────────────────────
EVENTO "tool_result" recebido:
  updateToolResult(msgId, toolCallId, "index.ts\napp.ts")
  → ToolCallPart.status = "success"
  → ToolCallPart.result = "index.ts\napp.ts"
  → ToolCallPart.completedAt = now

  UI mostra:
    [▶ Thought 4 tokens]
    [● ls /src  0.3s ▼]

──────────────────────────────────────────
EVENTO "response" recebido:
  cancelEmptyThinking(msgId)  → no-op se já cancelado
  appendToAssistant(msgId, "O diretório contém ")
  → contentParts.push(TextPart { content: "O diretório contém " })

  UI mostra:
    [▶ Thought 4 tokens]
    [● ls /src  0.3s ▼]
    O diretório contém ▊  ← cursor piscando

──────────────────────────────────────────
EVENTO "done" recebido:
  completeAllAgentSteps(msgId)
  finishAssistant(msgId)
  → message.isStreaming = false
  → ThinkingParts: isStreaming = false
  → cursor some

  UI mostra (estado final):
    [▶ Thought 4 tokens]
    [● ls /src  0.3s ▼]
    O diretório contém dois arquivos: index.ts e app.ts
```

---

## 13. Ciclo de Vida Completo (Exemplo)

**Prompt:** *"Leia o arquivo src/app/page.tsx e explique o que ele faz"*

```
PASSO 1: AGENTE PENSA
─────────────────────
  [LLM recebe system prompt + mensagem do usuário]

  LLM raciocina internamente:
  "Preciso ler o arquivo. Mas primeiro devo verificar
   com ls que o arquivo existe e confirmar o caminho exato."

  → emit("thought", "Vou verificar o arquivo com ls primeiro...")


PASSO 2: TOOL CALL — ls
────────────────────────
  LLM decide chamar: ls(path="src/app")

  → emit("tool_call", { id:"tc-1", name:"ls", args:{path:"src/app"} })

  SafeBackend.execute() não é chamado (ls não usa execute)
  FilesystemBackend.ls("src/app") → retorna listagem

  → emit("tool_result", { id:"tc-1", name:"ls", result:"page.tsx\nlayout.tsx\n..." })


PASSO 3: TOOL CALL — read_file
───────────────────────────────
  LLM vê que page.tsx existe, decide ler:
  read_file(file_path="src/app/page.tsx")

  → emit("tool_call", { id:"tc-2", name:"read_file", args:{file_path:"src/app/page.tsx"} })

  FilesystemBackend.readFile("src/app/page.tsx") → retorna conteúdo

  → emit("tool_result", { id:"tc-2", name:"read_file", result:"1→import...\n..." })


PASSO 4: RESPOSTA FINAL
────────────────────────
  LLM processa o conteúdo do arquivo e gera resposta

  → emit("response", "O arquivo `page.tsx` é a página principal...")
  → emit("response", "Ele importa os componentes...")
  → emit("response", "...") [streaming chunk a chunk]
  → emit("done", "")


TIMELINE FINAL NA UI:
─────────────────────

  ┌──────────────────────────────────────────────┐
  │ ▶ Thought  18 tokens                         │
  └──────────────────────────────────────────────┘
  ┌──────────────────────────────────────────────┐
  │ ● ls  src/app  0.1s                    [▼]   │
  └──────────────────────────────────────────────┘
  ┌──────────────────────────────────────────────┐
  │ ● read_file  src/app/page.tsx  0.2s    [▼]   │
  └──────────────────────────────────────────────┘

  O arquivo `page.tsx` é a página principal da aplicação
  Next.js. Ele importa os componentes...

  [markdown renderizado com syntax highlighting]
```

---

## Arquivos Principais

| Arquivo | Responsabilidade |
|---------|-----------------|
| `src/lib/agent/index.ts` | System prompt completo + factory do agente |
| `src/lib/agent/deep-agent-config.ts` | Montagem do agente (tools, backend, checkpointer) |
| `src/lib/agent/safe-backend.ts` | Guardrail de segurança (30+ padrões bloqueados) |
| `src/lib/agent/providers.ts` | Registro de provedores LLM (5 provedores) |
| `src/lib/agent/tools/search-web.ts` | Tool customizada de busca web (SearXNG) |
| `src/lib/agent/chat-stream-normalizer.ts` | Tradução de eventos LangGraph → StreamEvents |
| `src/lib/agent/stream.ts` | Primitiva SSE (ReadableStream wrapper) |
| `src/lib/agent/log-bus.ts` | Event bus + ring buffer 500 eventos |
| `src/lib/agent/conversations.ts` | CRUD de conversas (in-memory, pendente migração) |
| `src/lib/db/postgres.ts` | PostgresSaver (LangGraph checkpointing) |
| `src/app/api/agent/chat/route.ts` | Endpoint HTTP, orquestra agente + SSE |
| `src/hooks/use-agent-chat.ts` | Loop SSE no cliente, dispatch ao store |
| `src/stores/agent-store.ts` | Zustand: estado global + mutações de contentParts |
| `src/types/agent.ts` | Tipos: ContentPart, StreamEvent, LLMProvider |
| `src/components/agent/chat-interface.tsx` | UI principal + ContentPartRenderer |
| `src/components/agent/tool-call-block.tsx` | UI: card de tool call com timer ao vivo |
| `src/components/agent/thinking-block.tsx` | UI: bloco de raciocínio colapsável |
| `src/components/agent/response-block.tsx` | UI: markdown renderizado + cursor streaming |
