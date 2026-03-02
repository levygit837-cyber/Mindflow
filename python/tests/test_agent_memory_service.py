from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from omnimind_backend.memory.service import AgentMemoryService
from omnimind_backend.storage.models import (
    AgentMemoryCursor,
    AgentMemoryEmbedding,
    AgentMemoryFact,
    AgentMemoryWindow,
    Base,
)


def _make_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return Session(bind=engine)


def test_memory_service_creates_summary_window_per_agent_threshold() -> None:
    db = _make_session()
    service = AgentMemoryService(
        summary_window_tokens=20,
        retrieval_top_k=4,
        embedding_dims=64,
    )

    service.record_message(
        db,
        session_id="sess-1",
        agent_id="coder",
        role="user",
        content="Planejar arquitetura de autenticação com JWT e refresh token.",
    )
    service.record_message(
        db,
        session_id="sess-1",
        agent_id="coder",
        role="assistant",
        content="Definir endpoints /login e /refresh, política de expiração e rotação de refresh token.",
    )
    db.commit()

    windows = list(
        db.scalars(
            select(AgentMemoryWindow).where(
                AgentMemoryWindow.session_id == "sess-1",
                AgentMemoryWindow.agent_id == "coder",
            )
        )
    )
    assert len(windows) == 1
    assert windows[0].summary_md
    assert windows[0].coverage_ratio == 1.0

    facts = list(
        db.scalars(
            select(AgentMemoryFact).where(
                AgentMemoryFact.session_id == "sess-1",
                AgentMemoryFact.agent_id == "coder",
            )
        )
    )
    assert facts

    embeddings = list(
        db.scalars(
            select(AgentMemoryEmbedding).where(
                AgentMemoryEmbedding.session_id == "sess-1",
                AgentMemoryEmbedding.agent_id == "coder",
            )
        )
    )
    assert embeddings

    cursor = db.scalar(
        select(AgentMemoryCursor).where(
            AgentMemoryCursor.session_id == "sess-1",
            AgentMemoryCursor.agent_id == "coder",
        )
    )
    assert cursor is not None
    assert cursor.window_index == 1
    assert cursor.tokens_since_summary == 0


def test_memory_service_retrieves_relevant_rag_context() -> None:
    db = _make_session()
    service = AgentMemoryService(
        summary_window_tokens=12,
        retrieval_top_k=3,
        embedding_dims=64,
    )

    service.record_message(
        db,
        session_id="sess-2",
        agent_id="researcher",
        role="user",
        content="Precisamos pesquisar benchmark de bancos vetoriais e opções de pgvector.",
    )
    service.record_message(
        db,
        session_id="sess-2",
        agent_id="researcher",
        role="assistant",
        content="Comparação inicial: pgvector, Qdrant e Pinecone com foco em custo e latência.",
    )
    db.commit()

    result = service.retrieve_context(
        db,
        session_id="sess-2",
        agent_id="researcher",
        query="Quais decisões já tomamos sobre pgvector e vetores?",
    )

    assert result.context
    assert result.references
    lowered = result.context.lower()
    assert "pgvector" in lowered or "vetoria" in lowered
