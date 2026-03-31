# Project Memory — Memória Agêntica de Código

## Visão Geral

A **Project Memory** é um sistema de armazenamento persistente que indexa **todo o código funcional** do projeto (funções, classes, métodos) permitindo:

1. **Busca Exata** — Encontrar função/classe pelo nome exato
2. **Busca Semântica** — Encontrar funções por similaridade de significado
3. **Leitura Completa** — Recuperar o código-fonte completo de qualquer função/classe indexada

## Fluxo de Dados

```
┌─────────────────────────────────────────────────────────────────┐
│                    PROJECT MEMORY FLOW                           │
│                                                                  │
│   1. MAPEAMENTO         2. EXTRAÇÃO         3. ARMAZENAMENTO    │
│   ┌──────────┐         ┌──────────┐         ┌──────────┐       │
│   │ get_     │────────▶│ Parser   │────────▶│ Storage  │       │
│   │ context_ │         │ extrai   │         │ persiste │       │
│   │ tree     │         │ código   │         │ código   │       │
│   └──────────┘         └──────────┘         └──────────┘       │
│        │                     │                     │             │
│        ▼                     ▼                     ▼             │
│   ┌──────────┐         ┌──────────┐         ┌──────────┐       │
│   │ get_     │         │ Funções  │         │ pgvector │       │
│   │ file_    │         │ Classes  │         │ KuzuDB   │       │
│   │ skeleton │         │ Métodos  │         │ JSON     │       │
│   └──────────┘         └──────────┘         └──────────┘       │
│                                                                  │
│   4. BUSCA               5. LEITURA                             │
│   ┌──────────┐         ┌──────────┐                             │
│   │ Exata:   │────────▶│ Retorna  │                             │
│   │ nome     │         │ código   │                             │
│   │ exato    │         │ completo │                             │
│   └──────────┘         └──────────┘                             │
│   ┌──────────┐                                                  │
│   │ Semânt:  │──▶ similaridade ──▶ top-k ──▶ leitura           │
│   │ query    │                                                  │
│   └──────────┘                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Arquitetura de Armazenamento

### Estrutura de Dados

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import hashlib

class CodeType(Enum):
    """Tipo de elemento de código."""
    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    CONSTANT = "constant"
    DECORATOR = "decorator"
    TYPE_ALIAS = "type_alias"

@dataclass
class CodeElement:
    """Um elemento de código indexado (função, classe, método)."""
    
    # Identificação
    id: str                              # hash único: sha256(file_path:name:type)
    name: str                            # Nome do elemento
    type: CodeType                       # Tipo (function, class, method)
    file_path: str                       # Arquivo onde está definido
    
    # Localização
    start_line: int                      # Linha inicial
    end_line: int                        # Linha final
    
    # Código
    signature: str                       # Assinatura: def foo(a: int) -> bool
    full_source: str                     # Código-fonte completo
    
    # Metadados
    docstring: Optional[str] = None      # Docstring se houver
    decorators: list[str] = field(default_factory=list)  # @decorator
    parent_class: Optional[str] = None   # Se for método, qual a classe
    
    # Análise
    complexity: int = 0                  # Complexidade ciclomática
    lines_of_code: int = 0               # Linhas de código
    dependencies: list[str] = field(default_factory=list)  # Funções/classes usadas
    
    # Embedding (para busca semântica)
    embedding: Optional[list[float]] = None  # Vetor de embedding
    
    @staticmethod
    def generate_id(file_path: str, name: str, code_type: CodeType) -> str:
        """Gera ID único para o elemento."""
        content = f"{file_path}:{name}:{code_type.value}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def to_searchable_text(self) -> str:
        """Gera texto para indexação semântica."""
        parts = [
            f"Name: {self.name}",
            f"Type: {self.type.value}",
            f"File: {self.file_path}",
            f"Signature: {self.signature}",
        ]
        if self.docstring:
            parts.append(f"Documentation: {self.docstring}")
        return "\n".join(parts)


@dataclass
class ProjectMemory:
    """Memória completa de um projeto."""
    
    project_id: str                      # ID do projeto
    project_path: str                    # Caminho raiz do projeto
    name: str                            # Nome do projeto
    
    # Índices
    elements_by_id: dict[str, CodeElement] = field(default_factory=dict)
    elements_by_name: dict[str, list[str]] = field(default_factory=dict)  # name -> [ids]
    elements_by_file: dict[str, list[str]] = field(default_factory=dict)  # file -> [ids]
    elements_by_type: dict[CodeType, list[str]] = field(default_factory=dict)  # type -> [ids]
    
    # Estatísticas
    total_elements: int = 0
    total_functions: int = 0
    total_classes: int = 0
    total_methods: int = 0
    total_lines_indexed: int = 0
    
    # Metadados
    created_at: str = ""
    last_updated: str = ""
    version: int = 1
```

## Camadas de Armazenamento

### 1. Storage Layer (Persistência)

```python
# python/mindflow_backend/memory/project_memory/storage.py

class ProjectMemoryStorage:
    """Persistência da Project Memory com múltiplos backends."""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        
        # Backend 1: PostgreSQL + pgvector (embeddings)
        self.pg_storage = PostgreSQLProjectStorage(project_id)
        
        # Backend 2: KuzuDB (grafo de dependências)
        self.graph_storage = KuzuProjectStorage(project_id)
        
        # Backend 3: JSON cache (acesso rápido)
        self.cache = ProjectMemoryCache(project_id)
    
    async def save_element(self, element: CodeElement) -> None:
        """Salva um elemento de código em todos os backends."""
        
        # 1. Salvar no PostgreSQL (dados + embedding)
        await self.pg_storage.upsert_element(element)
        
        # 2. Salvar no grafo (dependências)
        await self.graph_storage.add_element(element)
        for dep in element.dependencies:
            await self.graph_storage.add_dependency(element.id, dep)
        
        # 3. Atualizar cache
        await self.cache.set(element.id, element)
    
    async def get_element(self, element_id: str) -> Optional[CodeElement]:
        """Recupera elemento por ID."""
        
        # Tentar cache primeiro
        cached = await self.cache.get(element_id)
        if cached:
            return cached
        
        # Buscar no PostgreSQL
        element = await self.pg_storage.get_element(element_id)
        if element:
            await self.cache.set(element_id, element)
        
        return element
    
    async def search_exact(self, name: str) -> list[CodeElement]:
        """Busca exata por nome."""
        return await self.pg_storage.search_by_name(name)
    
    async def search_semantic(
        self,
        query: str,
        top_k: int = 10,
        min_similarity: float = 0.7,
    ) -> list[tuple[CodeElement, float]]:
        """Busca semântica por similaridade."""
        
        # Gerar embedding da query
        query_embedding = await self.embedding_service.embed(query)
        
        # Buscar no pgvector
        results = await self.pg_storage.search_by_embedding(
            embedding=query_embedding,
            top_k=top_k,
            min_similarity=min_similarity,
        )
        
        return results
```

### 2. PostgreSQL Schema

```sql
-- Tabela principal de elementos de código
CREATE TABLE IF NOT EXISTS project_code_elements (
    id VARCHAR(16) PRIMARY KEY,
    project_id VARCHAR(64) NOT NULL,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(20) NOT NULL,  -- function, class, method
    file_path TEXT NOT NULL,
    start_line INTEGER NOT NULL,
    end_line INTEGER NOT NULL,
    signature TEXT NOT NULL,
    full_source TEXT NOT NULL,
    docstring TEXT,
    decorators JSONB DEFAULT '[]',
    parent_class VARCHAR(255),
    complexity INTEGER DEFAULT 0,
    lines_of_code INTEGER DEFAULT 0,
    dependencies JSONB DEFAULT '[]',
    embedding vector(768),  -- pgvector para embeddings
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Índices
    CONSTRAINT unique_element UNIQUE (project_id, file_path, name, type)
);

-- Índices para busca
CREATE INDEX idx_elements_project ON project_code_elements(project_id);
CREATE INDEX idx_elements_name ON project_code_elements(name);
CREATE INDEX idx_elements_type ON project_code_elements(type);
CREATE INDEX idx_elements_file ON project_code_elements(file_path);
CREATE INDEX idx_elements_embedding ON project_code_elements 
    USING ivfflat (embedding vector_cosine_ops);
```

### 3. KuzuDB Schema (Grafo de Dependências)

```cypher
-- Nodes
CREATE NODE TABLE CodeElement (
    id STRING,
    name STRING,
    type STRING,
    file_path STRING,
    signature STRING,
    PRIMARY KEY (id)
)

-- Edges
CREATE REL TABLE DEPENDS_ON (
    FROM CodeElement TO CodeElement,
    weight DOUBLE
)

CREATE REL TABLE CONTAINS (
    FROM CodeElement TO CodeElement  -- class CONTAINS method
)

CREATE REL TABLE CALLS (
    FROM CodeElement TO CodeElement  -- function CALLS function
)
```

## API de Busca

### Busca Exata

```python
class ProjectMemorySearch:
    """API de busca na Project Memory."""
    
    def __init__(self, storage: ProjectMemoryStorage):
        self.storage = storage
    
    async def find_exact(
        self,
        name: str,
        code_type: Optional[CodeType] = None,
        file_path: Optional[str] = None,
    ) -> list[CodeElement]:
        """Busca exata por nome.
        
        Examples:
            find_exact("authenticate_user")
            find_exact("UserModel", code_type=CodeType.CLASS)
            find_exact("validate", file_path="auth/service.py")
        """
        results = await self.storage.search_exact(name)
        
        # Filtros opcionais
        if code_type:
            results = [r for r in results if r.type == code_type]
        if file_path:
            results = [r for r in results if r.file_path == file_path]
        
        return results
    
    async def find_similar(
        self,
        query: str,
        top_k: int = 10,
        min_similarity: float = 0.7,
        code_type: Optional[CodeType] = None,
    ) -> list[tuple[CodeElement, float]]:
        """Busca semântica por similaridade.
        
        Examples:
            find_similar("função que valida email")
            find_similar("classe de conexão com banco de dados")
            find_similar("middleware de autenticação JWT")
        """
        results = await self.storage.search_semantic(
            query=query,
            top_k=top_k,
            min_similarity=min_similarity,
        )
        
        # Filtro por tipo
        if code_type:
            results = [(elem, score) for elem, score in results 
                       if elem.type == code_type]
        
        return results
    
    async def get_full_source(self, element_id: str) -> Optional[str]:
        """Recupera código-fonte completo de um elemento.
        
        Returns:
            Código-fonte completo ou None se não encontrado
        """
        element = await self.storage.get_element(element_id)
        return element.full_source if element else None
    
    async def get_dependencies(self, element_id: str) -> list[CodeElement]:
        """Recupera todas as dependências de um elemento."""
        deps_ids = await self.storage.graph.get_dependencies(element_id)
        return [
            await self.storage.get_element(dep_id)
            for dep_id in deps_ids
        ]
```

## Indexer (Mapeamento + Extração)

```python
# python/mindflow_backend/memory/project_memory/indexer.py

class ProjectMemoryIndexer:
    """Indexador que mapeia e extrai todo o código do projeto."""
    
    def __init__(
        self,
        storage: ProjectMemoryStorage,
        contextplus_executor: Callable,
        embedding_service: EmbeddingService,
    ):
        self.storage = storage
        self.contextplus = contextplus_executor
        self.embeddings = embedding_service
    
    async def index_project(
        self,
        project_path: str,
        project_id: str,
        file_patterns: list[str] = ["*.py", "*.ts"],
    ) -> ProjectMemory:
        """Indexa todo o projeto.
        
        Fluxo:
        1. Discovery: get_context_tree → lista arquivos
        2. Skeleton: get_file_skeleton → assinaturas
        3. Full Read: Lê arquivo completo
        4. Parse: Extrai funções/classes com código completo
        5. Embed: Gera embeddings
        6. Store: Persiste em todos os backends
        """
        
        memory = ProjectMemory(
            project_id=project_id,
            project_path=project_path,
            name=Path(project_path).name,
        )
        
        # Phase 1: Discovery
        tree_result = await self.contextplus(
            "get_context_tree",
            {"target_path": project_path, "depth_limit": 5}
        )
        files = extract_files_from_tree(tree_result, file_patterns)
        
        # Phase 2-6: Para cada arquivo
        for file_path in files:
            elements = await self._index_file(file_path, project_id)
            
            for element in elements:
                # Adicionar ao índice em memória
                memory.elements_by_id[element.id] = element
                memory.elements_by_name.setdefault(element.name, []).append(element.id)
                memory.elements_by_file.setdefault(element.file_path, []).append(element.id)
                memory.elements_by_type.setdefault(element.type, []).append(element.id)
                
                # Persistir
                await self.storage.save_element(element)
                
                # Atualizar estatísticas
                memory.total_elements += 1
                if element.type == CodeType.FUNCTION:
                    memory.total_functions += 1
                elif element.type == CodeType.CLASS:
                    memory.total_classes += 1
                elif element.type == CodeType.METHOD:
                    memory.total_methods += 1
                memory.total_lines_indexed += element.lines_of_code
        
        return memory
    
    async def _index_file(
        self,
        file_path: str,
        project_id: str,
    ) -> list[CodeElement]:
        """Indexa um único arquivo."""
        
        elements = []
        
        # 1. Ler arquivo completo
        read_result = await self.contextplus(
            "get_file_skeleton",
            {"file_path": file_path}
        )
        
        if not read_result.get("success"):
            return elements
        
        # 2. Extrair funções
        for func in read_result.get("functions", []):
            element = CodeElement(
                id=CodeElement.generate_id(
                    file_path, func["name"], CodeType.FUNCTION
                ),
                name=func["name"],
                type=CodeType.FUNCTION,
                file_path=file_path,
                start_line=func["start_line"],
                end_line=func["end_line"],
                signature=func["signature"],
                full_source=func.get("source", ""),
                docstring=func.get("docstring"),
                decorators=func.get("decorators", []),
                lines_of_code=func["end_line"] - func["start_line"] + 1,
            )
            
            # Gerar embedding
            element.embedding = await self.embeddings.embed(
                element.to_searchable_text()
            )
            
            elements.append(element)
        
        # 3. Extrair classes
        for cls in read_result.get("classes", []):
            element = CodeElement(
                id=CodeElement.generate_id(
                    file_path, cls["name"], CodeType.CLASS
                ),
                name=cls["name"],
                type=CodeType.CLASS,
                file_path=file_path,
                start_line=cls["start_line"],
                end_line=cls["end_line"],
                signature=cls["signature"],
                full_source=cls.get("source", ""),
                docstring=cls.get("docstring"),
                lines_of_code=cls["end_line"] - cls["start_line"] + 1,
            )
            
            element.embedding = await self.embeddings.embed(
                element.to_searchable_text()
            )
            
            elements.append(element)
            
            # 4. Extrair métodos da classe
            for method in cls.get("methods", []):
                method_element = CodeElement(
                    id=CodeElement.generate_id(
                        file_path, method["name"], CodeType.METHOD
                    ),
                    name=method["name"],
                    type=CodeType.METHOD,
                    file_path=file_path,
                    start_line=method["start_line"],
                    end_line=method["end_line"],
                    signature=method["signature"],
                    full_source=method.get("source", ""),
                    docstring=method.get("docstring"),
                    parent_class=cls["name"],
                    lines_of_code=method["end_line"] - method["start_line"] + 1,
                )
                
                method_element.embedding = await self.embeddings.embed(
                    method_element.to_searchable_text()
                )
                
                elements.append(method_element)
        
        return elements
```

## Integração com o CodebaseAnalysisGraph

A Project Memory se integra ao graph como um **nodo adicional** entre Deep Analysis e Validation:

```
Discovery → Skeleton → Deep Analysis → INDEX TO MEMORY → Validation → Loop/Report
```

```python
async def index_to_memory_node(state: CodebaseAnalysisState) -> CodebaseAnalysisState:
    """Indexa todo o código mapeado na Project Memory."""
    
    indexer = ProjectMemoryIndexer(
        storage=state.project_memory_storage,
        contextplus_executor=contextplus_executor,
        embedding_service=embedding_service,
    )
    
    # Indexar todos os arquivos analisados
    for file_path, file_data in state.analyzed_files.items():
        elements = await indexer._index_file(file_path, state.project_id)
        state.indexed_elements.extend(elements)
    
    # Atualizar métricas
    state.memory_stats = {
        "total_indexed": len(state.indexed_elements),
        "functions": sum(1 for e in state.indexed_elements 
                        if e.type == CodeType.FUNCTION),
        "classes": sum(1 for e in state.indexed_elements 
                      if e.type == CodeType.CLASS),
        "methods": sum(1 for e in state.indexed_elements 
                      if e.type == CodeType.METHOD),
    }
    
    return state
```

## Exemplos de Uso

### 1. Busca Exata

```python
search = ProjectMemorySearch(storage)

# Encontrar função authenticate_user
results = await search.find_exact("authenticate_user")
# → [CodeElement(name="authenticate_user", file="auth/service.py", ...)]

# Ler código completo
source = await search.get_full_source(results[0].id)
# → def authenticate_user(email: str, password: str) -> AuthResult:\n    ...
```

### 2. Busca Semântica

```python
# Encontrar funções relacionadas a validação de email
results = await search.find_similar("validação de formato de email")
# → [
#   (CodeElement(name="validate_email_format", ...), 0.92),
#   (CodeElement(name="is_valid_email", ...), 0.87),
#   (CodeElement(name="check_email_syntax", ...), 0.81),
# ]

# Ler a mais similar
source = await search.get_full_source(results[0][0].id)
```

### 3. Busca por Classe

```python
# Encontrar classe UserModel
results = await search.find_exact("UserModel", code_type=CodeType.CLASS)
# → [CodeElement(name="UserModel", type=CLASS, ...)]

# Ler código completo da classe
source = await search.get_full_source(results[0].id)
# → class UserModel(BaseModel):\n    id: int\n    email: str\n    ...
```

## Arquivos a Criar

| Arquivo | Descrição |
|---------|-----------|
| `memory/project_memory/__init__.py` | Módulo principal |
| `memory/project_memory/models.py` | CodeElement, ProjectMemory |
| `memory/project_memory/storage.py` | ProjectMemoryStorage |
| `memory/project_memory/indexer.py` | ProjectMemoryIndexer |
| `memory/project_memory/search.py` | ProjectMemorySearch |
| `memory/project_memory/embeddings.py` | Embedding service |
| `memory/project_memory/cache.py` | Cache LRU |
| `storage/postgresql/migrations/002_project_memory.py` | Migration SQL |
| `schemas/memory/project_memory.py` | Schemas Pydantic |

## Resumo do Fluxo Completo

```
1. MAPEAMENTO
   get_context_tree → lista todos os arquivos
   get_file_skeleton → extrai assinaturas

2. EXTRAÇÃO
   Lê arquivo completo
   Parser extrai funções, classes, métodos
   Captura código-fonte de cada elemento

3. ARMAZENAMENTO
   Gera embedding semântico
   Salva no PostgreSQL (dados + pgvector)
   Salva no KuzuDB (grafo de dependências)
   Atualiza cache LRU

4. BUSCA EXATA
   SELECT * FROM elements WHERE name = 'foo'
   → Retorna elemento(s) com código completo

5. BUSCA SEMÂNTICA
   embedding(query) → cosine_similarity → top-k
   → Retorna elementos similares com score

6. LEITURA COMPLETA
   element.full_source → código-fonte completo
   element.dependencies → funções/classes que usa
