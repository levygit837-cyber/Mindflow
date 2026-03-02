# OmniMind Vault Gap Documentation Integration Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Consolidar e incorporar no projeto real as informacoes relevantes do vault Obsidian (`OmniProject`, `Possivel Features`, `Ideas + Canvas`) que ainda nao estao documentadas no repositório `/home/levybonito/Projetos/OmniMind`.

**Architecture:** Implementacao doc-first, com rastreabilidade de origem por documento/canvas, matriz de lacunas, contratos arquiteturais por agente (incluindo agentes novos), governanca de contexto, estrategia de workflows assincronos e roteiro de entrega por fases. Cada adicao deve ser verificavel por comandos automatizaveis.

**Tech Stack:** Markdown (`docs/architecture`, `docs/adr`, `docs/roadmap`), Bash (`grep`, `find`, `test`), Python scripts de verificacao (`python/scripts`), referencias do backend atual (FastAPI + LangGraph + DeepAgents + Postgres).

---

### Task 1: Criar Matriz de Lacunas e Inventario de Fontes

**Files:**
- Create: `docs/architecture/obsidian-vault-gap-analysis.md`
- Test: `python/scripts/verify_obsidian_docs_coverage.sh`

**Step 1: Write the failing test**

```bash
test -f docs/architecture/obsidian-vault-gap-analysis.md
```

**Step 2: Run test to verify it fails**

Run: `cd /home/levybonito/Projetos/OmniMind && test -f docs/architecture/obsidian-vault-gap-analysis.md`  
Expected: exit code `1` (arquivo ainda nao existe).

**Step 3: Write minimal implementation**

Criar `docs/architecture/obsidian-vault-gap-analysis.md` com estas secoes completas:

```markdown
# Obsidian Vault Gap Analysis

## Scope and Source Inventory
- OmniProject/*.md
- Possivel Features/Ideas-Canvas-e-Notas/*.md
- Possivel Features/Ideas-Canvas-e-Notas/*.canvas

## Method
- Hash dedup (docs ja existentes vs unicos)
- Topic extraction por documento
- Coverage map para docs atuais

## Gap Matrix
| Source | Topic | Present in Real Project | Missing Detail | Target File |

## High-Priority Missing Topics
## Medium-Priority Missing Topics
## Low-Priority Missing Topics
## Decisions and Non-Goals
```

A matriz deve incluir no minimo os topicos:
- `Creative Agent contract`
- `SecurityGuard contract + gate`
- `Orchestrator context partition`
- `Research source trust + citations`
- `Input normalizer`
- `Workflow caller async (n8n/zapier/webhook)`
- `Session canvas/chunk memory strategy`

**Step 4: Run test to verify it passes**

Run: `cd /home/levybonito/Projetos/OmniMind && test -f docs/architecture/obsidian-vault-gap-analysis.md && grep -q "## Gap Matrix" docs/architecture/obsidian-vault-gap-analysis.md`  
Expected: exit code `0`.

**Step 5: Commit**

```bash
git add docs/architecture/obsidian-vault-gap-analysis.md
git commit -m "docs: add Obsidian vault gap analysis baseline"
```

---

### Task 2: Documentar Contratos Estendidos do Time de Agentes

**Files:**
- Create: `docs/architecture/agent-team-extended-contracts.md`
- Modify: `docs/architecture/python-backend.md`
- Test: `python/scripts/verify_obsidian_docs_coverage.sh`

**Step 1: Write the failing test**

```bash
grep -q "## Creative Agent Contract" docs/architecture/agent-team-extended-contracts.md
```

**Step 2: Run test to verify it fails**

Run: `cd /home/levybonito/Projetos/OmniMind && grep -q "## Creative Agent Contract" docs/architecture/agent-team-extended-contracts.md`  
Expected: `grep: No such file or directory` ou exit code `2/1`.

**Step 3: Write minimal implementation**

Criar `docs/architecture/agent-team-extended-contracts.md` com:

```markdown
# Agent Team Extended Contracts

## Core Agents (Current)
- Coder
- Analyst
- Researcher
- ArchTech
- Critic

## Creative Agent Contract
- work type classification
- divergence/convergence workflow
- ask-one-question gate
- output schema

## SecurityGuard Agent Contract
- fast/deep pipeline
- severity gate (critical/high)
- CI/CD blocking policy
- evidence requirements

## Analyst Fast/Deep Contract
- Fast Mode
- Deep Analyse Mode
- confidence threshold
- response contract
```

Adicionar no `docs/architecture/python-backend.md` nova secao:

```markdown
## Vault-Derived Agent Contract Extensions (2026-03-02)
- See: `docs/architecture/agent-team-extended-contracts.md`
```

**Step 4: Run test to verify it passes**

Run:
`cd /home/levybonito/Projetos/OmniMind && grep -q "## Creative Agent Contract" docs/architecture/agent-team-extended-contracts.md && grep -q "## SecurityGuard Agent Contract" docs/architecture/agent-team-extended-contracts.md && grep -q "Vault-Derived Agent Contract Extensions" docs/architecture/python-backend.md`  
Expected: exit code `0`.

**Step 5: Commit**

```bash
git add docs/architecture/agent-team-extended-contracts.md docs/architecture/python-backend.md
git commit -m "docs: add extended agent team contracts from vault"
```

---

### Task 3: Documentar Pipeline de Research, Fontes e Confianca

**Files:**
- Create: `docs/architecture/researcher-pipeline-and-source-trust.md`
- Test: `python/scripts/verify_obsidian_docs_coverage.sh`

**Step 1: Write the failing test**

```bash
grep -q "## Source Tiering" docs/architecture/researcher-pipeline-and-source-trust.md
```

**Step 2: Run test to verify it fails**

Run: `cd /home/levybonito/Projetos/OmniMind && grep -q "## Source Tiering" docs/architecture/researcher-pipeline-and-source-trust.md`  
Expected: exit code `1/2`.

**Step 3: Write minimal implementation**

Criar documento com secoes:

```markdown
# Researcher Pipeline and Source Trust

## Query Planning by Request Type
## Query Count Scaling by Complexity
## Source Tiering
- Official
- Non-official
- Unknown
- Social
- Academic

## Relevance and Confidence Scoring
## Cross-Source Reanalysis
## Structured Final Response with Citations
## Async Workflow Option (n8n/webhook) for heavy research
## Logs and Observability per research execution
```

**Step 4: Run test to verify it passes**

Run:
`cd /home/levybonito/Projetos/OmniMind && grep -q "## Source Tiering" docs/architecture/researcher-pipeline-and-source-trust.md && grep -q "Structured Final Response with Citations" docs/architecture/researcher-pipeline-and-source-trust.md`  
Expected: exit code `0`.

**Step 5: Commit**

```bash
git add docs/architecture/researcher-pipeline-and-source-trust.md
git commit -m "docs: add researcher source trust and citation pipeline"
```

---

### Task 4: Documentar Governanca de Contexto do Orquestrador

**Files:**
- Create: `docs/architecture/orchestrator-context-governance.md`
- Modify: `docs/architecture/ARCHITECTURE_PLAN.md`
- Test: `python/scripts/verify_obsidian_docs_coverage.sh`

**Step 1: Write the failing test**

```bash
grep -q "## Context Partition Strategy" docs/architecture/orchestrator-context-governance.md
```

**Step 2: Run test to verify it fails**

Run: `cd /home/levybonito/Projetos/OmniMind && grep -q "## Context Partition Strategy" docs/architecture/orchestrator-context-governance.md`  
Expected: exit code `1/2`.

**Step 3: Write minimal implementation**

Criar `docs/architecture/orchestrator-context-governance.md` com:

```markdown
# Orchestrator Context Governance

## Principle: Orchestrator Owns Coordination, Not Raw File Context
## Context Partition Strategy
- chunk budget
- partition by session/task/objective

## Explorer-to-Orchestrator Summarization Contract
## No Raw Context Injection Rule
## Resume/Rollup Rules for Long Sessions
## Context Quality Gates
```

Atualizar `docs/architecture/ARCHITECTURE_PLAN.md` com secao:

```markdown
## Vault-Derived Context Governance Additions
- See: docs/architecture/orchestrator-context-governance.md
```

**Step 4: Run test to verify it passes**

Run:
`cd /home/levybonito/Projetos/OmniMind && grep -q "## Context Partition Strategy" docs/architecture/orchestrator-context-governance.md && grep -q "Vault-Derived Context Governance Additions" docs/architecture/ARCHITECTURE_PLAN.md`  
Expected: exit code `0`.

**Step 5: Commit**

```bash
git add docs/architecture/orchestrator-context-governance.md docs/architecture/ARCHITECTURE_PLAN.md
git commit -m "docs: add orchestrator context governance from vault"
```

---

### Task 5: Documentar Input Normalization e Session Chunk Canvas

**Files:**
- Create: `docs/architecture/input-normalization-and-session-chunks.md`
- Test: `python/scripts/verify_obsidian_docs_coverage.sh`

**Step 1: Write the failing test**

```bash
grep -q "## Input Normalization Layer" docs/architecture/input-normalization-and-session-chunks.md
```

**Step 2: Run test to verify it fails**

Run: `cd /home/levybonito/Projetos/OmniMind && grep -q "## Input Normalization Layer" docs/architecture/input-normalization-and-session-chunks.md`  
Expected: exit code `1/2`.

**Step 3: Write minimal implementation**

Criar documento com secoes:

```markdown
# Input Normalization and Session Chunk Strategy

## Input Normalization Layer
- noise removal
- repetition collapse
- intent-preserving rewrite

## Session Context Partitioning
- chunk segmentation
- chunk metadata
- chunk classification

## Session Canvas Concept (Internal)
- graph of context chunks
- retrieval by range/topic
- confidence and freshness signals
```

**Step 4: Run test to verify it passes**

Run:
`cd /home/levybonito/Projetos/OmniMind && grep -q "## Input Normalization Layer" docs/architecture/input-normalization-and-session-chunks.md && grep -q "## Session Canvas Concept (Internal)" docs/architecture/input-normalization-and-session-chunks.md`  
Expected: exit code `0`.

**Step 5: Commit**

```bash
git add docs/architecture/input-normalization-and-session-chunks.md
git commit -m "docs: add input normalization and session chunk strategy"
```

---

### Task 6: Documentar Workflow Caller Assincrono e Retry/Queue Policy

**Files:**
- Create: `docs/architecture/workflow-caller-async-integration.md`
- Modify: `docs/architecture/python-backend.md`
- Test: `python/scripts/verify_obsidian_docs_coverage.sh`

**Step 1: Write the failing test**

```bash
grep -q "## External Workflow Caller Pattern" docs/architecture/workflow-caller-async-integration.md
```

**Step 2: Run test to verify it fails**

Run: `cd /home/levybonito/Projetos/OmniMind && grep -q "## External Workflow Caller Pattern" docs/architecture/workflow-caller-async-integration.md`  
Expected: exit code `1/2`.

**Step 3: Write minimal implementation**

Criar documento com:

```markdown
# Workflow Caller Async Integration

## External Workflow Caller Pattern
- pre-built workflows
- async trigger
- webhook callback

## Retry Policy
- transient vs non-transient errors
- exponential backoff + jitter
- max retries
- timeout
- idempotency key
- dead letter queue

## Suggested Integration Targets in Current Backend
- workers/queue
- workers/tasks
- runtime/stream
```

Adicionar link no `python-backend.md`:

```markdown
- See: `docs/architecture/workflow-caller-async-integration.md`
```

**Step 4: Run test to verify it passes**

Run:
`cd /home/levybonito/Projetos/OmniMind && grep -q "dead letter queue" docs/architecture/workflow-caller-async-integration.md && grep -q "workflow-caller-async-integration.md" docs/architecture/python-backend.md`  
Expected: exit code `0`.

**Step 5: Commit**

```bash
git add docs/architecture/workflow-caller-async-integration.md docs/architecture/python-backend.md
git commit -m "docs: add async workflow caller and retry queue policy"
```

---

### Task 7: Formalizar DT Contracts v2 (alinhado ao vault)

**Files:**
- Create: `docs/architecture/decomposition-thinking-contracts-v2.md`
- Modify: `docs/architecture/python-backend.md`
- Test: `python/scripts/verify_obsidian_docs_coverage.sh`

**Step 1: Write the failing test**

```bash
grep -q "## Sub-Component State Contract" docs/architecture/decomposition-thinking-contracts-v2.md
```

**Step 2: Run test to verify it fails**

Run: `cd /home/levybonito/Projetos/OmniMind && grep -q "## Sub-Component State Contract" docs/architecture/decomposition-thinking-contracts-v2.md`  
Expected: exit code `1/2`.

**Step 3: Write minimal implementation**

Criar documento com:

```markdown
# Decomposition Thinking Contracts v2

## Main Component Contract
## Sub-Component Contract
## Sub-Component State Contract
## Synthesis Contract
## Agent-to-Component Navigation Contract
## Score Formula and Validation Threshold
## Mapping to Current Files
- orchestrator/decomposition/*
- schemas/decomposition.py
- orchestrator/graph.py
```

Adicionar no `python-backend.md`:

```markdown
## DT v2 Contracts
- See: docs/architecture/decomposition-thinking-contracts-v2.md
```

**Step 4: Run test to verify it passes**

Run:
`cd /home/levybonito/Projetos/OmniMind && grep -q "## Sub-Component State Contract" docs/architecture/decomposition-thinking-contracts-v2.md && grep -q "## DT v2 Contracts" docs/architecture/python-backend.md`  
Expected: exit code `0`.

**Step 5: Commit**

```bash
git add docs/architecture/decomposition-thinking-contracts-v2.md docs/architecture/python-backend.md
git commit -m "docs: define decomposition thinking contracts v2"
```

---

### Task 8: Registrar Decisao Arquitetural em ADR

**Files:**
- Create: `docs/adr/0004-vault-derived-agent-contracts-and-context-governance.md`
- Modify: `docs/adr/README.md`
- Test: `python/scripts/verify_obsidian_docs_coverage.sh`

**Step 1: Write the failing test**

```bash
test -f docs/adr/0004-vault-derived-agent-contracts-and-context-governance.md
```

**Step 2: Run test to verify it fails**

Run: `cd /home/levybonito/Projetos/OmniMind && test -f docs/adr/0004-vault-derived-agent-contracts-and-context-governance.md`  
Expected: exit code `1`.

**Step 3: Write minimal implementation**

Criar ADR com estrutura:

```markdown
# ADR 0004: Vault-Derived Agent Contracts and Context Governance
## Status
## Context
## Decision
## Consequences
## Rollout Plan
```

Atualizar `docs/adr/README.md` adicionando entrada do ADR 0004.

**Step 4: Run test to verify it passes**

Run:
`cd /home/levybonito/Projetos/OmniMind && test -f docs/adr/0004-vault-derived-agent-contracts-and-context-governance.md && grep -q "0004-vault-derived-agent-contracts-and-context-governance" docs/adr/README.md`  
Expected: exit code `0`.

**Step 5: Commit**

```bash
git add docs/adr/0004-vault-derived-agent-contracts-and-context-governance.md docs/adr/README.md
git commit -m "docs(adr): record vault-derived contracts and context governance decision"
```

---

### Task 9: Criar Roadmap de Integracao das Features do Vault

**Files:**
- Create: `docs/roadmap/obsidian-feature-integration-roadmap.md`
- Modify: `docs/architecture/ARCHITECTURE_PLAN.md`
- Test: `python/scripts/verify_obsidian_docs_coverage.sh`

**Step 1: Write the failing test**

```bash
grep -q "## Phase 0 - Documentation Convergence" docs/roadmap/obsidian-feature-integration-roadmap.md
```

**Step 2: Run test to verify it fails**

Run: `cd /home/levybonito/Projetos/OmniMind && grep -q "## Phase 0 - Documentation Convergence" docs/roadmap/obsidian-feature-integration-roadmap.md`  
Expected: exit code `1/2`.

**Step 3: Write minimal implementation**

Criar roadmap com fases:

```markdown
# Obsidian Feature Integration Roadmap

## Phase 0 - Documentation Convergence
## Phase 1 - Agent Contract Parity (Creative + SecurityGuard)
## Phase 2 - Context Governance and Input Normalization
## Phase 3 - Async Workflow Caller and Retry Queue Hardening
## Phase 4 - DT v2 Runtime Evolution
## Milestones, Risks, Exit Criteria
```

Atualizar `ARCHITECTURE_PLAN.md` com link para novo roadmap.

**Step 4: Run test to verify it passes**

Run:
`cd /home/levybonito/Projetos/OmniMind && grep -q "## Phase 0 - Documentation Convergence" docs/roadmap/obsidian-feature-integration-roadmap.md && grep -q "obsidian-feature-integration-roadmap.md" docs/architecture/ARCHITECTURE_PLAN.md`  
Expected: exit code `0`.

**Step 5: Commit**

```bash
git add docs/roadmap/obsidian-feature-integration-roadmap.md docs/architecture/ARCHITECTURE_PLAN.md
git commit -m "docs(roadmap): add vault feature integration phases"
```

---

### Task 10: Automatizar Verificacao de Cobertura Documental

**Files:**
- Create: `python/scripts/verify_obsidian_docs_coverage.sh`
- Test: `python/scripts/verify_obsidian_docs_coverage.sh`

**Step 1: Write the failing test**

```bash
test -x python/scripts/verify_obsidian_docs_coverage.sh
```

**Step 2: Run test to verify it fails**

Run: `cd /home/levybonito/Projetos/OmniMind && test -x python/scripts/verify_obsidian_docs_coverage.sh`  
Expected: exit code `1`.

**Step 3: Write minimal implementation**

Criar script executavel:

```bash
#!/usr/bin/env bash
set -euo pipefail

required_files=(
  "docs/architecture/obsidian-vault-gap-analysis.md"
  "docs/architecture/agent-team-extended-contracts.md"
  "docs/architecture/researcher-pipeline-and-source-trust.md"
  "docs/architecture/orchestrator-context-governance.md"
  "docs/architecture/input-normalization-and-session-chunks.md"
  "docs/architecture/workflow-caller-async-integration.md"
  "docs/architecture/decomposition-thinking-contracts-v2.md"
  "docs/roadmap/obsidian-feature-integration-roadmap.md"
  "docs/adr/0004-vault-derived-agent-contracts-and-context-governance.md"
)

for f in "${required_files[@]}"; do
  test -f "$f"
done

grep -q "Creative Agent Contract" docs/architecture/agent-team-extended-contracts.md
grep -q "SecurityGuard Agent Contract" docs/architecture/agent-team-extended-contracts.md
grep -q "Context Partition Strategy" docs/architecture/orchestrator-context-governance.md
grep -q "Source Tiering" docs/architecture/researcher-pipeline-and-source-trust.md
grep -q "Input Normalization Layer" docs/architecture/input-normalization-and-session-chunks.md
```

**Step 4: Run test to verify it passes**

Run:
`cd /home/levybonito/Projetos/OmniMind && chmod +x python/scripts/verify_obsidian_docs_coverage.sh && python/scripts/verify_obsidian_docs_coverage.sh`  
Expected: exit code `0`, sem output de erro.

**Step 5: Commit**

```bash
git add python/scripts/verify_obsidian_docs_coverage.sh
git commit -m "chore(docs): add coverage verification script for vault-derived docs"
```

---

### Task 11: Verificacao Final + Relatorio de Integracao

**Files:**
- Create: `docs/architecture/obsidian-integration-summary.md`
- Test: `python/scripts/verify_obsidian_docs_coverage.sh`

**Step 1: Write the failing test**

```bash
test -f docs/architecture/obsidian-integration-summary.md
```

**Step 2: Run test to verify it fails**

Run: `cd /home/levybonito/Projetos/OmniMind && test -f docs/architecture/obsidian-integration-summary.md`  
Expected: exit code `1`.

**Step 3: Write minimal implementation**

Criar documento final com:

```markdown
# Obsidian Integration Summary

## What Was Added
## Source-to-Target Mapping
## Coverage Checklist
## Open Questions
## Deferred Items (Intentionally Not Added)
```

Incluir saida consolidada de verificacao documental e lista de pendencias reais de implementacao (nao-documentais).

**Step 4: Run test to verify it passes**

Run:
`cd /home/levybonito/Projetos/OmniMind && test -f docs/architecture/obsidian-integration-summary.md && python/scripts/verify_obsidian_docs_coverage.sh`  
Expected: exit code `0`.

**Step 5: Commit**

```bash
git add docs/architecture/obsidian-integration-summary.md
git commit -m "docs: add final summary for Obsidian-to-project documentation integration"
```

---

## Global Verification

Run:

```bash
cd /home/levybonito/Projetos/OmniMind
python/scripts/verify_obsidian_docs_coverage.sh
git log --oneline -n 12
```

Expected:
- coverage script retorna `0`
- commits exibem todas as tasks da documentacao.

## Execution Notes

- Aplicar `@cpo-verification-before-completion` antes de declarar conclusao.
- Solicitar review com `@cpo-requesting-code-review` ao final da execucao.
- Se surgir conflito entre docs antigas TypeScript (`Architeture-guides`) e stack atual Python, priorizar stack atual e registrar conflito na secao `Deferred Items`.
