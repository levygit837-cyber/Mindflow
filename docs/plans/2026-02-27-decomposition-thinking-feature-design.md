# Plano de Feature — Decomposition Thinking (DT) no Orquestrador OmniMind

Data base: 27/02/2026

## 1) Validação da estratégia (objetiva)

## Veredito
Sua estratégia é eficaz para tarefas complexas e multi-arquivo, desde que:
1. DT seja ativado por critério de complexidade (não para tudo).
2. Cada sub-componente tenha estado persistido e contexto isolado.
3. A síntese final tenha gate de qualidade antes de responder ao usuário.

## Onde DT tende a melhorar
1. Implementações com dependências cruzadas (ex.: `Page.tsx` depende de função em outro módulo).
2. Tarefas longas com risco de perda de contexto.
3. Fluxos com necessidade de pausa/retomada e rastreabilidade.

## Onde DT pode piorar
1. Perguntas simples e diretas (overhead de latência).
2. Casos em que decomposição gera fragmentação excessiva (muitos componentes pequenos).

## Política recomendada de ativação
1. `thinking_mode=normal` por padrão.
2. `thinking_mode=decomposition` quando `complexity_score >= 0.65` ou solicitação explícita do usuário.
3. Fallback automático para `normal` quando houver erro de decomposição após `N` tentativas.

---

## 2) Contratos formais

## 2.1 Contrato de Componente Principal
Representa a tarefa macro e governa os sub-componentes.

```json
{
  "session_id": "uuid",
  "task_input": "string",
  "thinking_mode": "normal|decomposition",
  "complexity_score": 0.0,
  "decomposition_strategy": "deterministic_dag_v1",
  "status": "created|decomposing|executing|synthesizing|completed|failed|cancelled",
  "constraints": ["string"],
  "acceptance_criteria": ["string"],
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601",
  "completed_at": "ISO-8601|null"
}
```

Regras:
1. Deve existir apenas um componente principal por `session_id`.
2. `thinking_mode` é imutável após iniciar execução.
3. `completed` só é permitido após gate de síntese.

## 2.2 Contrato para Sub-Componentes
Unidade mínima de trabalho navegável pelo agente.

```json
{
  "component_id": "A",
  "session_id": "uuid",
  "title": "string",
  "description": "string",
  "priority": 1,
  "dependencies": ["B", "C"],
  "context_scope": {
    "allowed_inputs": ["shared_summary", "dependency_results", "local_snapshot"],
    "forbidden_inputs": ["raw_full_context_other_components"]
  },
  "work_plan": ["string"],
  "status": "pending|ready|in_progress|paused|blocked|validating|done|failed",
  "score": {
    "progress": 0.0,
    "quality": 0.0,
    "tests": 0.0,
    "confidence": 0.0,
    "final": 0.0
  },
  "result": "string|null",
  "shared_notes": "string|null",
  "snapshot": "string|null",
  "started_at": "ISO-8601|null",
  "completed_at": "ISO-8601|null"
}
```

Regras:
1. `dependencies` deve formar DAG (sem ciclos).
2. `result` só pode ser preenchido em `done`.
3. `final >= 0.75` é requisito mínimo para elegibilidade à síntese.

## 2.3 Contrato para Estados dos Sub-Componentes

Estados permitidos:
1. `pending`: criado, aguardando avaliação de dependências.
2. `ready`: liberado para execução.
3. `in_progress`: execução ativa.
4. `paused`: interrompido com snapshot persistido.
5. `blocked`: impedido por dependência/erro externo.
6. `validating`: execução finalizada, em validação de evidências.
7. `done`: validado e pronto para síntese.
8. `failed`: não resolvido após tentativas máximas.

Transições válidas:
1. `pending -> ready`
2. `ready -> in_progress`
3. `in_progress -> paused|blocked|validating|failed`
4. `paused -> ready|blocked`
5. `blocked -> ready|failed`
6. `validating -> done|in_progress|failed`

Regra de isolamento de contexto:
1. Snapshot de um componente nunca deve ser injetado bruto em outro.
2. Comunicação entre componentes ocorre por `shared_notes` resumidas e resultados aprovados.

## 2.4 Contrato para Sintetização de Componentes

```json
{
  "session_id": "uuid",
  "synthesis_input": {
    "original_task": "string",
    "accepted_components": [
      {
        "component_id": "A",
        "result": "string",
        "final_score": 0.88
      }
    ],
    "global_constraints": ["string"]
  },
  "synthesis_checks": {
    "all_required_components_done": true,
    "no_blocking_dependency": true,
    "min_confidence_reached": true,
    "contradiction_check_passed": true
  },
  "final_response": "string",
  "synthesis_score": 0.0,
  "status": "ready|generated|rework_required|finalized"
}
```

Regras:
1. Síntese só inicia com todos os componentes obrigatórios em `done`.
2. Se `contradiction_check_passed=false`, volta para rework em componentes relevantes.
3. `finalized` publica resposta e encerra sessão.

## 2.5 Contrato de Estados do Agente em relação aos componentes

```json
{
  "agent_state": "idle|decomposing|selecting_component|working_component|navigating|validating_component|synthesizing|finalizing|error",
  "active_component_id": "A|null",
  "navigation": {
    "from_component_id": "A|null",
    "to_component_id": "C|null",
    "reason": "dependency|required_context|validation_rework|scheduler_pick",
    "checkpoint_id": "uuid|null"
  },
  "execution_policy": {
    "max_retries_per_component": 2,
    "max_navigation_hops_without_progress": 6
  }
}
```

Regras:
1. Navegação exige checkpoint persistido antes da troca de componente.
2. `working_component` deve sempre apontar para um único `active_component_id`.
3. Excesso de hops sem progresso leva a `error` controlado + fallback.

---

## 3) Como implementar com o stack atual do OmniMind

## 3.1 Ponto de entrada (FastAPI + gRPC)
1. Estender `AgentChatRequest` em `/python/omnimind_backend/schemas/agent.py` com:
   - `thinkingMode?: "normal" | "decomposition"`
   - `decompositionConfig?: {...}`
2. Propagar no gRPC (`/python/omnimind_backend/grpc/proto/omnimind_backend.proto`).
3. Em `/python/omnimind_backend/agents/runtime.py`, adicionar roteador:
   - `NormalThinkingPipeline`
   - `DecompositionThinkingPipeline`

## 3.2 Orquestração (LangGraph + runtime Python)
Implementar em `python/omnimind_backend/agents/decomposition/`:
1. `classifier.py` (complexidade/gate).
2. `decomposer.py` (gera DAG de sub-componentes).
3. `scheduler.py` (topological + priority).
4. `resolver.py` (loop com pause/resume e navegação).
5. `synthesizer.py` (resposta final + checks).
6. `scoring.py` (progress/quality/tests/confidence).

Observação prática:
1. MVP pode começar em loop determinístico Python (mais simples).
2. Segunda etapa pode migrar o fluxo para grafo LangGraph para paralelismo/control flow avançado.

## 3.3 Persistência (PostgreSQL + SQLAlchemy + Alembic)
Adaptar para Postgres (não SQLite) e criar tabelas:
1. `dt_sessions`
2. `dt_components`
3. `dt_component_state_events`
4. `dt_syntheses`

Implementar repository em `/python/omnimind_backend/storage/repositories.py`:
1. CRUD de sessão DT.
2. Atualização atômica de estado de componente.
3. Registro de navegação/checkpoints.
4. Consulta de score/estado para UI e auditoria.

## 3.4 Execução assíncrona (Redis + RQ)
1. Para tarefas curtas: inline no request de stream.
2. Para tarefas longas: enfileirar job RQ e streamar progresso por SSE.

## 3.5 Streaming e UX (SSE + PySide6/QML)
Aproveitar o contrato atual de eventos e adicionar novos `agent_step`:
1. `dt_decompose_started|completed`
2. `dt_component_started|paused|resumed|validated|done|failed`
3. `dt_navigation`
4. `dt_synthesis_started|completed`

No desktop (`/python/omnimind_desktop`):
1. Mostrar lista de componentes com status + score.
2. Exibir trilha de navegação entre componentes.
3. Exibir justificativa de fallback para `normal`.

---

## 4) Métrica de eficácia (para validar de verdade)

## KPIs obrigatórios
1. `task_success_rate` (DT vs normal).
2. `rework_rate` (quantas vezes volta de síntese para componente).
3. `latency_p95` (impacto real de tempo).
4. `hallucination_incidents` (erros factuais/contradições por task).
5. `component_confidence_mean`.

## Experimento recomendado
1. Selecionar 30 tarefas reais do OmniMind (código + análise).
2. Rodar 15 em `normal`, 15 em `DT`.
3. Medir KPIs e decisão de rollout com threshold:
   - `success_rate_DT >= success_rate_normal + 10%`
   - `latency_p95_DT <= 2.2x normal` para manter UX aceitável

---

## 5) Roadmap incremental (baixo risco)

## Fase 1 — Contratos e Persistência
1. Schemas Pydantic + proto gRPC.
2. Migrações Alembic e repositories.
3. Eventos de estado DT no stream.

## Fase 2 — Pipeline DT (MVP)
1. Classificador + decompositor + scheduler + resolver sequencial.
2. Score básico por componente.
3. Síntese com checks mínimos.

## Fase 3 — Hardening
1. Regras anti-loop e detecção de ciclo.
2. Retry/fallback robusto.
3. Métricas e observabilidade.

## Fase 4 — Evolução
1. Paralelismo de componentes independentes.
2. Decomposição recursiva (depth limitado).
3. Aprendizado de padrões de decomposição por histórico.

---

## 6) Conclusão prática

DT é uma boa feature para o Orquestrador OmniMind, mas deve ser tratado como modo avançado de execução, não como default universal.

Decisão recomendada:
1. Aprovar estratégia.
2. Implementar MVP orientado a contratos no stack atual Python/Postgres/SSE.
3. Ligar por gate de complexidade e medir KPIs antes de expandir.
