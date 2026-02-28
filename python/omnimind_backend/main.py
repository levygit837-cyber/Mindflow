import logging

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from omnimind_backend.api.router import router
from omnimind_backend.infra.config import get_settings
from omnimind_backend.infra.logging import configure_logging
from omnimind_backend.storage.db import engine
from omnimind_backend.storage.models import Base

settings = get_settings()
configure_logging(logging.DEBUG if settings.app_env == "development" else logging.INFO)

app = FastAPI(title=settings.app_name)


def _parse_csv(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


cors_allow_origins = _parse_csv(settings.cors_allow_origins)
cors_allow_methods = _parse_csv(settings.cors_allow_methods) or ["*"]
cors_allow_headers = _parse_csv(settings.cors_allow_headers) or ["*"]
cors_allow_credentials = settings.cors_allow_credentials and "*" not in cors_allow_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allow_origins,
    allow_credentials=cors_allow_credentials,
    allow_methods=cors_allow_methods,
    allow_headers=cors_allow_headers,
)

app.include_router(router)


@app.on_event("startup")
def startup() -> None:
    # Convenience bootstrap for local environments.
    Base.metadata.create_all(bind=engine)


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
