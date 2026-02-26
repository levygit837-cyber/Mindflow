# Reference Doc Set — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Gerar 11 arquivos Markdown em `Reference/doc/` que sirvam como guia completo de arquitetura de agentes para humanos (decisão de direção) e LLMs (execução).

**Architecture:** Cada arquivo segue estrutura obrigatória de 9 seções (A–I). Os arquivos são organizados em 4 camadas de leitura (Fundação → Arquitetura → Qualidade → Operacional). Todo arquivo começa com cabeçalho de dependências para o LLM saber o que ler antes.

**Tech Stack:** deepagents · LangGraph · LangChain · Python · Next.js (frontend consumer)

---

## Árvore de destino

```
Reference/doc/
  ToolsDoc.md
  AgentsDoc.md
  SubAgentsDoc.md
  OrquestradorDoc.md
  MemoryDoc.md
  ContextoDoc.md
  SkillsDoc.md
  Evaluation.md
  PromptGuide.md
  SystemPromptDoc.md
  Backends.md
```

## Estrutura obrigatória de cada arquivo

```
A) Visão geral (2–6 bullets)
B) Conceitos essenciais (definições curtas)
C) Boas práticas (DO / DON'T)
D) Receitas reutilizáveis (checklists, passos)
E) Exemplos práticos (mín. 3, com 1 ruim + corrigido)
F) Confiabilidade / anti-alucinação
G) Analogia (1–2 parágrafos)
H) Erros comuns e como evitar
I) Mini-template pronto pra copiar/colar
```

## Cabeçalho padrão de cada arquivo

```md
# NomeDoc
> Camada: X | Depende de: Y | Referenciado por: Z
> Stack: deepagents · LangGraph · LangChain
```

---

## Camadas e ordem de geração

| # | Arquivo | Camada | Depende de | Referenciado por |
|---|---------|--------|------------|------------------|
| 1 | ToolsDoc.md | 1 — Fundação | — | AgentsDoc, SubAgentsDoc, OrquestradorDoc |
| 2 | AgentsDoc.md | 1 — Fundação | ToolsDoc | SubAgentsDoc, OrquestradorDoc |
| 3 | ContextoDoc.md | 1 — Fundação | AgentsDoc | MemoryDoc, PromptGuide, SystemPromptDoc |
| 4 | SubAgentsDoc.md | 2 — Arquitetura | AgentsDoc, ToolsDoc | OrquestradorDoc |
| 5 | OrquestradorDoc.md | 2 — Arquitetura | SubAgentsDoc, AgentsDoc | — |
| 6 | MemoryDoc.md | 2 — Arquitetura | AgentsDoc, ContextoDoc | PromptGuide |
| 7 | PromptGuide.md | 3 — Qualidade | ContextoDoc, MemoryDoc | SystemPromptDoc |
| 8 | SystemPromptDoc.md | 3 — Qualidade | PromptGuide | AgentsDoc, SubAgentsDoc |
| 9 | SkillsDoc.md | 3 — Qualidade | AgentsDoc, ToolsDoc | OrquestradorDoc |
| 10 | Evaluation.md | 4 — Operacional | todos acima | — |
| 11 | Backends.md | 4 — Operacional | AgentsDoc | OrquestradorDoc |

---

## Tasks

### Task 1: ToolsDoc.md

**Files:**
- Create: `Reference/doc/ToolsDoc.md`

**Conteúdo esperado:**
- O que é uma tool no contexto de agentes (função com schema bem definido)
- Diferença entre tool síncronas vs assíncronas
- Como criar tools com LangChain (`@tool`, `BaseTool`, `StructuredTool`)
- Como criar tools com deepagents
- Schema de input/output (Pydantic/JSON Schema)
- Boas práticas: nomes descritivos, um único propósito, erro explícito
- Exemplos: tool de filesystem, tool de busca web, tool ruim + corrigida
- Template pronto: `BaseTool` com Pydantic

**Step 1: Criar o arquivo**
Gerar o conteúdo completo seguindo as 9 seções obrigatórias.

**Step 2: Salvar em `Reference/doc/ToolsDoc.md`**

**Step 3: Verificar**
- Arquivo existe em `Reference/doc/`
- Tem as 9 seções (A–I)
- Tem pelo menos 3 exemplos em E
- Tem 1 exemplo ruim + corrigido em E
- Tem mini-template em I

---

### Task 2: AgentsDoc.md

**Files:**
- Create: `Reference/doc/AgentsDoc.md`

**Conteúdo esperado:**
- O que é um agente (loop LLM + tools + estado)
- Diferença entre agente simples e agente com grafo (LangGraph)
- Como montar um agente com deepagents (`create_deep_agent`)
- Como montar um agente com LangGraph (`StateGraph`, nodes, edges)
- Quando usar cada abordagem
- Ciclo de vida: entrada → raciocínio → tool call → resposta
- Exemplos: agente de chat, agente de coding, agente ruim + corrigido
- Template: agente mínimo funcional

---

### Task 3: ContextoDoc.md

**Files:**
- Create: `Reference/doc/ContextoDoc.md`

**Conteúdo esperado:**
- O que é contexto de um agente (janela de tokens disponível)
- Tipos de contexto: mensagens, tool results, histórico, system prompt
- Estratégias de compressão: summarização, sliding window, relevância
- Quando truncar vs quando resumir
- Como o OmniMind gerencia contexto hoje (stream_event_queue, chat_stream_normalizer)
- Exemplos: contexto cheio explodindo, versão controlada, estratégia híbrida

---

### Task 4: SubAgentsDoc.md

**Files:**
- Create: `Reference/doc/SubAgentsDoc.md`

**Conteúdo esperado:**
- O que é um sub-agente (agente invocado por outro agente como tool)
- Paralelismo: como rodar sub-agentes em paralelo (asyncio, LangGraph parallel branches)
- Comunicação entre sub-agentes: mensagens, estado compartilhado, eventos
- Quando usar sub-agente vs tool simples
- Padrão fan-out / fan-in
- Exemplos: sub-agente de análise, sub-agente de revisão, pattern ruim + corrigido
- Template: sub-agente com interface de tool

---

### Task 5: OrquestradorDoc.md

**Files:**
- Create: `Reference/doc/OrquestradorDoc.md`

**Conteúdo esperado:**
- O que é um orquestrador (agente que decide quem faz o quê)
- Padrões: supervisor, pipeline, reactive
- Como o swarm_runner.py funciona hoje (referência ao código real)
- Roteamento de tarefas: como decidir qual agente/sub-agente invocar
- Tratamento de falhas: retry, fallback, dead letter
- Exemplos: orquestrador simples, orquestrador com fallback, ruim + corrigido
- Template: orquestrador com LangGraph supervisor pattern

---

### Task 6: MemoryDoc.md

**Files:**
- Create: `Reference/doc/MemoryDoc.md`

**Conteúdo esperado:**
- Tipos de memória: working (curto prazo), episódic (histórico), semantic (conhecimento), procedural (skills)
- Implementações: in-memory, Redis, PostgreSQL, vector store
- Como deepagents usa `StateBackend` e `FilesystemBackend`
- Checkpointing com LangGraph (`MemorySaver`, `SqliteSaver`)
- Quando persistir vs quando descartar
- Exemplos: memória de conversa, memória de projeto, ruim + corrigido

---

### Task 7: PromptGuide.md

**Files:**
- Create: `Reference/doc/PromptGuide.md`

**Conteúdo esperado:**
- Anatomia de um prompt eficaz (role, contexto, instrução, formato, exemplo)
- Técnicas: chain-of-thought, few-shot, zero-shot, structured output
- Como estruturar instrução de tool call no prompt
- Como instruir o agente a perguntar quando falta info (vs assumir)
- Formato de saída: JSON schema no prompt, exemplos de output esperado
- Exemplos: prompt vago + versão melhorada, prompt com few-shot, prompt ruim + corrigido
- Template: prompt estruturado padrão OmniMind

---

### Task 8: SystemPromptDoc.md

**Files:**
- Create: `Reference/doc/SystemPromptDoc.md`

**Conteúdo esperado:**
- O que é system prompt e qual seu escopo (define personalidade, limites, ferramentas disponíveis)
- System prompt por tipo de interação:
  - Agente geral (conversa)
  - Tool call (instrução focada)
  - Sub-agente (escopo reduzido)
  - Pensamento interno (chain-of-thought)
  - Execução de código (sandbox, limites)
  - Revisão/avaliação
- Como compor system prompts modulares (base + extensões)
- Como o OmniMind faz hoje (`base.py` + `tools/`)
- Exemplos: system prompt genérico, específico de tool, ruim + corrigido
- Template: system prompt modular com seções

---

### Task 9: SkillsDoc.md

**Files:**
- Create: `Reference/doc/SkillsDoc.md`

**Conteúdo esperado:**
- O que é uma skill (capacidade reutilizável, acima de tool, abaixo de agente completo)
- Diferença entre skill, tool e agente
- Como criar uma skill: definição, trigger, execução
- Skills compostas (skill que usa outras skills)
- Como o sistema de skills do OmniMind funciona
- Exemplos: skill de commit, skill de debug, skill ruim + corrigida
- Template: skill com checklist de execução

---

### Task 10: Evaluation.md

**Files:**
- Create: `Reference/doc/Evaluation.md`

**Conteúdo esperado:**
- Por que avaliar (agentes podem estar "confiantes mas errados")
- Métricas: fidelidade, relevância, grounding, latência, custo
- Tipos de avaliação: unitária (por tool), integração (por fluxo), end-to-end
- Como escrever evals simples sem frameworks pesados
- Quando usar LLM-as-judge
- Exemplos: eval de tool, eval de resposta final, eval ruim + corrigida
- Nível: reduzido se conteúdo for escasso, completo se tiver substância

---

### Task 11: Backends.md

**Files:**
- Create: `Reference/doc/Backends.md`

**Conteúdo esperado:**
- Provedores suportados: anthropic, openai, ollama, google, vertexai
- Como `providers.py` seleciona o modelo (`get_model_for_provider`)
- Variáveis de ambiente necessárias por provedor
- Trade-offs: custo, velocidade, capacidade de tool use, contexto máximo
- Como trocar de provedor sem mudar lógica de agente
- Nível: reduzido (é referência de config, não guia conceitual)

---

## Ordem de execução

```
Task 1 → Task 2 → Task 3 → Task 4 → Task 5 → Task 6
→ Task 7 → Task 8 → Task 9 → Task 10 → Task 11
```

Execução sequencial (cada doc referencia o anterior).

## Validação final

Após gerar todos os 11 arquivos, verificar:
- [ ] `Reference/doc/` contém os 11 arquivos
- [ ] Cada arquivo tem as 9 seções (A–I) ou justificativa de redução
- [ ] Cada arquivo tem cabeçalho com camada + dependências
- [ ] Exemplos de código são Python real (não pseudo-código inventado)
- [ ] Termos "incertos" estão marcados com `(incerto)` e instrução de como confirmar
- [ ] Nenhuma API inventada
