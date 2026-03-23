"""
Application configuration loaded from environment variables / .env file.
"""

from __future__ import annotations

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


_ROOT = Path(__file__).resolve().parent.parent  # founders_office_ai_ops/


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM (Google Gemini)
    google_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    # Database
    database_url: str = f"sqlite:///{_ROOT / 'founders_ops.db'}"

    # FAISS
    faiss_index_path: str = str(_ROOT / "faiss_index")

    # App
    app_env: str = "development"
    log_level: str = "INFO"


settings = Settings()
