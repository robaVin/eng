"""Application configuration, loaded from environment / .env file."""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # AI (OpenAI)
    ai_provider: str = "openai"
    openai_api_key: str | None = None
    ai_model: str = "gpt-4o"  # vision-capable default; auto-falls back if unavailable

    # Auth
    teacher_password: str = "changeme"
    secret_key: str = "dev-insecure-secret-change-me"

    # Storage
    data_dir: str = "./data"

    # Server / cookies
    cookie_secure: bool = False
    max_upload_mb: int = 15

    @property
    def data_path(self) -> Path:
        p = Path(self.data_dir).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def uploads_path(self) -> Path:
        p = self.data_path / "uploads"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def db_url(self) -> str:
        return f"sqlite:///{(self.data_path / 'app.db').as_posix()}"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def ai_configured(self) -> bool:
        import os

        return bool(self.openai_api_key or os.environ.get("OPENAI_API_KEY"))


settings = Settings()
