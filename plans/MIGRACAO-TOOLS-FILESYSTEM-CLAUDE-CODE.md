# Plano de Migração: Tools FileSystem para Padrão Claude Code

**Data:** 2026-04-01  
**Objetivo:** Migrar todas as tools de FileSystem e Shell do MindFlow para seguir os padrões de qualidade, segurança e arquitetura do Claude Code.

---

## Análise Comparativa

### Claude Code (Referência)
- **Localização:** `/home/levybonito/Projetos/MindFlow/claude/tools/`
- **Linguagem:** TypeScript
- **Características:**
  - Validação de segurança multi-camada (AST parsing, regex validators)
  - Sistema de permissões granular com wildcards
  - Integração com git diff, file history, LSP
  - Schemas com Zod + validação estrita
  - UI components React para visualização
  - Error handling detalhado com sugestões contextuais
  - Suporte a múltiplos formatos (imagens, PDFs, notebooks)

### MindFlow (Estado Atual)
- **Localização:** `/home/levybonito/Projetos/MindFlow/python/mindflow_backend/agents/tools/`
- **Linguagem:** Python
- **Características:**
  - Validação de segurança básica (regex patterns)
  - Schemas com Pydantic
  - Controles de workspace/sandbox básicos
  - Error handling funcional mas limitado
  - Sem integração com git/LSP
  - Sem suporte a formatos especiais

---

## Fases de Migração

### **FASE 1: Análise e Documentação** (1-2 dias)

#### Objetivos
- Mapear todas as tools existentes em ambos os repositórios
- Documentar diferenças de implementação
- Identificar gaps de funcionalidade
- Definir prioridades de migração

#### Tarefas
1. **Inventário Completo**
   - [ ] Listar todas as tools de FileSystem do Claude Code
   - [ ] Listar todas as tools de FileSystem do MindFlow
   - [ ] Criar matriz de comparação (features × tools)

2. **Análise de Schemas**
   - [ ] Documentar schema Zod do Claude Code
   - [ ] Documentar schema Pydantic do MindFlow
   - [ ] Mapear equivalências de tipos
   - [ ] Identificar campos ausentes no MindFlow

3. **Análise de Segurança**
   - [ ] Documentar validadores do Claude Code (bashSecurity.ts)
   - [ ] Documentar validadores do MindFlow (security.py)
   - [ ] Listar vulnerabilidades não cobertas
   - [ ] Priorizar validações críticas

4. **Análise de Permissões**
   - [ ] Documentar sistema de permissões do Claude Code
   - [ ] Documentar sistema de permissões do MindFlow
   - [ ] Identificar gaps de controle de acesso

#### Entregáveis
- `docs/tools/ANALISE-COMPARATIVA-TOOLS.md`
- `docs/tools/MATRIZ-FEATURES-TOOLS.md`
- `docs/tools/GAPS-SEGURANCA.md`

---

### **FASE 2: Schemas e Interfaces** (2-3 dias)

#### Objetivos
- Criar schemas Pydantic equivalentes aos schemas Zod do Claude Code
- Padronizar interfaces de tools
- Implementar validação estrita de parâmetros

#### Tarefas

1. **Atualizar Base Schemas**
   - [ ] Expandir `ToolParameter` com todos os campos do Claude Code
   - [ ] Adicionar `format`, `constraints`, `validation_rules`
   - [ ] Implementar `ToolMetadata` para tracking (git, LSP, history)
   - [ ] Criar `ToolPermissionContext` para controle de acesso

2. **FileSystem Schemas**
   - [ ] Atualizar `READ_FILE_SCHEMA`:
     - Adicionar `offset`, `limit`, `pages` (PDF)
     - Adicionar `include_line_numbers`, `encoding`
     - Adicionar `follow_symlinks`, `resolve_path`
   - [ ] Atualizar `WRITE_FILE_SCHEMA`:
     - Adicionar `create_dirs`, `backup`, `overwrite`
     - Adicionar `preserve_permissions`, `atomic_write`
   - [ ] Atualizar `EDIT_FILE_SCHEMA`:
     - Adicionar `replace_all`, `preserve_quotes`
     - Adicionar `dry_run`, `show_diff`
   - [ ] Criar `GLOB_SEARCH_SCHEMA` completo:
     - Adicionar `exclude_patterns`, `follow_symlinks`
     - Adicionar `max_depth`, `file_types`
   - [ ] Criar `GREP_SEARCH_SCHEMA` completo:
     - Adicionar `-A`, `-B`, `-C` (context lines)
     - Adicionar `multiline`, `case_sensitive`
     - Adicionar `output_mode` (content/files/count)

3. **Shell/Bash Schemas**
   - [ ] Criar `BASH_TOOL_SCHEMA`:
     - Parâmetros: `command`, `timeout`, `working_dir`
     - Parâmetros: `environment`, `capture_output`, `shell`
     - Parâmetros: `check_return_code`, `run_in_background`
   - [ ] Adicionar `BashPermissionContext`
   - [ ] Adicionar `BashSecurityPolicy`

4. **Validation Rules**
   - [ ] Implementar `field_validator` para paths (absolute, exists, readable)
   - [ ] Implementar `model_validator` para combinações de parâmetros
   - [ ] Adicionar validação de encoding
   - [ ] Adicionar validação de file size limits

#### Entregáveis
- `python/mindflow_backend/schemas/tools/filesystem_schemas_v2.py`
- `python/mindflow_backend/schemas/tools/shell_schemas_v2.py`
- `python/mindflow_backend/schemas/tools/tool_metadata.py`
- `python/mindflow_backend/schemas/tools/tool_permissions.py`

---

### **FASE 3: Segurança e Validação** (3-4 dias)

#### Objetivos
- Implementar validação de segurança equivalente ao Claude Code
- Criar sistema de permissões granular
- Adicionar proteções contra ataques conhecidos

#### Tarefas

1. **Bash Security Validators**
   - [ ] Portar `validateCommandInjection` (command injection)
   - [ ] Portar `validatePathTraversal` (path traversal)
   - [ ] Portar `validateDangerousCommands` (rm -rf, dd, mkfs, etc.)
   - [ ] Portar `validateEvalLike` (eval, exec, source)
   - [ ] Portar `validateNewlines` (newline injection)
   - [ ] Portar `validateCarriageReturn` (CR injection)
   - [ ] Portar `validateIFSInjection` (IFS manipulation)
   - [ ] Portar `validateJqCommand` (jq system() function)
   - [ ] Portar `validateZshDangerousCommands` (zmodload, etc.)
   - [ ] Portar `validateMalformedTokenInjection` (unbalanced delimiters)

2. **Filesystem Security**
   - [ ] Implementar `checkReadPermissionForTool`
   - [ ] Implementar `checkWritePermissionForTool`
   - [ ] Adicionar validação de symlinks
   - [ ] Adicionar validação de device files (`/dev/zero`, `/dev/random`)
   - [ ] Adicionar proteção contra race conditions (TOCTOU)
   - [ ] Implementar `WorkspaceSecurityError` detalhado

3. **Permission System**
   - [ ] Criar `PermissionRule` (allow/deny/ask patterns)
   - [ ] Criar `PermissionMatcher` (wildcard matching)
   - [ ] Criar `PermissionDecision` (behavior + reason)
   - [ ] Implementar `matchWildcardPattern` (glob-style)
   - [ ] Adicionar permission caching

4. **Sandbox Enhancements**
   - [ ] Adicionar `SandboxMode.READ_ONLY` enforcement
   - [ ] Adicionar `SandboxMode.FULL` com write validation
   - [ ] Implementar `validate_shell_command` robusto
   - [ ] Adicionar timeout enforcement
   - [ ] Adicionar output size limits

5. **Security Testing**
   - [ ] Criar test suite para command injection
   - [ ] Criar test suite para path traversal
   - [ ] Criar test suite para permission bypass
   - [ ] Adicionar fuzzing tests

#### Entregáveis
- `python/mindflow_backend/agents/tools/security/bash_validators.py`
- `python/mindflow_backend/agents/tools/security/filesystem_validators.py`
- `python/mindflow_backend/agents/tools/security/permission_system.py`
- `python/tests/security/test_bash_security.py`
- `python/tests/security/test_filesystem_security.py`

---

### **FASE 4: Implementação Core Tools** (4-5 dias)

#### Objetivos
- Reimplementar tools principais com padrões Claude Code
- Adicionar features ausentes
- Manter backward compatibility

#### Tarefas

1. **FileReadTool v2**
   - [ ] Adicionar suporte a `offset` e `limit`
   - [ ] Adicionar `include_line_numbers`
   - [ ] Adicionar detecção de encoding automática
   - [ ] Adicionar suporte a imagens (base64 encoding)
   - [ ] Adicionar suporte a PDFs (com `pages` parameter)
   - [ ] Adicionar suporte a notebooks (.ipynb)
   - [ ] Adicionar blocked device path detection
   - [ ] Adicionar macOS screenshot path resolution
   - [ ] Implementar `suggestPathUnderCwd` para erros
   - [ ] Adicionar file modification time tracking

2. **FileWriteTool v2**
   - [ ] Adicionar `create_dirs` automático
   - [ ] Adicionar `backup` antes de overwrite
   - [ ] Adicionar atomic write (write to temp + rename)
   - [ ] Adicionar git diff generation
   - [ ] Adicionar file history tracking
   - [ ] Implementar `preserve_permissions`
   - [ ] Adicionar LSP notification (file updated)
   - [ ] Adicionar skill directory discovery
   - [ ] Implementar structured patch output

3. **FileEditTool v2**
   - [ ] Adicionar `replace_all` flag
   - [ ] Adicionar `preserve_quotes` (single/double)
   - [ ] Adicionar `dry_run` mode
   - [ ] Implementar fuzzy matching (`findActualString`)
   - [ ] Adicionar file modification time check (TOCTOU)
   - [ ] Adicionar git diff generation
   - [ ] Adicionar file history tracking
   - [ ] Implementar `areFileEditsInputsEquivalent` (dedup)
   - [ ] Adicionar line ending preservation
   - [ ] Adicionar encoding preservation

4. **GlobTool v2**
   - [ ] Adicionar `exclude_patterns`
   - [ ] Adicionar `follow_symlinks` flag
   - [ ] Adicionar `max_depth` limit
   - [ ] Adicionar `file_types` filter
   - [ ] Implementar sorting by modification time
   - [ ] Adicionar permission checking
   - [ ] Adicionar `.gitignore` respect
   - [ ] Implementar `head_limit` e `offset`

5. **GrepTool v2**
   - [ ] Adicionar context lines (`-A`, `-B`, `-C`)
   - [ ] Adicionar `multiline` mode
   - [ ] Adicionar `output_mode` (content/files/count)
   - [ ] Adicionar `case_sensitive` flag
   - [ ] Implementar `head_limit` e `offset`
   - [ ] Adicionar file type filtering
   - [ ] Adicionar glob pattern filtering
   - [ ] Implementar ripgrep integration
   - [ ] Adicionar permission checking

6. **BashTool v2**
   - [ ] Implementar todos os security validators
   - [ ] Adicionar `run_in_background` support
   - [ ] Adicionar progress reporting (>2s commands)
   - [ ] Implementar command semantic analysis
   - [ ] Adicionar git operation tracking
   - [ ] Implementar `isReadOnly` detection
   - [ ] Adicionar sed edit command parsing
   - [ ] Implementar sandbox integration
   - [ ] Adicionar output truncation handling
   - [ ] Implementar image output detection

#### Entregáveis
- `python/mindflow_backend/agents/tools/filesystem/file_operations_v2.py`
- `python/mindflow_backend/agents/tools/filesystem/search_tools_v2.py`
- `python/mindflow_backend/agents/tools/system/shell_executor_v2.py`
- `python/tests/unit/tools/test_filesystem_v2.py`
- `python/tests/unit/tools/test_shell_v2.py`

---

### **FASE 5: Integração e Features Avançadas** (3-4 dias)

#### Objetivos
- Integrar tools com sistemas externos (git, LSP)
- Adicionar tracking e analytics
- Implementar caching inteligente

#### Tarefas

1. **Git Integration**
   - [ ] Implementar `fetchSingleFileGitDiff`
   - [ ] Adicionar git status tracking
   - [ ] Implementar `trackGitOperations`
   - [ ] Adicionar git blame integration
   - [ ] Implementar diff visualization

2. **File History**
   - [ ] Implementar `fileHistoryTrackEdit`
   - [ ] Adicionar snapshot creation
   - [ ] Implementar history rollback
   - [ ] Adicionar history visualization

3. **LSP Integration** (Opcional - se aplicável)
   - [ ] Adicionar diagnostic tracking
   - [ ] Implementar file update notifications
   - [ ] Adicionar symbol resolution
   - [ ] Implementar code navigation

4. **Analytics e Metrics**
   - [ ] Implementar `logFileOperation`
   - [ ] Adicionar execution time tracking
   - [ ] Implementar error rate monitoring
   - [ ] Adicionar usage analytics

5. **Caching**
   - [ ] Implementar result caching
   - [ ] Adicionar cache invalidation
   - [ ] Implementar TTL-based expiration
   - [ ] Adicionar cache size limits

6. **Skill Discovery**
   - [ ] Implementar `discoverSkillDirsForPaths`
   - [ ] Adicionar automatic skill activation
   - [ ] Implementar conditional skills

#### Entregáveis
- `python/mindflow_backend/agents/tools/integrations/git_integration.py`
- `python/mindflow_backend/agents/tools/integrations/file_history.py`
- `python/mindflow_backend/agents/tools/analytics/tool_metrics.py`
- `python/mindflow_backend/agents/tools/caching/result_cache.py`

---

### **FASE 6: Testing e Validação** (3-4 dias)

#### Objetivos
- Criar test suite completo
- Validar segurança
- Testar integração com LLM

#### Tarefas

1. **Unit Tests**
   - [ ] Tests para cada tool (read, write, edit, glob, grep, bash)
   - [ ] Tests para validators de segurança
   - [ ] Tests para permission system
   - [ ] Tests para schemas e validação
   - [ ] Coverage mínimo: 80%

2. **Integration Tests**
   - [ ] Tests de integração tool + LLM
   - [ ] Tests de integração tool + sandbox
   - [ ] Tests de integração tool + git
   - [ ] Tests de integração tool + file history

3. **Security Tests**
   - [ ] Penetration tests (command injection)
   - [ ] Path traversal tests
   - [ ] Permission bypass tests
   - [ ] Fuzzing tests
   - [ ] OWASP Top 10 validation

4. **Performance Tests**
   - [ ] Benchmark de leitura de arquivos grandes
   - [ ] Benchmark de busca (grep/glob)
   - [ ] Benchmark de execução shell
   - [ ] Memory leak detection

5. **Compatibility Tests**
   - [ ] Backward compatibility com tools antigas
   - [ ] Cross-platform tests (Linux/Mac/Windows)
   - [ ] Python version compatibility (3.11+)

#### Entregáveis
- `python/tests/unit/tools/` (completo)
- `python/tests/integration/tools/` (completo)
- `python/tests/security/` (completo)
- `python/tests/performance/` (completo)
- `docs/testing/TOOL-TEST-REPORT.md`

---

### **FASE 7: Documentação e Migração** (2-3 dias)

#### Objetivos
- Documentar novas tools
- Criar guia de migração
- Deprecar tools antigas gradualmente

#### Tarefas

1. **Documentação Técnica**
   - [ ] API reference para cada tool
   - [ ] Schema documentation
   - [ ] Security guidelines
   - [ ] Permission system guide
   - [ ] Integration guides (git, LSP, etc.)

2. **Guias de Uso**
   - [ ] Quick start guide
   - [ ] Common patterns
   - [ ] Error handling guide
   - [ ] Troubleshooting guide

3. **Migration Guide**
   - [ ] Mapping old → new tools
   - [ ] Breaking changes list
   - [ ] Migration checklist
   - [ ] Code examples (before/after)

4. **Deprecation Plan**
   - [ ] Marcar tools antigas como deprecated
   - [ ] Adicionar warnings em runtime
   - [ ] Criar aliases para backward compatibility
   - [ ] Definir timeline de remoção

5. **Training Materials**
   - [ ] Tutorial videos (opcional)
   - [ ] Example notebooks
   - [ ] Best practices guide

#### Entregáveis
- `docs/tools/API-REFERENCE.md`
- `docs/tools/MIGRATION-GUIDE.md`
- `docs/tools/SECURITY-GUIDE.md`
- `docs/tools/BEST-PRACTICES.md`
- `CHANGELOG.md` (atualizado)

---

## Riscos e Mitigações

### Riscos Identificados

1. **Breaking Changes**
   - **Risco:** Mudanças nos schemas podem quebrar código existente
   - **Mitigação:** Manter backward compatibility via aliases, deprecation gradual

2. **Performance Degradation**
   - **Risco:** Validações extras podem impactar performance
   - **Mitigação:** Benchmarking contínuo, caching agressivo, validação lazy

3. **Security Gaps**
   - **Risco:** Portar validadores pode introduzir bugs
   - **Mitigação:** Code review rigoroso, security testing extensivo, fuzzing

4. **Complexity Increase**
   - **Risco:** Código mais complexo = mais difícil de manter
   - **Mitigação:** Documentação detalhada, testes abrangentes, code comments

5. **Integration Issues**
   - **Risco:** Integração com git/LSP pode falhar em alguns ambientes
   - **Mitigação:** Graceful degradation, feature flags, error handling robusto

---

## Métricas de Sucesso

### Quantitativas
- [ ] 100% das tools principais migradas
- [ ] 80%+ test coverage
- [ ] 0 vulnerabilidades críticas (security scan)
- [ ] <10% performance degradation
- [ ] 100% backward compatibility (via aliases)

### Qualitativas
- [ ] Código mais legível e manutenível
- [ ] Documentação completa e clara
- [ ] Feedback positivo da equipe
- [ ] Redução de bugs em produção
- [ ] Melhor experiência do desenvolvedor

---

## Timeline Estimado

| Fase | Duração | Dependências |
|------|---------|--------------|
| Fase 1: Análise | 1-2 dias | - |
| Fase 2: Schemas | 2-3 dias | Fase 1 |
| Fase 3: Segurança | 3-4 dias | Fase 2 |
| Fase 4: Core Tools | 4-5 dias | Fase 3 |
| Fase 5: Integração | 3-4 dias | Fase 4 |
| Fase 6: Testing | 3-4 dias | Fase 5 |
| Fase 7: Documentação | 2-3 dias | Fase 6 |
| **TOTAL** | **18-25 dias** | |

---

## Próximos Passos

1. **Aprovação do Plano**
   - Revisar este documento
   - Ajustar prioridades se necessário
   - Aprovar timeline e recursos

2. **Kickoff Fase 1**
   - Criar branch `feature/tools-migration-claude-code`
   - Iniciar análise comparativa
   - Documentar findings

3. **Setup Ambiente**
   - Configurar ambiente de desenvolvimento
   - Instalar dependências necessárias
   - Configurar CI/CD para testes

---

## Referências

### Claude Code
- `/home/levybonito/Projetos/MindFlow/claude/tools/FileReadTool/`
- `/home/levybonito/Projetos/MindFlow/claude/tools/FileWriteTool/`
- `/home/levybonito/Projetos/MindFlow/claude/tools/FileEditTool/`
- `/home/levybonito/Projetos/MindFlow/claude/tools/GlobTool/`
- `/home/levybonito/Projetos/MindFlow/claude/tools/GrepTool/`
- `/home/levybonito/Projetos/MindFlow/claude/tools/BashTool/`

### MindFlow
- `/home/levybonito/Projetos/MindFlow/python/mindflow_backend/agents/tools/filesystem/`
- `/home/levybonito/Projetos/MindFlow/python/mindflow_backend/agents/tools/system/`
- `/home/levybonito/Projetos/MindFlow/python/mindflow_backend/schemas/tools/`

### Documentação
- Claude Code: `claude/docs/` (se disponível)
- MindFlow: `docs/architecture/`
- Security: OWASP Top 10, CWE Top 25

---

**Última Atualização:** 2026-04-01  
**Status:** Aguardando Aprovação  
**Responsável:** Levy Bonito
