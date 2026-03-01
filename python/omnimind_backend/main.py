import logging

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from omnimind_backend.agents._registry import register_all_personalities
from omnimind_backend.api.router import router
from omnimind_backend.infra.config import get_settings
from omnimind_backend.infra.logging import configure_logging
from omnimind_backend.infra.middleware.rate_limiter import RateLimiterMiddleware
from omnimind_backend.infra.middleware.request_context import RequestContextMiddleware
from omnimind_backend.infra.middleware.security_headers import SecurityHeadersMiddleware
from omnimind_backend.storage.db import engine
from omnimind_backend.storage.models import Base

settings = get_settings()
configure_logging(logging.DEBUG if settings.app_env == "development" else logging.INFO)

app = FastAPI(title=settings.app_name)


def _parse_csv(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


cors_allow_origins = _parse_csv(settings.cors_allow_origins)
cors_allow_credentials = settings.cors_allow_credentials and "*" not in cors_allow_origins
cors_expose_headers = _parse_csv(settings.cors_expose_headers)

# Production CORS hardening: restrict methods and headers.
if settings.app_env == "production":
    cors_allow_methods = _parse_csv(settings.cors_allow_methods) or ["GET", "POST", "OPTIONS"]
    cors_allow_headers = _parse_csv(settings.cors_allow_headers) or [
        "Authorization", "Content-Type", "X-Request-ID",
    ]
    cors_expose_headers = cors_expose_headers or ["X-Request-ID"]
else:
    cors_allow_methods = _parse_csv(settings.cors_allow_methods) or ["*"]
    cors_allow_headers = _parse_csv(settings.cors_allow_headers) or ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allow_origins,
    allow_credentials=cors_allow_credentials,
    allow_methods=cors_allow_methods,
    allow_headers=cors_allow_headers,
    expose_headers=cors_expose_headers,
)

app.include_router(router)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimiterMiddleware)
app.add_middleware(RequestContextMiddleware)


@app.on_event("startup")
def startup() -> None:
    # Convenience bootstrap for local environments.
    Base.metadata.create_all(bind=engine)
    # Phase 2: Boot agent registry.
    register_all_personalities()


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
