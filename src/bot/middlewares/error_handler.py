"""Global error handling middleware for Telegram updates."""

from telegram.error import Conflict, Forbidden, NetworkError, TelegramError
from telegram.ext import ContextTypes

from src.core.logger import get_logger

logger = get_logger(__name__)


async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle exceptions raised in telegram update handlers."""
    error = context.error

    if isinstance(error, Conflict):
        logger.warning(
            f"Telegram 409 Conflict: another bot instance is currently active. Details: {error}"
        )
        return

    if isinstance(error, NetworkError):
        logger.warning(f"Telegram NetworkError: {error}")
        return

    if isinstance(error, Forbidden):
        logger.info(f"Bot was blocked or lacks permissions in chat: {error}")
        return

    if isinstance(error, TelegramError):
        logger.warning(f"Telegram API Error: {error}")
        return

    logger.error(
        f"Unhandled exception while processing update {update}: {error}",
        exc_info=error,
    )
