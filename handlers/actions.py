"""Legacy actions handler bridge."""

from src.bot.handlers.actions import handle_message
from src.infrastructure.constants.aliases import COMMAND_ALIASES

handle_action_command = handle_message

__all__ = [
    "COMMAND_ALIASES",
    "handle_action_command",
    "handle_message",
]
