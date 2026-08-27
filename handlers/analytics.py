"""Legacy analytics handlers bridge."""

from src.bot.handlers.analytics import (
    chat_stats_command,
    handle_profile_callback,
    handle_reaction_update,
    id_command,
    profile_command,
)

__all__ = [
    "chat_stats_command",
    "handle_profile_callback",
    "handle_reaction_update",
    "id_command",
    "profile_command",
]
