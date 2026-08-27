"""Legacy configuration bridge forwarding to src.core.config."""

from src.core.config import get_settings

_s = get_settings()
BOT_TOKEN = _s.BOT_TOKEN
WEATHER_API_KEY = _s.WEATHER_API_KEY
DEFAULT_CHAT_ID = str(_s.DEFAULT_CHAT_ID)
