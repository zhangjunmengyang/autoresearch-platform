"""Runtime settings."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings.

    The default store is a JSON document so the platform can run locally before
    PostgreSQL is provisioned. Alembic remains the schema contract for durable
    deployments.
    """

    model_config = SettingsConfigDict(env_prefix="AUTORESEARCH_", env_file=".env", extra="ignore")

    app_name: str = "AutoResearch Platform"
    api_prefix: str = "/api/v1"
    project_root: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[3])
    data_path: Path | None = None
    store_backend: Literal["json", "postgres"] = "json"
    database_url: str | None = None
    api_token: str | None = None
    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["http://127.0.0.1:5174"])

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("["):
                return json.loads(stripped)
            return [item.strip() for item in stripped.split(",") if item.strip()]
        return value

    @property
    def store_path(self) -> Path:
        return self.data_path or self.project_root / "data" / "autoresearch_store.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
