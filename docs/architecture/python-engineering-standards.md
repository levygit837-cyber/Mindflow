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
- Frontend desktop: `python/omnimind_desktop` (PySide6 + QML)
- Testes: `python/tests`

Código legado em `src/` não define o padrão de arquitetura novo.

## 3) Arquitetura de Pastas (Canonical)

```text
python/
  omnimind_backend/
    api/           # Adapters HTTP/SSE (FastAPI), sem regra de negócio complexa
    schemas/       # Contratos de entrada/saída (Pydantic)
    agents/        # Runtime de agentes e orquestração de stream
    mind/          # Casos de uso do domínio "mind"
    storage/       # Persistência (models, migrations, repositories)
    workers/       # Execução assíncrona (RQ)
    grpc/          # Contratos e serviços internos gRPC
    infra/         # Config, logging, integrações transversais
  omnimind_desktop/
    qml/           # Camada visual
    viewmodels/    # Estado e binding UI
    api/           # Cliente HTTP/SSE para backend
  tests/           # Testes automatizados
  scripts/         # Scripts operacionais de desenvolvimento
```

## 4) Regras de Dependência Entre Camadas

### Backend

- `api/*` pode depender de `schemas`, `mind`, `agents`, `storage.repositories`, `infra`.
- `schemas/*` não depende de FastAPI, SQLAlchemy, PySide ou gRPC.
- `mind/*` e `agents/*` não dependem de FastAPI (framework-agnostic).
- `storage/*` centraliza acesso a banco; rotas não devem escrever SQL direto.
- `infra/*` contém bootstrap/config/logging compartilhado.

### Desktop

- `qml/*` não chama backend diretamente.
- `qml/*` conversa apenas com `viewmodels/*`.
- `viewmodels/*` usam `api/*` como gateway para backend.

## 5) Convenções de Código Python

- Formatação e lint por `ruff`.
- Tipagem obrigatória em APIs públicas e módulos novos.
- Imports absolutos (`from omnimind_backend...`, `from omnimind_desktop...`).
- Uma responsabilidade principal por arquivo.
- Evitar funções utilitárias genéricas sem domínio claro.

## 6) Convenções de Testes

- Testes ficam em `python/tests` com nome `test_*.py`.
- Todo bug fix deve incluir teste de regressão.
- Cobrir contratos críticos: schemas, stream de eventos, fluxo de sessão/job.

Pipeline local mínimo antes de commit:

```bash
cd python
uv run --extra dev ruff check .
uv run --extra dev ruff format --check .
uv run --extra dev mypy omnimind_backend omnimind_desktop
uv run --extra dev pytest
```

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
