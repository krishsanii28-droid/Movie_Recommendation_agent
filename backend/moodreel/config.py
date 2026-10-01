"""Application settings, loaded from environment variables / `.env`.

Every AI component has an ``auto`` mode: it uses the full Hugging Face stack when
the libraries (and model weights) are available and silently falls back to a
lightweight built-in implementation otherwise. That keeps the app runnable on a
laptop, in CI and on free hosting tiers.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BACKEND_DIR.parent / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- TMDB ---------------------------------------------------------------
    tmdb_api_key: str = ""
    tmdb_read_token: str = ""  # v4 bearer token (alternative to api key)
    tmdb_base_url: str = "https://api.themoviedb.org/3"
    tmdb_image_base: str = "https://image.tmdb.org/t/p"
    tmdb_requests_per_second: float = 20.0  # TMDB allows ~40-50/s; stay polite
    region: str = "IN"
    languages: list[str] = Field(default_factory=lambda: ["ml", "hi", "ta", "te", "en"])

    # --- Storage --------------------------------------------------------------
    database_url: str = f"sqlite:///{DATA_DIR / 'moodreel.db'}"
    chroma_dir: str = str(DATA_DIR / "chroma")
    vector_backend: Literal["auto", "chroma", "memory"] = "auto"

    # --- Models ---------------------------------------------------------------
    embedding_backend: Literal["auto", "sentence-transformers", "hashing"] = "auto"
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    emotion_backend: Literal["auto", "hf", "lexicon"] = "auto"
    emotion_model: str = "j-hartmann/emotion-english-distilroberta-base"
    llm_backend: Literal["none", "local", "hf_inference"] = "none"
    llm_model: str = "Qwen/Qwen2.5-1.5B-Instruct"
    llm_max_new_tokens: int = 512
    hf_token: str = ""

    # --- Agent ----------------------------------------------------------------
    agent_max_steps: int = 6
    default_recommendations: int = 4

    # --- API ------------------------------------------------------------------
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )
    log_level: str = "INFO"
    session_ttl_minutes: int = 120

    @property
    def tmdb_configured(self) -> bool:
        return bool(self.tmdb_api_key or self.tmdb_read_token)


@lru_cache
def get_settings() -> Settings:
    return Settings()
