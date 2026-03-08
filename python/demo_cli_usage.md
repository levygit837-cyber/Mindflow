# MindFlow CLI - Demonstração de Uso

## 🚀 Visão Geral

A CLI Chat do MindFlow agora está pronta para testar o fluxo completo de orquestrador e agentes! 

## 📋 Estrutura Implementada

### **Comandos Principais**

1. **`mindflow start`** - Inicia o aplicativo completo
2. **`mindflow test orchestrator`** - Testa fluxo de orquestração
3. **`mindflow test scenarios`** - Executa cenários predefinidos
4. **`mindflow test agents`** - Testa registry de agentes

### **Renderers Avançados**

- **OrchestratorStreamRenderer** - Visualização de decisões do orquestrador
- **ChatStreamRenderer** - Streaming rico com suporte a agentes
- **Painéis Rich** - Interface interativa com debugging

## 🛠️ Como Usar

### **1. Iniciar o Backend**

```bash
cd /home/levybonito/Projetos/MindFlow/python
source .venv/bin/activate
mindflow-api
```

### **2. Modo Interativo**

```bash
# Terminal 2
cd /home/levybonito/Projetos/MindFlow/python
source .venv/bin/activate
python -m mindflow_cli start --mode interactive --debug-orchestrator
```

**O que esperar:**
- Interface interativa com Rich console
- Painel de agentes disponíveis
- Input contínuo para mensagens
- Visualização de decisões do orquestrador

### **3. Testar Fluxo de Orquestrador**

```bash
# Teste simples
python -m mindflow_cli test orchestrator --message "Create a Python function"

# Teste com debug completo
python -m mindflow_cli test orchestrator \
  --message "Analyze this codebase for security vulnerabilities" \
  --show-routing \
  --show-agent-selection \
  --trace-execution

# Teste com provider específico
python -m mindflow_cli test orchestrator \
  --message "Design a REST API architecture" \
  --provider vertexai \
  --model gemini-3-flash \
  --debug-orchestrator
```

### **4. Cenários de Teste**

```bash
# Cenários básicos
python -m mindflow_cli test scenarios --scenario basic

# Cenários complexos
python -m mindflow_cli test scenarios --scenario complex

# Multi-agente
python -m mindflow_cli test scenarios --scenario multi-agent

# Com provider específico
python -m mindflow_cli test scenarios --scenario basic --provider openai
```

### **5. Testar Registry de Agentes**

```bash
python -m mindflow_cli test agents
```

## 🎯 Exemplos de Mensagens para Teste

### **Roteamento para CODER:**
- "Create a Python function to calculate factorial"
- "Write a simple REST API endpoint"
- "Debug this Python code: print('hello world'"
- "Implement a binary search algorithm"

### **Roteamento para ANALYST:**
- "Analyze this codebase for security vulnerabilities"
- "Review this architecture for scalability issues"
- "Audit this code for performance bottlenecks"
- "Evaluate this design pattern usage"

### **Roteamento para RESEARCHER:**
- "Research best practices for API security"
- "Find documentation for LangChain integration"
- "Compare different database technologies for this use case"

### **Multi-Agente:**
- "Research best practices for API security, then implement secure authentication"
- "Analyze system performance, then optimize the bottlenecks"
- "Create comprehensive documentation and implement the features"

## 🔧 Opções da CLI

### **`mindflow start`**
- `--mode`: `interactive`, `test`, `benchmark`
- `--provider`: `openai`, `vertexai`, etc.
- `--model`: `gpt-4`, `gemini-3-flash`, etc.
- `--debug-orchestrator`: Mostra decisões do orquestrador
- `--save-session`: Salva logs da sessão

### **`mindflow test orchestrator`**
- `--message`: Mensagem de teste (obrigatório)
- `--show-routing`: Mostra processo de routing
- `--show-agent-selection`: Mostra seleção de agente
- `--trace-execution`: Trace completo da execução
- `--provider`: Override do provider
- `--model`: Override do model

### **`mindflow test scenarios`**
- `--scenario`: `basic`, `complex`, `multi-agent`
- `--provider`: Override do provider
- `--model`: Override do model

## 🎨 Interface Rich

### **Painéis de Informação:**
- **Agent Panel**: Agentes disponíveis e especializações
- **Decision Panel**: Decisões do orquestrador em tempo real
- **Session Info**: Informações da sessão atual
- **Debug Toggle**: Ativa/desativa modo debug

### **Elementos Visuais:**
- **Spinner** para processamento
- **Progress bars** para operações longas
- **Tables** para dados estruturados
- **Trees** para hierarquias
- **Panels** para informações agrupadas

## 📊 Saídas Esperadas

### **Modo Interativo:**
```
🚀 MindFlow CLI
Interactive Agent Orchestration System

Available Agents
┌─────────────┬─────────────────┬─────────────────────────────────┐
│ Agent       │ Status          │ Specialization                 │
├─────────────┼─────────────────┼─────────────────────────────────┤
│ CODER       │ ✅ Available    │ Code generation, debugging      │
│ ANALYST     │ ✅ Available    │ Security audits, code review    │
│ RESEARCHER  │ ✅ Available    │ Web search, documentation       │
│ ORCHESTRATOR│ ✅ Available    │ Multi-agent coordination        │
└─────────────┴─────────────────┴─────────────────────────────────┘

Type your message below, or use /help for commands

[bold blue]You[/] Create a Python function for fibonacci
```

### **Teste de Orquestrador:**
```
🧪 Orchestrator Flow Test
Testing agent routing and execution

Test Message: Create a Python function for fibonacci
Provider: openai
Model: gpt-3.5-turbo

🔄 Starting Orchestrator Flow...

🔀 Step 1: Analyzing user request and selecting agent...
🤖 Step 2: CODER Agent Activated
⚡ Step 3: Executing task with tools...
✅ Test Completed

📊 Test Summary
============================================================
Original Message: Create a Python function for fibonacci

🔀 Routing Decision:
Intent analysis completed with 0.92 confidence
Recommended agent: CODER
Reasoning: User wants code implementation

🤖 Selected Agent: CODER

⚡ Execution Steps: 3 steps
  1. Analyzed requirements
  2. Implemented solution
  3. Validated code

💬 Response Preview:
Here's a Python function to calculate fibonacci numbers...

============================================================
```

## 🚨 Solução de Problemas

### **Common Issues:**

1. **Backend não está rodando:**
   ```bash
   # Verificar se backend está ativo
   curl http://localhost:8000/health
   ```

2. **Dependências faltando:**
   ```bash
   # Reinstalar dependências
   source .venv/bin/activate
   pip install --break-system-packages -e .
   ```

3. **Import errors:**
   ```bash
   # Verificar PYTHONPATH
   export PYTHONPATH=/home/levybonito/Projetos/MindFlow/python:$PYTHONPATH
   ```

### **Debug Mode:**
```bash
# Ativar debug completo
python -m mindflow_cli start --mode interactive --debug-orchestrator --provider openai
```

## 🎉 Próximos Passos

1. **Testar todos os cenários** básicos, complexos e multi-agente
2. **Experimentar diferentes providers** (OpenAI, Vertex AI, Ollama)
3. **Testar modo benchmark** para performance
4. **Extender com novos comandos** conforme necessário
5. **Coletar feedback** para melhorias

---

**A CLI Chat do MindFlow está pronta para uso!** 🚀

Teste o fluxo completo de orquestrador e agentes com uma interface rica e interativa.
