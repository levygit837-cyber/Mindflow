"""Session Memory — Memória Semântica de Sessões.

Gerencia contexto dentro de sessões com embeddings vetoriais em tempo real.
SessionChunker (LLM-based) foi removido. Retrieval agora usa pgvector diretamente.

Core Services:
- SessionMemoryService: Serviço principal de memória de sessão
- MemoryDatabase: Persistência especializada
"""

from .service import SessionMemoryService
from .storage import MemoryDatabase

__all__ = [
    "SessionMemoryService",
    "MemoryDatabase",
]
