# OmniMind Python Engineering Standards

Este documento define as convenções oficiais para manter o projeto sustentável no longo prazo.

## 1) Objetivo

Padronizar arquitetura, organização de pastas, estilo de código, testes e versionamento para:

- reduzir acoplamento,
- aumentar previsibilidade de mudanças,
- facilitar onboarding,
- manter qualidade com crescimento do time e do produto.

## 2) Escopo do Runtime

O runtime principal do OmniMind é Python:

- Backend: `python/omnimind_backend`
- Interface principal (direção): CLI terminal-first `Typer + Rich` (`python/omnimind_cli`)
- Frontend desktop legado: `python/omnimind_desktop` (em depreciação)
- Testes: `python/tests`

Contexto de decisão:

- ADR 0001: baseline de engenharia Python.
- ADR 0002: direção terminal-first e depreciação progressiva do desktop.

## 3) Arquitetura de Pastas (Canonical)

```text
python/
  omnimind_backend/
    api/           # Adapters HTTP/SSE (FastAPI), sem regra de negócio complexa
    schemas/       # Contratos de entrada/saída (Pydantic)
    agents/        # Runtime de agentes e orquestração de stream
    storage/       # Persistência (models, migrations, repositories)
    workers/       # Execução assíncrona (RQ)
    grpc/          # Contratos e serviços internos gRPC
    infra/         # Config, logging, integrações transversais
  omnimind_cli/
    commands/      # Comandos Typer (entrada da aplicação)
    render/        # Componentes Rich (painéis, tabelas, progresso, timeline)
    workflows/     # Orquestrações de alto nível por comando
    clients/       # Clientes HTTP/SSE para backend
  omnimind_desktop/  # Legado temporário, sem novas features
  tests/           # Testes automatizados
  scripts/         # Scripts operacionais de desenvolvimento
```

## 4) Regras de Dependência Entre Camadas

### Backend

- `api/*` pode depender de `schemas`, `agents`, `storage.repositories`, `infra`.
- `schemas/*` não depende de FastAPI, SQLAlchemy, PySide ou gRPC.
- `agents/*` não depende de FastAPI (framework-agnostic).
- `storage/*` centraliza acesso a banco; rotas não devem escrever SQL direto.
- `infra/*` contém bootstrap/config/logging compartilhado.

### CLI

- `commands/*` não deve conter regra de negócio.
- `workflows/*` orquestra chamadas de backend e estado de execução.
- `render/*` só transforma estado em output terminal.
- `clients/*` encapsula HTTP/SSE e tratamento de reconexão/timeouts.

### Desktop (Legado)

- sem novas features;
- apenas correções críticas até remoção completa.

## 5) Convenções de Código Python

- Formatação e lint por `ruff`.
- Tipagem obrigatória em APIs públicas e módulos novos.
- Imports absolutos (`from omnimind_backend...`, `from omnimind_desktop...`).
- Uma responsabilidade principal por arquivo.
- Evitar funções utilitárias genéricas sem domínio claro.

## 6) Convenções de Testes

- Testes ficam em `python/tests` com nome `test_*.py`.
- Todo bug fix deve incluir teste de regressão.
- Cobrir contratos críticos: schemas, stream de eventos, integração CLI↔API.

Pipeline local mínimo antes de commit:

```bash
cd python
uv run --extra dev ruff check .
uv run --extra dev ruff format --check .
uv run --extra dev mypy omnimind_backend omnimind_desktop
uv run --extra dev pytest
```

Nota: durante transição para `omnimind_cli`, trocar `omnimind_desktop` por `omnimind_cli` no typecheck.

## 7) Versionamento e Git

- Commits no formato Conventional Commits (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`).
- Branches de trabalho: `feature/*`, `fix/*`, `refactor/*`, `docs/*`.
- Versionamento semântico no pacote Python (`MAJOR.MINOR.PATCH`).
- Mudança incompatível de API ou schema público exige:
  - `ADR` registrada,
  - nota de migração no PR,
  - atualização de contratos/documentação.

## 8) ADR Obrigatória Para Decisões Estruturais

Criar ADR em `docs/adr/` para:

- mudança de arquitetura em camadas,
- mudança de stack/framework,
- novo padrão transversal (persistência, eventos, observabilidade),
- depreciação de módulos centrais.

Template oficial em `docs/adr/0000-template.md`.

## 9) Definition of Done (DoD) Técnico

Uma task só é considerada completa quando:

- segue este padrão de arquitetura,
- possui tipagem e lint aprovados,
- testes automatizados relevantes estão verdes,
- documentação foi atualizada quando necessário.
