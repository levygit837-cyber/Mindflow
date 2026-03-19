# Guia de Uso: Agentes com Iterações Ilimitadas

## 🚀 O Que Mudou

### Limites Removidos

**Antes:**
- Orchestrator: 50 iterações
- Analyst: 25 iterações
- Analyst (deep_iteration): 15 iterações
- Coder: 30 iterações
- Researcher: 20 iterações
- Deep Work max_depth: 10 turnos

**Agora:**
- Orchestrator: **1000 iterações** (praticamente ilimitado)
- Analyst: **500 iterações** (praticamente ilimitado)
- Analyst (deep_iteration): **1000 iterações** (praticamente ilimitado)
- Coder: **1000 iterações** (praticamente ilimitado)
- Researcher: **500 iterações** (praticamente ilimitado)
- Todos os specialists: **500 iterações**
- Deep Work max_depth: **1000 turnos**

## 📋 Como Funciona

### 1. Sistema de Iterações

Cada agente agora pode executar até **500-1000 iterações** de ferramentas antes de retornar uma resposta. Isso significa:

- **Analyst** pode ler centenas de arquivos, fazer grep em todo o codebase múltiplas vezes
- **Coder** pode implementar features complexas com dezenas de arquivos
- **Researcher** pode fazer pesquisas profundas com múltiplas buscas e validações
- **Orchestrator** pode coordenar investigações longas com múltiplas delegações

### 2. Protocolo Deep Work

O módulo `orchestrator/deep_work.py` detecta quando um agente quer continuar investigando:

**Marcadores de Continuação (Português):**
- "preciso investigar mais"
- "vou continuar"
- "deixe-me explorar"

**Marcadores de Continuação (Inglês):**
- "continue investigating"
- "need to explore further"
- "requires deeper analysis"
- "let me investigate"
- "I should check"

Quando detectado, o sistema:
1. Captura o contexto da investigação anterior
2. Constrói um novo prompt com histórico
3. Reinicia o agente com contexto acumulado
4. Repete até 1000 turnos ou conclusão

### 3. Memory Grounding

O sistema **não limita mais** iterações quando há contexto de memória. Antes, `memory_grounded=True` forçava apenas 2 iterações. Agora usa o limite completo do agente.

## 🎯 Como Usar

### Modo 1: Investigação Profunda Direta

```bash
# Via CLI
.venv/bin/mindflow-cli chat --orchestrate -m "Faça uma análise profunda e exaustiva do sistema de memória do MindFlow. Investigue todos os arquivos relacionados, trace todas as dependências, analise a arquitetura completa."
```

**O que acontece:**
1. Orchestrator delega para `analyst:deep_iteration`
2. Analyst usa até 1000 iterações para investigar
3. Lê dezenas/centenas de arquivos
4. Faz múltiplas análises cruzadas
5. Retorna análise completa

### Modo 2: Implementação Complexa

```bash
.venv/bin/mindflow-cli chat --orchestrate -m "Implemente um sistema completo de cache distribuído com Redis, incluindo invalidação, TTL configurável, e fallback para memória local. Crie todos os arquivos necessários, testes unitários e documentação."
```

**O que acontece:**
1. Orchestrator delega para `coder`
2. Coder usa até 1000 iterações
3. Cria múltiplos arquivos
4. Executa testes
5. Refina implementação baseado em erros
6. Documenta tudo

### Modo 3: Pesquisa Exaustiva

```bash
.venv/bin/mindflow-cli chat --orchestrate -m "Pesquise as melhores práticas de 2026 para implementar sistemas de agentes LLM em produção. Compare frameworks, analise trade-offs, valide com múltiplas fontes."
```

**O que acontece:**
1. Orchestrator delega para `researcher`
2. Researcher usa até 500 iterações
3. Faz múltiplas buscas web
4. Valida informações cruzadas
5. Compara fontes
6. Retorna análise consolidada

### Modo 4: Sessão Interativa Longa

```python
# Via API
import requests

response = requests.post(
    "http://localhost:8000/v1/agent/chat/stream",
    json={
        "message": "Vamos fazer uma investigação profunda. Primeiro analise a arquitetura do orchestrator, depois trace como as delegações funcionam, depois analise o sistema de memória, e finalmente proponha melhorias.",
        "session_id": "deep-session-001",
        "orchestrate": True,
        "provider": "vertexai",
        "model": "gemini-3.1-flash-lite-preview"
    },
    stream=True
)

for line in response.iter_lines():
    if line:
        print(line.decode('utf-8'))
```

**O que acontece:**
1. Orchestrator processa a solicitação complexa
2. Delega para múltiplos agentes sequencialmente
3. Cada agente usa seu limite completo de iterações
4. Contexto acumula entre delegações
5. Sessão pode durar minutos/horas

## 🔍 Monitoramento

### Logs de Iteração

Os logs mostram o progresso das iterações:

```
[INFO] agent_tool_call iteration=1/1000 tool=read_file
[INFO] agent_tool_call iteration=2/1000 tool=grep_search
[INFO] agent_tool_call iteration=3/1000 tool=read_file
...
[INFO] agent_tool_call iteration=247/1000 tool=read_file
[INFO] agent_completed total_iterations=247 status=success
```

### Verificar Limites Atuais

```bash
cd /home/levybonito/Projetos/MindFlow/python
.venv/bin/python3 test_deep_work.py
```

Saída esperada:
```
✅ orchestrator: 1000 iterations
✅ analyst: 500 iterations
✅ analyst:deep_iteration: 1000 iterations
✅ coder: 1000 iterations
✅ researcher: 500 iterations
✅ Deep work module: All tests passed
```

## ⚠️ Considerações Importantes

### 1. Custo de API

Com limites ilimitados, uma única sessão pode:
- Fazer centenas de chamadas LLM
- Processar milhares de tokens
- Custar significativamente mais

**Recomendação:** Monitore custos via dashboard do Vertex AI.

### 2. Tempo de Execução

Sessões longas podem levar:
- Análises profundas: 5-30 minutos
- Implementações complexas: 10-60 minutos
- Pesquisas exaustivas: 5-20 minutos

**Recomendação:** Use modo streaming para acompanhar progresso.

### 3. Qualidade vs Quantidade

Mais iterações ≠ sempre melhor. O agente deve:
- Ter objetivo claro
- Saber quando parar
- Evitar loops infinitos

**Recomendação:** Seja específico nas instruções.

### 4. Interrupção Manual

Se um agente entrar em loop:

```bash
# Encontre o processo
ps aux | grep uvicorn

# Mate o processo
kill -9 <PID>

# Reinicie o backend
/home/levybonito/Projetos/MindFlow/python/.venv/bin/python3 -m uvicorn mindflow_backend.main:app --host 0.0.0.0 --port 8000 > /tmp/backend.log 2>&1 &
```

## 🧪 Testes Recomendados

### Teste 1: Análise Profunda

```bash
.venv/bin/mindflow-cli chat --orchestrate -m "Analise TODO o sistema de orchestração do MindFlow. Leia todos os arquivos relacionados, trace todas as dependências, documente a arquitetura completa."
```

**Expectativa:** 100-300 iterações, 5-15 minutos

### Teste 2: Implementação Grande

```bash
.venv/bin/mindflow-cli chat --orchestrate -m "Implemente um sistema completo de logging estruturado com níveis configuráveis, rotação de arquivos, e integração com Sentry. Inclua testes."
```

**Expectativa:** 200-500 iterações, 10-30 minutos

### Teste 3: Pesquisa Cruzada

```bash
.venv/bin/mindflow-cli chat --orchestrate -m "Pesquise e compare os 5 principais frameworks de agentes LLM de 2026. Para cada um, valide informações em múltiplas fontes e crie tabela comparativa."
```

**Expectativa:** 50-150 iterações, 5-10 minutos

## 📊 Arquivos Modificados

```
python/mindflow_backend/agents/specialists/runtime_policy.py
  - Todos os max_iterations aumentados para 500-1000

python/mindflow_backend/orchestrator/deep_work.py
  - max_depth aumentado de 10 para 1000

python/mindflow_backend/orchestrator/step_runner.py
  - Removida limitação de 2 iterações com memory_grounded
```

## 🚦 Status

✅ **Limites removidos** - Todos os agentes com 500-1000 iterações
✅ **Memory grounding corrigido** - Usa limite completo
✅ **Deep work protocol** - Suporta até 1000 turnos de continuação
✅ **Validação** - Todos os testes passando

## 🔄 Próximos Passos (Opcional)

Se quiser ainda mais controle:

1. **Checkpoint/Resume**: Salvar estado de investigações longas
2. **Progress Callbacks**: Notificações a cada N iterações
3. **Budget Control**: Limites de custo por sessão
4. **Auto-stop Heuristics**: Detectar quando agente está em loop

---

**Última atualização:** 2026-03-18
**Versão:** 2.0 (Unlimited)
