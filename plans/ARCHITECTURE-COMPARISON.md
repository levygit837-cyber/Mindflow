# Comparação Arquitetural: MindFlow vs Claude Code

**Objetivo:** Mapear componentes equivalentes e identificar gaps para facilitar a migração

---

## 🏗️ Visão Geral Arquitetural

### MindFlow (Atual)
```
┌─────────────────────────────────────────────────────────────┐
│                        FastAPI + gRPC                        │
├─────────────────────────────────────────────────────────────┤
│  Orchestrator  │  Agents  │  Memory  │  Communication Bus  │
├─────────────────────────────────────────────────────────────┤
│         Runtime (Streaming, Execution, Routing)             │
├─────────────────────────────────────────────────────────────┤
│    PostgreSQL + pgvector  │  RabbitMQ  │  KuzuDB (Graph)   │
└─────────────────────────────────────────────────────────────┘
```

### Claude Code (Referência)
```
┌─────────────────────────────────────────────────────────────┐
│                      CLI Interface (Ink)                     │
├─────────────────────────────────────────────────────────────┤
│  QueryEngine  │  Commands  │  Hooks  │  Permissions        │
├─────────────────────────────────────────────────────────────┤
│         Tools  │  Tasks  │  Agents  │  MCP Integration     │
├─────────────────────────────────────────────────────────────┤
│    Context Management  │  Memory (memdir)  │  State         │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Mapeamento de Componentes

### 1. Gerenciamento de Estado

| Aspecto | MindFlow | Claude Code | Gap |
|---------|----------|-------------|-----|
| **State Management** | AppState implícito via DB | `AppState.tsx` centralizado | ❌ Falta state centralizado |
| **Session State** | PostgreSQL sessions | In-memory + disk persistence | ⚠️ Híbrido necessário |
| **Task State** | RabbitMQ + DB | `Task.ts` + disk output | ❌ Falta task state machine |
| **Permission State** | N/A | Permission cache + policies | ❌ Não existe |

**Ação:** Criar `AppState` centralizado em Python mantendo persistência DB

### 2. Sistema de Ferramentas (Tools)

| Aspecto | MindFlow | Claude Code | Gap |
|---------|----------|-------------|-----|
| **Tool Definition** | Pydantic schemas | TypeScript interfaces | ✅ Equivalente |
| **Tool Registry** | Em refatoração | `tools.ts` registry | ⚠️ Incompleto |
| **Tool Execution** | RuntimeExecutor | Tool.execute() | ✅ Similar |
| **Tool Permissions** | N/A | Per-tool permission checks | ❌ Não existe |
| **Tool Progress** | Streaming events | ToolProgressData | ✅ Similar |

**Ação:** Adicionar permission layer antes de tool execution

### 3. Agentes

| Aspecto | MindFlow | Claude Code | Gap |
|---------|----------|-------------|-----|
| **Agent Definition** | SPADE agents | AgentDefinition | ⚠️ Diferentes paradigmas |
| **Agent Communication** | XMPP/InternalBus | Message passing | ✅ Equivalente |
| **Sub-Agents** | Missões hierárquicas | AgentTool spawning | ⚠️ Padrões diferentes |
| **Agent Isolation** | Containers/processes | Worktree isolation | ❌ Falta isolamento |
| **Agent Registry** | Runtime policies | Agent definitions dir | ✅ Similar |

**Ação:** Manter SPADE/XMPP, adicionar AgentTool pattern para sub-agents

### 4. Memória

| Aspecto | MindFlow | Claude Code | Gap |
|---------|----------|-------------|-----|
| **Session Memory** | PostgreSQL + pgvector | memdir + disk files | ⚠️ Diferentes abordagens |
| **Project Memory** | Indexação de código | File-based memory | ✅ Similar |
| **Shared Memory** | Universal memory store | Team memory sync | ✅ Similar |
| **Memory Retrieval** | Semantic search | Context-aware retrieval | ✅ Equivalente |
| **Memory Cleanup** | TTL + manual | Automatic cleanup | ⚠️ Melhorar automação |

**Ação:** Manter PostgreSQL, adicionar file-based cache para performance

### 5. Contexto

| Aspecto | MindFlow | Claude Code | Gap |
|---------|----------|-------------|-----|
| **Context Building** | Manual por agente | QueryEngine centralizado | ❌ Não existe |
| **Context Budget** | Sem limite formal | 200k tokens tracked | ❌ Não existe |
| **Context Providers** | Ad-hoc | Provider pattern | ❌ Não existe |
| **Context Compression** | N/A | Automatic compression | ❌ Não existe |

**Ação:** Implementar QueryEngine com budget management (FASE 1)

### 6. Execução

| Aspecto | MindFlow | Claude Code | Gap |
|---------|----------|-------------|-----|
| **Task Execution** | RabbitMQ workers | Task types (bash, agent, etc.) | ⚠️ Diferentes paradigmas |
| **Background Tasks** | Celery-like | run_in_background flag | ✅ Similar |
| **Task Output** | Streaming + DB | Disk files + streaming | ⚠️ Híbrido melhor |
| **Task Lifecycle** | Manual management | Automatic cleanup | ⚠️ Melhorar automação |

**Ação:** Adicionar Task abstraction sobre RabbitMQ (FASE 2)

### 7. Hooks & Extensibilidade

| Aspecto | MindFlow | Claude Code | Gap |
|---------|----------|-------------|-----|
| **Pre-execution Hooks** | N/A | PreToolUse hooks | ❌ Não existe |
| **Post-execution Hooks** | N/A | PostToolUse hooks | ❌ Não existe |
| **Session Hooks** | N/A | Stop hooks | ❌ Não existe |
| **Hook Configuration** | N/A | settings.json | ❌ Não existe |

**Ação:** Implementar hook system completo (FASE 2)

### 8. Comandos

| Aspecto | MindFlow | Claude Code | Gap |
|---------|----------|-------------|-----|
| **Command System** | API endpoints | Slash commands (80+) | ❌ Não existe |
| **Command Registry** | N/A | Dynamic registration | ❌ Não existe |
| **Command Help** | OpenAPI docs | /help command | ⚠️ Melhorar UX |
| **Custom Commands** | N/A | User-defined commands | ❌ Não existe |

**Ação:** Implementar command system (FASE 3)

### 9. Permissões & Segurança

| Aspecto | MindFlow | Claude Code | Gap |
|---------|----------|-------------|-----|
| **Permission System** | N/A | Granular permissions | ❌ Não existe |
| **Permission Modes** | N/A | auto/prompt/deny/policy | ❌ Não existe |
| **Path Allowlists** | Config-based | Dynamic allowlists | ⚠️ Básico |
| **Audit Logging** | Basic logging | Detailed audit trail | ⚠️ Melhorar |

**Ação:** Implementar permission system completo (FASE 1)

### 10. Loops & Scheduling

| Aspecto | MindFlow | Claude Code | Gap |
|---------|----------|-------------|-----|
| **Cron Jobs** | N/A | CronCreate/CronDelete | ❌ Não existe |
| **Recurring Tasks** | N/A | Loop execution | ❌ Não existe |
| **Job Persistence** | N/A | Durable jobs | ❌ Não existe |

**Ação:** Implementar scheduling system (FASE 4)

---

## 🔄 Padrões de Migração

### Padrão 1: Tool Execution (Antes → Depois)

**Antes (MindFlow atual):**
```python
# Execução direta sem permission check
async def execute_tool(tool_name: str, tool_input: dict):
    tool = get_tool(tool_name)
    result = await tool.execute(tool_input)
    return result
```

**Depois (Com permissions):**
```python
async def execute_tool(
    tool_name: str,
    tool_input: dict,
    agent_id: str | None = None,
):
    # 1. Check permission first
    permission_result = await permission_manager.check_permission(
        tool_name=tool_name,
        tool_input=tool_input,
        agent_id=agent_id,
    )
    
    if not permission_result.allowed:
        raise PermissionError(f"Denied: {permission_result.reason}")
    
    # 2. Execute pre-hooks
    await hook_manager.execute_pre_hooks(tool_name, tool_input)
    
    # 3. Execute tool
    tool = get_tool(tool_name)
    result = await tool.execute(tool_input)
    
    # 4. Execute post-hooks
    await hook_manager.execute_post_hooks(tool_name, result)
    
    return result
```

### Padrão 2: Context Building (Antes → Depois)

**Antes (MindFlow atual):**
```python
# Context building ad-hoc em cada agente
async def process_query(query: str, session_id: str):
    # Cada agente busca seu próprio contexto
    memories = await memory_service.retrieve(query, session_id)
    git_status = await get_git_status()
    
    context = f"Memories: {memories}\nGit: {git_status}"
    
    response = await llm.generate(query, context)
    return response
```

**Depois (Com QueryEngine):**
```python
# Context building centralizado
async def process_query(query: str, session_id: str):
    # QueryEngine gerencia todo o contexto
    query_ctx = QueryContext(
        query=query,
        session_id=session_id,
        max_tokens=200_000,
        include_memory=True,
        include_git=True,
    )
    
    context = await query_engine.build_context(query_ctx)
    
    # Context já vem estruturado e dentro do budget
    response = await llm.generate(query, context)
    return response
```

### Padrão 3: Agent Spawning (Antes → Depois)

**Antes (MindFlow atual):**
```python
# Spawning via SPADE/XMPP
async def spawn_specialist_agent(mission: Mission):
    agent = SpecialistAgent(
        jid=f"specialist@{XMPP_DOMAIN}",
        password=DEFAULT_PASSWORD,
    )
    await agent.start()
    await agent.assign_mission(mission)
    return agent
```

**Depois (Com AgentTool pattern):**
```python
# Spawning via AgentTool (mantendo SPADE internamente)
async def spawn_specialist_agent(
    agent_type: str,
    task_description: str,
):
    # AgentTool abstrai o spawning
    agent_tool = AgentTool(agent_type=agent_type)
    
    result = await agent_tool.execute({
        "description": task_description,
        "prompt": "Analyze the codebase for security issues",
    })
    
    # Internamente usa SPADE/XMPP, mas interface é padronizada
    return result
```

### Padrão 4: Task Management (Antes → Depois)

**Antes (MindFlow atual):**
```python
# Task via RabbitMQ direto
async def run_background_task(command: str):
    publisher = RabbitMQPublisher()
    await publisher.publish({
        "type": "bash_command",
        "command": command,
    })
    # Sem tracking de status
```

**Depois (Com Task abstraction):**
```python
# Task com lifecycle management
async def run_background_task(command: str):
    task = await task_manager.spawn_task(
        task_type=TaskType.LOCAL_BASH,
        description=f"Running: {command}",
        command=command,
    )
    
    # Task tem ID, status, output file
    print(f"Task {task.id} started")
    
    # Pode monitorar status
    status = await task_manager.get_status(task.id)
    
    # Pode ler output
    output = await task_manager.read_output(task.id)
    
    return task
```

---

## 🎯 Decisões Arquiteturais Críticas

### Decisão 1: Manter ou Substituir SPADE/XMPP?

**Opção A: Manter SPADE/XMPP (RECOMENDADO)**
- ✅ Preserva investimento existente
- ✅ Comunicação multi-agente robusta
- ✅ Escalabilidade comprovada
- ❌ Complexidade adicional

**Opção B: Migrar para Message Passing Simples**
- ✅ Mais simples
- ✅ Alinhado com Claude Code
- ❌ Perde features de SPADE
- ❌ Reescrita massiva

**Decisão:** Manter SPADE/XMPP, adicionar AgentTool como abstraction layer

### Decisão 2: PostgreSQL vs File-based Memory?

**Opção A: Manter PostgreSQL (RECOMENDADO)**
- ✅ Persistência robusta
- ✅ Queries complexas
- ✅ pgvector para semantic search
- ❌ Overhead de I/O

**Opção B: Migrar para File-based**
- ✅ Mais simples
- ✅ Alinhado com Claude Code
- ❌ Perde queries SQL
- ❌ Escalabilidade limitada

**Decisão:** Manter PostgreSQL, adicionar file-based cache para hot data

### Decisão 3: RabbitMQ vs In-Process Tasks?

**Opção A: Manter RabbitMQ (RECOMENDADO)**
- ✅ Distribuído
- ✅ Escalável
- ✅ Fault-tolerant
- ❌ Complexidade

**Opção B: Migrar para In-Process**
- ✅ Mais simples
- ✅ Alinhado com Claude Code
- ❌ Não escala
- ❌ Single point of failure

**Decisão:** Manter RabbitMQ, adicionar Task abstraction por cima

---

## 📈 Roadmap de Convergência

### Curto Prazo (Fase 1-2)
- Adicionar camadas de abstração sobre infraestrutura existente
- Implementar permission system e hooks
- Manter 100% backward compatibility

### Médio Prazo (Fase 3-4)
- Refinar abstractions baseado em feedback
- Adicionar command system e scheduling
- Começar deprecation de APIs antigas

### Longo Prazo (Pós-Fase 4)
- Avaliar migração de componentes específicos
- Otimizar performance baseado em métricas
- Considerar simplificações onde apropriado

---

## ✅ Checklist de Compatibilidade

### APIs Existentes (Manter)
- [ ] FastAPI endpoints funcionam sem mudanças
- [ ] gRPC services funcionam sem mudanças
- [ ] RabbitMQ workers funcionam sem mudanças
- [ ] SPADE agents funcionam sem mudanças
- [ ] Memory APIs funcionam sem mudanças

### Novas APIs (Adicionar)
- [ ] Permission APIs
- [ ] Hook APIs
- [ ] Command APIs
- [ ] Task management APIs
- [ ] QueryEngine APIs

### Configuração (Estender)
- [ ] Manter variáveis de ambiente existentes
- [ ] Adicionar novas configurações opcionais
- [ ] Documentar todas as mudanças
- [ ] Fornecer valores default sensatos

---

## 🎓 Guia de Estudo para a Equipe

### Semana 1: Entender Claude Code
- [ ] Ler `src/QueryEngine.ts` completo
- [ ] Estudar `src/Tool.ts` e tool implementations
- [ ] Analisar `src/hooks/` architecture
- [ ] Revisar `src/tasks/` patterns

### Semana 2: Entender Gaps
- [ ] Revisar este documento
- [ ] Identificar componentes críticos
- [ ] Discutir decisões arquiteturais
- [ ] Alinhar prioridades

### Semana 3: Preparar Implementação
- [ ] Setup de ambiente de desenvolvimento
- [ ] Criar branches de feature
- [ ] Definir ownership de componentes
- [ ] Iniciar Fase 1

---

**Próximo:** Iniciar implementação da [Fase 1](./PHASE-1-IMPLEMENTATION-GUIDE.md)
