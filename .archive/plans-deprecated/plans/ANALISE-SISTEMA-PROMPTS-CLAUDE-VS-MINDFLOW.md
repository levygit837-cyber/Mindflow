# Análise: Sistema de Prompts — Claude Code vs MindFlow

**Data:** 2026-01-04
**Objetivo:** Analisar como o sistema de prompts do Claude Code funciona, comparar com o MindFlow, e identificar processos obrigatórios que o MindFlow deve adicionar.

---

## 1. Arquitetura do Sistema de Prompts do Claude Code

### 1.1 Visão Geral do Pipeline

O Claude Code utiliza um pipeline **multi-camada com prioridades** para construir o system prompt final. A montagem ocorre em 3 camadas independentes que são combinadas antes da chamada de API:

```
fetchSystemPromptParts() - executa em PARALELO via Promise.all
├── getSystemPrompt()    → Tool descriptions, Instruções, Rules, Memory
├── getUserContext()     → Date/time, OS/Shell, Timezone, CWD
└── getSystemContext()   → Git status, Cache breakers, Injection
        │
        ▼
buildEffectiveSystemPrompt() - sistema de PRIORIDADES
├── Prioridade 0: Override (substitui TUDO)
├── Prioridade 1: Coordinator mode
├── Prioridade 2: Agent definition (proactive → APPEND, else → REPLACE)
├── Prioridade 3: Custom system prompt
├── Prioridade 4: Default system prompt
└── appendSystemPrompt → SEMPRE adicionado no final
        │
        ▼
buildSystemPromptBlocks() - split em blocos para PROMPT CACHING
└── [Global Block] [Tools Block] [Context Block] ...
```

### 1.2 Os 3 Componentes Independentes

**Componente 1: `getSystemPrompt()` → `constants/prompts.ts`**

- Monta o conteúdo base do system prompt
- Entradas: tools, mainLoopModel, additionalWorkingDirectories, mcpClients
- Saída: Array de strings (segmentos do prompt)
- Inclui descrições XML de TODAS as ferramentas disponíveis

**Componente 2: `getUserContext()` → `context.ts`**

- Retorna contexto dinâmico que muda a cada requisição (memoizado)
- Conteúdo: Data/hora, SO, Shell, CWD, Timezone

**Componente 3: `getSystemContext()` → `context.ts`**

- Retorna contexto estável da sessão (memoizado, invalidado por clearSessionCaches)
- Conteúdo: Git status, Cache breakers, Injeções de system prompt

### 1.3 Processos Obrigatórios do Claude Code

| # | Processo | Descrição | Arquivo |
|---|----------|-----------|---------|
| 1 | **Context Injection** | Data/hora, OS, shell, CWD | `context.ts` → `getUserContext()` |
| 2 | **Git Status Injection** | Branch, staged files | `context.ts` → `getSystemContext()` |
| 3 | **Tool Description Injection** | Lista XML de ferramentas | `constants/prompts.ts` |
| 4 | **Memory File Loading** | CLAUDE.md do projeto/usuário | Pipeline de prompts |
| 5 | **Priority Assembly** | Hierarquia de prioridades | `utils/systemPrompt.ts` |
| 6 | **Prompt Caching** | Blocos com cache_control | `services/api/claude.ts` |
| 7 | **Cache Invalidation** | Limpeza ao mudar contexto | `commands/clear/caches.ts` |
| 8 | **Agent Override/Append** | Agentes substituem/anexam | `utils/systemPrompt.ts` |
| 9 | **Environment Details** | Ambiente de execução | `constants/prompts.ts` |
| 10 | **MCP Context** | Servidores MCP conectados | `utils/queryContext.ts` |

---

## 2. Arquitetura do Sistema de Prompts do MindFlow

### 2.1 Visão Geral do Pipeline Atual

O MindFlow utiliza um pipeline **linear simples** que concatena strings:

```
build_system_prompt() (base.py)
└── MINDFLOW_PREAMBLE + personality + PERSISTENCE (concatenação linear)
        │
        ▼
compose_orchestrator_prompt() (orchestrator.py)
└── Preamble + segmentos nomeados (core, governance, delegation, etc.)
        │
        ▼
ToolPromptInjector (tool_injection.py)
⚠️ EXISTE mas NÃO está integrado ao pipeline padrão
└── Gera descrições XML e instruções de uso de ferramentas
```

### 2.2 Componentes Atuais

**`build_system_prompt()` → `base.py`:** Concatena 3 strings fixas (Preamble + Personality + Persistence). Não tem contexto dinâmico, ferramentas ou ambiente.

**`compose_orchestrator_prompt()` → `orchestrator.py`:** Concatena segmentos nomeados. Apenas concatenação, sem sistema de prioridades.

**`ToolPromptInjector` → `tool_injection.py`:** Gera descrições XML. Implementado mas **NÃO integrado** ao pipeline padrão.

**`AgentRuntimePolicy._inject_tool_descriptions()` → `runtime_policy.py`:** Injeta ferramentas ao criar agente, mas inconsistente.

### 2.3 Processos que o MindFlow NÃO TEM

| # | Processo | Status | Impacto |
|---|----------|--------|---------|
| 1 | **Context Injection** | ❌ NÃO EXISTE | **ALTO** |
| 2 | **Git Status Injection** | ❌ NÃO EXISTE | **MÉDIO** |
| 3 | **Tool Description no pipeline** | ⚠️ Existe mas NÃO integrado | **ALTO** |
| 4 | **Priority System** | ❌ NÃO EXISTE | **MÉDIO** |
| 5 | **Memory File Loading** | ⚠️ PARCIAL | **MÉDIO** |
| 6 | **Prompt Caching** | ❌ NÃO EXISTE | **ALTO** |
| 7 | **Cache Invalidation** | ❌ NÃO EXISTE | **MÉDIO** |
| 8 | **Environment Details** | ❌ NÃO EXISTE | **MÉDIO** |
| 9 | **MCP Context** | ❌ NÃO EXISTE | **BAIXO** |
| 10 | **Session Tracking** | ❌ NÃO EXISTE | **MÉDIO** |
