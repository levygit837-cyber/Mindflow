# PRD — Code Context Accumulator

> **Status**: Draft  
> **Data**: 2026-03-31  
> **Área**: Coder Agent / Infra de Contexto

---

## 1. Resumo

Toda vez que um agente Coder escrever um arquivo de código, o sistema deve extrair automaticamente os símbolos contidos nele (funções, classes, imports, tipos) e persistir esse contexto em um banco vetorial (e opcionalmente em um bucket estruturado). Esse contexto acumulado fica disponível para consulta nos próximos ciclos de geração, reduzindo duplicação, melhorando coerência entre arquivos e aumentando a qualidade do código gerado em sessões longas.

---

## 2. Contatos

| Nome | Papel | Observação |
|------|-------|------------|
| Levy | Owner / Engenheiro | Visão e decisões de arquitetura |
| Cascade | Assistente de implementação | Geração de código e análise |

---

## 3. Contexto

### O problema hoje

Quando um agente Coder escreve múltiplos arquivos em uma sessão, ele não tem memória de curto prazo sobre o que já foi escrito. Isso causa:

- **Duplicação**: funções com nomes diferentes fazendo a mesma coisa
- **Inconsistência de interface**: chamadas a funções com assinaturas erradas
- **Falta de coerência estrutural**: imports redundantes, padrões misturados
- **Retrabalho**: o agente "esquece" o que fez três arquivos atrás

### Por que agora

O MindFlow já tem:
- `FileWriteTool` — ponto de hook natural (post-write)
- `SocratiCode` — infraestrutura de indexação vetorial já em uso
- `MemoryObserver` (Phase 3B) — padrão de observer já planejado
- `MindFlowSandbox` — contexto de execução isolado

A peça que falta é conectar a escrita de arquivo à atualização de contexto.

### O que a análise mostrou

A partir do estudo de viabilidade feito anteriormente, a parte genuinamente valiosa da ideia original é:

> **Symbol context accumulation** — extração de símbolos + persistência vetorial — melhora coerência multi-arquivo com custo próximo de zero para o agente.

Hipóteses validadas:
- Extração de símbolos como contexto melhora geração futura **(Alta confiança)**
- Sub-processos async em background têm latência aceitável **(Alta confiança)**

Hipóteses descartadas neste escopo:
- "Token-by-token" timing — arquiteturalmente inviável sem reescrita do loop de tool invocation; post-write é equivalente
- Auto-testes como sinal de qualidade — validação circular, descartado nesta fase

---

## 4. Objetivo

### Meta principal

> Reduzir inconsistências e duplicações no código gerado por agentes Coder em sessões multi-arquivo, aumentando a coerência estrutural entre arquivos gerados.

### Key Results (mensuráveis)

| KR | Métrica | Meta |
|----|---------|------|
| KR1 | Redução de funções duplicadas por sessão | −60% vs. baseline |
| KR2 | Latência adicionada ao `write_file` pelo hook | < 50ms (p95) |
| KR3 | Símbolos indexados disponíveis para consulta em sessões subsequentes | 100% dos arquivos `.py` e `.ts` escritos |
| KR4 | Cobertura: tipos de arquivo suportados na v1 | `.py`, `.ts`, `.js` |

---

## 5. Segmento de Mercado

**Usuário primário**: agentes Coder do MindFlow executando tarefas de codificação multi-arquivo em uma sessão.

**Restrições**:
- O sistema deve ser transparente para o agente — nenhuma mudança no prompt ou comportamento do modelo
- Não deve bloquear a escrita do arquivo (operação async/background)
- Deve funcionar dentro do sandbox de segurança existente

---

## 6. Proposta de Valor

### Para o agente Coder

| Antes | Depois |
|-------|--------|
| Não sabe o que escreveu 3 arquivos atrás | Consulta vetorial traz funções/classes relevantes ao contexto |
| Duplica lógica sem saber | Context injection previne duplicação |
| Usa interfaces inconsistentes | Assinaturas de funções disponíveis antes de cada nova chamada |

### Para o usuário final

- Código gerado com menos bugs de integração entre módulos
- Menos iterações de revisão manual
- Sessões mais longas com maior coerência

---

## 7. Solução

### 7.1 Fluxo

```
Coder Agent
    └── chama write_file(file_path, content)
            │
            ▼
     FileWriteTool.execute()
            │
            ├── [Síncrono] Escreve arquivo no disco
            │
            └── [Async, background] dispara CodeContextAccumulator
                        │
                        ├── SymbolExtractor.extract(content, language)
                        │       └── Extrai: funções, classes, imports, tipos
                        │
                        └── asyncio.gather(
                                VectorStore.upsert(symbols, file_path, session_id),
                                StructuredStore.save(symbol_index_entry)
                            )
```

O agente **não espera** pelo accumulator — a escrita retorna imediatamente. A indexação ocorre em background via `asyncio.create_task`.

### 7.2 Funcionalidades (v1)

#### F1 — SymbolExtractor

Extrai símbolos de arquivos de código usando o módulo `ast` (Python nativo) e regex para TypeScript/JavaScript.

**Python** (via `ast`):
```
FunctionDef → nome, argumentos, tipo de retorno, docstring, linha
ClassDef    → nome, métodos, atributos, docstring, linha
Import/ImportFrom → módulo, alias
```

**TypeScript/JavaScript** (via regex):
```
function foo / const foo = () → nome, params
class Foo → nome, métodos
import { ... } from '...' → módulo, símbolos
```

**Saída por arquivo**:
```json
{
  "file_path": "src/auth/service.py",
  "language": "python",
  "session_id": "sess-abc123",
  "timestamp": "2026-03-31T09:00:00Z",
  "symbols": [
    {
      "kind": "function",
      "name": "authenticate",
      "args": ["user: str", "password: str"],
      "return_type": "AuthResult",
      "docstring": "Autentica usuário pelo banco de dados.",
      "line": 42
    },
    {
      "kind": "class",
      "name": "AuthService",
      "methods": ["authenticate", "logout", "refresh_token"],
      "line": 10
    }
  ]
}
```

#### F2 — Vector Store Persistence

Cada símbolo é vetorizado e indexado para busca semântica. A chave primária é `(session_id, file_path, symbol_name)`.

**Backends suportados (em ordem de preferência)**:
1. **Qdrant** — já usado pelo SocratiCode no projeto
2. **ChromaDB** — fallback local leve
3. **JSON file bucket** — fallback zero-dependency para desenvolvimento

**Schema de indexação**:

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | `str` | hash(`session_id + file_path + name`) |
| `vector` | `float[]` | embedding do texto: `"{kind} {name}({args}) → {return_type}"` |
| `payload.kind` | `str` | `function`, `class`, `import` |
| `payload.name` | `str` | nome do símbolo |
| `payload.file_path` | `str` | arquivo de origem |
| `payload.session_id` | `str` | sessão do agente |
| `payload.args` | `str[]` | argumentos (funções) |
| `payload.return_type` | `str` | tipo de retorno |
| `payload.docstring` | `str` | documentação |

#### F3 — Structured Bucket (JSON Index)

Além do vetor, salva um índice estruturado em formato JSON para consulta exata rápida:

```
.mindflow_context/
    {session_id}/
        symbol_index.json     ← índice consolidado de todos os arquivos da sessão
        {file_hash}.json      ← símbolos por arquivo
```

**Propósito**: consulta O(1) por nome exato de função, sem necessidade de embedding.

#### F4 — Context Query API (para injeção futura no prompt)

Interface simples que o agente pode usar antes de gerar um novo arquivo:

```python
symbols = await context_store.search(
    query="authentication service",
    session_id=session_id,
    top_k=10,
    kinds=["function", "class"]
)
```

Retorna uma lista de símbolos relevantes formatados para injeção no prompt do modelo.

### 7.3 Tecnologia

| Componente | Tecnologia | Justificativa |
|-----------|-----------|---------------|
| Extração Python | `ast` (stdlib) | Zero dependência, robusto |
| Extração TS/JS | regex patterns | Leve, sem parser JS em Python |
| Vector store | Qdrant (já existente) | Reutiliza infra do SocratiCode |
| Structured store | JSON file bucket | Zero infra, fallback confiável |
| Embedding | mesmo modelo do SocratiCode | Consistência de espaço vetorial |
| Async | `asyncio.create_task` | Non-blocking, sem overhead |

### 7.4 Ponto de Integração

O hook é adicionado ao `FileWriteTool.execute()` em `file_operations.py`:

```python
# Após escrita bem-sucedida, dispara accumulator em background
if self._context_accumulator and file_path.endswith(SUPPORTED_EXTENSIONS):
    asyncio.create_task(
        self._context_accumulator.accumulate(file_path, content, session_id)
    )
```

O `_context_accumulator` é injetado no construtor — opcional, sem impacto se `None`.

### 7.5 Hipóteses / Premissas desta versão

| # | Premissa | Impacto se falsa |
|---|---------|-----------------|
| P1 | Qdrant está acessível no ambiente de execução | Fallback para JSON bucket |
| P2 | Embedding de `"{kind} {name}({args})"` captura semântica suficiente | Busca pode retornar ruído; ajustar template |
| P3 | `session_id` está disponível no contexto de execução do `FileWriteTool` | Indexação por sessão falha; usar `file_path` como chave |
| P4 | Extração JS via regex cobre 80% dos casos comuns | Símbolos não detectados; adicionar parser na v2 |

### 7.6 Fora de Escopo (v1)

- Auto-geração de testes *(descartado: validação circular)*
- Análise de qualidade / code smells
- Token-by-token streaming de argumentos
- Suporte a `.java`, `.go`, `.rs` (v2)
- Dashboard de visualização dos símbolos acumulados

---

## 8. Releases

### v1 — MVP (Symbol Extraction + JSON Bucket)

**Objetivo**: Provar que a extração funciona e o contexto é persistido sem impacto em performance.

- `SymbolExtractor` para Python (`ast`) e TypeScript/JS (regex)
- JSON file bucket como store (zero nova infra)
- Hook em `FileWriteTool` via `asyncio.create_task`
- Testes unitários de extração

**Critério de saída**: símbolos extraídos corretamente em 5 arquivos Python e 3 TS de teste, latência do `write_file` < 5ms de overhead.

---

### v2 — Vector Store Integration

**Objetivo**: Indexação semântica usando Qdrant existente para busca por similaridade.

- Integração com Qdrant (reusa infra SocratiCode)
- `Context Query API` funcional
- Injeção automática de contexto no início de novas gerações de arquivo pelo Coder
- Métricas: símbolos indexados, latência de busca, hits por sessão

---

### v3 — Multi-language + Context Enrichment

**Objetivo**: Expandir cobertura e enriquecer contexto.

- Suporte a `.java`, `.go`, `.rs` via tree-sitter
- Dependency graph entre funções (quem chama quem)
- Integração com `MemoryObserver` (Phase 3B) para anotações de qualidade
- A/B test: sessões com vs. sem context injection → medir coerência

---

## Apêndice — Conexão com a Arquitetura MindFlow Existente

```
FileWriteTool (specialist/coder/filesystem/file_operations.py)
    └── CodeContextAccumulator (NEW)
            ├── SymbolExtractor (NEW)
            ├── VectorStore → Qdrant (infra SocratiCode existente)
            └── StructuredBucket → .mindflow_context/ (NEW, JSON)

MemoryObserver (Phase 3B, planejado)
    └── pode consumir eventos do CodeContextAccumulator

CodingTaskChain (chains/templates/coding_task_chain.py)
    └── antes do step Coder: consulta ContextQueryAPI → injeta símbolos relevantes
```
