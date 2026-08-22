import os
import time
import asyncio
import datetime
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
from handlers.mechanics import risk_command
from handlers.actions import handle_message

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class HealthCheckHandler(BaseHTTPRequestHandler):
    """Міні-вебсервер для успішного проходження Render Health Check та UptimeRobot (підтримка GET та HEAD)"""
    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", "2")
        self.end_headers()

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", "2")
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
    """Налаштовує меню команд бота та примусово скидає застарілі webhook сесії"""
    try:
        await application.bot.delete_webhook(drop_pending_updates=True)
    except Exception as e:
        logger.warning(f"delete_webhook попередження: {e}")

    private_commands = [
        BotCommand("start", "💫 Головне меню бота"),
        BotCommand("help", "📋 Довідка та команди"),
        BotCommand("profile", "👤 Профіль та психоаналіз"),
        BotCommand("weather", "🌤 Погода")
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
        BotCommand("commands", "📋 Всі команди")
    ]

    await application.bot.set_my_commands(private_commands, scope=BotCommandScopeAllPrivateChats())
    await application.bot.set_my_commands(group_commands, scope=BotCommandScopeAllGroupChats())

def main() -> None:
    """Головна точка входу: ініціалізація та запуск бота для Render.com"""
    # 1. Запуск фонового вебсервера для Render (No open ports detected)
    health_thread = threading.Thread(target=start_health_check_server, daemon=True)
    health_thread.start()

    # 2. Нескінченний цикл запуску з авто-відновленням при 409 Conflict
    while True:
        try:
            # Створюємо новий чистий event loop для кожного запуску (запобігає 'Event loop is closed')
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

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
            application.add_handler(CommandHandler("commands", commands_command))
            application.add_handler(CommandHandler("flipcoin", flipcoin_command))
            application.add_handler(CommandHandler("relationships", relationships_command))
            application.add_handler(CommandHandler("myrelationships", my_relationships_command))
            application.add_handler(CommandHandler("proposals", proposals_command))
            application.add_handler(CommandHandler("dating", dating_command))
            application.add_handler(CommandHandler("trio", trio_command))
            application.add_handler(CommandHandler("breakup", breakup_command))
            application.add_handler(CommandHandler("divorce", breakup_command))
            application.add_handler(CommandHandler("chatstats", chat_stats_command))
            application.add_handler(CommandHandler("profile", profile_command))
            application.add_handler(CommandHandler(["id", "whois"], id_command))
            application.add_handler(CommandHandler("weather", weather_command))
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

            logger.info("🚀 Vanilla Бот успішно запущений...")

            application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,
                bootstrap_retries=-1,
                timeout=30
            )
            break

        except Conflict as e:
            logger.warning(f"⚠️ Telegram 409 Conflict (старий контейнер на Render ще зупиняється): {e}. Пауза 10 секунд...")
            time.sleep(10)
        except NetworkError as e:
            logger.warning(f"⚠️ Мережева затримка: {e}. Пауза 5 секунд...")
            time.sleep(5)
        except Exception as e:
            logger.error(f"❌ Помилка роботи бота: {e}. Пауза 10 секунд...")
            time.sleep(10)

if __name__ == '__main__':
    main()
