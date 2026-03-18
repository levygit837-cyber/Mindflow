# Pre-Mortem Analysis: MindFlow Security Hardening

**Data:** 2026-03-17
**Escopo:** Implementação das correções de segurança identificadas na análise de 2026-03-17
**Horizonte imaginado:** O plano foi executado e falhou. O que deu errado?

---

## Contexto do Plano

Implementar 4 sprints de hardening de segurança no MindFlow backend:

- **Sprint 1** — Habilitar auth/rate limit por default, isolamento de sessão por `owner_id`
- **Sprint 2** — RBAC nas rotas, audit logging, brute force detection, shell rate limit
- **Sprint 3** — Docker sandbox, shell command whitelist, prompt injection filter
- **Sprint 4** — HTTPS enforcement, symlink protection, `SecretStr` nas settings, pip-audit no CI

---

## Tigers — Riscos Reais

### T1: Habilitar `auth_enabled=True` por default quebra tudo imediatamente
**Urgência: Launch-Blocking**

**Contexto técnico:**
`protected_route_dependencies` já está conectado em todos os routers via `api/dependencies/security.py`. `require_api_key()` em `infra/middleware/auth.py` retorna `None` quando `auth_enabled=False` — ou seja, a proteção existe mas está apagada. Ligar o flag **imediatamente bloqueará**:

- CLI (`mindflow-cli chat`) — não envia `Authorization: Bearer`
- Frontend React — `LocalAgentClient` não envia headers de auth
- Todos os testes automatizados — nenhum configura `AUTH_MASTER_KEY`
- Qualquer script ou integração existente

**Por que vai falhar:**
A equipe vai ligar o flag em staging, tudo vai quebrar em cascata, e a pressão vai ser para desligar de volta. O resultado: auth continua desabilitado "temporariamente" por meses.

**Mitigação:**
1. Antes de ligar o flag, adicionar suporte a `Authorization` no CLI e no `LocalAgentClient`
2. Criar `AUTH_MASTER_KEY` no `.env` de desenvolvimento com um valor fixo de dev
3. Atualizar `conftest.py` para injetar o header em todos os testes de integração
4. Fazer rollout: `dev → staging (com monitoring) → prod`
5. Só ligar `auth_enabled=True` por default depois que todos os clientes estiverem adaptados

**Owner:** Backend + Frontend
**Prazo:** Antes de qualquer mudança no default

---

### T2: A cadeia de migrations está quebrada — adicionar `owner_id` ao `ChatSession` vai falhar
**Urgência: Launch-Blocking**

**Contexto técnico:**
O banco está no revision `20260308_0008`. As migrations 0009–0012 existem mas **0009 está quebrada** (memory: `ALTER TABLE session_embeddings fails — table doesn't exist`). Adicionar `owner_id` requer uma nova migration que depende da chain inteira.

Estado atual:
```
0008 (atual) → 0009 (BROKEN) → 0010 → 0011 → 0012 → nova migration owner_id
```

**Por que vai falhar:**
Qualquer `alembic upgrade head` vai travar em 0009. Se tentarmos pular para a nova migration diretamente, perderemos integridade referencial. Dados de sessão existentes ficarão sem `owner_id` (NULL) e a constraint `NOT NULL` vai rejeitar inserts novos.

**Mitigação:**
1. **Primeiro:** Corrigir a migration 0009 (ou criar 0009-fix que verifica `IF NOT EXISTS` antes do `ALTER TABLE`)
2. Executar e verificar 0009–0012 em staging com dados reais antes de adicionar `owner_id`
3. Adicionar `owner_id` como `NULLABLE` com default `'system'` para dados legados
4. Migrar registros existentes: `UPDATE chat_sessions SET owner_id = 'legacy-user' WHERE owner_id IS NULL`
5. Só após validação adicionar constraint NOT NULL

**Owner:** Backend
**Prazo:** Sprint 1, primeira semana

---

### T3: O AuthManager avançado (JWT/RBAC) em `infra/security/auth.py` é código morto
**Urgência: Fast-Follow**

**Contexto técnico:**
`infra/security/auth.py` tem JWT, RBAC com 5 roles/5 permissões, lockout, session timeout — tudo implementado. Mas `api/dependencies/security.py` usa **somente** `require_api_key` de `infra/middleware/auth.py`, que é a versão simplificada (só API key, sem roles). O RBAC planejado no Sprint 2 pressupõe conectar o sistema avançado, mas isso requer reescrever as dependencies e todos os decorators de rota.

**Por que vai falhar:**
A estimativa para "implementar RBAC" vai ser grosseiramente subestimada. O código existe, mas conectar dois sistemas de auth divergentes (o middleware simples vs. o AuthManager avançado) é uma refatoração não-trivial com alto risco de regressão.

**Mitigação:**
1. Decidir: usar o `AuthManager` avançado ou evoluir o middleware simples?
2. Se usar `AuthManager`: criar `api/dependencies/security.py` que retorna um `UserContext` com roles
3. Criar `require_role("admin")` como FastAPI dependency baseada no `UserContext`
4. Aplicar primeiro em **um** endpoint (ex: `PUT /v1/config/`) e validar antes de escalar
5. Manter o middleware simples como fallback enquanto a migração ocorre

**Owner:** Backend
**Prazo:** Sprint 2, segunda semana

---

### T4: Docker sandbox para shell execution é uma mudança de arquitetura, não de sprint
**Urgência: Track**

**Contexto técnico:**
`shell_executor.py` usa `subprocess.Popen(command, shell=True, ...)` com cwd e env sanitizados. Trocar para Docker requer:

- Docker daemon rodando em **todos** os ambientes (dev local, CI, prod)
- Volume mount para passar o `root_dir` para dentro do container
- Latência adicional por spawn de container (0.5–2s por comando)
- Imagem Docker customizada com as ferramentas permitidas
- Gestão de ciclo de vida dos containers (cleanup, timeout, orphan handling)
- Possível incompatibilidade com o `ShellTabService` que mantém sessões persistentes

**Por que vai falhar:**
Escalonar Docker sandbox em um sprint é subestimar o trabalho. Em dev local (sem Docker configurado), o sistema vai quebrar completamente. A equipe vai sofrer pressão para reverter.

**Mitigação:**
1. **Curto prazo (Sprint 3):** Melhorar o subprocess atual — `shell=False` + `shlex.split()` + whitelist de comandos + `resource.setrlimit()` para CPU/memória
2. **Médio prazo:** Introduzir Docker sandbox como modo opcional (`SANDBOX_BACKEND=docker|subprocess`)
3. **Longo prazo:** Migrar para Docker quando infraestrutura de prod estiver definida
4. Nunca quebrar `SANDBOX_BACKEND=subprocess` como fallback

**Owner:** Backend + DevOps
**Prazo:** Sprint 3 (versão subprocess melhorada), Sprint 5+ (Docker)

---

### T5: Rate limiting depende de Redis estar saudável — fail-open anula a proteção
**Urgência: Fast-Follow**

**Contexto técnico:**
`RateLimiterMiddleware` tem comportamento fail-open explícito:
```python
except Exception:
    return await call_next(request)  # Redis caiu → todo tráfego passa
```

Habilitar `RATE_LIMIT_ENABLED=True` por default cria uma **falsa sensação de segurança**: se Redis cair, o rate limiting desaparece silenciosamente.

**Mitigação:**
1. Adicionar métrica/alerta quando Redis estiver indisponível e rate limiting degradado
2. Implementar rate limiting in-memory como fallback (sliding window simples sem persistência)
3. Ou: fail-closed para endpoints críticos (shell execution, auth) mas fail-open para endpoints de leitura

**Owner:** Backend + Infra
**Prazo:** Sprint 2

---

## Paper Tigers — Preocupações Superestimadas

### PT1: CORS wildcard vazando para produção
Já há verificação de `APP_ENV` em `main.py`. A hardening de prod já está diferenciada do dev no código existente. O risco real é baixo — exige configuração incorreta explícita de `APP_ENV=production` com `CORS_ALLOW_ORIGINS=*`.

**Veredicto:** Documentar o comportamento, não é prioridade de implementação.

---

### PT2: `Pydantic SecretStr` vai quebrar muita coisa
A mudança é localizada em `infra/config/settings.py`. `SecretStr` só afeta o `repr()` e `str()` dos campos — o `.get_secret_value()` acessa o valor real. As únicas quebras serão onde o código usa `settings.anthropic_api_key` diretamente em f-strings (log de debug). São poucos pontos, facilmente auditáveis com `grep`.

**Veredicto:** Baixo risco, vale fazer no Sprint 4.

---

### PT3: Prompt injection filter vai bloquear mensagens legítimas
Filtros de prompt injection baseados em regex têm alta taxa de falso positivo. Usuários legítimos usam palavras como "ignore" e "override" em contextos normais.

**Veredicto:** Implementar como **log apenas** (sem bloquear), com threshold ajustável. Só bloquear após análise de dados reais.

---

## Elephants — O que não estamos discutindo

### E1: Como gerenciar API keys em produção sem interface admin?
O sistema de API keys existe (`infra/middleware/auth.py`, modelo `ApiKey`), mas não há nenhuma interface para **criar, listar, revogar ou rotacionar** chaves. A única opção é `AUTH_MASTER_KEY` no `.env`. Antes de habilitar auth em produção, precisamos responder: quem gerencia as chaves e como?

**Investigar:** Criar um endpoint admin básico de gerenciamento de keys, ou usar o `AUTH_MASTER_KEY` como única key de produção com rotação manual.

---

### E2: Browser `EventSource` não suporta headers customizados
A autenticação nos endpoints SSE (`/agent/chat/stream`, `/agent/shell-tabs/{session_id}/events`) pressupõe `Authorization: Bearer` no header. Mas a API nativa do browser `EventSource` **não suporta headers customizados**. Isso significa que o frontend não pode autenticar SSE via Bearer token sem uma solução alternativa.

Alternativas:
- Token na query string (`?token=...`) — vaza no log do servidor
- Trocar `EventSource` por `fetch` com `ReadableStream` — requer rewrite do frontend
- Cookie de sessão — muda o modelo de auth

**Investigar:** Qual abordagem de auth para SSE é compatível com a arquitetura atual do frontend?

---

### E3: O plano de sprints não inclui testes de regressão de segurança
Cada mudança de segurança pode quebrar comportamentos existentes. Não há plano explícito para:
- Testes de regressão automáticos após habilitar auth
- Testes de integração para o novo `owner_id` isolation
- Smoke tests de shell execution após mudanças de sandbox

**Investigar:** Definir uma suite de testes de "security contract" que roda a cada PR afetando middleware, auth, ou sandbox.

---

## Action Plans — Launch-Blocking Tigers

### Action Plan T1: Rollout de auth sem quebrar clientes

| Item | Detalhe |
|------|---------|
| **Risco** | Ligar `auth_enabled=True` quebra CLI, frontend e testes |
| **Mitigação** | Adaptar todos os clientes ANTES de mudar o default |
| **Passo 1** | Adicionar `Authorization: Bearer $MINDFLOW_API_KEY` no CLI (`mindflow_cli/commands/chat.py`) |
| **Passo 2** | Adicionar header no `LocalAgentClient` do frontend |
| **Passo 3** | Configurar `AUTH_MASTER_KEY=dev-local-key-2026` no `.env` |
| **Passo 4** | Atualizar `conftest.py` para injetar header em testes |
| **Passo 5** | Ligar flag em dev, monitorar por 48h, depois staging |
| **Owner** | Backend + Frontend |
| **Prazo** | Sprint 1, Semana 2 |

---

### Action Plan T2: Corrigir migration chain antes de adicionar owner_id

| Item | Detalhe |
|------|---------|
| **Risco** | Migration 0009 quebrada bloqueia todas as migrations futuras |
| **Mitigação** | Corrigir 0009 antes de qualquer schema change |
| **Passo 1** | Ler `20260309_0009_pgvector_embeddings.py` e identificar o `ALTER TABLE` problemático |
| **Passo 2** | Corrigir com `IF NOT EXISTS` ou criar tabela antes do ALTER |
| **Passo 3** | Testar `alembic upgrade head` em banco limpo |
| **Passo 4** | Adicionar nova migration `20260317_0013_chat_session_owner_id.py` com `owner_id NULLABLE` |
| **Passo 5** | Data migration para registros legados |
| **Owner** | Backend |
| **Prazo** | Sprint 1, Semana 1 |

---

### Action Plan T4: Melhorar subprocess antes de considerar Docker

| Item | Detalhe |
|------|---------|
| **Risco** | Docker sandbox é over-engineering para o Sprint 3 — vai quebrar ambientes |
| **Mitigação** | Implementar subprocess hardened como intermediário seguro |
| **Passo 1** | Substituir `shell=True` por `shell=False` + `shlex.split()` em `shell_executor.py` |
| **Passo 2** | Trocar blocklist por whitelist de comandos permitidos |
| **Passo 3** | Adicionar `resource.setrlimit()` para CPU (30s) e memória (256MB) |
| **Passo 4** | Adicionar `SANDBOX_BACKEND` env var para habilitar Docker futuramente |
| **Owner** | Backend |
| **Prazo** | Sprint 3 |

---

## Sequência de Implementação Revisada

```
Sprint 1 — Fundação (sem quebrar nada)
  ├── W1: Corrigir migration 0009 + rodar migrations até 0012
  ├── W1: Adaptar CLI para enviar Authorization header
  ├── W2: Adaptar frontend (LocalAgentClient) para enviar header
  ├── W2: Atualizar conftest.py para testes com auth
  └── W2: Ligar auth_enabled=True em dev (monitorar 48h) → staging

Sprint 2 — Controles de acesso
  ├── W1: Decidir arquitetura RBAC (AuthManager vs. middleware simples)
  ├── W1: Implementar require_role("admin") como dependency FastAPI
  ├── W1: Aplicar em /v1/config/* endpoints
  ├── W2: Audit logging unificado (@audit_log decorator)
  ├── W2: Log de auth failures + brute force detection por IP
  └── W2: Rate limiting enabled=True + fallback in-memory + alertas de degradação

Sprint 3 — Sandbox hardening (subprocess, não Docker)
  ├── W1: shell=False + shlex.split() + whitelist de comandos
  ├── W1: resource.setrlimit() para CPU/memória no subprocess
  ├── W2: Resolver E2 (SSE auth via fetch + ReadableStream ou token temporário)
  └── W2: Security contract test suite

Sprint 4 — Hardening final
  ├── W1: SecretStr em Settings + sanitização de Settings em logs de erro
  ├── W1: Migration 0013 (owner_id) + session isolation em todas as queries
  ├── W2: HTTPS enforcement (X-Forwarded-Proto middleware)
  ├── W2: Symlink protection no resolve_workspace_path
  └── W2: pip-audit no CI/CD

Sprint 5+ — Docker sandbox (quando infra de prod estiver definida)
```

---

## Riscos Residuais Aceitos

| Risco | Decisão | Justificativa |
|-------|---------|---------------|
| Prompt injection filter | Apenas log, sem bloqueio | Alto falso positivo; dados reais primeiro |
| Docker sandbox | Adiado para Sprint 5+ | Infra de prod não definida; subprocess hardened é suficiente por agora |
| SBOM / pip-audit | Sprint 4 | Não é serviço público ainda; prioridade menor |
| CSP avançado | Sprint 4 | `default-src 'self'` já mitiga os principais vetores |

---

*Documento gerado em 2026-03-17. Revisitar antes do início de cada sprint para validar se as mitigações estão on track.*
