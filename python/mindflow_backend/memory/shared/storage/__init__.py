"""Shared Storage Layer.

Camada de abstração de banco de dados para suporte a:
- Múltiplos databases (PostgreSQL, SQLite)
- Connection pooling e otimizações
- Migrations e versionamento de schema
- Transações e consistência de dados
"""

from .database import MemoryDatabase
from .vector_db import MemoryVectorDB
from .models import Base

__all__ = [
    "MemoryDatabase",
    "MemoryVectorDB", 
    "Base",
]
