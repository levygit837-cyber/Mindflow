# Planejamento Consolidado - Agentes SPADE + XMPP + RabbitMQ + LangGraph/LangChain

**Data:** 2026-03-02  
**Status:** Aprovado em brainstorming técnico e consolidado para execução incremental.  
**Objetivo principal:** Evoluir o OmniMind para um modelo multiagente com SPADE, comunicação XMPP entre agentes, filas assíncronas com RabbitMQ e LangChain/LangGraph atuando como motor de raciocínio (não como orquestrador primário da rede de agentes).

---

## 1. Contexto e objetivo

Queremos:
1. Agentes SPADE autônomos que conversem entre si via XMPP.
2. Delegação de tarefas em filas assíncronas (RabbitMQ) para workloads pesados.
3. Reuso de LangChain/LangGraph como **subprocesso cognitivo** (Reasoning Engine).
4. Estratégia híbrida de execução (sync + async) para reduzir latência.
5. Memória por agente com sumarização por janela de contexto e recuperação futura via RAG.

---

## 2. Decisão arquitetural (target)

### 2.1 Plano de Controle (coordenação)
1. **SPADE + XMPP** será o plano de controle.
2. Mensagens interagentes usam semântica de performativas (`request`, `inform`, `agree`, `failure`).
3. Atores principais:
   - `SpadeOrchestratorAgent`
   - agentes de capacidade (`coder`, `analyst`, `researcher`, `arch_tech`, `critic`)
   - bridge de resultados para o stream da API.

### 2.2 Plano de Trabalho (execução assíncrona)
1. **RabbitMQ** será o plano de execução para tarefas longas/pesadas.
2. Filas propostas:
   - `agent.tasks.<agent_type>`
   - `reasoning.requests`
   - `reasoning.results`
   - `agent.events`
   - `dead_letter.*`
3. Padrões obrigatórios:
   - retry com backoff
   - DLQ
   - idempotência por `message_id`
   - correlação por `correlation_id`

### 2.3 Plano Cognitivo (raciocínio)
1. **LangChain/LangGraph** passa a ser motor de raciocínio encapsulado.
2. Não é barramento de coordenação entre agentes SPADE.
3. Pode ser invocado:
   - síncrono (baixa latência)
   - assíncrono via Rabbit (workload pesado)

---

## 3. Contratos e schemas

### 3.1 Envelope unificado (XMPP + Rabbit)
```python
class AgentEnvelope(BaseModel):
    schema_version: Literal["spade.v1"] = "spade.v1"
    message_id: UUID
    correlation_id: UUID
    conversation_id: str
    sender_jid: str
    recipient_jid: str | None = None
    performative: Literal["request", "inform", "agree", "failure"]
    intent: Literal[
        "delegate_task", "reasoning_request", "reasoning_result",
        "tool_request", "tool_result", "status_update"
    ]
    execution_mode: Literal["sync", "async", "auto"] = "auto"
    priority: Literal["low", "normal", "high", "critical"] = "normal"
    ttl_ms: int = 60000
    created_at: datetime
    payload: dict[str, Any]
```

### 3.2 Contrato de raciocínio
```python
class ReasoningRequest(BaseModel):
    request_id: UUID
    task: str
    agent_type: str
    thinking_mode: str
    context: dict[str, Any] = {}
    max_latency_ms: int = 2500
    allow_sync: bool = True

class ReasoningResult(BaseModel):
    request_id: UUID
    status: Literal["ok", "partial", "error", "timeout"]
    answer: str
    thoughts: list[str] = []
    tool_calls: list[dict[str, Any]] = []
    metrics: dict[str, float] = {}
```

### 3.3 Compatibilidade e versionamento
1. `schema_version` obrigatório em todos os envelopes.
2. Evolução sem quebra via versionamento por contrato.
3. Auditoria por `conversation_id + correlation_id`.

---

## 4. Política híbrida de execução (sync + async)

### 4.1 Regra de roteamento
1. `sync` quando:
   - tarefa curta
   - sem fan-out multiagente
   - sem tool de I/O pesado
   - `complexity_score` baixo
2. `async` quando:
   - tarefas longas/pesadas
   - dependências externas lentas
   - necessidade de retry robusto
   - decomposição multiagente

### 4.2 Fallback de latência
1. Tenta sync com timeout curto (ex.: 2500 ms).
2. Em timeout, publica job async no Rabbit.
3. Emite evento de continuação no stream (`deferred_to_async`) com `correlation_id`.
4. Cliente pode aguardar janela curta ou retomar por token/sessão.

---

## 5. Memória por agente SPADE (decisão aprovada)

### 5.1 Unidade de memória
1. Memória é **separada por agente**: `(conversation_id, agent_id)`.
2. Não é cursor global da conversa.

### 5.2 Janela de contexto
1. Janela alvo: até 1M de contexto do modelo.
2. Gatilho de sumarização: a cada **300k tokens por agente**.
3. Cada janela gera:
   - resumo consolidado
   - fatos estruturados
   - metadados de cobertura

### 5.3 Estratos de memória
1. **Raw Memory:** histórico completo de mensagens/eventos.
2. **Window Memory:** resumo por janela (300k).
3. **Fact Memory:** decisões, constraints, tarefas, riscos, artefatos.
4. **Working Memory:** cauda recente bruta para continuidade imediata.

---

## 6. VectorDB e persistência

### 6.1 Situação atual do projeto
1. Stack disponível: Postgres + Redis.
2. Não havia VectorDB dedicado em uso real no fluxo principal.

### 6.2 Estratégia recomendada
1. **Fase inicial:** Postgres como fonte única + embeddings persistidos.
2. **Evolução recomendada:** migrar para `pgvector` no Postgres.
3. **Escala maior futura:** avaliar Qdrant/Pinecone se necessário.

### 6.3 Critério de escolha
1. Baixo custo operacional inicial: Postgres.
2. Busca semântica com consistência transacional.
3. Migração controlada para ANN dedicado quando houver pressão de escala/latência.

---

## 7. Recuperação futura (RAG de memória)

### 7.1 Pipeline de recuperação
1. Recuperar cauda recente bruta.
2. Executar busca semântica em summaries/facts do agente.
3. Reforçar por recência e peso de fato.
4. Montar contexto final com orçamento de tokens.

### 7.2 Heurística de composição de contexto
1. 60%: contexto recente bruto
2. 30%: memória semântica relevante
3. 10%: fatos críticos persistentes

### 7.3 Rastreabilidade
1. Cada inferência deve carregar `memory_refs`.
2. Permite auditoria, replay e depuração.

---

## 8. Integração com o fluxo atual do OmniMind

### 8.1 Sem quebrar contrato externo
1. API SSE atual permanece estável.
2. O frontend continua consumindo eventos normalizados.
3. Mudança principal ocorre internamente (coordenação e execução).

### 8.2 Integrações alvo
1. Runtime registra memória por agente (user/assistant).
2. Orquestrador injeta memória recuperada no prompt do Reasoning Engine.
3. Decomposition pipeline passa a consumir memória histórica relevante.

---

## 9. Segurança e confiabilidade

1. Validar envelopes com schema estrito.
2. Sanitização de payloads antes de tool execution.
3. TTL e deduplicação por `message_id`.
4. Retry com limites + DLQ.
5. Timeout por classe de operação (`sync`, `async`, `tool`).
6. Correlação de logs por `conversation_id` e `correlation_id`.

---

## 10. Observabilidade

1. Métricas:
   - latência sync
   - tempo em fila async
   - taxa de fallback sync->async
   - taxa de retry e DLQ
   - cobertura de memória e taxa de recuperação
2. Eventos:
   - `reasoning_request_started`
   - `reasoning_request_completed`
   - `memory_window_created`
   - `memory_context_loaded`
   - `task_deferred_to_async`

---

## 11. Roadmap de implementação (incremental)

### Fase 1 - Fundações
1. Criar `TaskBus` abstrato e bridge para RabbitMQ.
2. Estruturar schemas `spade.v1`.
3. Provisionar infraestrutura XMPP (Prosody) e Rabbit.

### Fase 2 - SPADE runtime
1. Implementar `SpadeOrchestratorAgent`.
2. Implementar capability agents.
3. Estabelecer protocolo de mensagens interagentes.

### Fase 3 - Reasoning Engine
1. Encapsular LangGraph/LangChain como serviço cognitivo.
2. Habilitar execução híbrida (sync/async).
3. Incluir fallback de latência.

### Fase 4 - Memória e RAG
1. Persistência por agente com cursor de 300k tokens.
2. Sumarização de janela + fatos.
3. Recuperação semântica no fluxo de raciocínio.

### Fase 5 - Hardening
1. Testes de carga e caos.
2. Observabilidade completa.
3. Ajustes finos de thresholds e custo/latência.

---

## 12. Critérios de sucesso

1. Agentes SPADE trocando mensagens via XMPP em produção.
2. Execução híbrida com melhora perceptível de latência no caminho curto.
3. Tarefas longas robustas em Rabbit com retry e DLQ.
4. Memória por agente com resumo confiável a cada 300k tokens.
5. Recuperação RAG com ganho de continuidade e redução de repetição.

---

## 13. Riscos e mitigação

1. **Complexidade operacional inicial**  
Mitigação: rollout por fases + feature flags.
2. **Inconsistência entre sync e async**  
Mitigação: contratos únicos e correlação obrigatória.
3. **Explosão de custo de contexto/memória**  
Mitigação: janelas fixas, compactação e políticas de retenção.
4. **Recall fraco de memória semântica**  
Mitigação: re-ranking híbrido (semântico + recência + fatos).

---

## 14. Estado atual após esta rodada

1. Memória por agente e recuperação RAG já iniciadas no backend atual.
2. Integração de contexto de memória no fluxo de raciocínio (orquestrador/decomposition) já conectada.
3. SPADE/XMPP/RabbitMQ ainda pendentes de implementação da camada de coordenação e transporte.

