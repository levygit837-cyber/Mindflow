# Análise: Sistema de Injeção de Ferramentas no Prompt do Agente

## Data: 2026-01-04

---

## 1. RESUMO EXECUTIVO

### Pergunta Central
>
> Como o Claude Code injeta ferramentas diretamente no prompt do Agente? O MindFlow já tem um sistema similar?

### Resposta

**O MindFlow JÁ possui uma arquitetura de registro de ferramentas robusta e similar ao Claude Code.** Porém, há uma diferença crucial na **forma como as ferramentas são apresentadas ao LLM**:

| Aspecto | Claude Code | MindFlow | Gap |
|---------|-------------|----------|-----|
| **Registro de Ferramentas** | Tool objects com name/description/schema | ToolRegistry com @tool decorator | ✅ Similar |
| **Lazy Loading** | LazyToolRegistration | LazyToolRegistration (já copiado) | ✅ Implementado |
| **Permissões** | Granular por ferramenta | ToolPermissionContext | ✅ Implementado |
| **Mapeamento por Agente** | tools array em CustomAgentDefinition | ToolScope mapping em AgentRuntimePolicy | ✅ Similar |
| **Injeção no System Prompt** | `getUsingYourToolsSection()` + formato API | ❌ NÃO IMPLEMENTADO | ⚠️ **GAP CRÍTICO** |
| **Descrição no Prompt** | Formato XML `<functions>` com schema | ❌ Descrição apenas no registry | ⚠️ **GAP CRÍTICO** |

**Conclusão:** O MindFlow tem a infraestrutura de ferramentas, mas **não injeta as descrições das ferramentas no system prompt do agente**. Isso significa que o LLM não sabe quais ferramentas tem disponíveis até tentar chamá-las.

---

## 2. COMO O CLAUDE CODE INJETA FERRAMENTAS

### 2.1 Arquitetura de Injeção

O Claude Code usa **DOIS caminhos** para informar o LLM sobre ferramentas:

#### Caminho 1: API Parameter (Primário)

```typescript
// services/api/claude.ts
const response = await client.beta.messages.create({
  model: model,
  system: systemPromptBlocks,  // System prompt COM instruções de ferramentas
  tools: toolDefinitions,       // Array de Tool objects no formato API
  messages: messages
})
```

As ferramentas são passadas como **parâmetro `tools` na API call**, não no system prompt. O formato é:

```json
{
  "name": "Read",
  "description": "Reads a file from the local filesystem...",
  "input_schema": {
    "type": "object",
    "properties": {
      "file_path": { "type": "string", "description": "Absolute path to the file" }
    },
    "required": ["file_path"]
  }
}
```

#### Caminho 2: System Prompt (Instruções de Uso)

O system prompt contém seções que **ensinam como usar as ferramentas**:

```typescript
// constants/prompts.ts
function getUsingYourToolsSection(enabledTools: Set<string>): string {
  const items = [
    `Do NOT use the ${BASH_TOOL_NAME} to run commands when a relevant dedicated tool is provided.`,
    `To read files use ${FILE_READ_TOOL_NAME} instead of cat, head, tail, or sed`,
    `To edit files use ${FILE_EDIT_TOOL_NAME} instead of sed or awk`,
    // ... mais instruções
  ]
  return [`# Using your tools`, ...prependBullets(items)].join(`\n`)
}
```

#### Caminho 3: Lazy Tool Discovery (Ferramentas Diferidas)

Para ferramentas que não cabem no contexto inicial:

```typescript
// tools/ToolSearchTool/prompt.ts
const PROMPT_TAIL = ` Until fetched, only the name is known — there is no parameter schema, so the tool cannot be invoked. This tool takes a query, matches it against the deferred tool list, and returns the matched tools' complete JSONSchema definitions inside a <functions> block.`
```

### 2.2 Fluxo de Construção do System Prompt

```
getSystemPrompt()
  ├── getSimpleIntroSection()          # "You are an interactive agent..."
  ├── getSimpleSystemSection()         # Regras básicas
  ├── getSimpleDoingTasksSection()     # Como fazer tarefas
  ├── getActionsSection()              # Cuidado com ações
  ├── getUsingYourToolsSection()       # ⭐ COMO USAR FERRAMENTAS
  ├── getSimpleToneAndStyleSection()   # Tom de comunicação
  ├── getOutputEfficiencySection()     # Eficiência de output
  ├── SYSTEM_PROMPT_DYNAMIC_BOUNDARY   # Separador cache/dinâmico
  └── Seções dinâmicas (memória, MCP, etc.)
```

### 2.3 Formato XML para Descrição de Ferramentas

O Claude Code usa um formato específico para descrever ferramentas no prompt:

```xml
<functions>
<function>{"description": "Reads a file", "name": "Read", "parameters": {...}}</function>
<function>{"description": "Writes a file", "name": "Write", "parameters": {...}}</function>
</functions>
```

Este formato é usado em:

- `ToolSearchTool` (busca lazy de ferramentas)
- `buildDiffableContent()` (cache break detection)
- `formatAsTeammateMessage()` (mensagens entre teammates)

---

## 3. COMO O MINDFLOW GERENCIA FERRAMENTAS ATUALMENTE

### 3.1 Arquitetura Atual

```
ToolRegistry (singleton)
  ├── register_tool()          # Registra classe como ferramenta
  ├── get_tool()               # Recupera instância por nome
  ├── filter_by_category()     # Filtra por categoria
  └── LazyToolRegistration     # Carregamento lazy

_DefaultRegistry (por agente)
  ├── _build_tool_mapping()    # Mapeia ToolScope → ferramentas
  ├── _get_tools_for_scope()   # Retorna instâncias concretas
  └── get_tools_for_agent()    # Filtra por agente específico

AgentRuntimePolicy (política por agente)
  ├── agent_role: AgentType
  ├── tools: list[ToolScope]   # Escopos de ferramentas permitidas
  └── specialist: SpecialistType
```

### 3.2 Como as Ferramentas São Disponibilizadas aos Agentes

```python
# python/mindflow_backend/agents/tools/__init__.py
class _DefaultRegistry:
    def _get_tools_for_scope(self, scope: ToolScope) -> list[Any]:
        """Get concrete tool instances for a given ToolScope."""
        if scope == ToolScope.FILESYSTEM:
            return self._get_filesystem_tools()
        elif scope == ToolScope.SHELL:
            return self._get_shell_tools()
        # ... mais escopos
```

### 3.3 Onde as Ferramentas São Usadas

As ferramentas são usadas no `AgentRuntime` mas **NÃO são injetadas no system prompt**. O agente recebe:

1. ✅ Um system prompt estático
2. ✅ Instâncias de ferramentas (para execução)
3. ❌ **SEM descrições das ferramentas no prompt**

---

## 4. GAP ANALYSIS

### 4.1 O que o MindFlow JÁ TEM

| Componente | Status | Localização |
|------------|--------|-------------|
| ToolRegistry | ✅ Implementado | `python/mindflow_backend/agents/tools/base/tool_registry.py` |
| @tool decorator | ✅ Implementado | `python/mindflow_backend/schemas/tools/tool.py` |
| LazyToolRegistration | ✅ Implementado | `python/mindflow_backend/schemas/tools/registry.py` |
| ToolPermissionContext | ✅ Implementado | `python/mindflow_backend/schemas/tools/context.py` |
| ToolScope mapping | ✅ Implementado | `python/mindflow_backend/agents/tools/__init__.py` |
| AgentRuntimePolicy | ✅ Implementado | `python/mindflow_backend/agents/specialists/runtime_policy.py` |
| BaseAgent (config) | ✅ Implementado | `python/mindflow_backend/agents/_base.py` |

### 4.2 O que o MindFlow NÃO TEM

| Componente | Status | Impacto |
|------------|--------|---------|
| Tool descriptions no system prompt | ❌ Não existe | **ALTO** - LLM não sabe quais ferramentas tem |
| Formato XML `<functions>` | ❌ Não existe | **ALTO** - Padrão Claude Code não adotado |
| `getUsingYourToolsSection()` | ❌ Não existe | **MÉDIO** - Sem instruções de uso de ferramentas |
| Lazy tool discovery (ToolSearchTool) | ❌ Não existe | **MÉDIO** - Sem busca lazy de ferramentas |
| Tool result summarization | ❌ Não existe | **BAIXO** - Não crítico |

---

## 5. PROPOSTA DE IMPLEMENTAÇÃO

### 5.1 Visão Geral

Criar um sistema de **Tool Prompt Injector** que:

1. Gere descrições de ferramentas no formato que o LLM entende
2. Injete essas descrições no system prompt do agente
3. Suporte lazy loading para ferramentas pesadas
4. Seja compatível com o formato XML do Claude Code

### 5.2 Arquitetura Proposta

```
ToolPromptInjector (NOVO)
  ├── generate_tool_descriptions()    # Gera descrições no formato XML
  ├── generate_usage_instructions()   # Gera instruções de uso
  ├── inject_into_system_prompt()     # Injeta no prompt
  └── LazyToolDiscovery (NOVO)        # Busca lazy de ferramentas

SystemPromptBuilder (NOVO)
  ├── build_system_prompt()           # Constrói prompt completo
  ├── add_tool_section()              # Adiciona seção de ferramentas
  └── add_usage_section()             # Adiciona instruções de uso
```

### 5.3 Formato de Injeção

#### Opção A: Formato XML (Compatível com Claude Code)

```xml
# Available Tools

You have access to the following tools:

<functions>
<function>
<name>Read</name>
<description>Reads a file from the local filesystem. You can access any file in the working directory.</description>
<parameters>
{"type": "object", "properties": {"file_path": {"type": "string", "description": "Absolute path to the file"}}, "required": ["file_path"]}
</parameters>
</function>
<function>
<name>Write</name>
<description>Writes content to a file. Creates the file if it doesn't exist.</description>
<parameters>
{"type": "object", "properties": {"file_path": {"type": "string"}, "content": {"type": "string"}}, "required": ["file_path", "content"]}
</parameters>
</function>
</functions>
```

#### Opção B: Formato Markdown (Mais legível)

```markdown
# Available Tools

## Read
**Description:** Reads a file from the local filesystem.
**Parameters:**
- `file_path` (string, required): Absolute path to the file

## Write
**Description:** Writes content to a file.
**Parameters:**
- `file_path` (string, required): Absolute path to the file
- `content` (string, required): Content to write
```

**Recomendação:** Usar **Opção A (XML)** para compatibilidade com Claude Code e APIs de LLM.

### 5.4 Seções do System Prompt

```python
# NOVO: python/mindflow_backend/agents/prompts/tool_injection.py

def get_tool_descriptions_section(registry: ToolRegistry, agent: BaseAgent) -> str:
    """Gera seção de descrições de ferramentas para o system prompt."""
    tools = registry.get_tools_for_agent(agent)
    
    descriptions = []
    for tool in tools:
        descriptions.append(f"""<function>
<name>{tool.name}</name>
<description>{tool.description}</description>
<parameters>{json.dumps(tool.input_schema)}</parameters>
</function>""")
    
    return f"""# Available Tools

You have access to the following tools:

<functions>
{chr(10).join(descriptions)}
</functions>"""

def get_tool_usage_section(agent: BaseAgent) -> str:
    """Gera seção de instruções de uso de ferramentas."""
    items = []
    
    if agent.has_tool_scope(ToolScope.FILESYSTEM):
        items.append("To read files, use the Read tool instead of cat, head, or tail.")
        items.append("To write files, use the Write tool instead of echo or redirection.")
    
    if agent.has_tool_scope(ToolScope.SHELL):
        items.append("Use Bash for system commands that require shell execution.")
    
    if items:
        return "# Using Your Tools\n\n" + "\n".join(f"- {item}" for item in items)
    return ""
```

### 5.5 Integração com AgentRuntime

```python
# MODIFICAR: python/mindflow_backend/runtime/core/agent_runtime.py

class AgentRuntime:
    def build_system_prompt(self, agent: BaseAgent) -> str:
        """Constrói system prompt com injeção de ferramentas."""
        sections = [
            self.get_base_prompt(agent),
            get_tool_descriptions_section(self.registry, agent),  # NOVO
            get_tool_usage_section(agent),                        # NOVO
            self.get_environment_section(),
            self.get_memory_section(),
        ]
        return "\n\n".join(filter(None, sections))
```

### 5.6 Lazy Tool Discovery (Opcional)

Para ferramentas que não cabem no contexto inicial:

```python
# NOVO: python/mindflow_backend/agents/tools/lazy_discovery.py

class LazyToolDiscovery:
    """Permite descobrir ferramentas sob demanda."""
    
    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        self._discovered: set[str] = set()
    
    def get_discovery_prompt(self) -> str:
        """Retorna prompt para o agente descobrir ferramentas."""
        return """# Tool Discovery

Some tools are not shown initially to save context space. 
To discover additional tools, use the search_tool function with a query.

Example: search_tool("database operations")
"""
    
    def discover_tool(self, query: str) -> list[dict]:
        """Busca ferramentas por query e retorna descrições."""
        tools = self.registry.search_tools(query)
        return [self._format_tool(t) for t in tools if t.name not in self._discovered]
```

---

## 6. PLANO DE IMPLEMENTAÇÃO

### Fase 1: Tool Prompt Injector (2-3 dias)

- [ ] Criar `ToolPromptInjector` class
- [ ] Implementar `generate_tool_descriptions()`
- [ ] Implementar `generate_usage_instructions()`
- [ ] Criar testes unitários

### Fase 2: Integração com AgentRuntime (1-2 dias)

- [ ] Modificar `AgentRuntime.build_system_prompt()`
- [ ] Adicionar seção de ferramentas ao prompt
- [ ] Testar com agentes existentes

### Fase 3: Lazy Discovery (Opcional, 2-3 dias)

- [ ] Criar `LazyToolDiscovery` class
- [ ] Implementar busca por query
- [ ] Integrar com ToolRegistry

### Fase 4: Validação e Otimização (1-2 dias)

- [ ] Testar com diferentes modelos
- [ ] Otimizar tamanho das descrições
- [ ] Documentar API

**Total Estimado: 6-10 dias**

---

## 7. BENEFÍCIOS ESPERADOS

1. **LLM sabe quais ferramentas tem disponível** → Menos erros de "ferramenta não encontrada"
2. **Melhor uso das ferramentas** → Instruções claras de quando usar cada uma
3. **Compatibilidade com Claude Code** → Padrão já validado
4. **Redução de tokens** → Lazy loading evita descrições desnecessárias
5. **Melhor UX do agente** → Respostas mais precisas e eficientes

---

## 8. REFERÊNCIAS

### Arquivos Analisados no Claude Code

- `claude/constants/prompts.ts` - System prompt construction
- `claude/services/api/claude.ts` - API call construction
- `claude/tools/ToolSearchTool/prompt.ts` - Lazy tool discovery
- `claude/utils/swarm/inProcessRunner.ts` - Team tool injection

### Arquivos Analisados no MindFlow

- `python/mindflow_backend/agents/tools/__init__.py` - Tool registry
- `python/mindflow_backend/agents/tools/base/tool_registry.py` - Core registry
- `python/mindflow_backend/schemas/tools/registry.py` - Lazy registration
- `python/mindflow_backend/agents/_base.py` - Base agent definition
- `python/mindflow_backend/agents/specialists/runtime_policy.py` - Agent policies

### Documentação

- [Claude Code Docs](https://code.claude.com/docs/en/claude_code_docs_map.md)
- [Anthropic API - Tool Use](https://docs.anthropic.com/en/docs/tool-use)

---

## 9. PRÓXIMOS PASSOS

1. **Revisar este documento** com o time
2. **Decidir formato** (XML vs Markdown)
3. **Priorizar fase** (começar pela Fase 1)
4. **Criar branch** para implementação
5. **Implementar e testar**

---

*Documento gerado por análise automatizada com SocratiCode MCP*
*Última atualização: 2026-01-04*
