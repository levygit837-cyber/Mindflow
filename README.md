# 🧠 Mindflow — Multi-Agent AI Orchestrator

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6+-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.116+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![Flutter](https://img.shields.io/badge/Flutter-3.x-02569B?logo=flutter&logoColor=white)](https://flutter.dev/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-1C3C3C?logo=langchain&logoColor=white)](https://langchain-ai.github.io/langgraph/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Status](https://img.shields.io/badge/Status-Active%20Development-brightgreen)]()

> **Mindflow é uma plataforma de orquestração multi-agente que coordena equipes de IAs especializadas — Analyst, Coder, Researcher e Orchestrator — para resolver tarefas complexas de software de forma autônoma, segura e observável.**

---

## ✨ Funcionalidades Principais

- **🤖 Equipes Multi-Agente** — Orchestrator delega tarefas para agentes especializados com comunicação P2P e chat em grupo (MUC/XMPP)
- **📊 Planning & Decomposition** — Quebra automática de tarefas complexas em missões, com execução via grafos (LangGraph) e DAGs
- **🔧 Tool System Avançado** — Leitura/escrita de arquivos, execução shell sandboxed, busca (grep/glob), navegação web com LightPanda/Playwright e análise de PDFs
- **💬 Streaming em Tempo Real** — Respostas em streaming via SSE e WebSocket, com UI reativa no terminal, web e desktop
- **🧠 Memória Inteligente** — Memória vetorial (PostgreSQL + pgvector) + memória em grafo (KuzuDB) para contexto persistente entre sessões
- **🛡️ Segurança de Produção** — Sandbox de comandos, proteção contra path traversal, detecção de secrets, rate limiting e circuit breakers
- **🚀 Feature Flags & Rollout** — Sistema de flags para ativar funcionalidades gradualmente sem deploy
- **🖥️ Três Interfaces** — CLI terminal (React Ink), SPA web (React + Vite) e app desktop cross-platform (Flutter)

---

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                    Interfaces de Usuário                     │
│  ┌─────────┐  ┌──────────────┐  ┌─────────────────────────┐ │
│  │ CLI     │  │ Web SPA      │  │ Flutter Desktop         │ │
│  │ (Ink)   │  │ (React+Vite) │  │ (Linux/macOS/Windows)   │ │
│  └────┬────┘  └──────┬───────┘  └────────────┬────────────┘ │
└───────┼──────────────┼───────────────────────┼──────────────┘
        │              │                       │
        └──────────────┼───────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Mindflow Backend (Python/FastAPI)               │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ API REST     │  │ gRPC Server  │  │ WebSocket/SSE    │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
│         └─────────────────┼─────────────────────┘            │
│                           ▼                                  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │        Unified Execution Engine (LangGraph)            │  │
│  │  • AgentTeamManager  • ToolExecutionLoop (ReAct)      │  │
│  │  • IntelligentRouter • PlanningFlow                    │  │
│  └────────────────────────────────────────────────────────┘  │
│                           │                                  │
│  ┌──────────────┐  ┌──────┴──────┐  ┌────────────────────┐  │
│  │ Agents       │  │ Chains      │  │ Skills Registry    │  │
│  │ (Specialists)│  │ (LangChain) │  │ (Markdown-based)   │  │
│  └──────────────┘  └─────────────┘  └────────────────────┘  │
└───────────────────────────┬──────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Infraestrutura & Dados                          │
│  PostgreSQL │ KuzuDB │ Redis │ RabbitMQ │ Prosody (XMPP)    │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Stack Tecnológico

| Camada | Tecnologias |
|--------|-------------|
| **Backend** | Python 3.11, FastAPI, LangChain, LangGraph, Pydantic v2, Uvicorn |
| **Banco de Dados** | PostgreSQL 16 + pgvector, KuzuDB (graph), Redis, asyncpg |
| **Mensageria** | RabbitMQ, gRPC, WebSocket, SSE, XMPP (Prosody) |
| **Automação** | LightPanda, Playwright, Docker SDK |
| **Frontend Web** | React 19, TypeScript, Vite, Tailwind CSS, Zustand |
| **CLI** | React Ink, Yoga Layout, NDJSON streaming |
| **Desktop** | Flutter 3.x, Provider, WebSocket Channel |
| **DevOps** | Docker, Docker Compose, Alembic, pytest, ruff, mypy |

---

## 🚀 Como Rodar

### Pré-requisitos
- Docker & Docker Compose
- Python 3.11+ e [uv](https://github.com/astral-sh/uv)
- Node.js 20+ (para frontend)
- Flutter 3.x (opcional, para desktop)

### 1. Clone e configure

```bash
git clone https://github.com/levygit837-cyber/Mindflow.git
cd Mindflow
cp .env.example .env
# Edite .env com suas chaves de API (Google, OpenAI, Anthropic, etc.)
```

### 2. Infraestrutura (Docker)

```bash
docker compose up -d postgres redis rabbitmq kuzudb prosody lightpanda
```

### 3. Backend

```bash
cd python
uv sync
uv run mindflow-api
```

### 4. Frontend Web

```bash
cd frontend
npm install
npm run dev
```

### 5. CLI (opcional)

```bash
cd src/cli
npm install
npm run dev
```

> 📖 Para instruções detalhadas, consulte os READMEs em [`src/cli/README.md`](./src/cli/README.md) e [`flutter_desktop/README.md`](./flutter_desktop/README.md).

---

## 📁 Estrutura do Projeto

```
Mindflow/
├── python/mindflow_backend/   # Backend Python (FastAPI, agentes, orquestração)
├── frontend/                  # SPA React + Vite
├── src/cli/                   # Interface de terminal (React Ink)
├── flutter_desktop/           # App desktop cross-platform (Flutter)
├── docker-compose.yml         # Infraestrutura completa
└── tests/                     # Testes unitários e de integração
```

---

## 📊 Status do Projeto

| Aspecto | Status |
|---------|--------|
| Core Backend | ✅ Funcional — API, agentes, tools, memória |
| Tool System v2 | ✅ Completo — segurança, cache, métricas, git integration |
| Unified Execution Engine | ✅ Implementado — ReAct, teams, graphs, chains |
| Frontend Web | 🔄 Em desenvolvimento — estrutura base pronta |
| CLI | 🔄 Em desenvolvimento — protótipo funcional |
| Flutter Desktop | 🔄 Em desenvolvimento — estrutura base pronta |
| Testes | 🔄 Expansão contínua |

> **Mindflow está em desenvolvimento ativo.** O backend e o sistema de agentes já são funcionais e estáveis. As interfaces (web, CLI, desktop) estão em construção progressiva.

---

## 🎯 Aprendizados Técnicos

Este projeto foi construído do zero com foco em aprendizado profundo de arquitetura de sistemas distribuídos:

- **Orquestração de Agentes** — Padrões de delegation, planning e síntese multi-agente com LangGraph
- **Streaming & Concorrência** — Protocolos NDJSON, SSE, WebSocket e gerenciamento de estado em tempo real
- **Segurança em IA** — Sandbox de execução, validação de paths, detecção de secrets e hardening de prompts
- **Bancos Híbridos** — Combinação de SQL relacional, vetorial (pgvector) e graph (KuzuDB) para diferentes perfis de dados
- **Resiliência** — Circuit breakers, rate limiting, feature flags e graceful degradation
- **Multi-plataforma** — Compartilhamento de lógica de backend entre web, terminal e desktop

---

## 📜 Licença

Distribuído sob a licença MIT. Veja [LICENSE](./LICENSE) para mais informações.

---

<p align="center">
  <i>Construído com 💻 e muito ☕ por alguém apaixonado por arquitetura de software e IA.</i>
</p>
