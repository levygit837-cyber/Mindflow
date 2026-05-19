# Plano de Implementacao: Evolucao do Sistema de IA do MindFlow

**Data:** 2026-04-03  
**Base:** `docs/09-analysis-and-reports/ANALISE-SISTEMA-IA-CLAUDE-CODE-VS-MINDFLOW.md`  
**Objetivo:** transformar os gaps operacionais identificados na comparacao com Claude Code em backlog executavel para o MindFlow

---

## 1. Objetivo do Plano

Este plano existe para levar o MindFlow do estado atual de "arquitetura boa com varios blocos fortes" para um estado de "runtime multi-agente maduro e operacionalmente confiavel".

O plano foca nas capacidades ainda nao absorvidas do Claude Code:

- runtime de subagentes
- resume completo de sessao
- memoria disciplinada
- session digest e handoff
- extensibilidade por skills/plugins
- observabilidade por linhagem de agente
- contratos de prompt/contexto
- worktree isolation
- governanca de provider routing

---

## 2. Fora de Escopo

Nao fazem parte deste plano porque ja foram usados como referencia no MindFlow:

- hooks
- compactacao
- tools
- circuit breakers e exceptions
- seguranca e modos

Esses sistemas podem aparecer como dependencia de integracao, mas nao sao o foco principal de implementacao aqui.

---

## 3. Principios de Execucao

1. **Integrar antes de reinventar**  
   O MindFlow ja possui varios servicos e contratos prontos. O plano prioriza wiring e maturacao.

2. **Fechar o runtime antes de ampliar a superficie**  
   Primeiro estabilizar subagentes, resume e memoria. Depois ampliar plataforma com skills/plugins.

3. **Cada fase precisa deixar um artefato operacional**  
   Nada de mudanca apenas conceitual. Cada fase deve resultar em runtime, contrato, teste ou observabilidade real.

4. **Persistencia e explainability sao requisitos de primeira classe**  
   Toda capacidade nova precisa ser rastreavel, reidratavel e explicavel.

---

## 4. Visao Geral do Roadmap

| Fase | Nome | Prioridade | Resultado |
|---|---|---:|---|
| 0 | Contratos e inventario tecnico | P0 | Base de implementacao e alinhamento arquitetural |
| 1 | Runtime de subagentes | P0 | Delegacao operacional madura |
| 2 | Resume e session restore canonico | P0 | Continuidade real entre sessoes |
| 3 | Governanca de memoria e session digest | P0 | Memoria util sem drift operacional |
| 4 | Plataforma de skills/plugins | P1 | Extensibilidade real do sistema |
| 5 | Observabilidade e contratos de contexto | P1 | Debug e telemetria por linhagem |
| 6 | Worktree isolation | P2 | Isolamento de execucao para codigo |
| 7 | Governanca de provider routing | P2 | Operacao segura em host/remote/multi-tenant |

---

## 5. Fase 0 - Contratos e Inventario Tecnico

**Objetivo:** congelar as interfaces e evitar implementacao difusa.

### Escopo

- Definir o contrato de `AgentRuntimeSession`
- Definir o contrato de `DelegatedAgentExecution`
- Definir o contrato de `SessionDigest`
- Definir o contrato de `AgentLineage`
- Definir o contrato de `PromptContextEnvelope`

### Arquivos alvo

Arquivos existentes a revisar:

- `python/mindflow_backend/schemas/orchestration/delegation.py`
- `python/mindflow_backend/services/core/session_runtime_state_service.py`
- `python/mindflow_backend/schemas/session/contracts.py`
- `python/mindflow_backend/schemas/session/review.py`
- `python/mindflow_backend/infra/logging/correlation.py`

Arquivos sugeridos para criar:

- `python/mindflow_backend/schemas/runtime/agent_runtime.py`
- `python/mindflow_backend/schemas/runtime/session_digest.py`
- `python/mindflow_backend/schemas/runtime/lineage.py`
- `python/mindflow_backend/schemas/runtime/prompt_context.py`

### Entregaveis

- contratos pydantic para runtime
- ADR curta documentando o modelo operacional
- mapeamento entre estruturas existentes e novas

### Criterios de aceite

- existe um schema canonico para sessao de agente
- existe um schema canonico para digest de sessao
- existe um schema canonico para lineage
- todas as proximas fases referenciam esses contratos

---

## 6. Fase 1 - Runtime de Subagentes

**Objetivo:** transformar a delegacao do MindFlow em runtime real de producao.

### Escopo

- criar spawn assincrono de agentes
- suportar background execution
- criar tool pool por agente
- rastrear parent/child lineage
- armazenar transcript e estado por agente
- emitir eventos de progresso e conclusao

### Base existente a reaproveitar

- `python/mindflow_backend/services/orchestration/orchestration_service.py`
- `python/mindflow_backend/workers/agents/orchestrator_worker.py`
- `python/mindflow_backend/schemas/orchestration/delegation.py`
- `python/mindflow_backend/execution/sub_teams/sub_team_session.py`
- `python/mindflow_backend/runtime/core/agent_runtime.py`

### Arquivos sugeridos

- `python/mindflow_backend/runtime/agents/agent_spawner.py`
- `python/mindflow_backend/runtime/agents/agent_monitor.py`
- `python/mindflow_backend/runtime/agents/agent_coordinator.py`
- `python/mindflow_backend/runtime/agents/agent_progress.py`
- `python/mindflow_backend/runtime/agents/agent_transcript_store.py`

### Entregaveis

- `spawn_agent()` interno do runtime
- `agent_id` estavel por execucao delegada
- suporte a `run_in_background`
- progresso observavel por agente
- transcript proprio por subagente

### Criterios de aceite

- o orquestrador consegue delegar para pelo menos um especialista em background
- o especialista possui `agent_id`, `parent_session_id` e `delegation_id`
- o transcript do especialista pode ser consultado apos a execucao
- o runtime consegue listar agentes ativos e completados

### Riscos

- vazamento de contexto entre agentes
- pool de tools inconsistente
- dificuldade de cancelar execucao em background

---

## 7. Fase 2 - Resume e Session Restore Canonico

**Objetivo:** permitir que sessoes longas e distribuicoes de runtime sejam retomadas com consistencia.

### Escopo

- consolidar fonte de verdade da sessao
- restaurar estado de agentes ativos e concluidos
- restaurar digest, todos, budget e contexto operacional
- suportar `resume` por session id

### Base existente a reaproveitar

- `python/mindflow_backend/runtime/streaming/stream.py`
- `python/mindflow_backend/runtime/execution/executor.py`
- `python/mindflow_backend/services/core/session_runtime_state_service.py`
- `python/mindflow_backend/services/orchestration/todo_planning_service.py`
- `python/mindflow_backend/api/v1/chat.py`

### Arquivos sugeridos

- `python/mindflow_backend/runtime/session/session_recovery.py`
- `python/mindflow_backend/runtime/session/session_restore.py`
- `python/mindflow_backend/runtime/session/session_snapshot_builder.py`

### Entregaveis

- `load_session_for_resume()`
- `restore_session_state()`
- snapshot operacional completo da sessao

### Criterios de aceite

- uma sessao interrompida pode ser retomada com historico, digest, todos e estado de runtime
- `resume=True` nao recompila contexto do zero sem necessidade
- o restore nao perde `agent lineage`

### Dependencias

- Fase 0
- parte da Fase 1

---

## 8. Fase 3 - Governanca de Memoria e Session Digest

**Objetivo:** separar memoria duravel de memoria operacional e reduzir drift.

### Escopo

- reescrever o protocolo de memoria do MindFlow
- definir o que nao salvar
- adicionar staleness metadata
- forcar verificacao contra estado atual antes de recomendar
- criar `SessionDigest` canonico
- gerar recap curto de "onde paramos"

### Base existente a reaproveitar

- `python/mindflow_backend/agents/prompts/specialized/memory_protocol.py`
- `python/mindflow_backend/agents/tools/integration/memory_tools.py`
- `python/mindflow_backend/memory/session_memory/service.py`
- `python/mindflow_backend/workers/system/session_review_worker.py`
- `python/mindflow_backend/schemas/session/review.py`
- `python/mindflow_backend/schemas/session/contracts.py`

### Arquivos sugeridos

- `python/mindflow_backend/agents/prompts/specialized/memory_governance.py`
- `python/mindflow_backend/runtime/memory/session_digest_service.py`
- `python/mindflow_backend/runtime/memory/memory_freshness.py`
- `python/mindflow_backend/runtime/memory/memory_hygiene_rules.py`

### Estrutura recomendada do SessionDigest

- titulo da sessao
- estado atual
- proximo passo concreto
- arquivos e funcoes relevantes
- workflow operativo
- erros e correcoes
- decisoes importantes
- resultados chave
- worklog resumido

### Criterios de aceite

- memoria duravel deixa de receber ruido de estado efemero
- toda memoria retornada ao agente traz sinal de frescor
- existe digest unico da sessao
- existe resumo curto para retomar contexto

---

## 9. Fase 4 - Plataforma de Skills e Plugins

**Objetivo:** fechar a camada de extensibilidade do MindFlow.

### Escopo

- skill discovery
- skill loading
- plugin manifest
- plugin command loading
- plugin skill loading
- enable/disable por escopo
- integracao com hooks e MCP

### Base existente a reaproveitar

- `python/mindflow_backend/commands/loader.py`
- `python/mindflow_backend/hooks/plugin_loader.py`
- `python/mindflow_backend/hooks/registry.py`
- `python/mindflow_backend/schemas/skills/registry.py`
- `python/mindflow_backend/interfaces/skills/registry.py`

### Arquivos sugeridos

- `python/mindflow_backend/plugins/manifest.py`
- `python/mindflow_backend/plugins/plugin_loader.py`
- `python/mindflow_backend/plugins/skill_loader.py`
- `python/mindflow_backend/plugins/command_loader.py`
- `python/mindflow_backend/plugins/plugin_registry.py`

### Decisoes recomendadas

- usar manifesto explicito por plugin
- permitir components do tipo `commands`, `skills`, `hooks`, `mcp`
- usar escopos `builtin`, `project`, `user`, `managed`

### Criterios de aceite

- o runtime carrega skills sem hardcode
- plugins conseguem registrar hooks e comandos
- existe discovery listavel e enable/disable por plugin

### Prioridade relativa

**P1**, logo apos estabilizar runtime e memoria

---

## 10. Fase 5 - Observabilidade e Contratos de Contexto

**Objetivo:** tornar o sistema rastreavel por agente e mais eficiente no uso de contexto.

### Escopo

- propagar `agent_id`, `parent_session_id`, `delegation_id`, `task_id`
- adicionar atributos de lineage em logs e metricas
- separar prefixo de prompt estatico do contexto dinamico
- permitir contexto minimo compartilhavel entre agentes

### Base existente a reaproveitar

- `python/mindflow_backend/infra/logging/correlation.py`
- `python/mindflow_backend/infra/logging/structured.py`
- `python/mindflow_backend/agents/tools/analytics/tool_metrics.py`
- `python/mindflow_backend/agents/prompts/assembler.py`
- `python/mindflow_backend/query/engine.py`
- `python/mindflow_backend/query/cache/file_cache.py`

### Arquivos sugeridos

- `python/mindflow_backend/runtime/observability/agent_lineage.py`
- `python/mindflow_backend/runtime/observability/agent_telemetry.py`
- `python/mindflow_backend/runtime/context/prompt_context_envelope.py`
- `python/mindflow_backend/runtime/context/cache_safe_context.py`

### Criterios de aceite

- todo log relevante pode ser atribuido a agente e sessao pai
- consultas do query engine usam envelope de contexto bem definido
- existe caminho para reuso de prefixo estatico e contexto minimo compartilhavel

---

## 11. Fase 6 - Worktree Isolation

**Objetivo:** permitir isolamento real de execucao paralela em tarefas de codigo.

### Escopo

- criar worktree por agente quando solicitado
- armazenar `worktree_path` no estado da sessao/agente
- fazer cleanup ao terminar
- restaurar worktree no resume

### Base existente a reaproveitar

- `python/mindflow_backend/hooks/types.py`
- runtime de subagentes da Fase 1
- session restore da Fase 2

### Arquivos sugeridos

- `python/mindflow_backend/runtime/worktree/worktree_service.py`
- `python/mindflow_backend/runtime/worktree/worktree_session.py`
- `python/mindflow_backend/runtime/worktree/worktree_cleanup.py`

### Criterios de aceite

- um agente de codigo pode executar em worktree dedicada
- a sessao sabe em qual worktree o agente rodou
- o resume restaura o contexto corretamente

### Prioridade relativa

**P2**, depois que o runtime multi-agente estiver maduro

---

## 12. Fase 7 - Governanca de Provider Routing

**Objetivo:** proteger a operacao quando o MindFlow rodar em host controlado, multi-tenant ou remote environments.

### Escopo

- definir precedence de configuracao
- separar configuracao do host de preferencia do usuario
- bloquear override indevido de provider/model
- registrar fallback e roteamento com explainability

### Base existente a reaproveitar

- `python/mindflow_backend/services/core/provider_service.py`
- `python/mindflow_backend/infra/api/router.py`
- `python/mindflow_backend/infra/api/gateway.py`

### Arquivos sugeridos

- `python/mindflow_backend/runtime/providers/provider_precedence.py`
- `python/mindflow_backend/runtime/providers/managed_provider_env.py`
- `python/mindflow_backend/runtime/providers/provider_routing_audit.py`

### Criterios de aceite

- o host pode marcar provider config como gerenciado
- config local nao sobrescreve roteamento critico
- fallback fica auditavel por request/sessao

---

## 13. Backlog Priorizado

| Ordem | Item | Prioridade | Tipo |
|---|---|---:|---|
| 1 | Contratos de runtime, digest e lineage | P0 | Fundacao |
| 2 | Spawn/monitor/coordinator de subagentes | P0 | Runtime |
| 3 | Session restore canonico | P0 | Runtime |
| 4 | Reescrita da governanca de memoria | P0 | IA |
| 5 | SessionDigest e recap de retomada | P0 | IA |
| 6 | Propagacao de lineage em logs e metricas | P1 | Observabilidade |
| 7 | Skill loader e plugin manifest | P1 | Plataforma |
| 8 | Plugin command/skill registry | P1 | Plataforma |
| 9 | PromptContextEnvelope e cache-safe context | P1 | Performance |
| 10 | Integracao de todos no restore e handoff | P1 | Operacao |
| 11 | Worktree service | P2 | Workspace |
| 12 | Provider precedence e managed routing | P2 | Infra |

---

## 14. Sequencia Recomendada de Execucao

### Sprint 1

- Fase 0 completa
- inicio da Fase 1

### Sprint 2

- finalizar Fase 1
- iniciar Fase 2

### Sprint 3

- finalizar Fase 2
- executar Fase 3

### Sprint 4

- Fase 4
- parte da Fase 5

### Sprint 5

- finalizar Fase 5
- iniciar Fase 6

### Sprint 6

- Fase 7
- endurecimento, testes de regressao e documentacao final

---

## 15. Definicao de Pronto

Uma fase so deve ser considerada concluida quando:

- ha contratos estaveis
- ha integracao no runtime principal
- ha logs e metricas suficientes para debug
- ha cobertura minima de testes unitarios e de integracao
- ha documentacao operacional da fase

---

## 16. Resultado Esperado

Ao final deste plano, o MindFlow deve sair de um estado de "arquitetura com varios blocos fortes" para um estado de "sistema de IA operacionalmente maduro", com:

- delegacao real entre agentes
- continuidade completa entre sessoes
- memoria util e confiavel
- extensibilidade por plataforma
- rastreabilidade por linhagem
- isolamento opcional de execucao

Esse e o passo que mais aproxima o MindFlow do nivel de maturidade do Claude Code sem exigir copia literal da codebase de referencia.
