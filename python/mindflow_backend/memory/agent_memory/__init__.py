"""Agent Memory - Memória Agêntica (LangGraph).

Gerencia estado persistente dos agentes com suporte a:
- Rolling windows para memória de longo prazo
- Sumarização automática de contexto
- Extração de fatos relevantes
- Checkpoints do LangGraph para persistência
- Integração com PostgreSQL para performance

Core Services:
- AgentMemoryService: Serviço principal de memória agêntica
- LangGraphCheckpointer: Persistência de estado via checkpoints
- RollingWindows: Gerenciamento de janelas rolantes
- FactExtractor: Extração de fatos do contexto
"""

from .service import AgentMemoryService
from .checkpointer import langgraph_checkpointer
from .windows import RollingWindow

__all__ = [
    "AgentMemoryService",
    "langgraph_checkpointer",
    "RollingWindow",
]
