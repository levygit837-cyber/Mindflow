# Diagrama de Fluxo do Sistema de Agentes MindFlow

## Fluxo Principal de Execução

```mermaid
graph TD
    A[Usuário] --> B[API FastAPI]
    B --> C[Router]
    C --> D[Orchestrator]
    
    D --> E[route_node]
    E --> F{Análise de Intent}
    F --> G[Seleção de Agente]
    G --> H{Modo de Pensamento}
    
    H -->|Standard| I[execute_node - Direct]
    H -->|Decomposition| J[execute_node - Pipeline]
    
    I --> K[Agent + Tools]
    J --> L[Task Pipeline]
    
    L --> M[Tasker.decompose]
    M --> N[Scheduler.order]
    N --> O[Resolver.resolve]
    O --> P[Synthesizer.synthesize]
    
    K --> Q[LLM Invocation]
    P --> Q
    
    Q --> R[respond_node]
    R --> S[Stream Events]
    S --> T[Resposta ao Usuário]
    
    U[Memory Service] --> E
    U --> K
    U --> O
    
    V[Tool Registry] --> K
    W[Sandbox] --> K
```

## Arquitetura de Componentes

```mermaid
graph TB
    subgraph "Camada de API"
        A1[FastAPI Server]
        A2[gRPC Server]
        A3[Middleware Layer]
    end
    
    subgraph "Camada de Orquestração"
        O1[Orchestrator Graph]
        O2[Intelligent Router]
        O3[Complexity Scorer]
    end
    
    subgraph "Sistema de Agentes"
        AG1[Agent Registry]
        AG2[Specialists]
        AG3[Personalities]
        AG4[Tool Registry]
    end
    
    subgraph "Agentes Especialistas"
        E1[Analyst]
        E2[Coder]
        E3[Researcher]
        E4[Security]
        E5[Review]
        E6[Architecture]
        E7[Creative]
        E8[Deep Analysis]
    end
    
    subgraph "Sistema de Memória"
        M1[Memory Service]
        M2[Vector Store]
        M3[Embeddings]
        M4[Context Manager]
    end
    
    subgraph "Sistema de Ferramentas"
        T1[Web Tools]
        T2[Filesystem Tools]
        T3[Code Tools]
        T4[System Tools]
        T5[Sandbox Environment]
    end
    
    subgraph "Armazenamento"
        S1[PostgreSQL]
        S2[Redis Cache]
        S3[File System]
    end
    
    A1 --> O1
    A2 --> O1
    A3 --> O1
    
    O1 --> AG1
    O2 --> AG1
    O3 --> AG1
    
    AG1 --> AG2
    AG2 --> E1
    AG2 --> E2
    AG2 --> E3
    AG2 --> E4
    AG2 --> E5
    AG2 --> E6
    AG2 --> E7
    AG2 --> E8
    
    AG4 --> T1
    AG4 --> T2
    AG4 --> T3
    AG4 --> T4
    AG4 --> T5
    
    M1 --> O1
    M2 --> M1
    M3 --> M1
    M4 --> M1
    
    S1 --> M1
    S2 --> M1
    S3 --> M1
```

## Fluxo de Decisão do Orquestrador

```mermaid
graph TD
    A[Mensagem do Usuário] --> B[Análise Semântica]
    B --> C{Intent Detectada}
    
    C -->|Programação| D[Coder Agent]
    C -->|Análise| E[Analyst Agent]
    C -->|Pesquisa| F[Researcher Agent]
    C -->|Segurança| G[Security Agent]
    C -->|Revisão| H[Review Agent]
    C -->|Arquitetura| I[Architecture Agent]
    C -->|Criação| J[Creative Agent]
    C -->|Análise Profunda| K[Deep Analysis Agent]
    
    L[Cálculo de Complexidade] --> M{Complexidade}
    M -->|Baixa| N[Modo Standard]
    M -->|Média| N
    M -->|Alta| O[Modo Decomposition]
    
    N --> P[Execução Direta]
    O --> Q[Pipeline de Tarefas]
    
    D --> P
    E --> P
    F --> P
    G --> P
    H --> P
    I --> P
    J --> P
    K --> P
    
    Q --> R[Decomposição]
    R --> S[Agendamento]
    S --> T[Resolução]
    T --> U[Síntese]
    
    P --> V[Resposta]
    U --> V
```

## Pipeline de Decomposição de Tarefas

```mermaid
graph TD
    A[Tarefa Complexa] --> B[Tasker.decompose]
    B --> C[Main Task + SubTasks]
    
    C --> D[Scheduler.order]
    D --> E[Ordem de Execução]
    
    E --> F[Loop de Resolução]
    F --> G{Próxima SubTask}
    
    G --> H[Resolver.resolve]
    H --> I[Recuperação de Contexto]
    I --> J[Execução com Agente]
    J --> K[Validação]
    K --> L[Score]
    
    L --> M{Score Válido?}
    M -->|Sim| N[Adicionar à Lista]
    M -->|Não| O[Reprocessar]
    
    N --> P{Mais SubTasks?}
    P -->|Sim| G
    P -->|Não| Q[Synthesizer.synthesize]
    
    O --> H
    Q --> R[Resposta Final]
```

## Sistema de Memória e Contexto

```mermaid
graph LR
    A[Input do Usuário] --> B[Memory Service]
    B --> C[Vector Search]
    C --> D[Contexto Relevante]
    
    E[Histórico de Sessões] --> F[Embeddings]
    F --> G[Vector Store]
    G --> C
    
    H[Respostas Anteriores] --> I[Processamento]
    I --> J[Sumarização]
    J --> F
    
    D --> K[Agente Selecionado]
    K --> L[Processamento com Contexto]
    L --> M[Resposta Contextualizada]
    M --> N[Armazenar na Memória]
    N --> F
```

## Sistema de Ferramentas e Sandbox

```mermaid
graph TD
    A[Agente] --> B{Modo Sandbox}
    
    B -->|NONE| C[Sem Ferramentas]
    B -->|READ_ONLY| D[Ferramentas Leitura]
    B -->|FULL| E[Ferramentas Completas]
    
    D --> F[Web Search]
    D --> G[File Read]
    D --> H[System Info]
    
    E --> I[Web Search + Scrape]
    E --> J[File Operations]
    E --> K[Code Execution]
    E --> L[System Commands]
    
    F --> M[Safe Environment]
    I --> N[Controlled Environment]
    J --> N
    K --> N
    L --> N
    
    N --> O[Sandbox Manager]
    O --> P[Resource Limits]
    O --> Q[Security Rules]
    O --> R[Audit Log]
```

## Fluxo de Comunicação gRPC

```mermaid
graph TD
    A[Cliente gRPC] --> B[gRPC Server]
    B --> C[Interceptor Chain]
    
    C --> D[Auth Interceptor]
    C --> E[Logging Interceptor]
    C --> F[Metrics Interceptor]
    C --> G[Error Handler]
    
    D --> H[Service Layer]
    E --> H
    F --> H
    G --> H
    
    H --> I[Agent Runtime Service]
    I --> J[Orchestrator]
    J --> K[Agent Execution]
    
    K --> L[Response Stream]
    L --> M[Response Interceptor]
    M --> N[Compression]
    N --> O[Caching]
    O --> P[Cliente]
```

## Monitoramento e Observabilidade

```mermaid
graph TD
    A[Request] --> B[Middleware de Logging]
    B --> C[Request ID]
    C --> D[Session ID]
    D --> E[Agent Type]
    
    E --> F[Performance Metrics]
    F --> G[Response Time]
    G --> H[Memory Usage]
    H --> I[Tool Usage]
    
    I --> J[Metrics Collector]
    J --> K[Prometheus]
    J --> L[Custom Dashboard]
    
    M[Error Events] --> N[Error Handler]
    N --> O[Error Classification]
    O --> P[Alert System]
    P --> Q[Monitoring Service]
    
    L --> Q
    Q --> R[Alerts/Notifications]
```
