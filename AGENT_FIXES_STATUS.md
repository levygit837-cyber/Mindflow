# Status das Correções - Agentes MindFlow

**Data:** 2026-03-19
**Objetivo:** Fazer agentes realizarem sessões longas de trabalho com uso de ferramentas

---

## ✅ Correções Aplicadas

### 1. Limites de Iteração Removidos
**Arquivo:** `python/mindflow_backend/agents/specialists/runtime_policy.py`

| Agente | Antes | Depois | Aumento |
|--------|-------|--------|---------|
| Orchestrator | 50 | 1000 | 20x |
| Analyst | 25 | 500 | 20x |
| Analyst (deep_iteration) | 15 | 1000 | 66x |
| Coder | 30 | 1000 | 33x |
| Researcher | 20 | 500 | 25x |
| Todos os specialists | 1-10 | 500 | 50-500x |

### 2. Deep Work Loop Integrado
**Arquivo:** `python/mindflow_backend/nodes/implementations/orchestrator/execute_node.py`

```python
# Deep Work Loop no ExecuteNode
while current_depth < max_depth:
    bridge_result = await agent_bridge.execute(agent_context)

    should_continue, reason = should_continue_investigation(response, current_depth)

    if not should_continue:
        break

    current_message = build_continuation_context(...)
    current_depth += 1
```

**Métricas adicionadas:**
- `deep_work_sessions` - Contador de sessões deep work
- `max_depth_reached` - Profundidade máxima alcançada

### 3. Roteamento Inteligente Ativado
**Arquivo:** `python/mindflow_backend/nodes/implementations/orchestrator/route_node.py`

**Antes:**
```python
# Hardcoded - sempre DIRECT_RESPONSE
decision = OrchestratorDecision(
    agent=AgentType.ORCHESTRATOR,
    execution_strategy=ExecutionStrategy.DIRECT_RESPONSE,
)
```

**Depois:**
```python
# Usa IntelligentRouter com análise LLM
router = get_intelligent_router()
decision = await router.route_message_intelligently(
    message=state["message"],
    folder_path=folder_path,
)
```

### 4. AgentBridge com Execução Real
**Arquivo:** `python/mindflow_backend/nodes/implementations/integration/agent_bridge.py`

**Antes:**
```python
# Stub - não executava LLM nem ferramentas
response_content = f"[{agent.agent_type.value}] Processing: {message}"
```

**Depois:**
```python
# Execução real com LLM e ferramentas
llm = get_model_for_provider(provider, model)
lc_tools = to_langchain_tools(tools)
llm_with_tools = llm.bind_tools(lc_tools)

response_text = await invoke_with_tools(
    llm=llm_with_tools,
    messages=messages,
    lc_tools=lc_tools,
    max_iterations=policy.max_iterations,  # 500-1000
)
```

### 5. CLI Configurado
**Arquivo:** `~/.mindflow/settings.json`

```json
{
  "auto_orchestrate": true,
  "default_provider": "vertexai",
  "default_model": "gemini-3.1-flash-lite-preview"
}
```

---

## ⚠️ Problema Atual

### Sintoma
Agentes **não estão usando ferramentas** mesmo com todas as correções aplicadas.

### Teste Realizado
```bash
.venv/bin/mindflow-cli chat -m "Leia o arquivo python/mindflow_backend/orchestrator/deep_work.py e me explique o que ele faz"
```

**Resultado:**
- Orchestrator responde diretamente sem ler o arquivo
- Nenhuma ferramenta é invocada
- Logs mostram: `POST /v1/agent/chat/stream` → LLM direto

### Fluxo Atual
```
CLI (orchestrate=true)
  ↓
AgentController.stream_chat()
  ↓
LocalAgentClient.stream_chat()
  ↓
AgentRuntime.stream_chat()
  ↓
_stream_chat_orchestrated()
  ↓
Orchestrator Graph (RouteNode → ExecuteNode → RespondNode)
  ↓
ExecuteNode usa AgentBridge
  ↓
AgentBridge.execute() ← PROBLEMA AQUI?
```

### Hipóteses

1. **AgentBridge não está sendo inicializado corretamente**
   - Sandbox pode estar falhando
   - Tools registry pode estar vazio
   - Erro silencioso na inicialização

2. **ExecuteNode não está usando AgentBridge**
   - Pode estar usando caminho alternativo
   - Pode estar falhando e usando fallback

3. **Ferramentas não estão sendo vinculadas ao LLM**
   - `to_langchain_tools()` pode estar retornando lista vazia
   - `bind_tools()` pode estar falhando silenciosamente

4. **Roteamento ainda não está funcionando**
   - IntelligentRouter pode estar falhando
   - Fallback para DIRECT_RESPONSE

---

## 🔍 Próximos Passos para Diagnóstico

### 1. Verificar Logs Detalhados
```bash
tail -500 /tmp/backend.log | grep -E "(route_node|agent_bridge|tool_call|iteration)"
```

### 2. Adicionar Logs de Debug
Adicionar logs em pontos críticos:
- `RouteNode.execute()` - verificar decisão de roteamento
- `ExecuteNode.execute()` - verificar se AgentBridge é chamado
- `AgentBridge.initialize()` - verificar se ferramentas são carregadas
- `AgentBridge._execute_agent_properly()` - verificar se LLM é chamado com ferramentas

### 3. Teste Direto do AgentBridge
Criar script de teste isolado:
```python
from mindflow_backend.nodes.implementations.integration.agent_bridge import AgentBridge

bridge = AgentBridge(agent_type="analyst", sandbox_mode=SandboxMode.READ_ONLY)
await bridge.initialize()

result = await bridge.execute({
    "message": "Leia o arquivo deep_work.py",
    "session_id": "test-123"
})

print(result)
```

### 4. Verificar Tools Registry
```python
from mindflow_backend.agents.tools import create_default_registry
from mindflow_backend.agents._registry import get_agent

registry = create_default_registry()
agent = get_agent("analyst")
tools = registry.get_tools_for_agent(agent)

print(f"Tools count: {len(tools)}")
for tool in tools:
    print(f"  - {tool.name}")
```

---

## 📋 Checklist de Validação

- [x] Limites de iteração aumentados (500-1000)
- [x] Deep Work Loop integrado no ExecuteNode
- [x] RouteNode usando IntelligentRouter
- [x] AgentBridge com execução real de LLM
- [x] CLI configurado com auto_orchestrate=true
- [ ] Ferramentas sendo vinculadas ao LLM
- [ ] Ferramentas sendo invocadas durante execução
- [ ] Iterações múltiplas acontecendo
- [ ] Deep Work Loop sendo ativado

---

## 🎯 Objetivo Final

**Comportamento esperado:**
```
User: "Leia o arquivo deep_work.py e explique"
  ↓
Orchestrator → Analyst
  ↓
Analyst usa read_file tool
  ↓
Analyst lê conteúdo do arquivo
  ↓
Analyst analisa e explica (100-300 iterações possíveis)
  ↓
Se precisar investigar mais: Deep Work Loop continua
  ↓
Resposta completa e detalhada
```

**Comportamento atual:**
```
User: "Leia o arquivo deep_work.py e explique"
  ↓
Orchestrator responde diretamente
  ↓
Nenhuma ferramenta usada
  ↓
Resposta genérica sem ler o arquivo
```

---

## 🔧 Arquivos Modificados

```
✅ python/mindflow_backend/agents/specialists/runtime_policy.py
✅ python/mindflow_backend/orchestrator/deep_work.py
✅ python/mindflow_backend/nodes/implementations/orchestrator/execute_node.py
✅ python/mindflow_backend/nodes/implementations/orchestrator/route_node.py
✅ python/mindflow_backend/nodes/implementations/integration/agent_bridge.py
✅ ~/.mindflow/settings.json
```

---

**Última atualização:** 2026-03-19 03:20 UTC
**Status:** Correções aplicadas, aguardando diagnóstico do problema de ferramentas
