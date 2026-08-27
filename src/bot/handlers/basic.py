"""Basic navigation and information handlers."""

import random

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from src.infrastructure.constants.risk_events import RISK_EVENTS
from src.infrastructure.utils.formatting import create_user_link

HELP_TEXT = (
    "📋 <b>ДОВІДКА КОМАНД БУГАЙЧИКА (Vanilla)</b> 🌾\n\n"
    "👤 <b>Профілі та Статистика:</b>\n"
    "• /profile (або <code>!профіль [@user]</code>) — Особиста картка користувача та психоаналіз\n"
    "• /id (або <code>!інфо [@user]</code>) — Telegram ID, роль та пара у чаті\n"
    "• /chatstats (або <code>!стата</code>) — Топ активності чату за сьогодні\n\n"
    "❤️ <b>Стосунки та Парні дії:</b>\n"
    "• /dating (або <code>!пропозиція [@user]</code>) — Запропонувати зустрічатися\n"
    "• /relationships (або <code>!стосунки</code>) — Список усіх пар чату\n"
    "• /myrelationships — Інформація про власні стосунки\n"
    "• /breakup (або <code>!розрив</code>) — Розірвати стосунки\n"
    "• <code>/kiss</code>, <code>/hug</code>, <code>/love</code>, <code>/date</code>, <code>/gift</code> — Прокачка очок у парі\n\n"
    "🎭 <b>РП-Дії (reply або @username):</b>\n"
    "• <code>!обняв</code>, <code>!поцілував</code>, <code>!вдарив</code>, <code>!кусь</code> — Вільні РП-реакції\n\n"
    "🎲 <b>Розваги та Погода:</b>\n"
    "• /risk (або <code>!ризик</code>) — РП-Рулетка подій чату\n"
    "• /flipcoin — Кинути монетку (Орел чи Решка)\n"
    "• /weather (або <code>!погода [місто]</code>) — Прогноз погоди\n\n"
    "🎬 <b>Відеосейвер:</b>\n"
    "• Надішліть посилання на <b>TikTok, Reels, Shorts або X/Twitter</b> — і бот миттєво завантажить чисте відео у чат!"
)


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Generate main interactive menu keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("📜 Список команд", callback_data="menu_commands"),
            InlineKeyboardButton("❤️ Стосунки", callback_data="menu_relationships"),
        ],
        [
            InlineKeyboardButton("🎰 РП-Рулетка", callback_data="menu_risk"),
            InlineKeyboardButton("📊 Статистика", callback_data="menu_stats"),
        ],
        [
            InlineKeyboardButton("ℹ️ Про Бугайчика", callback_data="menu_about"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_back_keyboard() -> InlineKeyboardMarkup:
    """Return 'Back to Main Menu' keyboard."""
    keyboard = [[InlineKeyboardButton("« ⬅️ Назад у Меню", callback_data="menu_main")]]
    return InlineKeyboardMarkup(keyboard)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    if not update.message:
        return
    user = update.message.from_user
    user_link = create_user_link(user.id, user.first_name) if user else "газдо"

    welcome_text = (
        f"🌲 <b>Дай Боже, {user_link}!</b>\n\n"
        "Я — Бугайчик, господар цього чату та твій вірний колєга з гір! ☕\n\n"
        "Обирай потрібний розділ у меню нижче! 👇"
    )

    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML",
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    if not update.message:
        return
    await update.message.reply_text(
        HELP_TEXT,
        reply_markup=get_back_keyboard(),
        parse_mode="HTML",
    )


async def commands_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /commands command."""
    if not update.message:
        return
    await update.message.reply_text(
        HELP_TEXT,
        reply_markup=get_back_keyboard(),
        parse_mode="HTML",
    )


async def flipcoin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /flipcoin command."""
    if not update.message:
        return
    result = random.choice(["🪙 Орел", "🪙 Решка"])
    await update.message.reply_text(f"🎲 Результат: <b>{result}</b>", parse_mode="HTML")


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button queries for main menu."""
    query = update.callback_query
    if not query:
        return
    await query.answer()

    data = query.data

    if data == "menu_main":
        user = query.from_user
        user_link = create_user_link(user.id, user.first_name) if user else "газдо"
        text = (
            f"🌲 <b>Головне Меню Бугайчика:</b>\n\n"
            f"Дай Боже, {user_link}! Обирай потрібну опцію з меню нижче! 👇"
        )
        await query.edit_message_text(
            text=text,
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML",
        )

    elif data == "menu_commands":
        await query.edit_message_text(
            text=HELP_TEXT,
            reply_markup=get_back_keyboard(),
            parse_mode="HTML",
        )

    elif data == "menu_relationships":
        text = (
            "❤️ <b>СИСТЕМА СТОСУНКІВ ТА РІВНІ КОХАННЯ:</b>\n\n"
            "1. 👋 Знайомство (0 очок)\n"
            "2. 😊 Симпатія (10 очок)\n"
            "3. 💕 Романтичні почуття (25 очок)\n"
            "4. 😍 Закоханість (45 очок)\n"
            "5. ❤️ Кохання (75 очок)\n"
            "6. 💖 Глибоке кохання (110 очок)\n"
            "7. 💝 Душевна єдність (150 очок)\n"
            "8. 💞 Вічне кохання (200 очок)\n"
            "9. 💫 Божественне кохання (250 очок)\n"
            "10. ✨ Абсолютна єдність (300 очок)\n\n"
            "💡 <b>Як підняти рівень?</b> Використовуй команди: "
            "<code>/kiss</code> (+3), <code>/hug</code> (+2), <code>/love</code> (+4), "
            "<code>/date</code> (+5), <code>/gift</code> (+3)."
        )
        await query.edit_message_text(
            text=text,
            reply_markup=get_back_keyboard(),
            parse_mode="HTML",
        )

    elif data == "menu_stats":
        text = (
            "📊 <b>СТАТИСТИКА ЧАТУ:</b>\n\n"
            "Щоб переглянути живий рейтинг дописувачів за сьогодні, надішли у чат команду:\n"
            "👉 <code>/chatstats</code> або <code>!стата</code>"
        )
        await query.edit_message_text(
            text=text,
            reply_markup=get_back_keyboard(),
            parse_mode="HTML",
        )

    elif data == "menu_risk":
        user = query.from_user
        user_name = user.first_name if user else "Користувач"
        user_link = create_user_link(user.id if user else 0, user_name)
        event = random.choice(RISK_EVENTS)
        risk_text = f"🎰 <b>РП-Рулетка для {user_link}:</b>\n\n{event}"
        await query.edit_message_text(
            text=risk_text,
            reply_markup=get_back_keyboard(),
            parse_mode="HTML",
        )

    elif data == "menu_about":
        text = (
            "🌲 <b>ПРО БУГАЙЧИКА:</b>\n\n"
            "Дай Боже! Я — Бугайчик, колоритний карпатський газда. "
            "Я допомагаю взаємодіяти через РП-дії, веду статистику чату, "
            "допомагаю будувати стосунки, показую точну погоду та швидко сейвлю відео з TikTok, "
            "Instagram Reels, Shorts та Twitter!\n\n"
            "⚡ <i>Завжди на зв'язку!</i>"
        )
        await query.edit_message_text(
            text=text,
            reply_markup=get_back_keyboard(),
            parse_mode="HTML",
        )
