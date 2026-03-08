# Estrutura Completa do Projeto MindFlow Backend

## Visão Geral

Este documento mapeia toda a estrutura de pastas e arquivos do projeto `python/mindflow_backend/**`, fornecendo uma visão completa da arquitetura do sistema.

## Estrutura Principal

```
python/mindflow_backend/
├── __init__.py                    # Inicialização do pacote principal
├── main.py                        # Ponto de entrada principal da aplicação
├── agents/                        # Sistema de agentes inteligentes
├── api/                           # API REST e endpoints
├── chains/                        # Cadeias de processamento
├── config/                        # Configurações do sistema
├── decomposition/                 # Módulo de decomposição de tarefas
├── exceptions/                    # Tratamento de exceções
├── graphs/                        # Grafos de execução
├── grpc/                          # Implementação gRPC
├── infra/                         # Infraestrutura e middleware
├── memory/                        # Sistema de memória
├── memory_backup/                 # Backup de memória
├── nodes/                         # Nós do sistema
├── orchestrator/                  # Orquestrador principal
├── runtime/                       # Runtime de execução
├── schemas/                       # Esquemas de dados
├── services/                      # Serviços do sistema
├── storage/                       # Armazenamento de dados
├── utils/                         # Utilitários
└── workers/                       # Sistema de workers
```

## Detalhamento dos Módulos

### 1. agents/ - Sistema de Agentes Inteligentes

```
agents/
├── __init__.py                    # Exportações principais
├── _base.py                       # Classe base de agentes
├── _registry.py                   # Registro de agentes
├── node_registry.py               # Registro de nós
├── output_categorizer.py          # Categorizador de saídas
├── session_review_agent.py        # Agente de revisão de sessão
├── stream_event_queue.py          # Fila de eventos streaming
├── tools.py                       # Ferramentas básicas
├── context/                       # Contexto e recuperação
│   ├── __init__.py
│   ├── analyzer.py                # Analisador de contexto
│   ├── cache.py                   # Cache de contexto
│   ├── retriever.py               # Recuperação de contexto
│   └── vector_store.py            # Armazenamento vetorial
├── core/                          # Núcleo do sistema de agentes
│   ├── container.py               # Container de agentes
│   ├── exceptions.py              # Exceções específicas
│   ├── initialization.py         # Inicialização
│   └── interfaces.py             # Interfaces principais
├── interfaces/                    # Contratos e interfaces
│   ├── __init__.py
│   ├── SCHEMA_CONTRACT_MAPPING.md # Mapeamento de contratos
│   ├── validate_contracts.py      # Validação de contratos
│   ├── agents/                    # Interfaces de agentes
│   │   ├── __init__.py
│   │   ├── agent.py               # Interface base
│   │   ├── analyst.py             # Analista
│   │   ├── coder.py               # Programador
│   │   ├── reviewer.py            # Revisor
│   │   └── researcher.py          # Pesquisador
│   ├── api/                       # Interfaces API
│   │   ├── __init__.py
│   │   ├── chat.py                # Chat
│   │   ├── monitoring.py          # Monitoramento
│   │   └── streaming.py           # Streaming
│   ├── core/                      # Interfaces core
│   │   ├── __init__.py
│   │   ├── agent.py               # Agente principal
│   │   ├── personality.py         # Personalidade
│   │   ├── session.py             # Sessão
│   │   ├── streaming.py           # Streaming
│   │   ├── task.py                # Tarefas
│   │   └── tool.py                # Ferramentas
│   ├── infrastructure/            # Infraestrutura
│   │   ├── __init__.py
│   │   ├── logging.py             # Logging
│   │   └── monitoring.py          # Monitoramento
│   └── orchestrator/              # Orquestrador
│       ├── __init__.py
│       ├── core.py                # Núcleo
│       ├── delegation.py          # Delegação
│       ├── personality.py         # Personalidade
│       ├── session.py             # Sessão
│       ├── streaming.py           # Streaming
│       ├── task.py                # Tarefas
│       └── tools.py               # Ferramentas
├── personalities/                 # Personalidades pré-definidas
│   ├── __init__.py
│   ├── analyst.py                 # Analista
│   ├── coder.py                   # Programador
│   ├── orchestrator.py            # Orquestrador
│   └── researcher.py              # Pesquisador
├── personality/                   # Sistema de personalidade
│   ├── __init__.py
│   ├── cache.py                   # Cache de personalidades
│   ├── configuration.py          # Configuração
│   ├── dynamic_prompts.py         # Prompts dinâmicos
│   ├── rule_engine.py             # Motor de regras
│   ├── selector.py                # Seletor
│   └── sub_personalities.py       # Sub-personalidades
├── prompts/                       # Sistema de prompts
│   ├── __init__.py
│   ├── base.py                    # Base de prompts
│   ├── backup/                    # Backup de prompts
│   │   ├── __init__.py
│   │   ├── analyst_backup.py      # Backup analista
│   │   ├── coder_backup.py        # Backup programador
│   │   ├── reviewer_backup.py     # Backup revisor
│   │   └── researcher_backup.py   # Backup pesquisador
│   ├── composite/                  # Prompts compostos
│   │   ├── __init__.py
│   │   ├── builder.py             # Construtor
│   │   ├── manager.py             # Gerenciador
│   │   ├── optimizer.py           # Otimizador
│   │   └── validator.py           # Validador
│   ├── core/                      # Núcleo de prompts
│   │   ├── __init__.py
│   │   ├── builder.py             # Construtor
│   │   ├── manager.py             # Gerenciador
│   │   ├── optimizer.py           # Otimizador
│   │   ├── renderer.py            # Renderizador
│   │   └── validator.py           # Validador
│   └── specialized/               # Prompts especializados
│       ├── __init__.py
│       ├── analyst.py             # Analista
│       ├── coder.py               # Programador
│       ├── orchestrator.py        # Orquestrador
│       ├── researcher.py          # Pesquisador
│       ├── reviewer.py            # Revisor
│       ├── session_review.py      # Revisão de sessão
│       ├── task_decomposition.py  # Decomposição de tarefas
│       ├── tool_selection.py      # Seleção de ferramentas
│       └── troubleshooting.py     # Resolução de problemas
├── research/                      # Sistema de pesquisa
│   ├── __init__.py
│   ├── action_trail.py            # Rastreamento de ações
│   ├── enhanced_researcher.py     # Pesquisador aprimorado
│   ├── pinchtab_service.py        # Serviço PinchTab
│   ├── pitchtab_monitor.py        # Monitor PitchTab
│   ├── query_engine.py            # Motor de consultas
│   ├── result_synthesizer.py      # Sintetizador de resultados
│   ├── source_trust_engine.py     # Motor de confiança
│   └── utils/                     # Utilitários de pesquisa
│       ├── __init__.py
│       ├── cache.py               # Cache
│       ├── logger.py              # Logger
│       └── validator.py           # Validador
└── tools/                         # Ferramentas dos agentes
    ├── __init__.py
    ├── base/                      # Ferramentas base
    │   ├── __init__.py
    │   ├── browser.py             # Navegador
    │   ├── code.py                # Código
    │   ├── filesystem.py          # Sistema de arquivos
    │   └── system.py              # Sistema
    ├── browser_search.py          # Busca na web
    ├── code/                      # Ferramentas de código
    │   └── execution.py           # Execução
    ├── filesystem/                # Sistema de arquivos
    │   ├── __init__.py
    │   ├── manager.py             # Gerenciador
    │   ├── operations.py          # Operações
    │   └── watcher.py             # Observador
    ├── research/                  # Ferramentas de pesquisa
    │   └── enhanced.py            # Pesquisa aprimorada
    ├── sandbox.py                 # Sandbox
    ├── system/                    # Ferramentas de sistema
    │   ├── __init__.py
    │   ├── monitoring.py          # Monitoramento
    │   ├── performance.py         # Performance
    │   └── resources.py           # Recursos
    └── web/                       # Ferramentas web
        ├── __init__.py
        ├── crawler.py             # Rastreador
        ├── scraper.py             # Extrator
        ├── search.py              # Busca
        └── validator.py           # Validador
```

### 2. api/ - API REST e Endpoints

```
api/
├── __init__.py                    # Inicialização
├── docs.py                        # Documentação da API
├── router.py                      # Router principal
├── sse.py                         # Server-Sent Events
├── controllers/                   # Controladores
│   ├── __init__.py
│   ├── agent_controller.py        # Controlador de agentes
│   ├── base_controller.py        # Controlador base
│   ├── orchestration_controller.py # Controlador de orquestração
│   ├── provider_controller.py      # Controlador de provedores
│   └── session_controller.py      # Controlador de sessão
├── interfaces/                    # Interfaces da API
│   ├── __init__.py
│   ├── agent.py                   # Interface de agente
│   ├── chat.py                    # Interface de chat
│   └── orchestration.py           # Interface de orquestração
├── middleware/                    # Middleware
│   ├── __init__.py
│   ├── auth.py                    # Autenticação
│   ├── cors.py                    # CORS
│   ├── error_handler.py           # Tratamento de erros
│   └── logging.py                 # Logging
├── schemas/                       # Esquemas da API
│   ├── __init__.py
│   ├── agent.py                   # Esquema de agente
│   ├── chat.py                    # Esquema de chat
│   ├── common.py                  # Esquemas comuns
│   └── session.py                 # Esquema de sessão
├── services/                      # Serviços da API
│   ├── __init__.py
│   ├── agent_service.py           # Serviço de agentes
│   ├── chat_service.py            # Serviço de chat
│   ├── orchestration_service.py   # Serviço de orquestração
│   └── session_service.py         # Serviço de sessão
└── v1/                            # Versão 1 da API
    ├── __init__.py
    ├── agent.py                   # Endpoints de agentes
    ├── chat.py                    # Endpoints de chat
    ├── config.py                  # Endpoints de configuração
    ├── legacy.py                  # Endpoints legados
    ├── metrics.py                 # Endpoints de métricas
    ├── monitoring.py              # Endpoints de monitoramento
    ├── orchestration.py           # Endpoints de orquestração
    ├── performance.py             # Endpoints de performance
    ├── providers.py               # Endpoints de provedores
    └── resilience.py              # Endpoints de resiliência
```

### 3. chains/ - Cadeias de Processamento

```
chains/
├── __init__.py                    # Inicialização
├── base/                          # Cadeias base
│   ├── __init__.py
│   ├── chain.py                   # Cadeia base
│   ├── factory.py                 # Fábrica de cadeias
│   └── registry.py                # Registro de cadeias
├── builders/                      # Construtores de cadeias
└── templates/                     # Templates de cadeias
```

### 4. config/ - Configurações do Sistema

```
config/
├── __init__.py                    # Inicialização
├── agents.py                      # Configuração de agentes
└── personality_rules.py           # Regras de personalidade
```

### 5. decomposition/ - Decomposição de Tarefas

```
decomposition/
├── __init__.py                    # Inicialização
├── engine.py                      # Motor de decomposição
├── context/                       # Contexto de decomposição
│   └── __init__.py
├── pipeline/                      # Pipeline de decomposição
│   ├── __init__.py
│   ├── decomposer.py              # Decompositor
│   ├── resolver.py                # Resolvedor
│   ├── scheduler.py              # Agendador
│   ├── scorer.py                  # Avaliador
│   └── synthesizer.py             # Sintetizador
├── scoring/                       # Sistema de pontuação
│   └── __init__.py
└── utils/                         # Utilitários
    └── __init__.py
```

### 6. exceptions/ - Tratamento de Exceções

```
exceptions/
├── __init__.py                    # Inicialização
├── agents.py                      # Exceções de agentes
├── agents/                        # Exceções específicas de agentes
│   └── __init__.py
├── api/                           # Exceções da API
│   ├── __init__.py
│   ├── auth.py                    # Autenticação
│   ├── chat.py                    # Chat
│   ├── orchestration.py           # Orquestração
│   └── session.py                 # Sessão
├── base/                          # Exceções base
│   ├── __init__.py
│   ├── core.py                    # Núcleo
│   ├── infrastructure.py          # Infraestrutura
│   └── validation.py              # Validação
├── external/                      # Exceções externas
│   ├── __init__.py
│   ├── api.py                     # API externa
│   ├── database.py                # Banco de dados
│   ├── network.py                 # Rede
│   └── storage.py                 # Armazenamento
├── infrastructure/                 # Exceções de infraestrutura
│   ├── __init__.py
│   ├── cache.py                   # Cache
│   ├── database.py                # Banco de dados
│   ├── logging.py                 # Logging
│   ├── monitoring.py              # Monitoramento
│   └── storage.py                 # Armazenamento
├── orchestrator/                  # Exceções do orquestrador
│   ├── __init__.py
│   ├── delegation.py              # Delegação
│   ├── personality.py             # Personalidade
│   ├── session.py                 # Sessão
│   └── task.py                    # Tarefas
├── runtime/                       # Exceções de runtime
│   ├── __init__.py
│   ├── agent.py                   # Agentes
│   ├── execution.py               # Execução
│   ├── monitoring.py              # Monitoramento
│   └── streaming.py               # Streaming
├── storage/                       # Exceções de armazenamento
│   ├── __init__.py
│   ├── database.py                # Banco de dados
│   ├── file.py                    # Arquivos
│   ├── memory.py                  # Memória
│   └── vector.py                  # Vetores
└── validation/                    # Exceções de validação
    ├── __init__.py
    ├── agents.py                  # Agentes
    ├── config.py                  # Configuração
    ├── input.py                   # Entrada
    └── schema.py                  # Esquema
```

### 7. graphs/ - Grafos de Execução

```
graphs/
├── __init__.py                    # Inicialização
├── factory.py                     # Fábrica de grafos
├── base/                          # Grafos base
│   ├── __init__.py
│   ├── graph.py                   # Grafo base
│   ├── node.py                    # Nó base
│   └── edge.py                    # Aresta base
├── chains/                        # Cadeias em grafos
└── orchestrator/                  # Orquestrador em grafos
    ├── __init__.py
    └── graph.py                   # Grafo do orquestrador
```

### 8. grpc/ - Implementação gRPC

```
grpc/
├── README.md                      # Documentação gRPC
├── __init__.py                    # Inicialização
├── client.py                      # Cliente gRPC
├── server.py                      # Servidor gRPC
├── config/                        # Configuração gRPC
│   ├── __init__.py
│   ├── config.py                  # Configuração principal
│   ├── dynamic/                   # Configuração dinâmica
│   │   ├── __init__.py
│   │   ├── api.py                 # API de configuração
│   │   ├── manager.py             # Gerenciador
│   │   ├── storage.py             # Armazenamento
│   │   ├── validator.py           # Validador
│   │   └── watcher.py             # Observador
│   ├── features/                  # Recursos
│   │   └── __init__.py
│   └── profiles/                  # Perfis
│       └── __init__.py
├── generated/                     # Código gerado
│   ├── __init__.py
│   ├── mindflow_backend_pb2.py    # Protobuf Python
│   └── mindflow_backend_pb2_grpc.py # gRPC Python
├── interceptors/                  # Interceptadores
│   ├── __init__.py
│   └── error_handler.py           # Tratamento de erros
├── interfaces/                    # Interfaces gRPC
│   ├── __init__.py
│   ├── client.py                  # Interface cliente
│   └── server.py                  # Interface servidor
├── monitoring/                    # Monitoramento
│   ├── __init__.py
│   ├── metrics.py                 # Métricas
│   └── tracing.py                 # Rastreamento
├── performance/                   # Performance
│   ├── __init__.py
│   ├── caching/                   # Cache
│   │   ├── __init__.py
│   │   ├── client_cache.py        # Cache cliente
│   │   ├── server_cache.py        # Cache servidor
│   │   └── strategies.py          # Estratégias
│   ├── compression/               # Compressão
│   │   ├── __init__.py
│   │   ├── client_compression.py  # Compressão cliente
│   │   ├── server_compression.py  # Compressão servidor
│   │   └── strategies.py          # Estratégias
│   ├── load_balancing/            # Balanceamento
│   │   ├── __init__.py
│   │   ├── client_lb.py           # LB cliente
│   │   └── server_lb.py           # LB servidor
│   ├── monitoring/                # Monitoramento
│   │   ├── __init__.py
│   │   ├── client_monitoring.py   # Monitoramento cliente
│   │   └── server_monitoring.py   # Monitoramento servidor
│   ├── optimization/              # Otimização
│   │   ├── __init__.py
│   │   ├── batch_processing.py    # Processamento em lote
│   │   ├── connection_pooling.py  # Pool de conexões
│   │   └── streaming.py           # Streaming
│   └── pooling/                   # Pooling
│       ├── __init__.py
│       ├── client_pool.py         # Pool cliente
│       ├── connection_pool.py     # Pool de conexões
│       ├── server_pool.py         # Pool servidor
│       └── thread_pool.py         # Pool de threads
├── proto/                         # Protocol Buffers
│   └── mindflow_backend.proto      # Definição protobuf
├── resilience/                    # Resiliência
│   ├── __init__.py
│   ├── circuit_breaker.py         # Circuit Breaker
│   ├── retry.py                   # Retry
│   ├── timeout.py                 # Timeout
│   └── utils.py                   # Utilitários
├── services/                      # Serviços gRPC
│   ├── __init__.py
│   └── agent_runtime_service.py    # Serviço de runtime
└── resilience/                    # Resiliência (repetido)
    ├── __init__.py
    ├── circuit_breaker.py         # Circuit Breaker
    ├── retry.py                   # Retry
    ├── timeout.py                 # Timeout
    └── utils.py                   # Utilitários
```

### 9. infra/ - Infraestrutura e Middleware

```
infra/
├── __init__.py                    # Inicialização
├── config.py                      # Configuração de infra
├── logging.py                     # Sistema de logging
├── middleware/                    # Middleware
│   ├── __init__.py
│   ├── auth.py                    # Autenticação
│   ├── cors.py                    # CORS
│   ├── error_handler.py           # Tratamento de erros
│   └── rate_limiting.py           # Rate limiting
├── normalizer.py                  # Normalizador
├── redis.py                       # Configuração Redis
├── resilience.py                  # Resiliência
└── sanitizer.py                   # Sanitização
```

### 10. memory/ - Sistema de Memória

```
memory/
├── __init__.py                    # Inicialização
├── api/                           # API de memória
│   ├── __init__.py
│   ├── manager.py                 # Gerenciador
│   ├── operations.py              # Operações
│   ├── retrieval.py               # Recuperação
│   └── storage.py                 # Armazenamento
├── core/                          # Núcleo de memória
│   ├── __init__.py
│   ├── base.py                    # Base
│   ├── cache.py                   # Cache
│   ├── manager.py                 # Gerenciador
│   ├── storage.py                 # Armazenamento
│   └── types.py                   # Tipos
├── embeddings/                    # Embeddings
│   ├── __init__.py
│   ├── cache.py                   # Cache
│   ├── generator.py               # Gerador
│   ├── manager.py                 # Gerenciador
│   └── storage.py                 # Armazenamento
├── retrieval/                     # Recuperação
│   ├── __init__.py
│   ├── base.py                    # Base
│   ├── semantic.py                # Semântica
│   ├── vector.py                  # Vetorial
│   └── hybrid.py                  # Híbrida
├── storage/                       # Armazenamento
│   ├── __init__.py
│   ├── cache.py                   # Cache
│   ├── database.py                # Banco de dados
│   ├── file.py                    # Arquivo
│   └── vector.py                  # Vetorial
├── utils/                         # Utilitários
│   ├── __init__.py
│   ├── logger.py                  # Logger
│   ├── metrics.py                 # Métricas
│   └── validation.py              # Validação
└── windows/                       # Janelas de memória
    ├── __init__.py
    ├── base.py                    # Base
    ├── manager.py                 # Gerenciador
    ├── policy.py                  # Política
    └── storage.py                 # Armazenamento
```

### 11. nodes/ - Nós do Sistema

```
nodes/
├── __init__.py                    # Inicialização
├── registry.py                    # Registro de nós
├── agents/                        # Nós de agentes (vazio)
├── base/                          # Nós base
│   ├── __init__.py
│   ├── node.py                    # Nó base
│   ├── processor.py               # Processador
│   └── transformer.py             # Transformador
├── control/                       # Nós de controle (vazio)
├── orchestrator/                  # Nós do orquestrador
│   ├── __init__.py
│   ├── decision.py                # Decisão
│   ├── execution.py               # Execução
│   ├── monitoring.py              # Monitoramento
│   └── routing.py                 # Roteamento
```

### 12. orchestrator/ - Orquestrador Principal

```
orchestrator/
├── __init__.py                    # Inicialização
├── graph.py                       # Grafo do orquestrador
├── context/                       # Contexto do orquestrador
│   ├── __init__.py
│   ├── manager.py                 # Gerenciador
│   ├── session.py                 # Sessão
│   ├── state.py                   # Estado
│   └── tracker.py                 # Rastreador
├── decomposition/                 # Decomposição
│   └── __init__.py
├── delegation/                    # Delegação
│   ├── __init__.py
│   ├── manager.py                 # Gerenciador
│   └── router.py                  # Roteador
└── routing/                       # Roteamento
    ├── __init__.py
    ├── decision.py                # Decisão
    ├── optimizer.py               # Otimizador
    ├── router.py                  # Roteador
    └── strategy.py                # Estratégia
```

### 13. runtime/ - Runtime de Execução

```
runtime/
├── __init__.py                    # Inicialização
├── agents/                        # Runtime de agentes (vazio)
├── core/                          # Core runtime (vazio)
├── execution/                     # Execução
│   └── __init__.py
├── monitoring/                    # Monitoramento
│   └── __init__.py
├── processing/                    # Processamento
│   ├── __init__.py
│   ├── batch.py                   # Processamento em lote
│   ├── stream.py                  # Streaming
│   └── worker.py                  # Worker
├── providers/                     # Provedores
│   └── __init__.py
├── registry/                      # Registro
│   └── __init__.py
├── streaming/                     # Streaming
│   ├── __init__.py
│   ├── client.py                  # Cliente
│   ├── manager.py                 # Gerenciador
│   ├── server.py                  # Servidor
│   └── utils.py                   # Utilitários
└── utils/                         # Utilitários
    └── __init__.py
```

### 14. schemas/ - Esquemas de Dados

```
schemas/
├── __init__.py                    # Inicialização
├── agents/                        # Esquemas de agentes
│   ├── __init__.py
│   ├── agent.py                   # Agente
│   ├── analyst.py                 # Analista
│   ├── coder.py                   # Programador
│   ├── researcher.py              # Pesquisador
│   └── reviewer.py                # Revisor
├── chat/                          # Esquemas de chat
│   ├── __init__.py
│   └── message.py                 # Mensagem
├── config/                        # Esquemas de configuração
│   ├── __init__.py
│   ├── agent.py                   # Configuração de agente
│   └── system.py                  # Configuração do sistema
├── core/                          # Esquemas core
│   ├── __init__.py
│   └── base.py                    # Base
├── errors/                        # Esquemas de erros
│   ├── __init__.py
│   ├── agent.py                   # Erros de agente
│   ├── api.py                     # Erros de API
│   ├── base.py                    # Erros base
│   └── system.py                  # Erros do sistema
├── grpc/                          # Esquemas gRPC
│   ├── __init__.py
│   ├── config.py                  # Configuração
│   ├── message.py                 # Mensagem
│   ├── request.py                 # Requisição
│   └── response.py                # Resposta
├── orchestration/                 # Esquemas de orquestração
│   ├── __init__.py
│   ├── agent.py                   # Agente
│   ├── delegation.py              # Delegação
│   ├── personality.py             # Personalidade
│   ├── session.py                 # Sessão
│   ├── task.py                    # Tarefa
│   └── tool.py                    # Ferramenta
└── session/                       # Esquemas de sessão
    ├── __init__.py
    ├── context.py                 # Contexto
    ├── memory.py                  # Memória
    ├── review.py                  # Revisão
    ├── state.py                   # Estado
    └── stream.py                  # Stream
```

### 15. services/ - Serviços do Sistema

```
services/
├── __init__.py                    # Inicialização
├── multilingual_embeddings.py     # Embeddings multilíngues
├── session_retriever.py           # Recuperação de sessão
├── session_review_service.py      # Serviço de revisão de sessão
├── vector_manager.py              # Gerenciador vetorial
├── communication/                 # Comunicação
│   ├── __init__.py
│   ├── grpc_client.py             # Cliente gRPC
│   ├── http_client.py             # Cliente HTTP
│   └── websocket_client.py       # Cliente WebSocket
├── context/                       # Contexto
│   ├── __init__.py
│   ├── analyzer.py                # Analisador
│   ├── manager.py                 # Gerenciador
│   ├── retriever.py               # Recuperador
│   └── storage.py                 # Armazenamento
├── core/                          # Serviços core
│   ├── __init__.py
│   ├── agent_service.py           # Serviço de agentes
│   ├── orchestrator_service.py    # Serviço do orquestrador
│   ├── session_service.py         # Serviço de sessão
│   ├── task_service.py            # Serviço de tarefas
│   └── tool_service.py            # Serviço de ferramentas
├── interfaces/                    # Interfaces de serviços
│   ├── __init__.py
│   ├── agent.py                   # Interface de agente
│   ├── communication.py           # Interface de comunicação
│   ├── context.py                 # Interface de contexto
│   ├── monitoring.py              # Interface de monitoramento
│   ├── orchestration.py           # Interface de orquestração
│   └── storage.py                 # Interface de armazenamento
├── monitoring/                    # Monitoramento
│   ├── __init__.py
│   ├── metrics.py                 # Métricas
│   ├── performance.py             # Performance
│   └── tracing.py                 # Rastreamento
└── orchestration/                 # Orquestração
    ├── __init__.py
    ├── agent_manager.py           # Gerenciador de agentes
    ├── delegation_service.py      # Serviço de delegação
    ├── personality_service.py     # Serviço de personalidade
    └── task_scheduler.py          # Agendador de tarefas
```

### 16. storage/ - Armazenamento de Dados

```
storage/
├── __init__.py                    # Inicialização
├── kuzudb/                        # KuzuDB
│   ├── __init__.py
│   └── connection.py              # Conexão
├── langgraph/                     # LangGraph
│   ├── __init__.py
│   └── storage.py                 # Armazenamento
├── postgresql/                    # PostgreSQL
│   ├── __init__.py
│   ├── connection.py              # Conexão
│   ├── migrations/                # Migrações
│   │   ├── __init__.py
│   │   ├── versions/              # Versões
│   │   │   ├── __init__.py
│   │   │   ├── 001_initial.py     # Migração inicial
│   │   │   ├── 002_add_sessions.py # Adicionar sessões
│   │   │   ├── 003_add_agents.py  # Adicionar agentes
│   │   │   ├── 004_add_tasks.py   # Adicionar tarefas
│   │   │   ├── 005_add_memory.py  # Adicionar memória
│   │   │   ├── 006_add_metrics.py # Adicionar métricas
│   │   │   ├── 007_add_indexes.py # Adicionar índices
│   │   │   ├── 008_add_grpc.py    # Adicionar gRPC
│   │   │   ├── 009_add_performance.py # Adicionar performance
│   │   │   └── 010_add_monitoring.py # Adicionar monitoramento
│   │   ├── alembic.ini            # Configuração Alembic
│   │   ├── env.py                 # Ambiente
│   │   ├── script.py.mako         # Template
│   │   └── README.md              # Documentação
│   ├── models.py                  # Modelos
│   └── repositories.py            # Repositórios
└── utils/                         # Utilitários
    ├── __init__.py
    └── migrations.py              # Migrações
```

### 17. utils/ - Utilitários

```
utils/
└── error_handling.py              # Tratamento de erros
```

### 18. workers/ - Sistema de Workers

```
workers/
├── __init__.py                    # Inicialização
├── main.py                        # Principal
├── agents/                        # Workers de agentes
│   ├── __init__.py
│   ├── agent_worker.py            # Worker de agente
│   ├── coder_worker.py            # Worker programador
│   ├── researcher_worker.py        # Worker pesquisador
│   ├── analyst_worker.py          # Worker analista
│   └── reviewer_worker.py         # Worker revisor
├── archive/                       # Arquivo
│   ├── __init__.py
│   ├── archiver.py                # Arquivador
│   ├── cleaner.py                 # Limpeza
│   ├── compressor.py              # Compressor
│   └── storage.py                 # Armazenamento
├── base/                          # Base
│   ├── __init__.py
│   ├── worker.py                  # Worker base
│   ├── manager.py                 # Gerenciador
│   └── scheduler.py               # Agendador
├── config/                        # Configuração
│   ├── __init__.py
│   ├── agent_config.py            # Configuração de agentes
│   ├── system_config.py          # Configuração do sistema
│   └── worker_config.py           # Configuração de workers
├── infrastructure/                # Infraestrutura
│   ├── __init__.py
│   ├── monitoring.py              # Monitoramento
│   ├── performance.py             # Performance
│   ├── resilience.py              # Resiliência
│   └── scaling.py                 # Escalabilidade
├── research/                      # Pesquisa
│   ├── __init__.py
│   ├── research_worker.py         # Worker de pesquisa
│   ├── task_processor.py          # Processador de tarefas
│   └── result_collector.py        # Coletor de resultados
├── system/                        # Sistema
│   ├── __init__.py
│   ├── health_checker.py          # Verificação de saúde
│   ├── maintenance.py             # Manutenção
│   ├── monitor.py                 # Monitor
│   └── scheduler.py               # Agendador
└── tasks/                         # Tarefas
    ├── __init__.py
    ├── agent_tasks.py             # Tarefas de agentes
    ├── system_tasks.py            # Tarefas do sistema
    ├── maintenance_tasks.py       # Tarefas de manutenção
    └── research_tasks.py          # Tarefas de pesquisa
```

## Resumo Estatístico

- **Total de diretórios principais**: 18
- **Total de subdiretórios**: ~200+
- **Total de arquivos Python**: ~300+
- **Módulos mais complexos**: agents/, grpc/, services/, storage/
- **Sistemas independentes**: memory/, workers/, orchestrator/
- **Infraestrutura completa**: api/, grpc/, infra/, storage/

## Principais Características

1. **Arquitetura Modular**: Sistema bem dividido em módulos independentes
2. **Sistema de Agentes**: Completo com personalidades e ferramentas
3. **gRPC Implementado**: Comunicação eficiente com performance
4. **Sistema de Memória**: Armazenamento vetorial e cache
5. **Orquestração Avançada**: Decomposição e delegação de tarefas
6. **API REST Completa**: Endpoints bem estruturados
7. **Sistema de Workers**: Processamento distribuído
8. **Monitoramento**: Métricas e performance integradas

## Tecnologias Principais

- **FastAPI**: Framework web para API REST
- **gRPC**: Comunicação de alta performance
- **PostgreSQL**: Banco de dados principal
- **Redis**: Cache e sessões
- **LangChain**: Framework de LLM
- **Vector Stores**: Armazenamento vetorial
- **Alembic**: Migrações de banco

---

*Documento gerado automaticamente em 2026-03-06*
*Total de diretórios mapeados: 18 principais + ~200 subdiretórios*
