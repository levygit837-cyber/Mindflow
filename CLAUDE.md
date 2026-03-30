<!-- gitnexus:start -->
# GitNexus MCP

This project is indexed by GitNexus as **MindFlow** (93539 symbols, 234822 relationships, 300 execution flows).

## Always Start Here

1. **Read `gitnexus://repo/{name}/context`** — codebase overview + check index freshness
2. **Match your task to a skill below** and **read that skill file**
3. **Follow the skill's workflow and checklist**

> If step 1 warns the index is stale, run `npx gitnexus analyze` in the terminal first.

## Skills

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->

---

# Context+ MCP — Agent Rules

> **MCP Server:** `contextplus` — Semantic Intelligence for Large-Scale Engineering

## 🚫 PROIBIDO: Leitura Direta de Arquivos

**Nunca leia arquivos diretamente** usando ferramentas nativas como `read_file`, `cat`, `open()`, ou qualquer outra forma de acesso direto ao conteúdo de arquivos do projeto.

Isso inclui, mas não se limita a:
- `read_file` / `readFile`
- `cat <arquivo>`
- `open(path).read()`
- `fs.readFileSync` / `fs.readFile`
- Qualquer tool nativa de leitura de arquivos do IDE

**Toda navegação e leitura de código DEVE passar exclusivamente pelas ferramentas do MCP `contextplus`.**

A única exceção permitida é quando `propose_commit` precisar do conteúdo atual para gerar o novo conteúdo — e mesmo assim, use `get_file_skeleton` antes para minimizar tokens.

## ✅ Fluxo Obrigatório de Execução

Siga esta sequência em todas as tarefas:

```
1. search_memory_graph     → Recuperar contexto de sessões anteriores (SEMPRE primeiro)
2. get_context_tree        → Mapear estrutura do projeto
3. get_file_skeleton       → Inspecionar assinaturas antes de qualquer leitura
4. semantic_code_search    → Encontrar arquivos relevantes por significado
5. get_blast_radius        → Antes de modificar ou deletar qualquer símbolo
6. propose_commit          → ÚNICA forma de salvar código
7. run_static_analysis     → Após edições, validar qualidade
8. upsert_memory_node      → Persistir aprendizados da sessão
```

## 🛠️ Referência Completa das Ferramentas

### 🔍 Discovery — Exploração do Código

#### `get_context_tree`
Obtém a árvore AST estrutural do projeto com cabeçalhos de arquivos, nomes de funções, classes e enums. Faz poda automática com base em tokens disponíveis.

**Use quando:** Iniciar qualquer tarefa. É o ponto de entrada obrigatório para entender a estrutura do projeto.

```
Input: { target_path?, depth_limit?, include_symbols?, max_tokens? }
Output: Árvore de diretórios com símbolos e seus intervalos de linha
```

**Regra:** Sempre execute `get_context_tree` no início de cada tarefa antes de qualquer outra ação.

#### `get_file_skeleton`
Retorna assinaturas de funções, métodos de classes e definições de tipos de um arquivo **sem ler o corpo completo**.

**Use quando:** Precisar entender o que um arquivo faz antes de ler seu conteúdo. Obrigatório antes de qualquer leitura completa.

```
Input: { file_path: string }
Output: Assinaturas com intervalos de linha (L12-L58)
```

**Regra:** NUNCA leia um arquivo completo sem antes executar `get_file_skeleton`. Se o esqueleto for suficiente, não vá além.

#### `semantic_code_search`
Busca arquivos no codebase **por significado**, não por texto exato. Usa embeddings Ollama sobre cabeçalhos e símbolos.

**Use quando:** Procurar arquivos relacionados a um conceito ou feature sem saber o nome exato.

```
Input: { query: string, top_k?: number }
Output: Arquivos ranqueados com score semântico e linhas de definição
```

#### `semantic_identifier_search`
Busca funções, classes e variáveis por significado, retornando definições ranqueadas e cadeias de chamada com números de linha.

**Use quando:** Precisar encontrar uma função/classe específica por conceito, ou rastrear onde um identificador é chamado.

```
Input: { query, top_k?, top_calls_per_identifier?, include_kinds? }
Output: Identificadores ranqueados com call chains e line numbers
```

#### `semantic_navigate`
Navega o codebase por significado usando spectral clustering. Agrupa arquivos semanticamente relacionados em clusters rotulados.

**Use quando:** Precisar entender a organização lógica do projeto por domínio/feature, sem depender da estrutura de diretórios.

```
Input: { max_depth?, max_clusters? }
Output: Clusters de arquivos agrupados por significado semântico
```

### 🔬 Analysis — Análise de Impacto

#### `get_blast_radius`
Rastreia **todos os arquivos e linhas** onde um símbolo é importado ou usado em todo o codebase.

**Use quando:** Antes de modificar, renomear ou deletar qualquer função, classe, variável ou símbolo.

```
Input: { symbol_name: string, file_context?: string }
Output: Lista de todos os usos do símbolo com arquivo e linha exata
```

**Regra:** É OBRIGATÓRIO executar `get_blast_radius` antes de deletar ou modificar qualquer símbolo. Nunca modifique sem saber o impacto.

#### `run_static_analysis`
Executa linters e compiladores nativos para encontrar variáveis não usadas, código morto e erros de tipo. Suporta TypeScript, Python, Rust, Go.

**Use quando:** Após escrever ou modificar código. Valide sempre antes de considerar a tarefa concluída.

```
Input: { target_path?: string }
Output: Erros e warnings do linter/compilador nativo
```

**Regra:** Execute `run_static_analysis` após cada conjunto de edições. Corrija todos os erros antes de finalizar.

### ⚙️ Code Ops — Operações de Código

#### `propose_commit`
**A ÚNICA forma de escrever/salvar código.** Valida o conteúdo contra regras de qualidade antes de salvar. Cria um ponto de restauração shadow antes de gravar.

**Use quando:** Sempre que precisar salvar qualquer modificação em um arquivo.

```
Input: { file_path: string, new_content: string }
Output: Validação de qualidade + confirmação de save + ID do restore point
```

**Regra:** NUNCA use ferramentas nativas de escrita de arquivo (`write_file`, `fs.writeFile`, etc.). Todo código DEVE ser salvo via `propose_commit`.

#### `get_feature_hub`
Navegador de hubs no estilo Obsidian. Hubs são arquivos `.md` com `[[wikilinks]]` que mapeiam features para arquivos de código.

**Use quando:** Precisar entender como features se relacionam com arquivos de código, ou encontrar arquivos órfãos não linkados a nenhuma feature.

```
Input: { hub_path?, feature_name?, show_orphans? }
Output: Mapa de features → arquivos de código com seus símbolos
```

### 🔄 Version Control — Controle de Versão Shadow

#### `list_restore_points`
Lista todos os restore points shadow criados pelo `propose_commit`. Cada um captura o estado dos arquivos antes de mudanças da IA.

**Use quando:** Precisar ver o histórico de mudanças feitas pela IA, ou antes de usar `undo_change`.

```
Input: {}
Output: Lista de restore points com ID, data e arquivos afetados
```

#### `undo_change`
Restaura arquivos ao estado anterior a uma mudança específica da IA. Usa restore points shadow. **Não afeta o git.**

**Use quando:** Uma mudança feita via `propose_commit` causou problemas e precisa ser revertida.

```
Input: { point_id: string }
Output: Confirmação dos arquivos restaurados
```

---

## 🔴 PRIORIDADE ABSOLUTA: Leitura Real do Código > Memórias

> **REGRA FUNDAMENTAL:** As ferramentas de leitura e análise de código do Context+ são INFINITAMENTE mais importantes que as memórias. Memórias são úteis como contexto suplementar, mas NUNCA substituem a leitura real do código-fonte atual.

### Por que o código real tem prioridade?

1. **Memórias podem estar desatualizadas** — O código muda constantemente. Uma memória salva há 3 sessões pode descrever uma arquitetura que já foi refatorada.
2. **Memórias são resumos, não verdade** — Elas capturam a *interpretação* de quem as escreveu, não o estado exato do código.
3. **O código-fonte é a única fonte de verdade** — Sempre que houver conflito entre uma memória e o código real, **o código real vence**.
4. **Memórias não capturam efeitos colaterais** — Uma mudança em um arquivo pode ter alterado o comportamento de outro sem que a memória reflita isso.

### Hierarquia de Confiança (do mais confiável ao menos confiável)

```
🥇 1. Código real via get_file_skeleton / get_context_tree  → VERDADE ABSOLUTA
🥈 2. Resultados de semantic_code_search / semantic_identifier_search → VERDADE VERIFICÁVEL
🥉 3. Resultados de get_blast_radius / run_static_analysis → VERDADE COMPUTADA
🏅 4. Memórias via search_memory_graph → CONTEXTO SUPLEMENTAR (pode estar desatualizado)
```

### Workflow Correto: Ferramentas PRIMEIRO, Memórias DEPOIS

```
PASSO 1 — LEITURA REAL DO CÓDIGO (OBRIGATÓRIO, NUNCA PULE):
├── get_context_tree         → Mapear a estrutura ATUAL do projeto
├── get_file_skeleton        → Ver assinaturas REAIS dos arquivos relevantes
├── semantic_code_search     → Encontrar arquivos por conceito no código REAL
├── semantic_identifier_search → Rastrear funções/classes/variáveis REAIS
└── semantic_navigate        → Entender a organização lógica REAL por clusters

PASSO 2 — MEMÓRIAS COMO CONTEXTO EXTRA (ÚTIL, MAS SECUNDÁRIO):
├── search_memory_graph      → Buscar decisões anteriores e contexto acumulado
└── retrieve_with_traversal  → Expandir contexto a partir de um nó conhecido

PASSO 3 — ANTES DE MODIFICAR (OBRIGATÓRIO):
├── get_blast_radius         → Medir impacto REAL no código atual
└── run_static_analysis      → Validar estado REAL do código

PASSO 4 — APÓS CONCLUIR (OBRIGATÓRIO):
├── propose_commit           → Salvar mudanças (ÚNICA forma permitida)
├── run_static_analysis      → Revalidar qualidade
└── upsert_memory_node       → Persistir aprendizados para próximas sessões
```

### Como Usar Cada Ferramenta do Context+ — Guia Detalhado

#### 🗺️ Ferramentas de Descoberta (Discovery) — USE SEMPRE PRIMEIRO

| Ferramenta | Para que serve | Quando usar | Exemplo de uso |
|------------|---------------|-------------|----------------|
| `get_context_tree` | Gera a árvore AST do projeto com arquivos, funções, classes e enums. Faz poda automática baseada em tokens. | **SEMPRE no início de QUALQUER tarefa.** É o mapa do código. | `{ target_path: "./python/src", depth_limit: 3 }` |
| `get_file_skeleton` | Retorna assinaturas de funções e tipos SEM o corpo. Mostra o "esqueleto" do arquivo. | **SEMPRE antes de ler um arquivo completo.** Se o esqueleto for suficiente, NÃO leia mais. | `{ file_path: "python/src/api/routes.py" }` |
| `semantic_code_search` | Busca arquivos por **significado semântico**, não por texto exato. Usa embeddings vetoriais. | Quando você sabe o *conceito* mas não o *nome do arquivo*. Ex: "autenticação JWT" | `{ query: "autenticação de usuário com tokens", top_k: 5 }` |
| `semantic_identifier_search` | Busca funções, classes e variáveis por significado. Retorna definições + cadeias de chamada. | Quando você precisa encontrar uma função/classe específica e saber onde ela é chamada. | `{ query: "validação de permissões", top_k: 3, include_kinds: ["function", "class"] }` |
| `semantic_navigate` | Agrupa arquivos em clusters semânticos rotulados. Usa spectral clustering para organizar por domínio. | Quando precisa entender a arquitetura lógica do projeto, ignorando a estrutura de pastas. | `{ max_depth: 2, max_clusters: 8 }` |

#### 🔬 Ferramentas de Análise (Analysis) — USE ANTES DE MODIFICAR

| Ferramenta | Para que serve | Quando usar | Exemplo de uso |
|------------|---------------|-------------|----------------|
| `get_blast_radius` | Rastreia TODOS os arquivos e linhas onde um símbolo é usado em todo o codebase. | **OBRIGATÓRIO antes de modificar, renomear ou deletar qualquer símbolo.** | `{ symbol_name: "authenticate_user", file_context: "auth/service.py" }` |
| `run_static_analysis` | Executa linters e compiladores nativos (tsc, eslint, py_compile, cargo, go vet). | **OBRIGATÓRIO após cada edição.** Detecta variáveis não usadas, erros de tipo, código morto. | `{ target_path: "./python/src" }` |

#### ⚙️ Ferramentas de Operação (Code Ops) — USE PARA SALVAR

| Ferramenta | Para que serve | Quando usar | Exemplo de uso |
|------------|---------------|-------------|----------------|
| `propose_commit` | **ÚNICA forma de salvar código.** Valida qualidade e cria restore point automático. | **SEMPRE que precisar salvar qualquer modificação.** Nunca use write_file ou ferramentas nativas. | `{ file_path: "src/auth.ts", new_content: "..." }` |
| `get_feature_hub` | Navega hubs .md com wikilinks que mapeiam features → arquivos de código. | Para entender como features se relacionam com código, ou encontrar arquivos órfãos. | `{ show_orphans: true }` |

#### 🔄 Ferramentas de Versionamento (Version Control) — USE PARA DESFAZER

| Ferramenta | Para que serve | Quando usar | Exemplo de uso |
|------------|---------------|-------------|----------------|
| `list_restore_points` | Lista todos os restore points criados pelo propose_commit. | Antes de usar undo_change, para ver o que pode ser revertido. | `{}` |
| `undo_change` | Restaura arquivos ao estado anterior. Não afeta o git real. | Quando uma mudança via propose_commit causou problemas. | `{ point_id: "rp_abc123" }` |

#### 🧠 Ferramentas de Memória (RAG Memory) — USE COMO COMPLEMENTO

> ⚠️ **LEMBRETE:** Estas ferramentas fornecem contexto SUPLEMENTAR. Elas NÃO substituem a leitura real do código via ferramentas de Discovery e Analysis acima.

| Ferramenta | Para que serve | Quando usar | Exemplo de uso |
|------------|---------------|-------------|----------------|
| `search_memory_graph` | Busca semântica + travessia de grafo nas memórias persistidas. | Para recuperar decisões e contexto de sessões anteriores. **Útil, mas CONFIRME contra o código real.** | `{ query: "decisão sobre cache layer", top_k: 5 }` |
| `upsert_memory_node` | Cria ou atualiza nós de memória com embedding automático. | **Ao final de cada tarefa** para persistir aprendizados para próximas sessões. | `{ id: "auth-refactor-v2", type: "concept", content: "..." }` |
| `create_relation` | Cria arestas tipadas entre nós de memória. | Para mapear relacionamentos entre componentes documentados na memória. | `{ from_id: "auth-service", to_id: "jwt-handler", relation_type: "depends_on" }` |
| `add_interlinked_context` | Adiciona múltiplos nós em bulk com auto-linking por similaridade. | Após sessões de exploração extensas, para persistir tudo de uma vez. | `{ nodes: [{id: "...", type: "file", content: "..."}] }` |
| `retrieve_with_traversal` | Caminha pelo grafo a partir de um nó e retorna vizinhos pontuados. | Para expandir contexto a partir de algo que você já encontrou na memória. | `{ node_id: "auth-service", max_depth: 2 }` |
| `prune_stale_links` | Remove arestas decaídas e nós órfãos do grafo de memória. | Manutenção periódica, especialmente após grandes refatorações. | `{ threshold: 0.3 }` |

### ❌ O Que NUNCA Fazer

1. **NUNCA confie cegamente em memórias** — Sempre valide contra o código real com `get_file_skeleton` ou `semantic_code_search`.
2. **NUNCA pule a leitura real do código** porque uma memória "parece" ter a resposta — A memória pode estar desatualizada.
3. **NUNCA use memórias como substituto para `get_blast_radius`** — O impacto real só se mede no código real.
4. **NUNCA assuma que a arquitetura não mudou** desde a última memória — Use `get_context_tree` para confirmar.
5. **NUNCA inicie uma tarefa lendo APENAS memórias** — Leia o código real PRIMEIRO, use memórias como complemento.

---

### 🧠 RAG Memory — Memória entre Sessões

#### `search_memory_graph`
Busca semântica + travessia de grafo na memória persistida de sessões anteriores.

**Use quando:** SEMPRE no início de cada tarefa. Recupera contexto acumulado de trabalho anterior.

```
Input: { query: string, top_k?, depth? }
Output: Nós de memória ranqueados com vizinhos de 1º e 2º grau
```

**Regra:** Sempre execute `search_memory_graph` antes de qualquer exploração de código. Evita retrabalho e re-exploração de áreas já mapeadas.

#### `upsert_memory_node`
Cria ou atualiza nós de memória (conceito, arquivo, símbolo, nota) com embedding automático.

**Use quando:** Ao final de uma tarefa, para persistir aprendizados, decisões arquiteturais e mapeamentos importantes.

```
Input: { id, type, content, metadata? }
Output: Nó criado/atualizado com embedding gerado
```

#### `create_relation`
Cria arestas tipadas entre nós de memória (`depends_on`, `implements`, `calls`, etc.).

**Use quando:** Ao mapear relacionamentos entre componentes, features ou módulos do sistema.

```
Input: { from_id, to_id, relation_type, weight? }
Output: Aresta criada no grafo de memória
```

#### `add_interlinked_context`
Adiciona múltiplos nós em bulk com linking automático por similaridade semântica (cosine ≥ 0.72).

**Use quando:** Precisar persistir um conjunto grande de contexto de uma só vez após uma sessão de exploração.

```
Input: { nodes: Array<{id, type, content}> }
Output: Nós criados com arestas de similaridade automáticas
```

#### `retrieve_with_traversal`
Parte de um nó inicial, caminha pelo grafo e retorna vizinhos pontuados por decaimento e profundidade.

**Use quando:** Precisar expandir o contexto a partir de um ponto de entrada conhecido no grafo de memória.

```
Input: { node_id, max_depth?, decay_lambda? }
Output: Nós vizinhos ranqueados por relevância e decaimento temporal
```

#### `prune_stale_links`
Remove arestas decaídas e nós órfãos do grafo de memória periodicamente.

**Use quando:** Manutenção periódica do grafo de memória, especialmente após grandes refatorações.

```
Input: { threshold? }
Output: Relatório de arestas e nós removidos
```

## ⚡ Regras de Eficiência de Tokens

1. Prefira `get_file_skeleton` ao invés de leitura completa sempre que possível.
2. Use `semantic_code_search` antes de navegar manualmente por diretórios.
3. Paralelize buscas independentes — não serialize operações que podem rodar juntas.
4. Nunca rescaneie áreas do código que já foram mapeadas na sessão atual.
5. Mantenha outputs concisos: updates curtos de status, sem dumps verbosos de raciocínio.

## 🚫 Anti-Padrões Proibidos

| # | Anti-Padrão |
|---|-------------|
| 1 | Ler arquivos completos sem verificar o skeleton antes |
| 2 | Deletar funções sem verificar o blast radius |
| 3 | Usar qualquer ferramenta nativa de leitura/escrita de arquivo |
| 4 | Serializar operações independentes que poderiam ser paralelas |
| 5 | Repetir comandos que falharam sem mudar a abordagem |
| 6 | Iniciar tarefas sem antes executar `search_memory_graph` |
| 7 | Finalizar tarefas sem persistir aprendizados via `upsert_memory_node` |
| 8 | Modificar símbolos sem antes executar `get_blast_radius` |
| 9 | Salvar código por qualquer meio que não seja `propose_commit` |
| 10 | Fazer planejamento extenso antes de executar — prefira execução imediata |

## 📋 Checklist por Tipo de Tarefa

### Exploração / Entendimento
```
[ ] search_memory_graph  — contexto anterior
[ ] get_context_tree     — estrutura do projeto
[ ] semantic_navigate    — clusters por domínio
[ ] get_file_skeleton    — inspecionar arquivos relevantes
[ ] upsert_memory_node   — persistir descobertas
```

### Modificação de Código
```
[ ] search_memory_graph        — contexto anterior
[ ] get_context_tree           — localizar o alvo
[ ] get_file_skeleton          — entender assinaturas
[ ] semantic_identifier_search — encontrar o símbolo exato
[ ] get_blast_radius           — medir impacto
[ ] propose_commit             — salvar mudanças
[ ] run_static_analysis        — validar qualidade
[ ] upsert_memory_node         — persistir decisões
```

### Deleção de Código
```
[ ] get_blast_radius    — OBRIGATÓRIO antes de qualquer deleção
[ ] propose_commit      — aplicar remoção
[ ] run_static_analysis — confirmar que nada quebrou
```

### Investigação de Bug
```
[ ] search_memory_graph        — bugs similares anteriores
[ ] semantic_code_search       — encontrar área relevante
[ ] semantic_identifier_search — rastrear símbolo problemático
[ ] get_blast_radius           — entender propagação
[ ] run_static_analysis        — detectar erros estáticos
[ ] propose_commit             — aplicar fix
```

---

*Gerado com base na documentação oficial do [Context+ MCP](https://github.com/ForLoopCodes/contextplus).*

---

# MindFlow Project Guide

## Tech Stack

**Backend (Python 3.11+):** FastAPI + gRPC + LangGraph agents + PostgreSQL (pgvector) + RabbitMQ + KuzuDB graph storage

**Frontend:** React 19 + TypeScript + Vite 8 + Tailwind v4 + Zustand

**Package Managers:** `uv` for Python (NOT pip/poetry), `npm` for frontend

## Essential Commands

**Backend (from `/python/`):**
- `uv sync` - Install dependencies
- `uv run mindflow-api` - Start FastAPI (port 8000)
- `uv run mindflow-grpc` - Start gRPC (port 50051)
- `uv run mindflow-worker` - Start RabbitMQ worker
- `make check` - Run all quality checks (format, lint, typecheck, test)
- `make format` - Auto-fix with ruff
- `uv run alembic upgrade head` - Run database migrations

**Frontend (from `/frontend/`):**
- `npm run dev` - Vite dev server (port 5173)
- `npm run lint` - ESLint check
- `npm run test` - Vitest unit tests
- `npm run test:e2e` - Playwright e2e tests

**Full Stack (from root):**
- `./start_dev.sh` - Start all services (Docker + API + Frontend + Worker)
- `./stop_dev.sh` - Stop all services
- `./status_dev.sh` - Check service status

## Critical Gotchas

1. **Always use `uv run` for Python commands** - This project uses `uv`, not pip or poetry
2. **Non-standard ports** - PostgreSQL on 5433 (not 5432), RabbitMQ on 5673 (not 5672)
3. **Tailwind v4 syntax** - Uses new `@import 'tailwindcss'` in CSS, no separate config file
4. **Multi-service coordination** - Backend has 3 processes (API, gRPC, worker) that must run together
5. **Feature flags** - Many features are toggled via env vars (ENABLE_RABBITMQ, ENABLE_LLM_PLANNING_TRIGGER, etc.)
6. **Agent iteration limits** - Configurable up to 1000 iterations (see UNLIMITED_AGENTS_GUIDE.md)

## Code Style

**Python:**
- Line length: 100 characters
- Indentation: 4 spaces
- Use ruff for formatting and linting
- Type hints required (mypy strict mode disabled but encouraged)

**TypeScript:**
- Indentation: 2 spaces
- ESLint 9 flat config with typescript-eslint
- Strict mode enabled

## Testing

- **Always run tests after making changes** - Use `make check` (Python) or `npm run test` (frontend)
- Python tests in `python/tests/` with markers: `@pytest.mark.live`, `@pytest.mark.slow`, `@pytest.mark.integration`
- Frontend uses Vitest for unit tests, Playwright for e2e
- Coverage threshold: 80% for Python

## Git Workflow

- **Commit style:** Conventional Commits (feat:, fix:, docs:, refactor:, test:, chore:)
- Always include Co-Authored-By line for AI commits
- Test before committing

## Environment Setup

Required env vars (see `.env.example`):
- `DATABASE_URL` - PostgreSQL connection
- `RABBITMQ_URL` - RabbitMQ AMQP connection
- `GOOGLE_API_KEY` or `GOOGLE_APPLICATION_CREDENTIALS` - Vertex AI auth
- `MINDFLOW_ALLOWED_PATHS` - Filesystem allowlist for agents
