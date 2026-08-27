"""Telegram bot application builder and handler registration."""

from telegram import (
    BotCommand,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    MessageReactionHandler,
    filters,
)

from src.bot.handlers.actions import handle_message
from src.bot.handlers.analytics import (
    chat_stats_command,
    handle_profile_callback,
    handle_reaction_update,
    id_command,
    profile_command,
)
from src.bot.handlers.basic import (
    button_callback,
    commands_command,
    flipcoin_command,
    help_command,
    start_command,
)
from src.bot.handlers.mechanics import risk_command
from src.bot.handlers.relationships import (
    breakup_command,
    dating_command,
    handle_relationship_callback,
    my_relationships_command,
    proposals_command,
    relationships_command,
    trio_command,
)
from src.bot.handlers.weather import weather_command
from src.bot.middlewares.error_handler import global_error_handler
from src.core.config import get_settings
from src.core.logger import get_logger

logger = get_logger(__name__)


async def setup_bot_commands(application: Application) -> None:
    """Register bot command scopes for group and private chats."""
    try:
        await application.bot.delete_webhook(drop_pending_updates=True)
    except Exception as e:
        logger.warning(f"delete_webhook notice: {e}")

    private_commands = [
        BotCommand("start", "💫 Головне меню бота"),
        BotCommand("help", "📋 Довідка та команди"),
        BotCommand("profile", "👤 Профіль та психоаналіз"),
        BotCommand("weather", "🌤 Погода"),
    ]

    group_commands = [
        BotCommand("start", "💫 Головне меню бота"),
        BotCommand("profile", "👤 Профіль та психоаналіз"),
        BotCommand("id", "🆔 Інфо про користувача"),
        BotCommand("chatstats", "📊 Активність чату"),
        BotCommand("relationships", "💕 Список пар чату"),
        BotCommand("myrelationships", "❤️ Мої стосунки"),
        BotCommand("dating", "💍 Запропонувати зустрічатися"),
        BotCommand("breakup", "💔 Розірвати стосунки"),
        BotCommand("risk", "🎰 РП-Рулетка подій"),
        BotCommand("flipcoin", "🪙 Монетка (Орел чи Решка)"),
        BotCommand("weather", "🌤 Погода"),
        BotCommand("commands", "📋 Всі команди"),
    ]

    try:
        await application.bot.set_my_commands(
            private_commands, scope=BotCommandScopeAllPrivateChats()
        )
        await application.bot.set_my_commands(group_commands, scope=BotCommandScopeAllGroupChats())
    except Exception as e:
        logger.warning(f"Could not register bot commands with Telegram: {e}")


def create_bot_application() -> Application:
    """Build and configure telegram Application with all handlers and error middleware."""
    settings = get_settings()

    application = (
        Application.builder()
        .token(settings.BOT_TOKEN)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .pool_timeout(30)
        .build()
    )

    application.post_init = setup_bot_commands

    # Basic Commands
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("commands", commands_command))
    application.add_handler(CommandHandler("flipcoin", flipcoin_command))

    # Relationships Commands
    application.add_handler(CommandHandler("relationships", relationships_command))
    application.add_handler(CommandHandler("myrelationships", my_relationships_command))
    application.add_handler(CommandHandler("proposals", proposals_command))
    application.add_handler(CommandHandler("dating", dating_command))
    application.add_handler(CommandHandler("trio", trio_command))
    application.add_handler(CommandHandler("breakup", breakup_command))
    application.add_handler(CommandHandler("divorce", breakup_command))

    # Analytics & Profiling Commands
    application.add_handler(CommandHandler("chatstats", chat_stats_command))
    application.add_handler(CommandHandler("profile", profile_command))
    application.add_handler(CommandHandler(["id", "whois"], id_command))

    # Utility Commands
    application.add_handler(CommandHandler("weather", weather_command))
    application.add_handler(CommandHandler("risk", risk_command))

    # Reaction updates
    application.add_handler(MessageReactionHandler(handle_reaction_update))

    # Inline callbacks
    application.add_handler(CallbackQueryHandler(handle_profile_callback, pattern=r"^prof_"))
    application.add_handler(
        CallbackQueryHandler(handle_relationship_callback, pattern=r"^(rel_|breakup_)")
    )
    application.add_handler(CallbackQueryHandler(button_callback))

    # Message handlers (Text, RP, Media URLs)
    application.add_handler(MessageHandler(~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.COMMAND, handle_message))

    # Error handling middleware
    application.add_error_handler(global_error_handler)

    return application
