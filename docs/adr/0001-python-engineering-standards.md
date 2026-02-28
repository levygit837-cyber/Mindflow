# ADR 0001 - Baseline de Arquitetura e Padronizacao Python

- Status: Accepted
- Data: 2026-02-27
- Decisores: OmniMind maintainers
- Tags: arquitetura, padronizacao, python, qualidade

## Contexto

O projeto evoluiu rapidamente e possui backend e frontend desktop em Python. Sem um padrão explícito de estrutura, estilo e governança, existe risco de acoplamento crescente, inconsistência de práticas entre módulos e baixa previsibilidade de manutenção no longo prazo.

## Decisao

Adotar baseline única de engenharia Python com:

1. Documento canônico de padrões em `docs/architecture/python-engineering-standards.md`.
2. Governança de decisões arquiteturais via ADR em `docs/adr/`.
3. Tooling padrão:
   - `.editorconfig` na raiz.
   - `python/Makefile` com comandos oficiais (`format`, `lint`, `typecheck`, `test`, `check`).
   - `python/.pre-commit-config.yaml` com `ruff` e `mypy`.
4. Convenção de versionamento:
   - SemVer para pacote Python.
   - Conventional Commits no fluxo de git.

## Alternativas Consideradas

1. Não formalizar padrões e manter convenções implícitas.
2. Aplicar refatoração estrutural completa imediatamente (big-bang).
3. Adotar baseline incremental com documentação + automação leve.

## Consequencias

### Positivas

- Decisões técnicas passam a ser rastreáveis.
- Onboarding e revisão de PR ficam mais consistentes.
- Qualidade fica verificável por comandos padrão.

### Negativas

- Existe custo inicial de adoção e ajuste de código legado para atender lint/tipagem integral.
- Equipe precisa disciplinar o uso de ADR e comandos padrão.

## Plano de Implementacao

1. Publicar padrões e template ADR.
2. Integrar comandos padrão no fluxo local.
3. Gradualmente remover dívida de lint/typecheck até baseline ficar verde de ponta a ponta.

## Plano de Migracao

Adoção incremental por PR. Cada mudança nova deve seguir o padrão; código legado é corrigido de forma progressiva por fatias.

## Referencias

- `docs/architecture/python-engineering-standards.md`
- `docs/adr/README.md`
- `python/Makefile`
- `python/.pre-commit-config.yaml`
