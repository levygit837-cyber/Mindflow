from contextlib import asynccontextmanager

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from mindflow_backend.infra.config import get_settings


@asynccontextmanager
async def langgraph_checkpointer():
    """Async context manager providing an AsyncPostgresSaver for LangGraph state persistence."""
    settings = get_settings()
    async with AsyncPostgresSaver.from_conn_string(settings.database.url) as checkpointer:
        await checkpointer.setup()
        yield checkpointer


@asynccontextmanager
async def langgraph_store():
    """Async context manager providing an AsyncPostgresStore for agentic long-term memory."""
    from langgraph.store.postgres import AsyncPostgresStore

    settings = get_settings()
    async with AsyncPostgresStore.from_conn_string(settings.database.url) as store:
        await store.setup()
        yield store


@asynccontextmanager
async def langgraph_memory():
    """Combined context manager: yields (checkpointer, store) for full LangGraph memory.

    Use this when a graph node needs both thread-level state (checkpointer)
    and cross-thread persistent facts (store).
    """
    async with langgraph_checkpointer() as checkpointer, langgraph_store() as store:
        yield checkpointer, store
