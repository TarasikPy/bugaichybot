import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils.helpers import create_user_link

HELP_TEXT = (
    "📋 <b>Список усіх команд бота:</b>\n\n"
    "📊 <b>Статистика та Профіль:</b>\n"
    "• /chatstats (або <code>!стата</code>) — Аналітика активності чату (топ за сьогодні)\n"
    "• /profile (або <code>!профіль</code>) — Особистий профіль користувача\n\n"
    "🎭 <b>РП-Дії:</b>\n"
    "• <code>!вдарив [хтось]</code> або <code>!вєбав</code> (у відповідь) — Вдарити користувача\n"
    "• <code>!збив</code> / <code>!обняв</code> — Інші РП-дії (з підтримкою reply та @mentions)\n\n"
    "❤️ <b>Стосунки:</b>\n"
    "• /dating (або <code>!пропозиція</code>) — Запропонувати зустрічатися (потребує згоди)\n"
    "• /relationships (або <code>!стосунки</code>) — Список усіх активних пар чату\n"
    "• /myrelationships (або <code>!моїстосунки</code>) — Інформація про власну пару\n"
    "• /breakup (або <code>!розрив</code>) — Розірвати стосунки / розлучитися\n\n"
    "💕 <b>Взаємодія у парах (+очки):</b>\n"
    "• /kiss — Поцілувати (+3 очки)\n"
    "• /hug — Обійняти (+2 очки)\n"
    "• /love — Заявити про кохання (+4 очки)\n"
    "• /date — Піти на побачення (+5 очок)\n"
    "• /gift — Подарувати подарунок (+3 очки)\n\n"
    "🪙 <b>Розваги:</b>\n"
    "• /flipcoin — Кинути монетку (Орел/Решка)"
)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробляє команду /start"""
    user = update.message.from_user if update.message else None
    user_link = create_user_link(user.id, user.first_name) if user else "користувачу"

    keyboard = [
        [InlineKeyboardButton("📖 Довідка команд", callback_data='instructions')],
        [InlineKeyboardButton("❤️ Стосунки", callback_data='about_relationships')],
        [InlineKeyboardButton("📊 Статистика", callback_data='chat_stats_cb')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_text = (
        f"🎭 <b>Привіт, {user_link}! Я бот для інтерактивних РП-дій та системи стосунків!</b>\n\n"
        f"{HELP_TEXT}\n\n"
        "Обери потрібну опцію з меню нижче! 👇"
    )

    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='HTML')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробляє команду /help"""
    await update.message.reply_text(HELP_TEXT, parse_mode='HTML')

async def commands_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показує красивий структурований список всіх команд"""
    await update.message.reply_text(HELP_TEXT, parse_mode='HTML')

async def flipcoin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда для кидання монети"""
    result = random.choice(["🪙 Орел", "🪙 Решка"])
    await update.message.reply_text(f"🎲 Результат: <b>{result}</b>", parse_mode='HTML')

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробляє натискання інлайн кнопок у головному меню"""
    query = update.callback_query
    await query.answer()

    if query.data == 'instructions':
        text = HELP_TEXT
    elif query.data == 'about_relationships':
        text = (
            "❤️ <b>Система стосунків:</b>\n\n"
            "1. 👋 Знайомство (0 очок)\n"
            "2. 😊 Симпатія (10 очок)\n"
            "3. 💕 Романтичні почуття (25 очок)\n"
            "4. 😍 Закоханість (45 очок)\n"
            "5. ❤️ Кохання (75 очок)\n"
            "6. 💖 Глибоке кохання (110 очок)\n"
            "7. 💝 Душевна єдність (150 очок)\n"
            "8. 💞 Вічне кохання (200 очок)\n"
            "9. 💫 Божественне кохання (250 очок)\n"
            "10. ✨ Абсолютна єдність (300 очок)"
        )
    elif query.data == 'chat_stats_cb':
        text = "📊 Для перегляду статистики використовуйте команду /chatstats або <code>!стата</code> у чаті."
    else:
        text = "Опція вибрана."

    await query.edit_message_text(text=text, parse_mode='HTML')
