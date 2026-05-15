from functools import lru_cache

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

    # Comma-separated list of allowed CORS origins. Production sets this to the
    # app and demo-site sslip.io URLs; local dev defaults to the common ports.
    cors_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000,http://localhost:8081,http://localhost:5173",
        alias="CORS_ORIGINS",
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
    # MiniMax-M2 is the model Vultr's /v1/chat/completions/RAG actually serves
    # (it transparently swaps requests for kimi-k2-instruct, deepseek-r1, etc).
    # Calling it by name gets us an honest audit_log and removes a misleading
    # "model: kimi-k2-instruct" entry that production would never see.
    vultr_inference_model: str = "MiniMaxAI/MiniMax-M2.7"
    vultr_vector_default_collection: str = ""

    speechmatics_api_key: str = ""
    speechmatics_batch_url: str = "https://asr.api.speechmatics.com/v2"

    audio_storage_dir: str = "/var/data/audio"

    # Demo iframe sandbox: visitors of demo.* hit the backend with an
    # `X-Demo-Session: <uuid>` header that scopes their writes. To run the
    # pitch live against the real (single-tenant) data while keeping the
    # sandbox active for the public, set this token in Coolify and append
    # `?bypass=<token>` to the app URL. The frontend then sends
    # `X-Demo-Session: bypass` and the backend treats the request as the
    # production tenant. Empty string disables the bypass entirely.
    demo_bypass_token: str = ""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
