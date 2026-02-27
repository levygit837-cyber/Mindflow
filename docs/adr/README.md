# ADRs (Architecture Decision Records)

Use esta pasta para registrar decisões arquiteturais importantes do OmniMind.

## Quando criar uma ADR

Crie uma ADR quando houver:

- mudança estrutural de arquitetura,
- adoção ou troca de framework/biblioteca crítica,
- alteração em contratos estáveis de API/eventos,
- nova política transversal de engenharia (segurança, observabilidade, persistência).

## Nome do arquivo

Formato:

`NNNN-titulo-curto.md`

Exemplos:

- `0001-camada-de-servicos-para-mind.md`
- `0002-unificacao-de-eventos-v1.md`

## Estado permitido

- `Proposed`
- `Accepted`
- `Superseded`
- `Deprecated`

## Fluxo mínimo

1. Criar ADR usando o template `0000-template.md`.
2. Discutir no PR.
3. Ao aprovar, atualizar status para `Accepted`.
4. Se houver mudança futura, criar nova ADR e marcar a anterior como `Superseded`.
