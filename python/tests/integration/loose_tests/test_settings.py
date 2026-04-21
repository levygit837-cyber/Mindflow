import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "MindFlow Python Backend"
    rate_limit_enabled: bool = False
    grpc_secure: bool = False
    grpc_tls_cert_path: str | None = None
    grpc_tls_key_path: str | None = None
    grpc_tls_ca_path: str | None = None

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

if __name__ == "__main__":
    settings = Settings()
    print(f"Rate Limiting: {settings.rate_limit_enabled}")
    print(f"gRPC Secure: {settings.grpc_secure}")
    print(f"TLS Cert: {settings.grpc_tls_cert_path}")
