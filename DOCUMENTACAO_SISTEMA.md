# Documentação do Sistema MindFlow - Arquitetura e Fluxo

## Visão Geral

O MindFlow é uma plataforma avançada de orquestração e gerenciamento de agentes inteligentes construída em Python com FastAPI. O sistema utiliza uma arquitetura modular baseada em especialistas, com um orquestrador central que coordena a execução de diferentes tipos de agentes para processar solicitações dos usuários.

## Estrutura Principal do Sistema

### 1. Ponto de Entrada (`main.py`)

O sistema é inicializado através do `main.py`, que configura:

- **FastAPI**: Servidor web principal na porta configurada
- **gRPC**: Servidor secundário para comunicação de alto desempenho
- **Middleware**: Camadas de segurança, CORS, rate limiting, cache e performance
- **Registro de Agentes**: Inicialização do sistema de especialistas durante o startup

```python
# Fluxo de inicialização
register_all_specialists()  # Registra todos os especialistas
config_manager = await get_config_manager().initialize()  # Configuração dinâmica
grpc_server = await start_grpc_server(grpc_config)  # Inicia gRPC se habilitado
```

### 2. Sistema de Agentes (`agents/`)

O sistema de agentes foi migrado para uma arquitetura de **especialistas unificados**:

#### 2.1. Registro de Agentes (`_registry.py`)

- **AgentRegistry**: Singleton que mantém todos os agentes registrados
- **register_all_specialists()**: Função de bootstrap que registra todos os especialistas disponíveis
- **get_agent()**: Recupera agentes por tipo em runtime

#### 2.2. Especialistas (`specialists/`)

O novo sistema unifica prompts e personalidades:

- **SecuritySpecialist**: Especialista em segurança
- **ReviewSpecialist**: Especialista em revisão
- **CreativeSpecialist**: Especialista em criatividade
- **ArchitectureSpecialist**: Especialista em arquitetura
- **BrainstormSpecialist**: Especialista em brainstorm
- **DeepAnalysisSpecialist**: Especialista em análise profunda

#### 2.3. Agentes Disponíveis

- **Analyst**: Análise e interpretação
- **Coder**: Programação e desenvolvimento
- **Researcher**: Pesquisa e investigação
- **Security**: Segurança e validação
- **Review**: Revisão e qualidade
- **Architecture**: Arquitetura de sistemas
- **Creative**: Criação e inovação
- **Deep Analysis**: Análise profunda e detalhada

### 3. Sistema de Orquestração (`orchestrator/`)

O orquestrador é o cérebro do sistema, responsável por:

#### 3.1. Fluxo Principal

O sistema utiliza um grafo de execução com três nós principais:

1. **route_node**: Análise inteligente da mensagem e seleção do agente
2. **execute_node**: Invocação do LLM com o prompt do agente selecionado
3. **respond_node**: Formatação da saída em eventos de streaming

#### 3.2. Modos de Pensamento

- **Standard**: Execução direta com o agente selecionado
- **Decomposition**: Para tarefas complexas, divide em subtarefas

#### 3.3. Roteamento Inteligente

O sistema utiliza `route_message_intelligently()` para:
- Analisar a intenção do usuário
- Selecionar o agente mais apropriado
- Determinar o modo de pensamento necessário

### 4. Sistema de Memória (`memory/`)

Implementa RAG (Retrieval-Augmented Generation):

- **Memória de Sessão**: Contexto da conversa atual
- **Memória de Longo Prazo**: Histórico de interações
- **Recuperação Semântica**: Busca por similaridade
- **Embeddings**: Representação vetorial do conteúdo

### 5. Sistema de Ferramentas (`agents/tools/`)

Cada agente tem acesso a ferramentas específicas:

- **Web**: Busca, scraping, validação
- **Filesystem**: Operações de arquivos
- **Code**: Execução e análise de código
- **System**: Monitoramento e recursos
- **Sandbox**: Ambiente seguro de execução

## Fluxo de Execução Detalhado

### 1. Recebimento da Requisição

```
Usuario -> API FastAPI -> Router -> Controller
```

### 2. Processamento no Orquestrador

```
Controller -> Orchestrator.graph() -> route_node()
```

#### 2.1. Análise e Roteamento

- **Análise de intent**: Compreensão do que o usuário quer
- **Seleção de agente**: Escolha do especialista mais adequado
- **Cálculo de complexidade**: Determinação se decomposição é necessária

#### 2.2. Recuperação de Contexto

```
Memory Service -> Recuperação Semântica -> Contexto Relevante
```

### 3. Execução do Agente

#### 3.1. Modo Standard

```
execute_node() -> Agent.selected -> LLM + Tools -> Response
```

#### 3.2. Modo Decomposition (Tarefas Complexas)

```
Tasker.decompose() -> Scheduler.order() -> Resolver.resolve() -> Synthesizer.synthesize()
```

### 4. Formatação e Resposta

```
respond_node() -> Stream Events -> Usuario
```

## Arquitetura de Dados

### 1. Esquemas (`schemas/`)

- **agent.py**: Estrutura dos agentes
- **orchestration/**: Esquemas de orquestração
- **session.py**: Gerenciamento de sessões
- **grpc/**: Estruturas gRPC

### 2. Armazenamento (`storage/`)

- **PostgreSQL**: Banco de dados principal
- **Vector Store**: Armazenamento de embeddings
- **File System**: Arquivos e cache

### 3. Configuração (`config/`)

- **Ambiente**: Variáveis de ambiente
- **Agentes**: Configurações específicas
- **gRPC**: Configuração dinâmica

## Sistema de Comunicação

### 1. API REST

- **Endpoints RESTful**: Comunicação síncrona
- **Server-Sent Events**: Streaming de respostas
- **Middleware**: Segurança e performance

### 2. gRPC

- **Alto desempenho**: Comunicação entre serviços
- **Streaming**: Respostas em tempo real
- **Configuração dinâmica**: Hot-reload de configurações

## Segurança e Sandbox

### 1. Modos de Sandbox

- **NONE**: Sem acesso a ferramentas (seguro)
- **READ_ONLY**: Acesso somente leitura
- **FULL**: Acesso completo controlado

### 2. Middleware de Segurança

- **Rate Limiting**: Limitação de requisições
- **CORS**: Controle de origem
- **Security Headers**: Headers de segurança
- **Validation**: Validação de entrada

## Monitoramento e Logging

### 1. Sistema de Logs

- **Estruturado**: JSON formatado
- **Níveis**: DEBUG, INFO, WARNING, ERROR
- **Contexto**: Session ID, Agent Type, Request ID

### 2. Métricas

- **Performance**: Tempo de resposta
- **Agentes**: Utilização por tipo
- **Sistema**: Recursos consumidos

## Escalabilidade e Performance

### 1. Cache

- **Memory Cache**: Cache em memória
- **Redis**: Cache distribuído
- **Response Cache**: Cache de respostas

### 2. Processamento

- **Async**: Operações assíncronas
- **Streaming**: Respostas em fluxo
- **Batch**: Processamento em lote

## Exemplo de Fluxo Completo

### Cenário: "Crie uma API REST em Python para gerenciar tarefas"

1. **Recebimento**: POST /api/chat com mensagem
2. **Roteamento**: 
   - Análise: Intent de "programação"
   - Seleção: AgentType.CODER
   - Complexidade: Média (não requer decomposição)
3. **Contexto**: Recupera projetos anteriores do usuário
4. **Execução**:
   - System prompt: Coder personality
   - Tools: filesystem, code, web
   - LLM: Gera código da API
5. **Resposta**: Streaming do código gerado
6. **Armazenamento**: Salva interação na memória

## Configuração e Deploy

### 1. Variáveis de Ambiente

```bash
# App
APP_NAME=MindFlow
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000

# gRPC
GRPC_ENABLED=true
GRPC_HOST=0.0.0.0
GRPC_PORT=50051

# Database
DATABASE_URL=postgresql://...
MEMORY_ENABLED=true

# AI Providers
DEFAULT_PROVIDER=openai
DEFAULT_MODEL=gpt-4
```

### 2. Docker

```yaml
version: '3.8'
services:
  mindflow-backend:
    build: ./python
    ports:
      - "8000:8000"
      - "50051:50051"
    environment:
      - DATABASE_URL=postgresql://...
      - REDIS_URL=redis://...
```

## Conclusão

O MindFlow implementa uma arquitetura sofisticada de orquestração de agentes inteligentes com:

- **Modularidade**: Sistema de especialistas plugável
- **Inteligência**: Roteamento automático e seleção de agentes
- **Segurança**: Sandbox e middleware de proteção
- **Performance**: Cache, streaming e processamento assíncrono
- **Escalabilidade**: Arquitetura distribuída com gRPC

O sistema está evoluindo para suportar workflows mais complexos, colaboração entre múltiplos agentes e capacidades avançadas de raciocínio.
