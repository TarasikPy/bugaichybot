import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils.helpers import create_user_link
from utils.bugaichyk_ai import get_random_quote, check_and_get_quote

HELP_TEXT = (
    "📋 <b>ОФІЦІЙНА ДОВІДКА КОМАНД БУГАЙЧИКА</b> 🌾\n\n"
    "📊 <b>Аналітика та Профілі:</b>\n"
    "• /chatstats (або <code>!стата</code>) — Топ активності чату за сьогодні\n"
    "• /profile (або <code>!профіль [@user]</code>) — Особиста картка користувача\n"
    "• /id (або <code>!інфо [@user]</code>) — Telegram ID, роль та пара у чаті\n\n"
    "🔥 <b>Розваги та Суд Бугайчика:</b>\n"
    "• /roast (або <code>!прожарка [@user]</code>) — Саркастичний підкол по лору\n"
    "• /judge (або <code>!суд</code>) — Суд Бугайчика для вирішення срачів\n"
    "• /quote (або <code>!цитата</code>) — Золотий фонд мудрості чату\n"
    "• /risk (або <code>!ризик</code>) — РП-Рулетка подій та випробувань\n\n"
    "❤️ <b>Стосунки та Парні дії:</b>\n"
    "• /dating (або <code>!пропозиція</code>) — Запропонувати зустрічатися\n"
    "• /relationships (або <code>!стосунки</code>) — Список усіх пар чату\n"
    "• /myrelationships — Інформація про власні стосунки\n"
    "• /breakup (або <code>!розрив</code>) — Розірвати стосунки\n"
    "• <code>/kiss</code>, <code>/hug</code>, <code>/love</code>, <code>/date</code>, <code>/gift</code> — Прокачка очок у парі\n\n"
    "🎭 <b>РП-Дії (з підтримкою reply / mentions):</b>\n"
    "• <code>!вдарив</code>, <code>!збив</code>, <code>!обняв</code>, <code>!поцілував</code> — ЖИВІ РП-реакції\n\n"
    "🌦️ <b>Погода та Розваги:</b>\n"
    "• /weather (або <code>!погода [місто]</code>) — Прогноз погоди від Бугайчика\n"
    "• /flipcoin — Кинути монетку (Орел чи Решка)"
)

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Генерує красиву інтерактивну клавіатуру для головного меню"""
    keyboard = [
        [
            InlineKeyboardButton("📜 Список команд", callback_data='menu_commands'),
            InlineKeyboardButton("❤️ Стосунки", callback_data='menu_relationships')
        ],
        [
            InlineKeyboardButton("📜 Мудрість дня", callback_data='menu_quote'),
            InlineKeyboardButton("📊 Статистика", callback_data='menu_stats')
        ],
        [
            InlineKeyboardButton("ℹ️ Про Бугайчика", callback_data='menu_about')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_keyboard() -> InlineKeyboardMarkup:
    """Повертає кнопку 'Назад у Головне Меню'"""
    keyboard = [[InlineKeyboardButton("« ⬅️ Назад у Меню", callback_data='menu_main')]]
    return InlineKeyboardMarkup(keyboard)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробляє команду /start з інтерактивним меню"""
    user = update.message.from_user if update.message else None
    user_link = create_user_link(user.id, user.first_name) if user else "газдо"

    welcome_text = (
        f"🌲 <b>Дай Боже, {user_link}!</b>\n\n"
        "Я — Бугайчик, справжній карпатський газда, господар цього чату та твій давній колєга з гір! ☕\n\n"
        "Обирай потрібний розділ у меню нижче! 👇"
    )

    await update.message.reply_text(welcome_text, reply_markup=get_main_menu_keyboard(), parse_mode='HTML')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробляє команду /help"""
    await update.message.reply_text(HELP_TEXT, reply_markup=get_back_keyboard(), parse_mode='HTML')

async def commands_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показує красивий структурований список всіх команд"""
    await update.message.reply_text(HELP_TEXT, reply_markup=get_back_keyboard(), parse_mode='HTML')

async def flipcoin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда для кидання монети"""
    result = random.choice(["🪙 Орел", "🪙 Решка"])
    await update.message.reply_text(f"🎲 Результат: <b>{result}</b>", parse_mode='HTML')

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробляє натискання інлайн кнопок інтерактивного меню"""
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == 'menu_main':
        user = query.from_user
        user_link = create_user_link(user.id, user.first_name) if user else "газдо"
        text = (
            f"🌲 <b>Головне Меню Бугайчика:</b>\n\n"
            f"Дай Боже, {user_link}! Обирай потрібну опцію з меню нижче! 👇"
        )
        await query.edit_message_text(text=text, reply_markup=get_main_menu_keyboard(), parse_mode='HTML')

    elif data == 'menu_commands':
        await query.edit_message_text(text=HELP_TEXT, reply_markup=get_back_keyboard(), parse_mode='HTML')

    elif data == 'menu_relationships':
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
            "💡 <b>Як підняти рівень?</b> Використовуй команди: <code>/kiss</code> (+3), <code>/hug</code> (+2), <code>/love</code> (+4), <code>/date</code> (+5), <code>/gift</code> (+3)."
        )
        await query.edit_message_text(text=text, reply_markup=get_back_keyboard(), parse_mode='HTML')

    elif data == 'menu_stats':
        text = (
            "📊 <b>СТАТИСТИКА ЧАТУ:</b>\n\n"
            "Щоб переглянути живий рейтинг дописувачів за сьогодні, надішли у чат команду:\n"
            "👉 <code>/chatstats</code> або <code>!стата</code>"
        )
        await query.edit_message_text(text=text, reply_markup=get_back_keyboard(), parse_mode='HTML')

    elif data == 'menu_quote':
        user = query.from_user
        _, quote_text = await check_and_get_quote(user.id if user else 0)
        await query.edit_message_text(text=quote_text, reply_markup=get_back_keyboard(), parse_mode='HTML')

    elif data == 'menu_about':
        text = (
            "🌲 <b>ПРО БУГАЙЧИКА (Карпатський Газда):</b>\n\n"
            "Дай Боже! Я — Бугайчик, колоритний Бойко з Карпат, ваш давній колєга та господар цього чату. "
            "Я завжди радий розрулити будь-яку суперечку, видати сувору карпатську мудрість, "
            "підтримати бесіду та простежити за залізобетонним порядком у чаті!\n\n"
            "⚡ <i>На варті нашої спільної бази 24/7!</i>"
        )
        await query.edit_message_text(text=text, reply_markup=get_back_keyboard(), parse_mode='HTML')
