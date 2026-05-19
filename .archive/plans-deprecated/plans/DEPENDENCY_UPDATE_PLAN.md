# Plano de Atualização de Dependências - MindFlow

**Data:** 2026-03-31  
**Objetivo:** Atualizar dependências frontend (npm) e backend (Python) de forma segura e incremental

---

## 📊 Análise Inicial

### Frontend (18 pacotes desatualizados)

#### 🔴 **BREAKING CHANGES (Major versions)**
- `typescript: 5.9.3 → 6.0.2` - **ALTO RISCO**
- `eslint: 9.39.3 → 10.1.0` - **ALTO RISCO**
- `@eslint/js: 9.39.3 → 10.0.1` - **ALTO RISCO**
- `@vitejs/plugin-react: 5.1.4 → 6.0.1` - **MÉDIO RISCO**
- `globals: 16.5.0 → 17.4.0` - **MÉDIO RISCO**
- `lucide-react: 0.575.0 → 1.7.0` - **MÉDIO RISCO**

#### 🟡 **MINOR UPDATES (Novos recursos, compatível)**
- `@uiw/react-md-editor: 4.0.11 → 4.1.0`
- `framer-motion: 12.34.3 → 12.38.0`
- `typescript-eslint: 8.56.1 → 8.58.0`

#### 🟢 **PATCH UPDATES (Bug fixes, seguro)**
- `@tailwindcss/vite: 4.2.1 → 4.2.2`
- `jsdom: 29.0.0 → 29.0.1`
- `react-router-dom: 7.13.1 → 7.13.2`
- `tailwindcss: 4.2.1 → 4.2.2`
- `vite: 8.0.0-beta.16 → 8.0.3`
- `vitest: 4.1.0 → 4.1.2`
- `zustand: 5.0.11 → 5.0.12`
- `@types/node: 24.11.0 → 24.12.0` (wanted version)
- `eslint-plugin-react-refresh: 0.4.26 → 0.4.26` (sem mudança)

### Backend (28+ pacotes desatualizados)

#### 🟡 **MINOR/PATCH UPDATES**
- `deepagents: 0.4.4 → 0.4.12` - **IMPORTANTE** (8 minor versions)
- `langgraph: 1.0.9 → 1.1.3` - **IMPORTANTE**
- `langchain: 1.2.10 → 1.2.13`
- `langchain-core: 1.2.16 → 1.2.23`
- `langchain-anthropic: 1.3.4 → 1.4.0`
- `fastapi: 0.133.1 → 0.135.2`
- `anthropic: 0.84.0 → 0.86.0`
- `grpcio: 1.78.0 → 1.80.0`
- `google-cloud-*`: Várias atualizações patch/minor
- Outros: patches seguros

---

## 🎯 Estratégia de Atualização

### Princípios
1. **Incremental** - Uma categoria por vez
2. **Testado** - Testes completos após cada fase
3. **Reversível** - Commits separados para rollback fácil
4. **Documentado** - Changelog de breaking changes

### Ordem de Execução
```
Fase 1: Patches seguros (Frontend + Backend)
Fase 2: Minor updates (Frontend + Backend)
Fase 3: Breaking changes (um por vez, com análise)
```

---

## 📋 Fase 1: Patches Seguros (BAIXO RISCO)

### Frontend - Patches
```bash
# Atualizar apenas patches (dentro do range semver)
npm update @tailwindcss/vite tailwindcss jsdom react-router-dom zustand vitest

# Atualizar Vite beta (8.0.0-beta.16 → 8.0.3)
npm install vite@8.0.3

# Atualizar @types/node para wanted version
npm install --save-dev @types/node@24.12.0
```

### Backend - Patches
```bash
cd python

# Atualizar patches seguros
uv pip install --upgrade \
  aio-pika \
  aiormq \
  anyio \
  charset-normalizer \
  cryptography \
  google-api-core \
  google-cloud-core \
  google-resumable-media \
  googleapis-common-protos \
  jsonpointer
```

### ✅ Checklist Fase 1
- [ ] Backup do estado atual (git commit)
- [ ] Executar atualizações
- [ ] `npm run lint` (frontend)
- [ ] `npm run test` (frontend)
- [ ] `npm run build` (frontend)
- [ ] `cd python && make check` (backend)
- [ ] `cd python && uv run pytest` (backend)
- [ ] Testar aplicação manualmente (smoke test)
- [ ] Commit: `chore: update patch dependencies (frontend + backend)`

---

## 📋 Fase 2: Minor Updates (MÉDIO RISCO)

### Frontend - Minor
```bash
# Atualizar minor versions
npm install \
  @uiw/react-md-editor@4.1.0 \
  framer-motion@12.38.0 \
  typescript-eslint@8.58.0
```

### Backend - Minor (Críticos primeiro)
```bash
cd python

# Grupo 1: Core framework updates
uv pip install --upgrade \
  fastapi==0.135.2 \
  anthropic==0.86.0 \
  grpcio==1.80.0 \
  grpcio-status==1.80.0 \
  grpcio-tools==1.80.0

# Grupo 2: LangChain ecosystem
uv pip install --upgrade \
  langchain==1.2.13 \
  langchain-core==1.2.23 \
  langchain-anthropic==1.4.0 \
  langchain-openai==1.1.12

# Grupo 3: DeepAgents + LangGraph (IMPORTANTE)
uv pip install --upgrade \
  deepagents==0.4.12 \
  langgraph==1.1.3

# Grupo 4: Google Cloud
uv pip install --upgrade \
  google-auth \
  google-cloud-aiplatform \
  google-cloud-bigquery \
  google-cloud-storage \
  google-cloud-vectorsearch \
  google-genai
```

### ✅ Checklist Fase 2
- [ ] Backup (git commit antes)
- [ ] Executar atualizações grupo por grupo
- [ ] Testes após cada grupo
- [ ] `npm run lint && npm run test && npm run build`
- [ ] `cd python && make check && uv run pytest`
- [ ] Testar features críticas:
  - [ ] Autenticação
  - [ ] Criação de agentes
  - [ ] Execução de missões
  - [ ] Chat interface
  - [ ] gRPC communication
- [ ] Commit: `chore: update minor dependencies (frontend + backend)`

---

## 📋 Fase 3: Breaking Changes (ALTO RISCO)

### ⚠️ Análise Necessária Antes de Atualizar

#### TypeScript 5.9 → 6.0
**Impacto:** Mudanças no sistema de tipos, novas regras de inferência  
**Ação:**
1. Ler changelog: https://devblogs.microsoft.com/typescript/announcing-typescript-6-0/
2. Verificar breaking changes
3. Atualizar em branch separada
4. Rodar `tsc --noEmit` para encontrar erros
5. Corrigir tipos quebrados
6. Testar extensivamente

**Comando:**
```bash
npm install --save-dev typescript@6.0.2
```

#### ESLint 9 → 10
**Impacto:** Novas regras, mudanças na configuração flat config  
**Ação:**
1. Ler migration guide: https://eslint.org/docs/latest/use/migrate-to-10.0.0
2. Atualizar `eslint.config.js`
3. Verificar compatibilidade de plugins
4. Testar linting

**Comando:**
```bash
npm install --save-dev eslint@10.1.0 @eslint/js@10.0.1
```

#### Outras Breaking Changes
- `@vitejs/plugin-react: 5 → 6` - Verificar changelog Vite
- `globals: 16 → 17` - Verificar mudanças em variáveis globais
- `lucide-react: 0.x → 1.x` - Verificar API changes de ícones

### ✅ Checklist Fase 3 (Para cada breaking change)
- [ ] Criar branch: `feat/update-{package}-v{version}`
- [ ] Ler changelog completo
- [ ] Documentar breaking changes esperados
- [ ] Atualizar pacote
- [ ] Corrigir erros de compilação
- [ ] Corrigir erros de lint
- [ ] Atualizar testes se necessário
- [ ] Rodar suite completa de testes
- [ ] Code review com **code-reviewer** agent
- [ ] Merge para main
- [ ] Commit: `feat: upgrade {package} to v{version}`

---

## 🔄 Estratégia de Rollback

### Se algo quebrar:
```bash
# Reverter último commit
git revert HEAD

# Ou resetar para commit anterior
git reset --hard HEAD~1

# Reinstalar dependências limpas
rm -rf node_modules package-lock.json
npm install

# Backend
cd python
uv sync --reinstall
```

---

## 📝 Ordem de Execução Recomendada

```
1. ✅ Fase 1: Patches (Frontend + Backend) - 1 commit
2. ✅ Fase 2: Minor (Frontend) - 1 commit
3. ✅ Fase 2: Minor (Backend Grupo 1) - 1 commit
4. ✅ Fase 2: Minor (Backend Grupo 2) - 1 commit
5. ✅ Fase 2: Minor (Backend Grupo 3) - 1 commit
6. ✅ Fase 2: Minor (Backend Grupo 4) - 1 commit
7. ⚠️  Fase 3: TypeScript 6.0 - branch separada
8. ⚠️  Fase 3: ESLint 10 - branch separada
9. ⚠️  Fase 3: Outros breaking - branches separadas
```

---

## 🧪 Testes Obrigatórios Após Cada Fase

### Frontend
```bash
npm run lint          # ESLint
npm run test          # Vitest unit tests
npm run build         # Production build
npm run preview       # Test build locally
```

### Backend
```bash
cd python
make check            # ruff format + lint + typecheck
uv run pytest         # All tests
uv run pytest -m integration  # Integration tests
```

### Manual Testing
- [ ] Login/Logout
- [ ] Criar novo agente
- [ ] Executar missão simples
- [ ] Verificar logs no console
- [ ] Testar chat interface
- [ ] Verificar comunicação gRPC

---

## 📊 Métricas de Sucesso

- ✅ Todos os testes passando
- ✅ Build sem erros
- ✅ Lint sem warnings
- ✅ Aplicação funcional em dev
- ✅ Sem regressões em features existentes
- ✅ Cobertura de testes mantida (≥80%)

---

## 🚨 Riscos Identificados

### Alto Risco
1. **TypeScript 6.0** - Pode quebrar tipos em todo o frontend
2. **ESLint 10** - Pode exigir reescrita de config
3. **deepagents 0.4.4 → 0.4.12** - 8 minor versions, pode ter breaking changes não documentados

### Mitigação
- Testar em branch separada
- Usar **code-reviewer** agent após mudanças
- Manter commits atômicos para rollback fácil
- Documentar todos os problemas encontrados

---

## 📅 Timeline Estimado

- **Fase 1 (Patches):** 30 minutos
- **Fase 2 (Minor):** 2-3 horas
- **Fase 3 (Breaking):** 1-2 dias (depende dos problemas encontrados)

**Total:** 2-3 dias para atualização completa e segura

---

## ✅ Aprovação para Início

Antes de começar:
- [ ] Backup completo do projeto
- [ ] Todos os testes atuais passando
- [ ] Branch limpa (sem mudanças não commitadas)
- [ ] Tempo disponível para rollback se necessário
