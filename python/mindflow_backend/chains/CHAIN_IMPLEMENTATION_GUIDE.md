# Guia de Implementação de Chains - MindFlow

## Visão Geral

Este guia descreve como implementar novas chains no sistema MindFlow de forma eficaz e alinhada com a arquitetura existente.

## Arquitetura de Chains

O sistema possui três camadas principais:

1. **BaseChain** - Classe abstrata com estrutura fundamental
2. **Templates** - Implementações concretas para padrões específicos
3. **Catalog** - Registro e factory para chains disponíveis

## Tipos de Chains Suportados

### 1. SequentialChain
- **Uso**: Workflows lineares simples
- **Exemplo**: Analysis → Implementation → Review
- **Quando usar**: Tarefas com ordem fixa e sem ramificações

### 2. ConditionalChain  
- **Uso**: Workflows com branching baseado em condições
- **Exemplo**: Analysis → [Simple|Complex] Path → Synthesis
- **Quando usar**: Tarefas que requerem diferentes abordagens

### 3. ParallelChain
- **Uso**: Execução simultânea de tarefas independentes
- **Exemplo**: [Research + Analysis + Testing] → Integration
- **Quando usar**: Tarefas que podem ser divididas e executadas em paralelo

### 4. AdaptiveChain
- **Uso**: Workflows que se adaptam durante execução
- **Exemplo**: Dynamic step selection based on intermediate results
- **Quando usar**: Tarefas complexas com requisitos variáveis

## Padrões de Implementação

### Padrão 1: Chain Simples (Function-based)

```python
class SimpleTaskChain:
    def __init__(self, config: SimpleTaskConfig):
        self.config = config
        
    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        # Lógica direta sem herança
        step1_result = await self._step1(context)
        step2_result = await self._step2(step1_result)
        return {"response": step2_result, "error": None}
```

**Vantagens:**
- Simples de implementar
- Flexível para casos específicos
- Baixo overhead

**Quando usar:**
- Workflows simples e lineares
- Protótipos rápidos
- Tarefas específicas sem reuso

### Padrão 2: BaseChain Inheritance

```python
class ComplexWorkflowChain(BaseChain):
    @property
    def chain_type(self) -> ChainType:
        return ChainType.CONDITIONAL
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        # Usa infraestrutura completa do BaseChain
        return await super().execute(context)
```

**Vantagens:**
- Acesso completo a métricas e validação
- Suporte para dependências complexas
- Integração nativa com o sistema

**Quando usar:**
- Workflows complexos com múltiplos passos
- Necessidade de validação e métricas
- Reuso de componentes

### Padrão 3: Template Method

```python
class AnalysisTemplate:
    def __init__(self, config: AnalysisConfig):
        self.config = config
    
    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        # Template fixo com implementações variáveis
        context_result = await self.analyze_context(context)
        deep_result = await self.deep_dive(context_result)
        synthesis = await self.synthesize(context_result, deep_result)
        return self.format_response(synthesis)
```

**Vantagens:**
- Estrutura consistente
- Fácil de estender
- Comportamento padronizado

**Quando usar:**
- Padrões repetitivos com pequenas variações
- Famílias de workflows similares
- Necessidade de consistência

## Melhores Práticas

### 1. Estrutura de Arquivos

```
mindflow_backend/chains/templates/
├── [nome]_chain.py          # Implementação principal
├── [nome]_config.py         # Configurações (se complexo)
└── [nome]_tests.py          # Testes específicos

mindflow_backend/chains/catalog.py     # Registro da chain
```

### 2. Nomenclatura

- **Arquivos**: `[pattern]_chain.py`
- **Classes**: `[Pattern]Chain`
- **Config**: `[Pattern]ChainConfig`
- **Chain ID**: `[pattern]_task` ou `[pattern]_workflow`

### 3. Configuração

```python
@dataclass(frozen=True, slots=True)
class ChainConfig:
    chain_id: str = "default_chain"
    # Parâmetros específicos
    max_context_chars: int = 8_000
    enable_feature: bool = True
    # Limites e thresholds
    timeout: float = 30.0
    retry_attempts: int = 3
```

### 4. Tratamento de Erros

```python
async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
    try:
        # Lógica principal
        result = await self._execute_workflow(context)
        return {"response": result, "error": None}
    except SpecificException as e:
        _logger.error("chain_specific_error", error=str(e))
        return {"response": "", "error": f"Specific error: {e}"}
    except Exception as e:
        _logger.error("chain_unexpected_error", error=str(e))
        return {"response": "", "error": f"Unexpected error: {e}"}
```

### 5. Logging e Métricas

```python
_logger = get_logger(__name__)

async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
    start_time = time.time()
    _logger.info("chain_started", chain_id=self.config.chain_id)
    
    try:
        result = await self._execute_workflow(context)
        execution_time = time.time() - start_time
        _logger.info("chain_completed", 
                    chain_id=self.config.chain_id,
                    execution_time=execution_time)
        return result
    except Exception as e:
        execution_time = time.time() - start_time
        _logger.error("chain_failed",
                     chain_id=self.config.chain_id,
                     execution_time=execution_time,
                     error=str(e))
        raise
```

### 6. Validação

```python
def validate(self) -> List[str]:
    """Valida a estrutura e configuração da chain."""
    issues = []
    
    # Validações básicas
    if not self.config.chain_id:
        issues.append("Chain ID is required")
    
    # Validações específicas
    if self.config.max_context_chars < 1000:
        issues.append("max_context_chars should be at least 1000")
    
    return issues
```

## Integração com Orchestrator

### 1. Registro no Catalog

```python
# chains/catalog.py
CHAIN_CATALOG: dict[str, ChainFactory] = {
    "my_chain": _my_chain_factory,
}

def _my_chain_factory() -> MyChain:
    return MyChain(MyChainConfig(chain_id="my_chain"))
```

### 2. Uso no Router

O Orchestrator pode selecionar chains através do `ExecutionStrategy.CHAIN`:

```python
# No intelligent_router.py
if complexity_score > 0.8:
    decision.execution_strategy = ExecutionStrategy.CHAIN
    decision.chain_id = "complex_workflow"
```

### 3. Contexto de Execução

As chains recebem contexto padronizado:

```python
context = {
    "message": "User request",
    "session_id": "session_uuid",
    "provider": "openai",
    "model": "gpt-4",
    "memory_context": "RAG context",
    "decision": {...}  # Decisão do orchestrator
}
```

## Exemplos de Implementação

### 1. Chain de Pesquisa

```python
class ResearchChain:
    """Context gathering → Deep research → Synthesis"""
    
    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        # Step 1: Context analysis
        context_result = await self._analyze_context(context)
        
        # Step 2: Deep research
        research_result = await self._deep_research(context, context_result)
        
        # Step 3: Synthesis
        synthesis = await self._synthesize(context_result, research_result)
        
        return {"response": synthesis, "error": None}
```

### 2. Chain de Desenvolvimento

```python
class DevelopmentChain(BaseChain):
    """Analysis → Implementation → Testing → Review"""
    
    def _setup_steps(self):
        self.add_step(ChainStep(
            step_id="analysis",
            step_type=StepType.AGENT_EXECUTION,
            agent=AgentType.ANALYST,
            task="Analyze requirements"
        ))
        self.add_step(ChainStep(
            step_id="implementation",
            step_type=StepType.AGENT_EXECUTION,
            agent=AgentType.CODER,
            task="Implement solution",
            depends_on=["analysis"]
        ))
        # ... mais steps
```

### 3. Chain Adaptativa

```python
class AdaptiveChain(BaseChain):
    """Dynamic workflow based on intermediate results"""
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        # Initial analysis
        analysis = await self._analyze(context)
        
        # Dynamic step selection
        if analysis["complexity"] > 0.7:
            return await self._complex_workflow(context, analysis)
        else:
            return await self._simple_workflow(context, analysis)
```

## Testes

### 1. Testes Unitários

```python
async def test_analysis_chain_execution():
    chain = AnalysisChain(AnalysisChainConfig())
    context = {"message": "Test request", "session_id": "test"}
    
    result = await chain.execute(context)
    
    assert result["error"] is None
    assert "response" in result
    assert len(result["response"]) > 0
```

### 2. Testes de Integração

```python
async def test_chain_with_orchestrator():
    from mindflow_backend.chains.catalog import get_chain
    
    chain = get_chain("analysis_task")
    context = {
        "message": "Complex request",
        "session_id": "integration_test",
        "provider": "openai",
        "model": "gpt-4"
    }
    
    result = await chain.execute(context)
    assert result["error"] is None
```

## Performance e Otimização

### 1. Limites de Contexto

```python
# Trunque contextos grandes para evitar overflow de tokens
def _limit_context(self, text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "... [truncated]"
```

### 2. Execução Paralela

```python
# Use asyncio.gather para tasks independentes
async def _execute_parallel_tasks(self, tasks: List[Coroutine]) -> List[Any]:
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r for r in results if not isinstance(r, Exception)]
```

### 3. Cache de Resultados

```python
# Cache resultados caros
@lru_cache(maxsize=128)
def _get_cached_analysis(self, query_hash: str) -> str:
    # Análise custosa
    pass
```

## Monitoramento e Debugging

### 1. Métricas Automáticas

```python
# BaseChain fornece métricas automaticamente
metrics = chain.get_metrics()
print(f"Execution time: {metrics.total_execution_time}")
print(f"Steps completed: {metrics.completed_steps}")
```

### 2. Step Logging

```python
# Enable step logging na configuração
config = ChainConfig(
    enable_step_logging=True,
    enable_metrics=True
)
```

### 3. Debug Mode

```python
# Adicione verbose logging para debugging
if self.config.debug_mode:
    _logger.setLevel(logging.DEBUG)
    _logger.debug("chain_context", context=context)
```

## Conclusão

Seguindo estes padrões e melhores práticas, você pode implementar chains que são:

- **Confiáveis**: Tratamento robusto de erros
- **Escaláveis**: Performance otimizada
- **Maintaináveis**: Código limpo e documentado
- **Integradas**: Compatibilidade total com o ecossistema MindFlow

O sistema foi projetado para ser extensível, permitindo adicionar novos padrões e tipos de chains conforme necessário.
