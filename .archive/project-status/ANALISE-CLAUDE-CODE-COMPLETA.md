# Análise Completa da Arquitetura do Claude Code

## 📋 Índice

1. [Visão Geral da Arquitetura](#1-visão-geral-da-arquitetura)
2. [Sistema de Agentes](#2-sistema-de-agentes)
3. [Gerenciamento de Contexto](#3-gerenciamento-de-contexto)
4. [Sistema de Ferramentas (Tools)](#4-sistema-de-ferramentas-tools)
5. [Sistema de Permissões e Segurança](#5-sistema-de-permissões-e-segurança)
6. [Hooks e Extensibilidade](#6-hooks-e-extensibilidade)
7. [MCP (Model Context Protocol)](#7-mcp-model-context-protocol)
8. [Compactação de Contexto](#8-compatação-de-contexto)
9. [Plan Mode](#9-plan-mode)
10. [Skills e Comandos](#10-skills-e-comandos)
11. [Pontos Fortes do Claude Code](#11-pontos-fortes-do-claude-code)

---

## 1. Visão Geral da Arquitetura

### 1.1 Componentes Principais

O Claude Code é uma CLI oficial da Anthropic para interagir com o modelo Claude. Sua arquitetura é composta por:

- **REPL (Read-Eval-Print Loop)**: Interface principal de interação com o usuário
- **Query Engine**: Motor de execução que gerencia o loop de conversação com a API
- **Tool System**: Sistema modular de ferramentas que o agente pode usar
- **Agent System**: Sistema de subagentes para tarefas complexas
- **MCP Integration**: Integração com servidores MCP para extensibilidade
- **Hook System**: Sistema de hooks para eventos do ciclo de vida
- **Context Manager**: Gerenciador de contexto com compactação automática

### 1.2 Fluxo de Execução

```
User Input → REPL → Query Engine → API Call → Tool Execution → Response
     ↓           ↓           ↓           ↓              ↓
  Process    Validate    Stream     Execute      Update Context
  Command    Context     Response   Tools        & Continue Loop
```

### 1.3 Linguagem e Stack

- **TypeScript/Node.js**: Base principal da aplicação
- **React (Ink)**: Interface terminal baseada em componentes React
- **Bun**: Runtime e bundler utilizado
- **Zod**: Validação de schemas para ferramentas

---

## 2. Sistema de Agentes

### 2.1 Arquitetura de Agentes

O Claude Code possui um sistema sofisticado de agentes que permite:

#### **Tipos de Agentes Built-in:**

1. **General Purpose Agent**: Agente genérico para tarefas diversas
   - Ferramentas: Glob, Grep, FileRead, WebFetch, WebSearch
   - Uso: Pesquisa complexa, análise de código, tarefas multi-step

2. **Claude Code Guide Agent**: Agente especializado em documentação
   - Modelo: Haiku (mais leve)
   - Modo de permissão: dontAsk
   - Uso: Perguntas sobre Claude Code, API, SDK

3. **Explore Agent**: Agente de exploração de código (somente leitura)
   - Não pode editar ou escrever arquivos
   - Uso: Pesquisa, análise, planejamento

### 2.2 Sistema de Subagentes

```typescript
// runAgent.ts - Função principal para executar agentes
export async function* runAgent({
  agentDefinition,
  promptMessages,
  toolUseContext,
  canUseTool,
  isAsync,
  availableTools,
  allowedTools,
  // ... outros parâmetros
}) {
  // 1. Monta pool de ferramentas do worker
  // 2. Cria contexto isolado para o subagente
  // 3. Executa query loop com streaming
  // 4. Gerencia transcripts e memória
  // 5. Limpa recursos ao finalizar
}
```

#### **Características dos Subagentes:**

- **Isolamento de Contexto**: Cada subagente tem seu próprio contexto
- **Ferramentas Próprias**: Pool de ferramentas calculado independentemente
- **Permissões Isoladas**: Não herdam aprovações do agente pai
- **Transcript Separado**: Histórico gravado em sidechain separado
- **Limpeza Automática**: Recursos liberados ao finalizar (memória, files, todos)

### 2.3 Modos de Execução

1. **Síncrono**: Bloqueia o loop principal até completar
2. **Assíncrono**: Executa em background, notifica ao completar
3. **Fork**: Executa em processo separado para tarefas longas

### 2.4 Teams (Swarm de Agentes)

```typescript
// TeamCreateTool - Criação de equipes
{
  "team_name": "my-project",
  "description": "Working on feature X"
}
```

- **Coordenação**: Múltiplos agentes trabalhando em paralelo
- **Task Lists**: Cada team tem uma lista de tarefas associada
- **Comunicação**: Agentes podem se coordenar via sistema de mensagens

---

## 3. Gerenciamento de Contexto

### 3.1 Composição do Contexto

O contexto do Claude Code é composto por:

```
┌─────────────────────────────────────────┐
│ System Prompt (fixo)                    │
├─────────────────────────────────────────┤
│ System Tools (built-in)                 │
├─────────────────────────────────────────┤
│ MCP Tools                               │
├─────────────────────────────────────────┤
│ Custom Agents                           │
├─────────────────────────────────────────┤
│ Memory Files (CLAUDE.md)                │
├─────────────────────────────────────────┤
│ Skills                                  │
├─────────────────────────────────────────┤
│ Conversation History                    │
├─────────────────────────────────────────┤
│ Attachments (hooks, diagnostics, etc.)  │
└─────────────────────────────────────────┘
```

### 3.2 Sistema de Memória

#### **CLAUDE.md Hierarchy:**

1. **User Memory** (`~/.claude/CLAUDE.md`): Preferências pessoais
2. **Project Memory** (`./CLAUDE.md`): Instruções do projeto (versionado)
3. **Local Memory** (`./CLAUDE.local.md`): Preferências locais (gitignored)
4. **Managed Memory**: Instruções gerenciadas por admins

#### **Memory Loading:**

```typescript
// Carregamento com filtros e triggers
- session_start: Carrega no início da sessão
- nested_traversal: Carrega ao navegar diretórios
- path_glob_match: Carrega por padrões de path
- include: Carregado via @-include
- compact: Carregado após compactação
```

### 3.3 Token Budget Management

O sistema gerencia tokens de forma sofisticada:

- **System Prompt**: Overhead fixo
- **System Tools**: Ferramentas built-in
- **MCP Tools**: Ferramentas de servidores MCP (podem ser deferred)
- **Deferred Tools**: Ferramentas adiadas quando tool search está ativo
- **Memory Files**: CLAUDE.md e regras
- **Skills**: Frontmatter de skills carregadas

### 3.4 Prefetch de Memória

```typescript
type MemoryPrefetch = {
  promise: Promise<Attachment[]>
  settledAt: number | null      // Quando a promise resolveu
  consumedOnIteration: number   // Em qual iteração foi consumida
  [Symbol.dispose](): void      // Cleanup automático
}
```

- **Non-blocking**: Prefetch roda em paralelo com streaming
- **Disposable**: Usa `using` para cleanup automático em todos os paths de saída
- **Consumo Condicional**: Se não estiver pronto, pula e tenta na próxima iteração

---

## 4. Sistema de Ferramentas (Tools)

### 4.1 Arquitetura de Ferramentas

```typescript
// Tool Definition
export type Tool = {
  name: string
  description: string
  inputSchema: ZodSchema
  call: (input, context) => Promise<Output>
  prompt: () => string
  renderToolUseMessage: (input) => ReactNode
  renderToolResultMessage: (output) => ReactNode
  // ... outros métodos
}
```

### 4.2 Montagem do Tool Pool

```typescript
// tools.ts - assembleToolPool
export function assembleToolPool(
  permissionContext: ToolPermissionContext,
  mcpTools: Tools
): Tools {
  // 1. Obtém ferramentas built-in (respeita filtro de modo)
  const builtInTools = getTools(permissionContext)
  
  // 2. Filtra MCP tools por regras de deny
  const allowedMcpTools = filterToolsByDenyRules(mcpTools, permissionContext)
  
  // 3. Ordena para estabilidade de cache (built-ins primeiro)
  // 4. Deduplica por nome (built-ins têm precedência)
  return uniqBy(
    [...builtInTools].sort(byName).concat(allowedMcpTools.sort(byName)),
    'name'
  )
}
```

### 4.3 StreamingToolExecutor

```typescript
export class StreamingToolExecutor {
  // Executa ferramentas conforme chegam no stream
  // - Ferramentas concorrentes podem rodar em paralelo
  // - Ferramentas não-concorrentes rodam sozinhas
  // - Resultados são bufferados e emitidos em ordem
  
  addTool(block: ToolUseBlock, assistantMessage: AssistantMessage): void
  discard(): void  // Descarta todas as ferramentas pendentes
  getRemainingResults(): AsyncGenerator<ToolResult>
}
```

#### **Características:**

- **Controle de Concorrência**: Ferramentas marcadas como `concurrent-safe` rodam em paralelo
- **Buffer de Resultados**: Resultados são emitidos na ordem de chegada das ferramentas
- **Abort Controller**: Aborta subprocessos irmãos quando uma ferramenta Bash falha
- **Discard**: Permite descartar todas as ferramentas pendentes em caso de fallback

### 4.4 Categorias de Ferramentas

1. **Built-in Tools**: FileRead, Glob, Grep, Bash, FileEdit, FileWrite
2. **Agent Tools**: AgentTool para spawn de subagentes
3. **MCP Tools**: Ferramentas de servidores MCP externos
4. **LSP Tools**: Integração com Language Server Protocol
5. **Computer Use Tools**: Ferramentas para uso de computador (macOS)

---

## 5. Sistema de Permissões e Segurança

### 5.1 Modos de Permissão

```typescript
type PermissionMode = 
  | 'default'        // Pergunta quando necessário
  | 'acceptEdits'    // Aceita edições automaticamente
  | 'dontAsk'        // Não pergunta (agents específicos)
  | 'bypassAll'      // Bypass total (apenas em sandbox seguro)
```

### 5.2 Sistema de Regras

```typescript
type ToolPermissionContext = {
  mode: PermissionMode
  alwaysAllowRules: PermissionRule[]   // Regras de allow
  alwaysDenyRules: PermissionRule[]    // Regras de deny
  session: PermissionRule[]            // Regras de sessão
}
```

#### **Tipos de Regras:**

- **Exact Match**: `Bash(npm test)` - Comando exato
- **Prefix Match**: `Bash(npm:*)` - Prefixo de comando
- **Wildcard**: `Bash(*echo*)` - Padrão com curinga
- **Tool-specific**: `Read(/path/to/file)` - Para ferramentas específicas

### 5.3 Sandbox System

```typescript
// shouldUseSandbox.ts
- Verifica se comando está em excludedCommands
- Verifica regras de deny/ask explícitas
- Para comandos compostos, verifica cada subcomando
- Auto-allow em sandboxed quando não há regras explícitas
```

#### **Características de Segurança:**

- **Comandos Excluídos**: Lista de comandos perigosos bloqueados
- **Subcommand Checking**: Verifica cada parte de comandos compostos
- **Sandbox Auto-allow**: Em sandbox, permite automaticamente se não há regra explícita
- **Network Restrictions**: Restrições de rede separadas do WebFetch preapproved

### 5.4 Dangerously Skip Permissions

```typescript
// setup.ts - Validação de --dangerously-skip-permissions
if (isAnt && entrypoint !== 'local-agent' && entrypoint !== 'claude-desktop') {
  // Só funciona em Docker/sandbox SEM acesso à internet
  if (!isSandboxed || hasInternet) {
    console.error('Can only be used in Docker/sandbox with no internet')
    process.exit(1)
  }
}
```

---

## 6. Hooks e Extensibilidade

### 6.1 Tipos de Hooks

```typescript
type HookEvent =
  | 'SessionStart'          // Início da sessão
  | 'UserPromptSubmit'      // Quando usuário envia prompt
  | 'PreToolUse'            // Antes de usar ferramenta
  | 'PostToolUse'           // Depois de usar ferramenta
  | 'PostToolFailure'       // Quando ferramenta falha
  | 'Stop'                  // Quando agente para
  | 'PreCompact'            // Antes de compactar contexto
  | 'ElicitationResult'     // Após resposta de elicitação MCP
  | 'ConfigChange'          // Quando arquivos de config mudam
  | 'InstructionsLoaded'    // Quando arquivo CLAUDE.md é carregado
```

### 6.2 Formato de Hook

```typescript
// Cada hook tem:
{
  summary: string           // Descrição resumida
  description: string       // Descrição detalhada com formato de I/O
  matcherMetadata: {        // Metadados para matching
    fieldToMatch: string
    values: string[]
  }
}
```

#### **Exemplo - PreToolUse Hook:**

```
Input: JSON com tool_name, input, tool_use_id
Output: 
  - Exit 0: Permite uso da ferramenta
  - Exit 2: Bloqueia uso da ferramenta
  - Outros: Mostra stderr ao usuário
```

### 6.3 Hooks por Agente

```typescript
// loadAgentsDir.ts - Hooks específicos por agente
type BaseAgentDefinition = {
  // ...
  hooks?: HooksSettings  // Hooks registrados quando agente inicia
  // ...
}

// Hooks são limpos quando agente termina
clearSessionHooks(rootSetAppState, agentId)
```

---

## 7. MCP (Model Context Protocol)

### 7.1 Arquitetura MCP

```typescript
// MCPConnectionManager.tsx
- Gerencia conexões com servidores MCP
- Reconexão automática para conexões SSE
- Suporte a servidores dinâmicos
- Integração com plugins
```

### 7.2 SDK MCP Transport Bridge

```typescript
// SdkControlTransport.ts
// Permite servidores MCP rodarem dentro do processo SDK

CLI → SDK:
1. MCP Client chama ferramenta
2. Transport envia via stdout para SDK
3. SDK processa e retorna via control response

SDK → CLI:
1. Query recebe control request
2. MCP server processa mensagem
3. Transport envia resposta de volta
```

### 7.3 MCP Tools Integration

```typescript
// tools.ts - assembleToolPool
- MCP tools são filtradas por deny rules
- Ordenadas para estabilidade de cache
- Deduplicadas com built-in tools (built-ins têm precedência)
```

### 7.4 MCP Elicitation

```typescript
// Sistema de elicitação para MCP
- Ferramentas podem solicitar input do usuário
- Suporte a URLs e confirmações
- Integração com sistema de permissões
```

---

## 8. Compactação de Contexto

### 8.1 Tipos de Compactação

1. **Manual Compact** (`/compact`): Usuário solicita explicitamente
2. **Auto Compact**: Automático quando contexto está quase cheio
3. **Session Memory Compact**: Compactação via sistema de memória de sessão
4. **Reactive Compact**: Compactação reativa em modo experimental

### 8.2 Thresholds e Buffers

```typescript
const AUTOCOMPACT_BUFFER_TOKENS = 13_000
const WARNING_THRESHOLD_BUFFER_TOKENS = 20_000
const ERROR_THRESHOLD_BUFFER_TOKENS = 20_000
const MANUAL_COMPACT_BUFFER_TOKENS = 3_000
```

### 8.3 Circuit Breaker

```typescript
// Para de tentar autocompact após N falhas consecutivas
const MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES = 3

// Prende sessões com contexto irrecuperavelmente sobrecarregado
// de gastar chamadas de API com tentativas fadadas ao fracasso
```

### 8.4 Cache Sharing

```typescript
// Prompt cache sharing para forked agents
const promptCacheSharingEnabled = getFeatureValue(
  'tengu_compact_cache_prefix',
  true  // Default: true (3P)
)

// Reutiliza cache de prefixo da conversa principal
// Economiza tokens de cache creation (~38B tok/day)
```

### 8.5 Fluxo de Compactação

```
1. Verifica se deve compactar (threshold check)
2. Executa PreCompact hooks
3. Cria attachment de skills invocadas
4. Chama API para gerar resumo
5. Substitui mensagens antigas pelo resumo
6. Executa PostCompact cleanup
7. Reseta cache read baseline
```

### 8.6 Memória Pós-Compactação

```typescript
// Preserva skills invocadas após compactação
function createSkillAttachmentIfNeeded(agentId?: string) {
  const invokedSkills = getInvokedSkillsForAgent(agentId)
  
  // Ordena por mais recente primeiro
  // Trunca cada skill para economizar tokens
  // Filtra por budget de tokens total
  return createAttachmentMessage({ type: 'invoked_skills', skills })
}
```

---

## 9. Plan Mode

### 9.1 Quando Usar

```typescript
// EnterPlanModeTool/prompt.ts
**Prefer using EnterPlanMode** para tarefas não-triviais:
1. Nova funcionalidade significativa
2. Múltiplas abordagens válidas
3. Modificações que afetam comportamento existente
4. Decisões arquiteturais
5. Mudanças em múltiplos arquivos (>2-3)
6. Requisitos incertos
```

### 9.2 Workflow do Plan Mode

#### **Fase 1: Entendimento Inicial**

```
1. Lança até N agentes Explore em PARALELO
2. Foca em entender o pedido do usuário
3. Busca funções, utilitários e padrões existentes
4. Evita propor código novo quando implementação existe
```

#### **Fase 2: Descoberta de Requisitos**

```
1. Analisa código encontrado
2. Identifica padrões e convenções
3. Mapeia dependências
4. Identifica riscos e considerações
```

#### **Fase 3: Proposta de Plano**

```
1. Cria arquivo de plano em .claude/plans/
2. Documenta abordagem
3. Lista etapas de implementação
4. Identifica testes necessários
```

### 9.3 Restrições do Plan Mode

```typescript
// Plan Mode V2 Instructions
- NÃO pode fazer edições (exceto arquivo de plano)
- NÃO pode rodar ferramentas não-read-only
- NÃO pode fazer commits
- APENAS pode usar ferramentas de leitura
- APENAS pode editar arquivo de plano especificado
```

### 9.4 Interview Phase

```typescript
// Modo iterativo de planejamento
if (isPlanModeInterviewPhaseEnabled()) {
  // Usa workflow iterativo com perguntas ao usuário
  // Ao invés de workflow de exploração em paralelo
}
```

---

## 10. Skills e Comandos

### 10.1 Sistema de Skills

```typescript
// Skills são capacidades on-demand
- Invocadas via /skill-name
- Carregam conteúdo de referência
- Preservam contexto após compactação
- Podem ter frontmatter com configurações
```

### 10.2 Discovery de Skills

```typescript
// Skill Discovery Tool
- Automaticamente surfacia skills relevantes a cada turno
- Filtra skills já visíveis ou carregadas
- Usuário pode chamar DiscoverSkills para busca manual
```

### 10.3 Slash Commands

```typescript
// Comandos locais vs forked
type Command = {
  type: 'local' | 'prompt' | 'remote'
  name: string
  description: string
  load: () => Promise<CommandModule>
}

// Forked commands rodam em subagentes
// Local commands rodam no loop principal
```

### 10.4 Hooks por Comando

```typescript
// Skills podem registrar hooks específicos
// Hooks rodam quando skill é invocada
// Hooks são limpos quando skill termina
```

---

## 11. Pontos Fortes do Claude Code

### 11.1 **Arquitetura Modular e Extensível**

✅ **Sistema de Plugins**: MCP permite adicionar ferramentas externas sem modificar código core
✅ **Hook System**: Extensibilidade via hooks em pontos-chave do ciclo de vida
✅ **Agent System**: Subagentes especializados para tarefas específicas
✅ **Skills System**: Capacidades on-demand carregadas dinamicamente

### 11.2 **Gerenciamento de Contexto Inteligente**

✅ **Compactação Automática**: Previne estouro de contexto sem interromper trabalho
✅ **Cache Sharing**: Reutiliza cache de prompt entre sessões (economia de tokens)
✅ **Memory Prefetch**: Carrega memória relevante em paralelo (non-blocking)
✅ **Token Budget**: Gerenciamento sofisticado de uso de tokens

### 11.3 **Segurança Robusta**

✅ **Sandbox System**: Execução isolada de comandos perigosos
✅ **Permission Modes**: Múltiplos níveis de permissão configuráveis
✅ **Command Validation**: Validação de comandos antes da execução
✅ **Network Restrictions**: Controle de acesso à rede

### 11.4 **Execução Concorrente e Streaming**

✅ **StreamingToolExecutor**: Executa ferramentas em paralelo quando seguro
✅ **Concurrent-safe Tools**: Ferramentas marcadas como seguras rodam em paralelo
✅ **Buffer de Resultados**: Resultados emitidos em ordem de chegada
✅ **Abort Controller**: Cancela subprocessos em caso de erro

### 11.5 **Sistema de Agentes Avançado**

✅ **Hierarquia de Agentes**: Agentes pai podem spawnar subagentes
✅ **Isolamento de Contexto**: Cada agente tem contexto isolado
✅ **Teams/Swarm**: Múltiplos agentes coordenados trabalhando em paralelo
✅ **Async Execution**: Agentes podem rodar em background

### 11.6 **Planejamento Estruturado**

✅ **Plan Mode**: Modo dedicado para planejamento antes de implementação
✅ **Exploração Paralela**: Múltiplos agentes exploram código simultaneamente
✅ **Arquivo de Plano**: Documentação estruturada da abordagem
✅ **Validação de Requisitos**: Identificação de ambiguidades antes de codar

### 11.7 **Experiência do Usuário**

✅ **REPL Interativo**: Interface terminal rica com React (Ink)
✅ **Feedback em Tempo Real**: Streaming de respostas e progresso
✅ **Keyboard Shortcuts**: Atalhos configuráveis
✅ **IDE Integration**: Integração com VS Code e JetBrains

### 11.8 **Observabilidade e Debug**

✅ **Query Profiling**: Medição detalhada de tempo em cada etapa
✅ **Transcript Recording**: Gravação completa de conversas e sidechains
✅ **Debug Logging**: Logs detalhados para troubleshooting
✅ **Analytics**: Telemetria para métricas de uso

### 11.9 **Resiliência**

✅ **Circuit Breaker**: Previne loops infinitos de autocompactação
✅ **Retry Logic**: Tentativas automáticas com backoff
✅ **Graceful Degradation**: Fallbacks quando serviços falham
✅ **Resource Cleanup**: Limpeza automática de recursos (memória, files, processes)

### 11.10 **Extensibilidade via MCP**

✅ **MCP Servers**: Servidores externos adicionam ferramentas e recursos
✅ **Dynamic MCP**: Suporte a servidores adicionados em runtime
✅ **SDK MCP**: Servidores podem rodar in-process
✅ **Channel Permissions**: Controle granular de permissões por canal

---

## Conclusão

O Claude Code é uma aplicação madura e bem-arquitetada que combina:

1. **Arquitetura Modular**: Componentes bem-definidos e extensíveis
2. **Gerenciamento de Contexto Avançado**: Compactação automática e cache sharing
3. **Sistema de Agentes Sofisticado**: Hierarquia, isolamento e coordenação
4. **Segurança Robusta**: Sandbox, permissões e validação
5. **Extensibilidade**: MCP, hooks, skills e plugins
6. **Performance**: Streaming, concorrência e prefetch
7. **Observabilidade**: Profiling, transcripts e analytics

Estes pontos fortes fazem do Claude Code uma referência para desenvolvimento de agentes de IA, especialmente em termos de:

- **Escalabilidade**: Suporte a sessões longas com compactação automática
- **Segurança**: Múltiplos níveis de proteção contra uso indevido
- **Extensibilidade**: Fácil adição de novas capacidades via MCP e hooks
- **Usabilidade**: Interface rica e feedback em tempo real
