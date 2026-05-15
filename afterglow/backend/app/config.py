from functools import lru_cache
from typing import Optional
from uuid import UUID

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    app_env: str = "local"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"
    max_file_size_mb: int = 20
    demo_mode: bool = False

    # Single-tenant pinning. If unset, /businesses/current returns the oldest
    # business in DB. The multi-business demo URLs still work because they
    # resolve through business_domain (see /dialer/incoming/[callId]).
    default_business_id: Optional[UUID] = Field(
        default=None, alias="AFTERGLOW_DEFAULT_BUSINESS_ID"
    )

    database_url: str = "postgresql+asyncpg://afterglow:afterglow@postgres:5432/afterglow"

    google_api_key: str = ""
    # gemini-flash-latest is the alias that always points to the most recent
    # Flash. We avoid `gemini-2.5-flash` here on purpose: it spends most of
    # its budget on internal "thinking" tokens and frequently returns empty
    # text on short prompts, which then drops us to the offline stub.
    gemini_default_model: str = "gemini-flash-latest"
    gemini_template_builder_model: str = "gemini-3-flash-preview"

    vultr_inference_base_url: str = "https://api.vultrinference.com/v1"
    vultr_inference_api_key: str = ""
    vultr_inference_model: str = "kimi-k2-instruct"
    vultr_vector_default_collection: str = ""

    speechmatics_api_key: str = ""
    speechmatics_batch_url: str = "https://asr.api.speechmatics.com/v2"

    audio_storage_dir: str = "/var/data/audio"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
