# ADR 0003 - Security Hardening & Observability Foundation

- Status: Proposed
- Data: 2026-02-27
- Decisores: OmniMind maintainers
- Tags: segurança, observabilidade, resiliência, middleware, backend

## Contexto

O OmniMind backend expõe atualmente a rota `POST /v1/agent/chat/stream` **sem autenticação**, sem headers de segurança HTTP, sem rate limiting, com logging em texto plano (sem correlation), e sem retry em chamadas a providers LLM. Essas lacunas são aceitáveis em fase de prototipação, mas bloqueiam a evolução para **múltiplos clientes e usuários** — visão central do projeto.

O plano de arquitetura (`ARCHITECTURE_PLAN.md`) define 3 fases (Structure → Agent System → Tool Registry), porém nenhuma endereça segurança e observabilidade como pré-requisito para o sistema multi-agent escalar com segurança.

### Riscos identificados

1. **API aberta:** qualquer pessoa pode consumir LLM (custo direto) sem controle.
2. **Sem rate limit:** um único cliente pode exaurir quota de LLM e degradar o serviço.
3. **Sem headers de segurança:** vulnerável a clickjacking, XSS, MIME-sniffing.
4. **Sem correlation de requests:** debug em produção é inviável sem `request_id`.
5. **Sem retry:** falhas transientes de LLM (429, 5xx) viram erro direto ao usuário.
6. **Input mal sanitizado:** Pydantic valida tipo/tamanho, mas não conteúdo (control chars, injection).
7. **gRPC inseguro:** `add_insecure_port` em produção.
8. **CORS permissivo:** `allow_methods="*"` e `allow_headers="*"` em todos os ambientes.

## Decisao

Inserir **Phase 1.5: Security Foundation** no plano de migração, entre Phase 1 (Structure) e Phase 2 (Agent System), com 8 tarefas granulares executáveis de forma incremental:

| Task | Escopo | Arquivos Novos | Arquivos Modificados |
|------|--------|----------------|---------------------|
| 1.5.1 | Security Headers | `infra/middleware/security_headers.py` | `main.py` |
| 1.5.2 | Request Context | `infra/middleware/request_context.py` | `main.py`, `infra/logging.py` |
| 1.5.3 | Structured Logging | — | `infra/logging.py`, `infra/config.py` |
| 1.5.4 | Rate Limiting | `infra/middleware/rate_limiter.py` | `main.py`, `infra/config.py` |
| 1.5.5 | Input Sanitization | `infra/sanitizer.py` | `api/v1/agent.py` |
| 1.5.6 | Retry & Circuit Breaker | `infra/resilience.py` | `agents/runtime.py`, `agents/tools.py` |
| 1.5.7 | API Key Auth | `infra/middleware/auth.py`, migration | `storage/models.py`, `api/v1/agent.py`, `infra/config.py` |
| 1.5.8 | CORS & gRPC Hardening | — | `infra/config.py`, `main.py`, `grpc/server.py` |

### Princípios de design

- **Aditivo:** Nenhuma task altera comportamento existente. Feature flags controlam ativação.
- **Incremental:** Cada task é independente e gera testes próprios.
- **Defense-in-depth:** Sanitização em 3 camadas (Schema → Sanitizer → Prompt Guard).
- **Environment-aware:** Headers rígidos e CORS restrito apenas em produção.

### Nova estrutura de pastas

```
infra/
├── config.py                  # EXTEND: security/rate-limit/auth settings
├── logging.py                 # EVOLVE: structured JSON + correlation
├── redis.py                   # KEEP
├── sanitizer.py               # NEW: L2 input sanitization
├── resilience.py              # NEW: retry config, circuit breaker
└── middleware/                # NEW
    ├── __init__.py
    ├── security_headers.py    # Helmet-equivalent
    ├── rate_limiter.py        # Redis sliding window
    ├── request_context.py     # X-Request-ID, timing
    └── auth.py                # API key (MVP) → JWT (future)
```

### Novas dependências

| Pacote | Propósito | Justificativa |
|--------|-----------|---------------|
| `structlog` | Logging estruturado | Integra com stdlib, suporta JSON e console, padrão de mercado |
| `tenacity` | Retry/backoff | Biblioteca madura (~1.2k ★), decorator pattern, zero boilerplate |
| `python-jose[cryptography]` | JWT (Phase 2+) | Necessário apenas na evolução para JWT |

## Alternativas Consideradas

1. **Não fazer (manter status quo):**
   - ✗ Bloqueante para multi-tenant, risco financeiro (LLM sem controle de custo).

2. **Usar framework externo (e.g., FastAPI-Security, Starlette-Admin):**
   - ✗ Adiciona dependências pesadas, acoplamento com framework, menor controle.

3. **implementar tudo junto em uma única fase (big-bang):**
   - ✗ Risco alto de regressão, contexto de AI fica muito grande, difícil debugar.

4. **Phase 1.5 incremental com feature flags (escolhida):**
   - ✓ Baixo risco, cada task verificável isoladamente, rollback por flag.

## Consequencias

### Positivas

- API protegida por autenticação antes de escalar para múltiplos usuários.
- Custo de LLM controlado via rate limiting per-key/per-IP.
- Debug em produção possível com structured logging + request correlation.
- Resiliência a falhas de provider LLM (retry automático com backoff).
- Baseline de segurança HTTP sem dependência de proxy reverso.
- Cada task pode ser implementada e merge de forma independente.

### Negativas

- 2 novas dependências (`structlog`, `tenacity`) no pacote.
- Complexidade incremental no middleware stack (ordem importa).
- Feature flags adicionam condicionais no código (removíveis após estabilização).
- API key requer seed/setup inicial para ambiente de desenvolvimento.

## Plano de Implementacao

Todas as tasks seguem o padrão: **criar → testar → integrar → verificar**.

1. **Task 1.5.1:** Security Headers (1-2h) — middleware isolado, teste de headers.
2. **Task 1.5.2:** Request Context (2-3h) — middleware + ContextVar + logging update.
3. **Task 1.5.3:** Structured Logging (3-4h) — `structlog` setup, dual output.
4. **Task 1.5.4:** Rate Limiting (3-4h) — Redis sliding window, teste de 429.
5. **Task 1.5.5:** Input Sanitization (2-3h) — sanitizer puro, teste de edge cases.
6. **Task 1.5.6:** Retry & Circuit Breaker (2-3h) — `tenacity` wrappers.
7. **Task 1.5.7:** API Key Auth (4-6h) — model + migration + dependency.
8. **Task 1.5.8:** CORS & gRPC Hardening (2h) — config + conditional TLS.

**Estimativa total:** 20-28h de implementação.

**Regra de execução:** Implementar uma task por vez. Verificar que todos os testes passam antes de avançar para a próxima. Isso preserva contexto e evita regressões acumuladas.

## Plano de Migracao

- **Sem breaking changes:** todas as features são aditivas e feature-flagged.
- **Rollback:** desativar feature flag (`AUTH_ENABLED=false`, `RATE_LIMIT_ENABLED=false`).
- **Ambientes existentes:** flags desativados por padrão em development.
- **CI:** adicionar testes de segurança ao pipeline existente (`pytest`).

## Priorização

```
P0 (bloquear deploy público sem isso):
├── Task 1.5.1 — Security Headers
├── Task 1.5.4 — Rate Limiting
└── Task 1.5.7 — API Key Auth

P1 (qualidade de produção):
├── Task 1.5.2 — Request Context
├── Task 1.5.3 — Structured Logging
├── Task 1.5.5 — Input Sanitization
└── Task 1.5.6 — Retry & Circuit Breaker

P2 (hardening avançado):
└── Task 1.5.8 — CORS & gRPC Hardening
```

## Referencias

- `ARCHITECTURE_PLAN.md` (updated with Phase 1.5)
- `docs/architecture/python-engineering-standards.md`
- `docs/adr/0001-python-engineering-standards.md`
- OWASP API Security Top 10 (https://owasp.org/API-Security/)
- FastAPI Security docs (https://fastapi.tiangolo.com/tutorial/security/)
