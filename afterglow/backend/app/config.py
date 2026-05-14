from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_env: str = "local"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"
    max_file_size_mb: int = 20
    demo_mode: bool = False

    database_url: str = "postgresql+asyncpg://afterglow:afterglow@postgres:5432/afterglow"

    google_api_key: str = ""
    gemini_default_model: str = "gemini-2.5-flash"
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
