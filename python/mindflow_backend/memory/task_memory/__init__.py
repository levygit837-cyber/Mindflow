"""Task Memory - Memória Semântica de Tasks.

Gerencia contexto entre tasks e sub-tasks com suporte a:
- Memória específica para decomposição de tarefas
- Recuperação cross-task entre diferentes tasks
- Integração com decomposition engine
- Compartilhamento de contexto entre tasks dependentes

Core Services:
- TaskMemoryService: Serviço principal de memória de tasks
- TaskRetriever: Recuperação semântica cross-task
- TaskDecomposer: Integração com decomposition engine
- TaskIntegration: Ponte com sistema de orquestração
"""

from .decomposer import TaskDecomposer
from .integration import TaskIntegration
from .retriever import TaskRetriever
from .service import TaskMemoryService

__all__ = [
    "TaskMemoryService",
    "TaskRetriever",
    "TaskDecomposer", 
    "TaskIntegration",
]
