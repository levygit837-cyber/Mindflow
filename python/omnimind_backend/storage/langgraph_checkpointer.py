from contextlib import asynccontextmanager

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from omnimind_backend.infra.config import get_settings


@asynccontextmanager
async def langgraph_checkpointer():
    settings = get_settings()
    async with AsyncPostgresSaver.from_conn_string(settings.database_url) as checkpointer:
        await checkpointer.setup()
        yield checkpointer
