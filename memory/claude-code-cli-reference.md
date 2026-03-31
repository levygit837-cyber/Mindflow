# Claude Code CLI - Referência da Codebase (src/)

## Visão Geral
O `src/` contém toda a implementação da CLI do Claude Code, organizada em uma arquitetura modular e extensível.

---

## Estrutura de Diretórios

```
src/
├── .claude/           # Configuração do agente
├── QueryEngine.ts     # Motor de queries/conversas
├── Task.ts            # Sistema de tarefas/processamento
├── Tool.ts            # Sistema de ferramentas
├── assistant/         # Modo assistente
├── bootstrap/         # Inicialização
├── bridge/            # Bridge remota
├── buddy/             # Modo buddy
├── cli/               # Interface CLI
├── commands/          # Comandos slash
├── commands.ts        # Registry de comandos
├── components/        # Componentes UI
├── constants/         # Constantes
├── context/           # Gerenciamento de contexto
├── context.ts         # Gerador de contexto
├── coordinator/       # Modo coordenador
├── cost-tracker.ts    # Rastreamento de custos
├── costHook.ts        # Hook de custo
├── dialogLaunchers.tsx# Launchers de dialogs
├── entrypoints/       # Pontos de entrada
├── history.ts         # Histórico de prompts
├── hooks/             # Hooks React
├── ink/               # Framework Ink (TUI)
├── ink.ts             # Ink wrapper
├── interactiveHelpers.tsx # Helpers interativos
├── keybindings/       # Keybindings
├── main.tsx           # Entry point principal
├── memdir/            # Memória/CLAUDE.md
├── migrations/        # Migrações de configuração
├── moreright/         # Modo more-right
├── native-ts/         # TS nativo
├── outputStyles/      # Estilos de output
├── plugins/           # Sistema de plugins
├── projectOnboardingState.ts # Estado de onboarding
├── query/             # Motor de query
├── query.ts           # Implementação de query
├── remote/            # Sessões remotas
├── replLauncher.tsx   # Launcher do REPL
├── schemas/           # Schemas de tipos
├── screens/           # Telas da UI
├── server/            # Servidor
├── services/          # Serviços
├── setup.ts           # Setup inicial
├── skills/            # Sistema de skills
├── state/             # Gerenciamento de estado
├── tasks/             # Tasks síncronas
├── tasks.ts           # Registry de tasks
├── tools/             # Ferramentas
├── tools.ts           # Registry de ferramentas
├── types/             # Definições de tipos
├── upstreamproxy/     # Proxy upstream
├── utils/             # Utilitários
├── vim/               # Modo vim
└── voice/             # Modo voz
```

---

## Componentes Principais

### 1. **QueryEngine.ts** - Motor de Conversa
- Gerencia o ciclo de vida de conversas
- `submitMessage()` processa mensagens do usuário
- Persiste sessões, rastreia uso de tokens
- Integra com MCP, skills, plugins

### 2. **Task.ts** - Sistema de Tarefas
- Tipos: `local_bash`, `local_agent`, `remote_agent`, `in_process_teammate`, `local_workflow`, `monitor_mcp`, `dream`
- Gerados IDs únicos com prefixos (`b`, `a`, `r`, `t`, `w`, `m`, `d`)
- Estados: `pending`, `running`, `completed`, `failed`, `killed`

### 3. **Tool.ts** - Sistema de Ferramentas
- Interface `Tool` com métodos:
  - `call()`: Executa a ferramenta
  - `description()`: Retorna descrição
  - `checkPermissions()`: Verifica permissões
  - `isReadOnly()`: Verifica se é leitura
  - `renderToolUseMessage()`: Renderiza uso
  - `mapToolResultToToolResultBlockParam()`: Converte resultado
- `buildTool()`: Factory para criar tools com defaults
- Suporte a aliases, searchHint, shouldDefer

### 4. **commands.ts** - Sistema de Comandos
- Comandos: `help`, `memory`, `clear`, `compact`, `config`, `init`, `login`, `logout`, `mcp`, `plugin`, `resume`, `review`, `session`, `status`, `theme`, `vim`, etc.
- Carregamento assíncrono de comandos
- Skills de diretório e plugins

### 5. **context.ts** - Gerador de Contexto
- `getSystemContext()`: Git status, injeção de prompt
- `getUserContext()`: CLAUDE.md, data atual
- Cache de resultado

### 6. **cost-tracker.ts** - Rastreamento de Custos
- `addToTotalSessionCost()`: Soma custos
- `formatTotalCost()`: Formata exibição
- `saveCurrentSessionCosts()`: Persiste custos
- Uso por modelo

---

## Arquitetura

### Fluxo Principal (main.tsx)
1. Parse de flags CLI
2. Inicialização de logging/telemetria
3. Configuração de tools/MCP
4. Setup de sessão (worktree, tmux, etc.)
5. Launch do REPL ou print mode
6. Processamento de queries

### Estado (AppState)
- Configuração de ferramentas
- Permissões
- MCP clients/tools
- Fast mode
- Múltiplos agentes
- Modo assistente

### Injeção de Dependências
- `QueryDeps` para injeção de funções
- `ToolUseContext` para contexto de uso
- `CanUseToolFn` para verificação de permissões

---

## Padrões de Design

### 1. Factory Pattern
```typescript
buildTool({
  name: 'toolName',
  inputSchema: z.object({}),
  call: async (args, context) => {},
})
```

### 2. Command Pattern
```typescript
{
  type: 'prompt',
  name: 'commandName',
  description: 'Description',
  async getPromptForCommand(args, context) { return 'prompt' },
}
```

### 3. Feature Flags
```typescript
feature('FEATURE_NAME') ? require('./feature.js') : null
```

### 4. Streaming/Async
```typescript
async function* query(): AsyncGenerator<Message, Terminal> {
  for await (const message of queryInner()) {
    yield message
  }
}
```

### 5. Guards/Validation
```typescript
if (!toolMatchesName(tool, name)) return null
```

---

## Ferramentas Implementadas (src/tools/)

| Ferramenta | Tipo | Descrição |
|-----------|------|-----------|
| AgentTool | Multi-agente | Subagentes, forking |
| BashTool | Sistema | Execução de comandos |
| FileReadTool | FS | Leitura de arquivos |
| FileEditTool | FS | Edição de arquivos |
| FileWriteTool | FS | Escrita de arquivos |
| GlobTool | FS | Busca de arquivos |
| GrepTool | FS | Busca de conteúdo |
| NotebookEditTool | FS | Edição notebooks |
| WebFetchTool | Web | Fetch de URLs |
| WebSearchTool | Web | Busca na web |
| TodoWriteTool | Tarefa | Gerencia TODOs |
| TaskStopTool | Tarefa | Para tasks |
| SkillTool | Sistema | Invoca skills |
| BriefTool | Comunicação | Envia para usuário |
| PushNotificationTool | Comunicação | Notificações |
| MCP tools | Sistema | Ferramentas MCP |
| ToolSearchTool | Sistema | Busca de tools |

---

## Serviços Importantes

### Serviços de API
- `claude.ts`: Chamadas à API do Claude
- `errors.ts`: Tratamento de erros
- `bootstrap.ts`: Dados iniciais

### Serviços de Compactação
- `autoCompact.ts`: Compactação automática
- `compact.ts`: Compactação manual
- `snipCompact.ts`: Compactação por snip

### Serviços de Contexto
- `contextCollapse.ts`: Collapse de contexto
- `attachments.ts`: Anexos de contexto

### Serviços de Plugins
- `pluginLoader.ts`: Carregamento de plugins
- `loadPluginCommands.ts`: Comandos de plugins
- `installedPluginsManager.ts`: Gerenciamento

### Serviços de MCP
- `client.ts`: Cliente MCP
- `config.ts`: Configuração MCP
- `types.ts`: Tipos MCP

---

## Hooks & Lifecycle

### Hooks de Query
- `queryStart`: Início de query
- `stopHook`: Após resposta
- `preToolUse`: Antes de tool
- `postToolUse`: Depois de tool
- `sessionStart`: Início de sessão

### Hooks de Sessão
- `setup`: Setup inicial
- `compact`: Compactação
- `clearSession`: Limpeza

---

## Configuração (bootstrap/state.ts)

### Session State
- `sessionId`: ID da sessão
- `cwd`: Diretório de trabalho
- `model`: Modelo LLM
- `permissionMode`: Modo de permissão
- `fastMode`: Modo rápido

### Cost State
- `totalCostUSD`: Custo total
- `totalAPIDuration`: Duração API
- `modelUsage`: Uso por modelo

---

## Referências para MindFlow

### Arquitetura Similar
1. **Sistema de ferramentas** - Interface consistente
2. **Sistema de comandos** - Extensível via plugins/skills
3. **QueryEngine** - Motor de conversa
4. **MCP** - Protocolo padronizado
5. **Estado global** - AppState singleton

### Padrões a Adotar
- **Factory Pattern** para criar componentes
- **Feature Flags** para funcionalidades
- **Feature Gating** para dead code elimination
- **Streaming** para respostas longas
- **MCP** para extensibilidade
- **Zod** para validação de schemas

### Integração com MindFlow
```python
# Exemplo de Tool no MindFlow (similar a Tool.ts)
class MindFlowTool(BaseTool):
    """Ferramenta do MindFlow"""
    
    name: str
    description: str
    input_schema: dict
    
    async def call(self, args: dict, context: ToolUseContext) -> ToolResult:
        raise NotImplementedError
    
    def check_permissions(self, input: dict, context: ToolUseContext) -> PermissionResult:
        raise NotImplementedError
    
    @classmethod
    def build(cls, **kwargs) -> 'MindFlowTool':
        """Factory para criar ferramenta com defaults"""
        defaults = {
            'is_enabled': lambda: True,
            'is_read_only': lambda input: False,
            'is_concurrency_safe': lambda input: False,
        }
        return cls(**{**defaults, **kwargs})
```

### Sugestões de Implementação
1. **MindFlowTool**: Interface similar a Tool.ts
2. **MindFlowCommand**: Sistema de comandos similar
3. **MindFlowQuery**: Engine de queries similar
4. **MindFlowContext**: Gerenciador de contexto
5. **MindFlowState**: Estado global singleton
6. **MindFlowMCP**: Servidor/cliente MCP

---

## Última Atualização
31/03/2026

## Referência
Claude Code CLI v2.0 - Fonte: src/ do repositório Anthropic