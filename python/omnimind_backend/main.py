import logging

import uvicorn
from fastapi import FastAPI

from omnimind_backend.api.deps import allowlist_repository
from omnimind_backend.api.router import router
from omnimind_backend.infra.config import get_settings
from omnimind_backend.infra.logging import configure_logging
from omnimind_backend.storage.db import db_session, engine
from omnimind_backend.storage.models import Base


settings = get_settings()
configure_logging(logging.DEBUG if settings.app_env == "development" else logging.INFO)

app = FastAPI(title=settings.app_name)
app.include_router(router)


@app.on_event("startup")
def startup() -> None:
    # Convenience bootstrap for local environments.
    Base.metadata.create_all(bind=engine)

    # Read-only allowlist is seeded from env at startup.
    with db_session() as session:
        allowlist_repository.bootstrap_from_env(session, settings.allowed_paths)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def run() -> None:
    uvicorn.run(
        "omnimind_backend.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_env == "development",
    )


if __name__ == "__main__":
    run()
