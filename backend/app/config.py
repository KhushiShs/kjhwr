"""Environment-based settings for WindWise backend.

All settings can be configured via environment variables or a .env file.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment or defaults."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    port: int = 8000
    host: str = "0.0.0.0"
    cors_origins: str | list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]
    data_dir: Path = Path(__file__).resolve().parents[2] / "data"
    default_cutoff_hour: int = 9
    default_cutoff_minute: int = 0

    @field_validator("cors_origins", mode="after")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            if value.strip() == "*":
                return ["*"]
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        if isinstance(value, list):
            return [str(v).strip() for v in value if str(v).strip()]
        return []

    @field_validator("data_dir", mode="before")
    @classmethod
    def parse_data_dir(cls, value: object) -> Path:
        if isinstance(value, (str, Path)):
            p = Path(value)
            if not p.is_absolute():
                # Prefer data/ relative to project root or current working dir if present
                if p.exists():
                    return p.resolve()
                repo_root = Path(__file__).resolve().parents[2] / p
                if repo_root.exists():
                    return repo_root.resolve()
            return p.resolve()
        return Path(value)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()
