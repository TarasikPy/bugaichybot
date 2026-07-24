import logging
from telegram import Update, BotCommandScopeAllGroupChats, BotCommandScopeAllPrivateChats, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    MessageReactionHandler,
    filters
)

from config.settings import BOT_TOKEN
from handlers.basic import (
    start_command,
    help_command,
    flipcoin_command,
    commands_command,
    button_callback
)
from handlers.relationships import (
    relationships_command,
    my_relationships_command,
    proposals_command,
    dating_command,
    trio_command,
    breakup_command,
    handle_relationship_callback
)
from handlers.analytics import chat_stats_command, profile_command, handle_reaction_update
from handlers.actions import handle_message

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def setup_bot_commands(application: Application) -> None:
    """Налаштовує меню команд бота"""
    private_commands = [
        BotCommand("start", "Головне меню бота"),
        BotCommand("help", "Довідка"),
        BotCommand("profile", "👤 Психологічний профіль та статистика")
    ]

    group_commands = [
        BotCommand("start", "💫 Розпочати роботу з ботом"),
        BotCommand("flipcoin", "🪙 Кинути монету"),
        BotCommand("relationships", "💕 Показати всі стосунки"),
        BotCommand("myrelationships", "❤️ Показати ваші стосунки"),
        BotCommand("commands", "📋 Всі команди"),
        BotCommand("dating", "💫 Розпочати стосунки (пропозиція з підтвердженням)"),
        BotCommand("breakup", "💔 Розірвати стосунки"),
        BotCommand("chatstats", "📊 Аналітика активності чату"),
        BotCommand("profile", "👤 Психологічний профіль та статистика")
    ]

    await application.bot.set_my_commands(private_commands, scope=BotCommandScopeAllPrivateChats())
    await application.bot.set_my_commands(group_commands, scope=BotCommandScopeAllGroupChats())

def main() -> None:
    """Головна точка входу: ініціалізація та запуск бота"""
    try:
        application = (
            Application.builder()
            .token(BOT_TOKEN)
            .connect_timeout(30)
            .read_timeout(30)
            .write_timeout(30)
            .pool_timeout(30)
            .build()
        )

        application.post_init = setup_bot_commands

        # Реєстрація хендлерів команд
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("flipcoin", flipcoin_command))
        application.add_handler(CommandHandler("relationships", relationships_command))
        application.add_handler(CommandHandler("myrelationships", my_relationships_command))
        application.add_handler(CommandHandler("proposals", proposals_command))
        application.add_handler(CommandHandler("dating", dating_command))
        application.add_handler(CommandHandler("trio", trio_command))
        application.add_handler(CommandHandler("breakup", breakup_command))
        application.add_handler(CommandHandler("divorce", breakup_command))
        application.add_handler(CommandHandler("commands", commands_command))
        application.add_handler(CommandHandler("chatstats", chat_stats_command))
        application.add_handler(CommandHandler("profile", profile_command))

        # Обробник реакцій користувачів
        application.add_handler(MessageReactionHandler(handle_reaction_update))

        # Обробники інлайн кнопок
        application.add_handler(CallbackQueryHandler(handle_relationship_callback, pattern=r"^(rel_|breakup_)"))
        application.add_handler(CallbackQueryHandler(button_callback))

        # Обробники повідомлень (включаючи підтримку префікса ! та /)
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_handler(MessageHandler(filters.COMMAND, handle_message))

        print("🚀 Бот успішно запущений з підтвердженням стосунків та структурованою довідкою...")

        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
            timeout=30
        )

    except Exception as e:
        logger.error(f"Помилка запуску бота: {e}")
        print(f"❌ Критична помилка: {e}")
        print("Перевірте BOT_TOKEN у файлі .env та інтернет-з'єднання")

if __name__ == '__main__':
    main()
