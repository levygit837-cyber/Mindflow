# Análise Comparativa de Segurança: Claude Code vs MindFlow

> **Data:** 04/01/2026
> **Escopo:** Análise completa dos sistemas de segurança de ambos projetos
> **Metodologia:** Análise estática do código-fonte via SocratiCode (semantic search + graph analysis)

---

## Sumário Executivo

| Dimensão | Claude Code | MindFlow | Gap |
|----------|-------------|----------|-----|
| **Sandbox de Execução** | bubblewrap (bwrap) com isolamento completo | MindFlowSandbox básico (filesystem-only) | 🔴 CRÍTICO |
| **Controle de Acesso a Arquivos** | Path canonicalization + symlink resolution + UNC detection | Path matching básico | 🔴 CRÍTICO |
| **Sistema de Permissões** | 6 modos + regras pattern-matching + UI dialogs | 6 modos + regras (sem UI integrada) | 🟡 PARCIAL |
| **Hooks System** | PreToolUse, PostToolUse, PermissionRequest com input mutation | PreToolUse, PostToolUse, PermissionRequest (implementado) | 🟢 OK |
| **Bash Security Validators** | AST parsing + compound command splitting + 10+ validators | 11 validators (string-based, sem AST) | 🟡 PARCIAL |
| **API Key Security** | Multi-provider (Anthropic, AWS Bedrock, Vertex, Foundry) com verificação | Provider base | 🟡 PARCIAL |
| **Proteção de Rede** | Sandbox network restrictions pre-aprovadas | sem controle de rede | 🔴 CRÍTICO |
| **Model Security** | Model validation + allowlist + fallback 3P | Provider configuration | 🔴 CRÍTICO |
| **Input Sanitization** | Path traversal, Windows patterns, DOS devices, ADS | Path traversal, basic patterns | 🟡 PARCIAL |
| **Circuit Breaker** | PermissionManager + hooks com circuit breaker | Circuit breaker implementado | 🟢 OK |
| **Swarm/Multi-Agent Security** | Mailbox-based permission sync + leader/worker | Teams com XMPP, sem permission sync | 🟡 PARCIAL |

---

## 1. Sandboxing e Isolamento de Execução

### Claude Code — bubblewrap (bwrap) Sandbox

O Claude Code implementa um sistema de sandbox profundo usando **bubblewrap (bubblewrap/bwrap)**, um sandbox de namespace Linux que isola processos do sistema host.

**Características:**

- **Filesystem isolation**: `--ro-bind` (read-only bind mounts), `--dev` (/dev isolation), `--proc`, `--unshare-all`
- **Network isolation**: `--unshare-net` isola completamente a rede, com regras explícitas para permitir hosts
- **PID isolation**: Processos dentro do sandbox não veem processos do host
- **Auto-allow bash**: Quando sandboxed, comandos bash são auto-aprovados (exceto excluded commands)
- **Git security**: Proteção contra git bare repo planting (HEAD, objects/, refs/, hooks/, config)
- **Binary hijack prevention**: Variáveis de ambiente como `LD_PRELOAD`, `LD_LIBRARY_PATH` são sanitizadas
- **Excluded commands**: Comandos como `docker`, `su`, `sudo`, `ssh` são excluídos do sandbox

**Arquivos-chave:**

- `utils/sandbox/sandbox-adapter.ts` — Configuração e execução do bwrap
- `tools/BashTool/shouldUseSandbox.ts` — Decisão de usar sandbox
- `tools/BashTool/bashPermissions.ts` — Permissões por comando

### MindFlow — MindFlowSandbox (FileSystem-Only)

O MindFlow possui uma classe `MindFlowSandbox` que é basicamente um wrapper de filesystem com root directory.

**Implementação atual:**

```python
# mindflow_backend/agents/tools/system/sandbox.py
sandbox = MindFlowSandbox(root_dir="/tmp/test_sandbox")
```

**O que falta:**

- ❌ **Sem namespace isolation** — Processos executam sem isolamento de PID, network ou filesystem
- ❌ **Sem network isolation** — Comandos bash podem acessar qualquer endpoint de rede
- ❌ **Sem binary hijack protection** — Variáveis `LD_PRELOAD`, `LD_LIBRARY_PATH` não são sanitizadas
- ❌ **Sem git security** — Vulnerável a git bare repo planting
- ❌ **Sem auto-allow logic** — Não há distinção entre comandos sandboxed vs não-sandboxed

**Recomendação:** Implementar bubblewrap ou nsjail como runtime de execução para comandos bash.

---

## 2. Controle de Acesso a Arquivos

### Claude Code — Defesa em Profundidade

O Claude Code implementa múltiplas camadas de proteção para acesso a arquivos:

**1. Path Canonicalization:**

- Resolve symlinks com `realpathSync`
- Verifica caminhos originais E resolvidos
- Computa uma vez e reusa para evitar syscalls redundantes

**2. Suspicious Windows Pattern Detection:**

- **NTFS Alternate Data Streams (ADS)**: `file.txt::$DATA`, `file.txt:stream`
- **8.3 Short Names**: `GIT~1`, `CLAUDE~1` — usados para bypass de segurança
- **Long Path Prefixes**: `\\?\C:\...`, `//?/C:/...` — bypass de limites de path
- **Trailing dots/spaces**: `.git.`, `.claude` — bypass por canonicalization
- **DOS Device Names**: `.git.CON`, `settings.json.PRN`, `.bashrc.AUX`
- **Three+ consecutive dots**: `.../file.txt` — bypass de path traversal
- **Detecção em TODAS as plataformas** — NTFS pode ser montado em Linux/macOS

**3. UNC Path Detection:**

- Paths começando com `\\` ou `//` são bloqueados (acesso a rede)

**4. Working Directory Enforcement:**

- FileRead/FileWrite/Edit só permitem paths dentro de working directories autorizados
- Additional Working Directories podem ser adicionadas pelo usuário

**Arquivos-chave:**

- `utils/permissions/filesystem.ts` — `hasSuspiciousWindowsPathPattern()`, `checkReadPermissionForTool()`

### MindFlow — Path Matching Básico

**Implementação atual:**

- `PathRule` com pattern matching (wildcard) para allow/deny
- `FilePermissionEnforcer` com working directory checks
- Path traversal detection (`../`)

**O que falta:**

- ❌ **Sem path canonicalization** — Symlinks não são resolvidos antes de checks
- ❌ **Sem Windows pattern detection** — 8.3 short names, ADS, DOS devices
- ❌ **Sem UNC path detection** — Paths de rede não são detectados
- ❌ **Sem symlink resolution caching** — Syscalls redundantes em cada check

**Recomendação:** Adicionar `resolve_symlinks=True` ao PathRule e implementar `has_suspicious_windows_pattern()`.

---

## 3. Sistema de Permissões

### Claude Code — 6 Modos + Pattern Matching

**Permission Modes:**

1. **default** — Usuário é perguntado por tool
2. **acceptEdits** — File writes no working directory são auto-aprovados
3. **plan** — Apenas leitura, nenhuma tool é executada
4. **bypassPermissions** — Todas as tools são auto-aprovadas
5. **dontAsk** — Nega todas as tools que precisariam de prompt
6. **auto** — Classificador decide (future: classifier + hooks)

**Permission Pipeline:**

```
1. Tool-wide DENY rules → deny imediato
2. Tool-wide ASK rules → ask imediato (exceto bypass mode)
3. Mode-based decisions
4. Tool.checkPermissions() → tool-specific logic
5. Tool-wide ALLOW rules → allow
6. Default: ask user
```

**Permission UI:**

- Diálogos visuais com "Always Allow", "Yes", "No"
- `SandboxPermissionRequest.tsx` — UI para network access
- `PermissionDialog.tsx` — Diálogo genérico de permissão
- `ApproveApiKey.tsx` — Aprovação de API keys customizadas

**Arquivos-chave:**

- `utils/permissions/permissions.ts` — `hasPermissionsToUseToolInner()`
- `components/permissions/SandboxPermissionRequest.tsx`

### MindFlow — 6 Modos + Pattern Matching (sem UI)

**Implementação atual:**

```python
# mindflow_backend/permissions/types.py
class PermissionMode(StrEnum):
    AUTO = "auto"
    PLAN = "plan"
    DEFAULT = "default"
    ACCEPT_EDITS = "accept_edits"
    BYPASS = "bypass"
    DONT_ASK = "dont_ask"
```

**Permission Pipeline (idêntica ao Claude Code):**

```
1. Tool-wide DENY rules → deny imediato
2. Tool-wide ASK rules → ask imediato
3. Mode-based decisions
4. Tool.check_permissions() → tool-specific logic
5. Tool-wide ALLOW rules → allow
6. Default: ask
```

**O que falta:**

- ❌ **Sem UI de permissão** — Nenhuma interface visual para approve/deny
- ❌ **Sem "Always Allow" persistence** — Regras não persistem em settings
- ❌ **Sem permission suggestions** — Opções de "allow for session", "allow always"
- ❌ **Sem permission mode cycling** — Shift+Tab para cycling modes

**Recomendação:** Implementar UI de permissão no frontend e persistência de regras via settings.

---

## 4. Hooks System

### Claude Code — Hooks com Input Mutation

**Hook Events:**

- `PreToolUse` — Antes da tool, pode **modificar input**
- `PostToolUse` — Depois da tool, pode modificar output
- `PostToolUseFailure` — Quando tool falha
- `Stop` — Session/agent stopped
- `UserPromptSubmit` — Quando usuário envia prompt
- `SessionStart` — Session iniciada
- `PermissionRequest` — Quando permissão seria pedida

**Hook Types:**

- **command** — Shell command com JSON output
- **prompt** — Prompt ao usuário
- **agent** — Executar agent especializado

**Key Feature — Input Mutation:**

```typescript
// PreToolUse hook pode modificar tool_input
// Hook recebe input original, retorna input modificado
// Hooks subsequentes veem o input modificado
yield { type: 'hookUpdatedInput', updatedInput: result.updatedInput }
```

**Arquivos-chave:**

- `utils/hooks.ts` — `runPreToolUseHooks()`, `executePermissionRequestHooks()`
- `services/tools/toolHooks.ts` — `runPreToolUseHooks()` com async generator
- `skills/bundled/updateConfig.ts` — Configuração de hooks via JSON

### MindFlow — Hooks Implementados

**Hook Events:**

```python
class HookEvent(StrEnum):
    PRE_TOOL_USE = "PreToolUse"
    POST_TOOL_USE = "PostToolUse"
    PRE_TOOL_USE_FAILURE = "PreToolUseFailure"
    POST_TOOL_USE_FAILURE = "PostToolUseFailure"
    STOP = "Stop"
    AGENT_START = "AgentStart"
    AGENT_STOP = "AgentStop"
    USER_PROMPT_SUBMIT = "UserPromptSubmit"
    SESSION_START = "SessionStart"
    PERMISSION_REQUEST = "PermissionRequest"
    PERMISSION_DENIED = "PermissionDenied"
    MISSION_START = "MissionStart"
    MISSION_STOP = "MissionStop"
```

**Implementações existentes:**

- `format_hook.py` — Auto-format após writes
- `lint_hook.py` — Lint após writes
- `test_hook.py` — Test runner após writes
- `git_hook.py` — Git hooks

**Status:** 🟢 Hooks system está bem implementado e funcional.

---

## 5. Bash Security Validators

### Claude Code — AST-Based Analysis

**Validators:**

- Command parsing com `splitCommand_DEPRECATED()` para compound commands
- Binary hijack detection (`LD_PRELOAD`, `LD_LIBRARY_PATH`, etc.)
- Excluded commands via settings
- Compound command analysis: `"echo hello && rm -rf /"` → verifica cada subcommand
- Wrapper stripping: `nice`, `time`, `sudo` (quando não excluído)

**Arquivo-chave:**

- `tools/BashTool/bashPermissions.ts` — `checkSandboxAutoAllow()`, `matchingRulesForInput()`

### MindFlow — 11 Validators (String-Based)

**Validators implementados:**

```python
# mindflow_backend/agents/tools/security/bash_validators.py
validate_carriage_return()      # \r injection
validate_control_characters()   # \x00, \x01
validate_newlines()             # \n injection
validate_command_injection()    # ;, |, $(), ``
validate_path_traversal()       # ../, /etc, /root
validate_dangerous_commands()   # rm -rf /, dd, mkfs
validate_curl_wget()            # curl | bash
validate_eval_like()            # eval, exec, source
validate_ifs_injection()        # IFS exploitation
validate_jq_command()           # jq command injection
validate_zsh_dangerous()        # zsh exploitation
```

**Master validator:**

```python
validate_bash_command()    # Executa todos os validators
is_command_safe()          # Helper boolean
get_command_security_issues() # Lista de issues
```

**O que falta:**

- ⚠️ **Sem AST parsing** — Validação é string-based, pode ser bypassed com encoding
- ⚠️ **Sem compound command splitting** — `echo safe && rm -rf /` pode não ser detectado
- ⚠️ **Sem binary hijack detection** — `LD_PRELOAD` não é detectado
- ✅ Tem 11 validators vs ~6 do Claude Code (mas menos sofisticados)

---

## 6. Segurança de APIs e Modelos

### Claude Code — Multi-Provider com Verificação

**API Providers Suportados:**

1. **Direct Anthropic API** — `ANTHROPIC_API_KEY`
2. **AWS Bedrock** — AWS credentials + region
3. **Google Vertex AI** — Google Auth + ADC
4. **Microsoft Foundry** — Azure AD / API key

**Security Features:**

- **API Key Verification:** `verifyApiKey()` faz chamada real para verificar
- **OAuth Token Management:** Refresh automático com fingerprint
- **Attribution Headers:** Fingerprint computation para tracking
- **Model Validation:** `validateModel()` verifica se modelo existe com API call
- **Model Allowlist:** `MODEL_ALIASES` + availableModels
- **Custom API Key Approval:** `ApproveApiKey.tsx` — UI para aprovar keys custom
- **Token Caching:** `validModelCache` para performance

**Arquivos-chave:**

- `services/api/client.ts` — Client factory por provider
- `utils/model/validateModel.ts` — Model validation
- `utils/auth.ts` — API key e OAuth management
- `services/api/claude.ts` — `verifyApiKey()`

### MindFlow — Provider Configuration Básico

**Implementação atual:**

```python
# mindflow_backend/query/providers/base.py
class Provider(ABC): ...
# Configured via settings
```

**O que falta:**

- ❌ **Sem API key verification** — Nenhuma verificação de que API key funciona
- ❌ **Sem model validation** — Modelos não são validados antes de uso
- ❌ **Sem model allowlist** — Qualquer modelo pode ser configurado
- ❌ **Sem OAuth management** — Sem token refresh ou attribution
- ❌ **Sem multi-provider UI** — Settings via config, não via UI

**Recomendação:** Implementar `validate_model()` com API call e API key refresh.

---

## 7. Proteção de Rede

### Claude Code — Network Restrictions por Host

**Sistema de Rede:**

- **Allowed hosts list** — Hosts pré-aprovados (localhost, etc.)
- **Domain preapproval** — `WebFetchTool/preapproved.ts` — Domínios code-related
- **Permission prompts** — Usuário aprova hosts desconhecidos
- **Swarm network sync** — Workers enviam permission requests ao leader
- **Deny network by default** — Sandbox inicia sem acesso à rede

**Arquivo-chave:**

- `tools/WebFetchTool/preapproved.ts` — "SECURITY WARNING: preapproved domains ONLY for WebFetch (GET only)"

### MindFlow — Sem Controle de Rede

**Status:** ❌ **Nenhum controle de rede implementado**

- Comandos bash podem acessar qualquer endpoint
- Sem validation de URLs
- Sem permission prompts para network access
- Sem domain allowlist

**Recomendação:** CRÍTICO — Implementar network restrictions no sandbox.

---

## 8. Segurança do Modelo (Model Security)

### Claude Code — Model Validation + Fingerprinting

**Features:**

- **Model validation:** `validateModel()` com API call real
- **Fingerprint computation:** Para OAuth attribution
- **3P Fallback:** Sugestão de modelo alternativo quando não encontrado
- **Betas management:** `getModelBetas()` por modelo
- **Structured outputs:** Beta headers para provider support

### MindFlow — Sem Model Security

**Status:** ❌ **Nenhuma model security implementada**

- Modelos são configurados mas não validados
- Sem fingerprinting
- Sem allowlist

---

## 9. Input Sanitization

### Claude Code — Comprehensive Sanitization

**Sanitization Points:**

- **Message sanitization:** `sanitizedMessages()` — remove invalid content
- **Image validation:** `validateImagesForAPI()` — size limits
- **Path sanitization:** Windows patterns, DOS devices, ADS
- **Command sanitization:** `splitCommand()`, binary hijack vars
- **Snippet tags:** `[id:]` tags para history snipping

### MindFlow — Sanitization Básica

**O que existe:**

- Path traversal detection
- Command injection detection

**O que falta:**

- ❌ Windows pattern detection
- ❌ Image validation
- ❌ Message sanitization

---

## 10. Circuit Breaker

### Ambos — Implementado 🟢

**Claude Code:**

- Circuit breaker no PermissionManager
- Failure threshold + recovery timeout

**MindFlow:**

```python
# mindflow_backend/permissions/manager.py
self._circuit_breaker = CircuitBreaker(
    name="permission-manager",
    failure_threshold=config.circuit_breaker_failure_threshold,
    recovery_timeout=config.circuit_breaker_recovery_timeout,
)
```

**Status:** Ambos implementam circuit breaker de forma similar. ✅

---

## 11. Swarm / Multi-Agent Security

### Claude Code — Mailbox Permission Sync

**Features:**

- **Leader/Worker architecture** — Workers enviam requests ao leader
- **SandboxPermissionRequestMessage** — Tipado com worker ID, name, color
- **Mailbox-based transport** — In-process ou file-based
- **Permission sync** — Regras de permissão sincronizadas entre agents

**Arquivo-chave:**

- `utils/swarm/permissionSync.ts` — `sendSandboxPermissionRequestViaMailbox()`
- `utils/teammateMailbox.ts` — `SandboxPermissionRequestMessage`

### MindFlow — Teams com XMPP, Sem Permission Sync

**O que existe:**

- Team sessions com XMPP
- Mission DAG para coordenação
- Team orchestrator

**O que falta:**

- ❌ **Sem permission sync** — Permissões não são sincronizadas entre agents
- ❌ **Sem leader election** — Sem mecanismo de leader para aprovação
- ❌ **Sem mailbox** — Comunicação via XMPP, sem mailbox de permissões

---

## Resumo de Gaps Críticos (🔴)

| # | Gap | Risco | Prioridade |
|---|-----|-------|------------|
| 1 | **Sem sandbox de execução (bwrap/nsjail)** | RCE no host | P0 |
| 2 | **Sem path canonicalization** | Bypass de segurança via symlinks | P0 |
| 3 | **Sem controle de rede** | Data exfiltration | P0 |
| 4 | **Sem model validation** | Modelo inválido ou malicioso | P1 |
| 5 | **Sem Windows pattern detection** | Bypass em NTFS | P1 |
| 6 | **Sem API key verification** | Key inválida causa falhas silenciosas | P1 |

## Resumo de Gaps Parciais (🟡)

| # | Gap | Impacto | Prioridade |
|---|-----|---------|------------|
| 1 | **Sem UI de permissão** | UX degradada | P1 |
| 2 | **Bash validators sem AST** | Falsos negativos | P1 |
| 3 | **Sem multi-provider UI** | Configuração complexa | P2 |
| 4 | **Sem permission persistence** | Regras perdidas por sessão | P2 |
| 5 | **Sem binary hijack detection** | LD_PRELOAD attacks | P1 |
| 6 | **Sem permission sync em swarm** | Agents com permissões inconsistentes | P1 |

## Itens Implementados Equivalentemente (🟢)

| # | Feature | Status |
|---|---------|--------|
| 1 | Permission modes (6 modos) | ✅ Implementado |
| 2 | Permission pipeline (deny→ask→mode→tool→allow→default) | ✅ Implementado |
| 3 | Hooks system (PreToolUse, PostToolUse, etc.) | ✅ Implementado |
| 4 | Circuit Breaker | ✅ Implementado |
| 5 | Pattern matching (wildcards) | ✅ Implementado |
| 6 | Bash validators (11 validators) | ✅ Parcialmente |

---

## Roadmap Recomendado

### Phase 1 — Critical (P0, 1-2 semanas)

1. **Implementar bubblewrap sandbox** para execução de comandos bash
2. **Adicionar path canonicalization** com symlink resolution
3. **Implementar network restrictions** com allowed hosts list

### Phase 2 — High Priority (P1, 2-3 semanas)

1. **Implementar UI de permissão** no frontend
2. **Adicionar AST-based bash validation** (usar `shlex` ou `bashlex`)
3. **Implementar binary hijack detection** (`LD_PRELOAD`, `LD_LIBRARY_PATH`)
4. **Adicionar model validation** com API call
5. **Implementar API key verification**
6. **Adicionar Windows pattern detection**

### Phase 3 — Medium Priority (P2, 3-4 semanas)

1. **Implementar permission persistence** em settings
2. **Adicionar permission sync** entre agents (mailbox)
3. **Implementar image validation** para message sanitization
4. **Adicionar OAuth/token management** para multi-provider

---

## Conclusão

O MindFlow tem uma **boa fundação de segurança** inspirada no Claude Code, com:

- Sistema de permissões de 6 modos funcional
- Hooks system completo e extensível
- 11 bash security validators
- Circuit breaker integrado

Porém, **gaps críticos de segurança** existem nas áreas de:

1. **Isolamento de execução** — sem sandbox de processo
2. **Proteção de filesystem** — sem canonicalization de paths
3. **Segurança de rede** — sem controle de acesso à rede

Estes gaps devem ser tratados como **prioridade máxima (P0)** antes de usar o MindFlow em ambientes de produção com código não confiável.
