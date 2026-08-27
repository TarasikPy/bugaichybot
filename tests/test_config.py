"""Unit tests for configuration loading and validation."""

import pytest

from src.core.config import Settings


def test_settings_validation() -> None:
    """Test valid bot token validation."""
    settings = Settings(
        BOT_TOKEN="123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ",
        DEFAULT_CHAT_ID=-100123456789,
        PORT=10000,
    )
    assert settings.BOT_TOKEN == "123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ"
    assert settings.PORT == 10000
    assert settings.DEFAULT_CHAT_ID == -100123456789


def test_invalid_token_raises_error() -> None:
    """Test invalid token raises ValueError."""
    with pytest.raises(ValueError, match="Неправильний формат BOT_TOKEN"):
        Settings(BOT_TOKEN="invalid_token_without_colon")
