# Planejamento Detalhado: FASE 3 - Integrar DelegationEngine no QueryEngine

## Objetivo
Mover funcionalidades do DelegationEngine para dentro do QueryEngine, mantendo compatibilidade com as 14 dependências existentes.

## Análise de Responsabilidades

### QueryEngine (Atual)
- Context building de múltiplos providers (Git, File, Memory, MCP)
- Token budget enforcement
- File caching via SessionFileCache
- Auto-compact service para context compaction
- Permission system integration

### DelegationEngine (Atual)
- Execução de tarefas delegadas a agentes especializados
- Workspace isolation via WorkTreeService
- CommunicationBus para P2P agent communication
- MissionLauncher integration (Phase 2B)
- Fallback management para resiliência
- Memory-grounded optimization (RAG from agent history)
- A2A external calls
- Tool execution strategies (callable vs legacy)

## Estratégia Proposta

### Opção A: Composição (Recomendada)
Manter QueryEngine e DelegationEngine como classes separadas, mas fazer QueryEngine usar DelegationEngine internamente.

**Vantagens:**
- Menor risco de breaking changes
- Separação de responsabilidades clara
- DelegationEngine continua funcionando para dependências existentes
- Migração incremental possível

**Implementação:**
```python
class QueryEngine:
    def __init__(self, ..., delegation_engine: DelegationEngine | None = None):
        # ... existing code ...
        self._delegation_engine = delegation_engine or get_delegation_engine()
    
    async def delegate_task(self, task: DelegationTask, ...) -> DelegationResult:
        """Delegate method that forwards to internal DelegationEngine."""
        return await self._delegation_engine.delegate_task(task, ...)
```

### Opção B: Fusão Completa
Mover toda lógica do DelegationEngine para dentro do QueryEngine.

**Vantagens:**
- Uma única classe
- Menos overhead de composição

**Desvantagens:**
- Alto risco de breaking changes
- QueryEngine fica muito grande e complexo
- 14 dependências precisam ser atualizadas
- Difícil de testar

## Recomendação: Opção A (Composição)

## Plano de Implementação (Opção A)

### Passo 1: Adicionar DelegationEngine como parâmetro opcional no QueryEngine
- Modificar QueryEngine.__init__() para aceitar delegation_engine opcional
- Se não fornecido, usar get_delegation_engine()
- Manter compatibilidade com código existente

### Passo 2: Adicionar método delegate_task() no QueryEngine
- Método wrapper que chama self._delegation_engine.delegate_task()
- Mantém mesma assinatura para compatibilidade

### Passo 3: Adicionar método execute_workflow_step() no QueryEngine
- Integrar lógica de conversão WorkflowStep → DelegationTask
- Chamar delegate_task() internamente
- Converter DelegationResult → formato esperado por step_runner

### Passo 4: Atualizar QueryEngine para usar StreamingToolExecutor
- Adicionar parâmetro para tool_definitions
- Integrar com execution.loops para tool execution
- Manter compatibilidade com providers existentes

### Passo 5: Atualizar dependências gradualmente
- Não remover DelegationEngine ainda
- Permitir que dependências continuem usando DelegationEngine diretamente
- QueryEngine age como facade adicional

## Arquivos a Modificar

1. `query/engine.py` - Adicionar composição com DelegationEngine
2. `query/__init__.py` - Exportar novos métodos
3. `orchestrator/delegation/engine.py` - Manter por enquanto (não remover)
4. `orchestrator/delegation/__init__.py` - Manter por enquanto

## Arquivos a Criar

1. `query/workflow_integration.py` - Lógica de WorkflowStep → DelegationTask
2. `query/tool_integration.py` - Integração com StreamingToolExecutor

## Riscos e Mitigações

### Risco: Circular imports
- **Mitigação:** Usar TYPE_CHECKING para imports opcionais
- **Mitigação:** Lazy imports dentro de métodos

### Risco: Breaking changes em dependências
- **Mitigação:** Não remover DelegationEngine nesta fase
- **Mitigação:** Manter assinaturas compatíveis
- **Mitigação:** Testes abrangentes antes de mudanças

### Risco: QueryEngine fica muito complexo
- **Mitigação:** Usar composição em vez de fusão
- **Mitigação:** Extrair lógica para módulos separados (workflow_integration, tool_integration)

## Critérios de Sucesso

1. QueryEngine pode delegar tarefas via delegate_task()
2. QueryEngine pode executar workflow steps via execute_workflow_step()
3. Dependências existentes continuam funcionando
4. Sem circular imports
5. Testes passam

## Próximos Passos

1. Confirmar estratégia de composição (Opção A)
2. Implementar Passo 1 (adicionar DelegationEngine como parâmetro)
3. Implementar Passo 2 (adicionar delegate_task wrapper)
4. Implementar Passo 3 (adicionar execute_workflow_step)
5. Testar integração
6. Implementar Passo 4 (integrar StreamingToolExecutor)
7. Testes finais
