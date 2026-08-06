import os
import time
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, BotCommandScopeAllGroupChats, BotCommandScopeAllPrivateChats, BotCommand
from telegram.error import Conflict, NetworkError
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
from handlers.analytics import chat_stats_command, profile_command, id_command, handle_reaction_update, handle_profile_callback
from handlers.weather import weather_command
from handlers.mechanics import roast_command, judge_command, quote_command, risk_command
from handlers.actions import handle_message

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class HealthCheckHandler(BaseHTTPRequestHandler):
    """Міні-вебсервер для успішного проходження Render Health Check (No open ports detected)"""
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        return  # Тиша у логах вебсервера

def start_health_check_server():
    """Запускає вебсервер для Render у фоновому потоці"""
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    logger.info(f"🌐 Health-Check HTTP Сервер запущено на порту {port}")
    server.serve_forever()

async def setup_bot_commands(application: Application) -> None:
    """Налаштовує меню команд бота"""
    private_commands = [
        BotCommand("start", "Головне меню бота"),
        BotCommand("help", "Довідка"),
        BotCommand("profile", "👤 Психологічний профіль та статистика"),
        BotCommand("weather", "🌤 Погода в місті")
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
        BotCommand("profile", "👤 Психологічний профіль та статистика"),
        BotCommand("weather", "🌤 Погода в місті чи селі"),
        BotCommand("roast", "🔥 Прожарка користувача"),
        BotCommand("judge", "⚖️ Суд Бугайчика / Розбірки чату"),
        BotCommand("quote", "📜 Золотий фонд чату (цитата дня)"),
        BotCommand("risk", "🎰 РП-Рулетка подій з лору")
    ]

    await application.bot.set_my_commands(private_commands, scope=BotCommandScopeAllPrivateChats())
    await application.bot.set_my_commands(group_commands, scope=BotCommandScopeAllGroupChats())

def main() -> None:
    """Головна точка входу: ініціалізація та запуск бота для Render.com"""
    # 1. Запуск фонового вебсервера для Render (No open ports detected)
    health_thread = threading.Thread(target=start_health_check_server, daemon=True)
    health_thread.start()

    # 2. Спроби запуску polling із захистом від 409 Conflict та перезапусків
    for attempt in range(1, 10):
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
            application.add_handler(CommandHandler(["id", "whois"], id_command))
            application.add_handler(CommandHandler("weather", weather_command))
            application.add_handler(CommandHandler("roast", roast_command))
            application.add_handler(CommandHandler("judge", judge_command))
            application.add_handler(CommandHandler("quote", quote_command))
            application.add_handler(CommandHandler("risk", risk_command))

            # Обробник реакцій користувачів
            application.add_handler(MessageReactionHandler(handle_reaction_update))

            # Обробники інлайн кнопок
            application.add_handler(CallbackQueryHandler(handle_profile_callback, pattern=r"^prof_"))
            application.add_handler(CallbackQueryHandler(handle_relationship_callback, pattern=r"^(rel_|breakup_)"))
            application.add_handler(CallbackQueryHandler(button_callback))

            # Обробники повідомлень
            application.add_handler(MessageHandler(~filters.COMMAND, handle_message))
            application.add_handler(MessageHandler(filters.COMMAND, handle_message))

            logger.info("🚀 Бот успішно запущений з підтвердженням стосунків та захистом від Render 409 Conflict...")

            application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,
                timeout=30
            )
            break

        except (Conflict, NetworkError) as e:
            logger.warning(f"⚠️ Конфлікт або мережева затримка (Спроба {attempt}/10): {e}. Пауза 5 секунд...")
            time.sleep(5)
        except Exception as e:
            logger.error(f"❌ Критична помилка запуску бота: {e}")
            break

if __name__ == '__main__':
    main()
