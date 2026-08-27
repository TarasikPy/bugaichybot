"""Application settings and configuration module using Pydantic Settings."""

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings loaded from environment variables and .env file."""

    BOT_TOKEN: str
    WEATHER_API_KEY: str = ""
    DEFAULT_CHAT_ID: int = -1004397346715
    PORT: int = 10000
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "production"
    ADMIN_USER_IDS: list[int] = [1318789006]

    # Concurrency and Media Downloader Limits
    MAX_CONCURRENT_DOWNLOADS: int = 3
    MAX_VIDEO_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB Telegram limit
    HTTP_TIMEOUT_SECONDS: float = 30.0
    FAST_API_TIMEOUT_SECONDS: float = 10.0

    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = Path(__file__).resolve().parent.parent.parent / "data"
    STORAGE_DIR: Path = Path(__file__).resolve().parent.parent.parent / "storage"
    RELATIONSHIPS_DIR: Path = Path(__file__).resolve().parent.parent.parent / "relationships_chats"

    # Cobalt fallback API endpoints
    COBALT_INSTANCES: list[str] = [
        "https://api.cobalt.tools/api/json",
        "https://cobalt-api.kwiatekm.tokyo/api/json",
        "https://co.wuk.sh/api/json",
    ]

    # HTTP Client Headers
    DEFAULT_USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    @field_validator("BOT_TOKEN")
    @classmethod
    def validate_bot_token(cls, v: str) -> str:
        """Validate Telegram bot token format."""
        token = v.strip()
        if not token:
            raise ValueError(
                "BOT_TOKEN не знайдено в змінних середовища! Створіть файл .env з BOT_TOKEN."
            )
        if ":" not in token or len(token.split(":")) != 2:
            raise ValueError(
                "Неправильний формат BOT_TOKEN! Токен повинен мати формат: ЧИСЛА:ЛІТЕРИ"
            )
        return token

    @property
    def default_headers(self) -> dict[str, str]:
        """Return standardized headers for external HTTP requests."""
        return {
            "User-Agent": self.DEFAULT_USER_AGENT,
            "Accept": "*/*",
        }

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()  # type: ignore[call-arg]
