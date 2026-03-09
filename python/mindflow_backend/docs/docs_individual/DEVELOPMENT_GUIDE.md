# Guia de Desenvolvimento - MindFlow Backend

## 📋 **Visão Geral**

Este guia descreve as melhores práticas e padrões para desenvolvimento no MindFlow backend após a migração de serviços e schemas.

---

## 🏗️ **Arquitetura Centralizada**

### **Estrutura de Diretórios**

```
mindflow_backend/
├── services/                 # 🏭 Serviços de Negócio (CENTRALIZADO)
│   ├── core/                # Serviços fundamentais
│   ├── orchestration/       # Orquestração e coordenação
│   ├── communication/       # gRPC e streaming
│   ├── memory/             # Gestão de memória
│   ├── context/            # Contexto semântico
│   ├── monitoring/         # Saúde e métricas
│   └── interfaces/         # Interfaces legadas
├── schemas/                 # 📋 Contratos de Dados
│   ├── memory/             # Schemas de memória (NOVO)
│   ├── session/            # Schemas de sessão
│   ├── agents/             # Schemas de agentes
│   ├── orchestration/      # Schemas de orquestração
│   └── api/                # Schemas de API
├── interfaces/              # 🔌 Contratos de Código
│   ├── services/           # Interfaces de serviços (CENTRALIZADO)
│   ├── agents/             # Interfaces de agentes
│   ├── api/                # Interfaces de API
│   └── core/               # Interfaces core
└── [outros módulos...]
```

---

## 🚀 **Guia Rápido de Uso**

### **1. Importando Serviços**

#### ✅ **Forma Recomendada**
```python
# Import centralizado (NOVO PADRÃO)
from mindflow_backend.services import (
    get_agent_service,
    get_memory_service,
    get_orchestration_service,
    get_session_service,
)

# Uso simples
agent_service = get_agent_service()
memory_service = get_memory_service()
```

#### ⚠️ **Forma Legada (Funciona, mas não recomendada)**
```python
# Ainda funciona via aliases, mas evite usar
from mindflow_backend.api.services import AgentService
from mindflow_backend.memory.core.service import MemoryService
```

### **2. Usando Schemas**

#### **Schemas Memory (NOVO)**
```python
from mindflow_backend.schemas.memory import (
    MemoryEntry,           # Contrato principal
    MemoryStoreRequest,   # Requisição
    MemoryStoreResponse,  # Resposta
    ContextWindow,        # Janela de contexto
    MemoryCursor,         # Cursor de navegação
)

# Criando entrada de memória
entry = MemoryEntry(
    id=uuid4(),
    session_id=uuid4(),
    content="Conteúdo importante",
    token_count=4,
    memory_type=MemoryType.EPISODIC
)

# Requisição de armazenamento
request = MemoryStoreRequest(
    session_id=uuid4(),
    content="Novo conteúdo",
    generate_embedding=True,
    tags=["importante", "contexto"]
)
```

#### **Schemas Session**
```python
from mindflow_backend.schemas.session import (
    RetrievalMode,
    RetrievedContext,
    ReviewTask,
    ReviewExecutionContext,
)
```

### **3. Implementando Interfaces**

#### **Novo Serviço com Interface**
```python
from mindflow_backend.services.interfaces.base import BaseAbstractService
from mindflow_backend.interfaces.services.memory import MemoryServiceInterface

class CustomMemoryService(BaseAbstractService, MemoryServiceInterface):
    """Serviço personalizado de memória."""
    
    def __init__(self):
        super().__init__()
        # Inicialização específica
    
    async def store_memory(self, session_id, agent_id, content, metadata=None):
        """Implementação obrigatória da interface."""
        self.log_operation("store_memory", session_id=session_id)
        # Lógica de armazenamento
        return {"success": True, "memory_id": uuid4()}
    
    async def retrieve_memory(self, session_id, limit=None, filters=None):
        """Implementação obrigatória da interface."""
        # Lógica de recuperação
        return []
    
    # Outros métodos obrigatórios...
```

---

## 🔧 **Padrões de Desenvolvimento**

### **1. Estrutura de Serviço**

#### **Template de Serviço**
```python
"""[Nome] service for [descrição].

This service provides [funcionalidade principal] including
[características importantes].
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.services.interfaces.base_interfaces import BaseAbstractService
from mindflow_backend.interfaces.services.[domain]_interfaces import [Service]Interface

class [Nome]Service(BaseAbstractService, [Service]Interface):
    """Service for [descrição detalhada].
    
    This service handles [funcionalidades] with [características]
    and maintains [qualidades].
    """
    
    def __init__(self) -> None:
        """Initialize [nome] service."""
        super().__init__()
        self.logger = get_logger(__name__)
        # Inicialização de dependências
    
    def _get_logger(self):
        """Get logger instance for this service."""
        return get_logger(__name__)
    
    # Métodos da interface...
```

### **2. Padrões de Import**

#### **Imports Organizados**
```python
# 1. Standard library
from __future__ import annotations
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional
from uuid import UUID

# 2. Third-party
from pydantic import BaseModel, Field

# 3. Internal - infraestrutura
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.infra.config import get_settings

# 4. Internal - schemas
from mindflow_backend.schemas.memory import MemoryEntry

# 5. Internal - interfaces
from mindflow_backend.interfaces.services.memory import MemoryServiceInterface

# 6. Internal - services
from mindflow_backend.services import get_memory_service
```

### **3. Padrões de Logging**

#### **Logging Estruturado**
```python
# Usar log_operation para operações importantes
self.log_operation(
    "store_memory",
    session_id=session_id,
    content_length=len(content),
    agent_id=agent_id
)

# Para erros
self.logger.error(
    "Failed to store memory",
    session_id=session_id,
    error=str(e),
    exc_info=True
)

# Para informações gerais
self.logger.info(
    "Memory service initialized",
    service_type="custom",
    version="1.0.0"
)
```

---

## 📋 **Checklist de Desenvolvimento**

### **Antes de Commitar**

#### ✅ **Serviços**
- [ ] Implementa interface correta
- [ ] Usa logging estruturado
- [ ] Trata exceções adequadamente
- [ ] Documenta métodos públicos
- [ ] Segue padrão de imports

#### ✅ **Schemas**
- [ ] Usa Pydantic BaseModel
- [ ] Documenta todos os campos
- [ ] Valida dados de entrada
- [ ] Fornece exemplos
- [ ] Lida com tipos opcionais

#### ✅ **Interfaces**
- [ ] Define métodos abstratos
- [ ] Documenta contratos
- [ ] Usa typing adequado
- [ ] Fornece exemplos de uso

---

## 🔄 **Migração de Código Legado**

### **1. Atualizando Imports**

#### **De (Legado)**
```python
from mindflow_backend.api.services.agent_service import AgentService
from mindflow_backend.memory.core.service import MemoryService
```

#### **Para (Novo)**
```python
from mindflow_backend.services import get_agent_service, get_memory_service
```

### **2. Atualizando Uso de Schemas**

#### **De (Legado)**
```python
# Se usava schemas espalhados
from some_random_place import SomeSchema
```

#### **Para (Novo)**
```python
# Usar schemas centralizados
from mindflow_backend.schemas.memory import MemoryEntry
```

### **3. Implementando Interfaces**

#### **De (Sem Interface)**
```python
class MyService:
    def some_method(self):
        pass
```

#### **Para (Com Interface)**
```python
class MyService(BaseAbstractService, MyServiceInterface):
    async def some_method(self):
        self.log_operation("some_method")
        pass
```

---

## 🧪 **Testes e Validação**

### **1. Teste de Import**

```python
def test_service_imports():
    """Testa se todos os serviços importam corretamente."""
    from mindflow_backend.services import (
        get_agent_service,
        get_memory_service,
        # ... outros serviços
    )
    
    # Testa instanciação
    agent_service = get_agent_service()
    assert agent_service is not None
```

### **2. Teste de Interface**

```python
def test_interface_implementation():
    """Testa se o serviço implementa a interface corretamente."""
    from mindflow_backend.services.memory.memory_service import MemoryService
    from mindflow_backend.interfaces.services.memory import MemoryServiceInterface
    
    service = MemoryService(None)
    assert hasattr(service, 'store_memory')
    assert hasattr(service, 'retrieve_memory')
```

### **3. Teste de Schema**

```python
def test_schema_validation():
    """Testa validação de schemas."""
    from mindflow_backend.schemas.memory import MemoryStoreRequest
    from uuid import uuid4
    
    request = MemoryStoreRequest(
        session_id=uuid4(),
        content="Test content"
    )
    
    assert request.session_id is not None
    assert request.content == "Test content"
```

---

## 🚨 **Boas Práticas de Segurança**

### **1. Validação de Entrada**
```python
# Sempre validar dados de entrada
from pydantic import validator

class MemoryStoreRequest(BaseModel):
    content: str = Field(min_length=1, max_length=100000)
    
    @validator('content')
    def validate_content(cls, v):
        if not v.strip():
            raise ValueError('Content cannot be empty')
        return v.strip()
```

### **2. Tratamento de Erros**
```python
async def store_memory(self, session_id, content, metadata=None):
    try:
        # Lógica principal
        result = await self._do_store_memory(session_id, content, metadata)
        return result
    except ValidationError as e:
        self.logger.error("Validation error", error=str(e))
        raise
    except DatabaseError as e:
        self.logger.error("Database error", error=str(e))
        raise ServiceError("Failed to store memory")
    except Exception as e:
        self.logger.error("Unexpected error", error=str(e), exc_info=True)
        raise
```

### **3. Logging Seguro**
```python
# Não logar dados sensíveis
self.log_operation(
    "store_memory",
    session_id=session_id,  # OK
    content_length=len(content),  # OK
    content=content  # ❌ NÃO logar conteúdo bruto
)
```

---

## 📚 **Recursos Adicionais**

### **Documentação**
- [Guia de Migração Completo](./MIGRACAO_SERVICOS_SCHEMAS_COMPLETA.md)
- [Referência de APIs](./API_REFERENCE.md)
- [Padrões de Arquitetura](./ARCHITECTURE_PATTERNS.md)

### **Ferramentas**
- **IDE**: Configurar autocomplete para novos imports
- **Linting**: Usar flake8/black com padrões atualizados
- **Testing**: pytest com fixtures para serviços

### **Comunidade**
- **Slack**: #mindflow-development
- **Reviews**: Code reviews focados em padrões
- **Mentoria**: Pair programming para migração

---

## 🔍 **Troubleshooting Comum**

### **Import Errors**
```python
# Erro: ModuleNotFoundError
# Solução: Verificar se o serviço está em /services/ e se __init__.py está atualizado
```

### **Interface Errors**
```python
# Erro: NotImplementedError
# Solução: Implementar todos os métodos abstratos da interface
```

### **Schema Validation**
```python
# Erro: ValidationError
# Solução: Verificar tipos e validadores dos schemas
```

---

## 🎯 **Roadmap Futuro**

### **Short Term (1-2 semanas)**
- [ ] Completar migração de código legado
- [ ] Adicionar mais testes de integração
- [ ] Otimizar performance de imports

### **Medium Term (1 mês)**
- [ ] Aplicar padrão a outros módulos
- [ ] Criar ferramentas de validação automática
- [ ] Documentar padrões adicionais

### **Long Term (2-3 meses)**
- [ ] Remoção de aliases legados
- [ ] Padronização completa do projeto
- [ ] Automação de verificações

---

**Status**: ✅ **GUIA ATUALIZADO E PRONTO PARA USO**

O MindFlow backend agora possui guias completos para desenvolvimento com a nova arquitetura centralizada! 🚀
