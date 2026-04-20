from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_root_env() -> str:
    """Walk up from CWD to find root .env (contains docker-compose.yml)."""
    current = Path.cwd()
    for parent in [current, *current.parents]:
        if (parent / "docker-compose.yml").exists():
            return str(parent / ".env")
    return str(current / ".env")


class SharedSettings(BaseSettings):
    """Base settings all services inherit. Loads from root .env automatically."""

    model_config = SettingsConfigDict(
        env_file=os.getenv("ENV_FILE", _find_root_env()),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Postgres
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    db_host: str = "localhost"
    postgres_port: int = 5432

    # CORS
    allowed_origins: str = "http://localhost:4200"

    # OpenTelemetry (optional — services that don't need tracing can skip)
    otel_collector_endpoint_grpc: str | None = None

    def get_allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    def get_database_url(self, db_name: str) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.db_host}:{self.postgres_port}/{db_name}"
        )
