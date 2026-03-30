# Roadmap das Próximas Fases - MindFlow Agentic Communication

## Estado Atual (30/03/2026)

### ✅ Fase 1: Infraestrutura — CONCLUÍDA

- Docker compose atualizado com Prosody, Redis, RabbitMQ
- Configuração Prosody criada (`docker/prosody/prosody.cfg.lua`)
- Ejabberd preservado como artefato futuro (`docker/ejabberd/ejabberd.yml`)

### ✅ Fase 2: Módulo de Comunicação SPADE/XMPP — CONCLUÍDA

- Estrutura `python/mindflow_backend/communication/` criada
- Protocolos XMPP e P2P
- Teams (in-memory) + TeamChat + TeamManager
- Connection manager com modo mock
- Services: XMPP, P2P, Team
- Circuit breaker base
- Schemas de configuração

### ✅ Fase 3: Quebra do AgentRuntime em Módulos — CONCLUÍDA

- `runtime/core/agent_runtime.py` — wrapper modular
- `runtime/routing/runtime_router.py` — resolução de modo de execução
- `runtime/streaming/stream_manager.py` — criação de eventos de stream
- `runtime/execution/executor.py` — todas as estratégias de execução
- `runtime/memory/memory_integration.py` — lifecycle de execução + dispatch de memória
- `runtime/__init__.py` — exports atualizados
- `stream.py` original (2289 linhas) preservado como implementação canônica

---

## 🔲 Próximas Fases

### Fase 4: Message Bus (Redis + RabbitMQ)

**Objetivo:** Implementar comunicação assíncrona entre agentes via message bus.

**Escopo:**

- Criar módulo `python/mindflow_backend/runtime/message_bus/`
- Implementar publisher/consumer para Redis (pub/sub para eventos em tempo real)
- Implementar publisher/consumer para RabbitMQ (filas para tarefas assíncronas)
- Definir protocolo de mensagens entre agentes (formato JSON padronizado)
- Integrar com o módulo de comunicação SPADE como fallback
- Eventos suportados:
  - `task_delegation` — orquestrador delega tarefa a agente especialista
  - `task_result` — agente retorna resultado
  - `memory_sync` — sincronização de contexto de memória
  - `team_broadcast` — mensagem para todos os membros de um team
  - `p2p_direct` — mensagem direta entre dois agentes

**Arquivos-alvo:**

- `python/mindflow_backend/runtime/message_bus/__init__.py`
- `python/mindflow_backend/runtime/message_bus/redis_bus.py`
- `python/mindflow_backend/runtime/message_bus/rabbitmq_bus.py`
- `python/mindflow_backend/runtime/message_bus/protocol.py`
- `python/mindflow_backend/runtime/message_bus/adapter.py` (ponte SPADE ↔ message bus)

---

### Fase 5: Integrar Circuit Breakers nos Serviços

**Objetivo:** Adicionar resiliência a todas as comunicações entre agentes.

**Escopo:**

- Integrar o `CircuitBreaker` criado em `communication/circuit_breaker/`
- Aplicar em:
  - `XMPPService` — proteção contra desconexão do servidor XMPP
  - `P2PService` — proteção contra falha de comunicação direta
  - `TeamService` — proteção contra falha de MUC
  - Message bus publishers (Redis e RabbitMQ)
- Configurar thresholds:
  - `failure_threshold`: 5 falhas consecutivas
  - `recovery_timeout`: 30 segundos
  - `half_open_max_calls`: 3 tentativas em estado half-open
- Implementar fallback: quando circuito abre, usar orquestração manual como degradação graceful
- Adicionar métricas de circuit breaker em logs estruturados

**Arquivos-alvo:**

- `python/mindflow_backend/communication/services/xmpp_service.py` — adicionar decorator @circuit_breaker
- `python/mindflow_backend/communication/services/p2p_service.py` — adicionar decorator
- `python/mindflow_backend/communication/services/team_service.py` — adicionar decorator
- `python/mindflow_backend/runtime/message_bus/` — adicionar em publishers

---

### Fase 6: Completar gRPC AgentRuntimeService

**Objetivo:** Serviço gRPC completo para comunicação estruturada entre containers de agentes.

**Escopo:**

- Completar o `AgentRuntimeService` (identificado como muito incompleto)
- Definir protobuf para:
  - `StreamChat` — streaming bidirecional
  - `CreateExecution` — criar execução remota
  - `GetExecutionStatus` — consultar status
  - `PauseExecution` — pausar execução
  - `ResumeExecution` — retomar execução
  - `SendMessage` — mensagem entre agentes
- Implementar server gRPC que expõe o AgentRuntime
- Implementar client gRPC para agentes remotos
- Service discovery (descobrir agentes disponíveis via gRPC reflection ou registry)

**Arquivos-alvo:**

- `python/mindflow_backend/grpc/` (diretório)
- `python/mindflow_backend/grpc/protos/agent_runtime.proto`
- `python/mindflow_backend/grpc/server.py`
- `python/mindflow_backend/grpc/client.py`
- `python/mindflow_backend/grpc/interceptors/` (logging, auth, circuit breaker)

---

### Fase 7: Integração com Orquestração Atual

**Objetivo:** Conectar todo o novo sistema de comunicação com a orquestração existente.

**Escopo:**

- Atualizar `IntelligentRouter` para usar message bus para delegação
- Atualizar `simple_flow` para emitir eventos no message bus
- Integrar tools de orquestração com comunicação SPADE
- Conectar runtime modular com runtime antigo via compatibility shim
- Persistir teams no PostgreSQL (decisão confirmada pelo usuário)
- Implementar agent discovery (encontrar agentes disponíveis)
- Testes de integração end-to-end

**Arquivos-alvo:**

- `python/mindflow_backend/orchestrator/routing/intelligent_router.py`
- `python/mindflow_backend/graphs/implementations/orchestrator/simple_flow.py`
- `python/mindflow_backend/communication/teams/team_manager.py` — adicionar persistência PostgreSQL
- `python/mindflow_backend/runtime/streaming/stream.py` — compatibility shim para novo runtime
- `python/tests/integration/` — testes de integração

---

## Ordem de Prioridade Confirmada

1. ✅ Infraestrutura (docker)
2. ✅ Comunicação SPADE/XMPP
3. ✅ Quebra do AgentRuntime
4. 🔲 Message Bus (Redis + RabbitMQ)
5. 🔲 Circuit Breakers
6. 🔲 gRPC AgentRuntimeService
7. 🔲 Integração com orquestração atual

## Decisões Arquiteturais

- **XMPP Server**: Prosody em desenvolvimento, ejabberd em produção
- **Agentes**: Um por container
- **Teams**: Persistidos no PostgreSQL (ainda in-memory)
- **Fallback**: Orquestração manual quando comunicação falha
- **Novos agentes**: SPADE em paralelo aos existentes
- **Compatibilidade**: stream.py original preservado até paridade completa
