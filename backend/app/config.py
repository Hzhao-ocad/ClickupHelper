from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ClickUp
    clickup_api_token: str = ""
    default_clickup_list_id: str = ""

    # DeepSeek (OpenAI-compatible)
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"
    deepseek_max_tokens: int = 2000
    deepseek_temperature: float = 0.1

    # Whisper
    whisper_model_size: str = "large-v3"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"

    # Session
    session_ttl_minutes: int = 60

    # Static files
    @property
    def static_dir(self) -> Path:
        return Path(__file__).resolve().parent.parent / "static"

    # ClickUp rate limiting
    clickup_rate_limit_delay_ms: int = 200
