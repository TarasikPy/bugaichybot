import logging
import re
import os
import json
import random
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, ChatMemberHandler

# Імпортуємо систему мудрості
from wisdom_system import (
    process_user_message,
    get_user_wisdom_stats,
    get_wisdom_leaderboard,
    format_level_announcement,
    WISDOM_LEVELS
)

# Словник для відмінювання українських імен (розширена бібліотека)
MALE_NAMES_DECLENSION = {
    'Андрій': 'Андрія', 'Олександр': 'Олександра', 'Володимир': 'Володимира',
    'Дмитро': 'Дмитра', 'Сергій': 'Сергія', 'Максим': 'Максима',
    'Артем': 'Артема', 'Роман': 'Романа', 'Іван': 'Івана',
    'Петро': 'Петра', 'Микола': 'Миколу', 'Павло': 'Павла',
    'Bogdan': 'Богдана', 'Тарас': 'Тараса', 'Юрій': 'Юрія',
    'Віктор': 'Віктора', 'Ігор': 'Ігоря', 'Олег': 'Олега',
    'Віталій': 'Віталія', 'Денис': 'Дениса', 'Антон': 'Антона',
    'Олексій': 'Олексія', 'Василь': 'Василя', 'Григорій': 'Григорія',
    'Михайло': 'Михайла', 'Ярослав': 'Ярослава', 'Владислав': 'Владислава',
    'Станіслав': 'Станіслава', 'Богуслав': 'Богуслава', 'Мирослав': 'Мирослава',
    'Святослав': 'Святослава', 'Ростислав': 'Ростислава', 'Вячеслав': 'Вячеслава',
    'Костянтин': 'Костянтина', 'Валентин': 'Валентина', 'Валерій': 'Валерія',
    'Геннадій': 'Геннадія', 'Леонід': 'Леоніда', 'Едуард': 'Едуарда',
    'Євген': 'Євгена', 'Арсен': 'Арсена', 'Руслан': 'Руслана',
    'Назар': 'Назара', 'Остап': 'Остапа', 'Орест': 'Ореста',
    'Богдан': 'Богдана', 'Степан': 'Степана', 'Ілля': 'Іллю',
    'Матвій': 'Матвія', 'Данило': 'Данила', 'Марко': 'Марка',
    'Тимофій': 'Тимофія', 'Захар': 'Захара', 'Елеазар': 'Елеазара',
    'Федір': 'Федора', 'Гліб': 'Гліба', 'Аркадій': 'Аркадія',
    'Анатолій': 'Анатолія', 'Борис': 'Бориса', 'Вадим': 'Вадима',
    'Георгій': 'Георгія', 'Дамян': 'Дамяна', 'Емиль': 'Емиля',
    'Жора': 'Жору', 'Заур': 'Заура', 'Кирило': 'Кирила',
    'Левко': 'Левка', 'Мирон': 'Мирона', 'Нестор': 'Нестора',
    'Онуфрій': 'Онуфрія', 'Прохор': 'Прохора', 'Ричард': 'Ричарда',
    'Савелій': 'Савелія', 'Тимур': 'Тимура', 'Ульрих': 'Ульриха',
    'Феодосій': 'Феодосія', 'Христофор': 'Христофора', 'Цезар': 'Цезара',
    'Шмуель': 'Шмуеля', 'Ярема': 'Ярему', 'Яків': 'Якова'
}

FEMALE_NAMES_DECLENSION = {
    'Анна': 'Анну', 'Марія': 'Марію', 'Катерина': 'Катерину',
    'Олена': 'Олену', 'Наталія': 'Наталію', 'Світлана': 'Світлану',
    'Тетяна': 'Тетяну', 'Ірина': 'Ірину', 'Людмила': 'Людмилу',
    'Галина': 'Галину', 'Валентина': 'Валентину', 'Лариса': 'Ларису',
    'Оксана': 'Оксану', 'Юлія': 'Юлію', 'Вікторія': 'Вікторію',
    'Дарина': 'Дарину', 'Софія': 'Софію', 'Емілія': 'Емілію',
    'Поліна': 'Поліну', 'Діана': 'Діану', 'Альона': 'Альону',
    'Богдана': 'Богдану', 'Владислава': 'Владиславу', 'Василина': 'Василину',
    'Гелена': 'Гелену', 'Дарія': 'Дарію', 'Єлизавета': 'Єлизавету',
    'Жанна': 'Жанну', 'Зоя': 'Зою', 'Ія': 'Ію',
    'Кристина': 'Кристину', 'Лілія': 'Лілію', 'Маргарита': 'Маргариту',
    'Ніна': 'Ніну', 'Ольга': 'Ольгу', 'Полина': 'Полину',
    'Роксолана': 'Роксолану', 'Стефанія': 'Стефанію', 'Тамара': 'Тамару',
    'Уляна': 'Уляну', 'Фаїна': 'Фаїну', 'Христина': 'Христину',
    'Ціна': 'Ціну', 'Шарлотта': 'Шарлотту', 'Ярослава': 'Ярославу',
    'Аліна': 'Аліну', 'Бажена': 'Бажену', 'Вера': 'Веру',
    'Гліб': 'Гліба', 'Данна': 'Данну', 'Ева': 'Еву',
    'Ілона': 'Ілону', 'Калина': 'Калину', 'Лада': 'Ладу',
    'Мирослава': 'Мирославу', 'Надія': 'Надію', 'Оріана': 'Оріану',
    'Роксана': 'Роксану', 'Соломія': 'Соломію', 'Таїсія': 'Таїсію',
    'Устина': 'Устину', 'Феодора': 'Феодору', 'Христя': 'Христю',
    'Ця': 'Цю', 'Шанна': 'Шанну', 'Ява': 'Яву',
    'Агата': 'Агату', 'Божена': 'Божену', 'Віра': 'Віру',
    'Горислава': 'Гориславу', 'Добромила': 'Добромилу', 'Есфір': 'Есфір',
    'Іванна': 'Іванну', 'Кіра': 'Кіру', 'Любов': 'Любов',
    'Мілена': 'Мілену', 'Неля': 'Нелю', 'Орися': 'Орисю',
    'Руслана': 'Руслану', 'Слава': 'Славу', 'Тіана': 'Тіану',
    'Ульяна': 'Ульяну', 'Фелісія': 'Фелісію', 'Хрістя': 'Христю',
    'Цвітана': 'Цвітана', 'Шура': 'Шуру', 'Яна': 'Яну'
}

# Дані для зберігання стосунків (зберігаються у файлі relationships.json)
RELATIONSHIPS_FILE = 'relationships.json'

# Детальна система рівнів стосунків
RELATIONSHIP_LEVELS = {
    0: {
        "name": "Знайомство",
        "emoji": "👋",
        "required_points": 0,
        "description": "Початковий етап знайомства, перші кроки до зближення"
    },
    1: {
        "name": "Симпатія",
        "emoji": "😊",
        "required_points": 10,
        "description": "З'являється взаємний інтерес та приємне спілкування"
    },
    2: {
        "name": "Романтичні почуття",
        "emoji": "💕",
        "required_points": 25,
        "description": "Перші романтичні моменти та особливі відчуття"
    },
    3: {
        "name": "Закоханість",
        "emoji": "😍",
        "required_points": 45,
        "description": "Глибока емоційна прив'язаність та частка думок один про одного"
    },
    4: {
        "name": "Кохання",
        "emoji": "❤️",
        "required_points": 75,
        "description": "Міцні почуття та готовність до серйозних стосунків"
    },
    5: {
        "name": "Глибоке кохання",
        "emoji": "💖",
        "required_points": 110,
        "description": "Безумовна любов та повне розуміння один одного, можна одружитись"
    },
    6: {
        "name": "Душевна єдність",
        "emoji": "💝",
        "required_points": 150,
        "description": "Ідеальна гармонія та духовний зв'язок"
    },
    7: {
        "name": "Вічне кохання",
        "emoji": "💞",
        "required_points": 200,
        "description": "Нерозривний зв'язок душ та серць на все життя"
    },
    8: {
        "name": "Божественне кохання",
        "emoji": "💫",
        "required_points": 250,
        "description": "Вищий рівень духовного з'єднання та любові"
    },
    9: {
        "name": "Абсолютна єдність",
        "emoji": "✨",
        "required_points": 300,
        "description": "Досконала гармонія двох душ як одне ціле"
    }
}

# Розширений список команд пар для стосунків з очками
COUPLE_COMMANDS = {
    'kiss': {'action': 'поцілував', 'points': 3, 'emoji': '💋'},
    'hug': {'action': 'обійняв', 'points': 2, 'emoji': '🤗'},
    'love': {'action': 'кохає', 'points': 4, 'emoji': '💕'},
    'date': {'action': 'ходить на побачення з', 'points': 5, 'emoji': '🌹'},
    'flirt': {'action': 'фліртує з', 'points': 2, 'emoji': '😏'},
    'gift': {'action': 'дарує подарунок', 'points': 3, 'emoji': '🎁'},
    'dance': {'action': 'танцює з', 'points': 3, 'emoji': '💃'},
    'hold': {'action': 'тримає за руку', 'points': 2, 'emoji': '👫'},
    'cuddle': {'action': 'обіймається з', 'points': 3, 'emoji': '🥰'},
    'whisper': {'action': 'шепоче солодкі слова', 'points': 3, 'emoji': '🗣️'},
    'smile': {'action': 'посміхається', 'points': 1, 'emoji': '😊'},
    'wink': {'action': 'підморгує', 'points': 1, 'emoji': '😉'},
    'compliment': {'action': 'робить комплімент', 'points': 2, 'emoji': '🥺'},
    'surprise': {'action': 'робить сюрприз', 'points': 4, 'emoji': '🎉'},
    'serenade': {'action': 'співає серенаду', 'points': 4, 'emoji': '🎵'},
    'cook': {'action': 'готує для', 'points': 3, 'emoji': '👨‍🍳'},
    'massage': {'action': 'робить масаж', 'points': 3, 'emoji': '💆'},
    'write': {'action': 'пише любовного листа', 'points': 4, 'emoji': '💌'},
    'picnic': {'action': 'влаштовує пікнік з', 'points': 5, 'emoji': '🧺'},
    'stargazing': {'action': 'дивиться на зірки з', 'points': 4, 'emoji': '🌟'},
    'travel': {'action': 'подорожує з', 'points': 6, 'emoji': '✈️'},
    'propose': {'action': 'робить пропозицію', 'points': 0, 'emoji': '💍'},
    'accept': {'action': 'приймає пропозицію від', 'points': 0, 'emoji': '✅'},
    'reject': {'action': 'відхиляє пропозицію від', 'points': 0, 'emoji': '❌'},
    'dating': {'action': 'розпочинає стосунки з', 'points': 2, 'emoji': '💫'},
    'breakup': {'action': 'розстається з', 'points': 0, 'emoji': '😢'},
    'divorce': {'action': 'розлучається з', 'points': 0, 'emoji': '💔'}
}

# Особливі команди для одружених пар
MARRIED_COMMANDS = {
    'honeymoon': {'action': 'їде в медовий місяць з', 'points': 10, 'emoji': '🏝️'},
    'anniversary': {'action': 'святкує річницю з', 'points': 8, 'emoji': '🎊'},
    'family_dinner': {'action': 'влаштовує сімейну вечерю з', 'points': 5, 'emoji': '🍽️'},
    'home_together': {'action': 'облаштовує дім разом з', 'points': 6, 'emoji': '🏠'},
    'support': {'action': 'підтримує в важкі часи', 'points': 7, 'emoji': '🤝'},
    'plan_future': {'action': 'планує майбутнє з', 'points': 6, 'emoji': '📋'},
    'adopt_pet': {'action': 'заводить домашню тварину з', 'points': 5, 'emoji': '🐕'},
    'renew_vows': {'action': 'поновлює шлюбні обітниці з', 'points': 15, 'emoji': '💒'}
}

# Команди для стосунків на трьох
TRIO_COMMANDS = {
    'group_hug': {'action': 'обіймається разом з', 'points': 4, 'emoji': '🤗'},
    'trio_date': {'action': 'йде на побачення втрьох з', 'points': 6, 'emoji': '🌹'},
    'group_dance': {'action': 'танцює втрьох з', 'points': 5, 'emoji': '💃'},
    'trio_travel': {'action': 'подорожує втрьох з', 'points': 8, 'emoji': '✈️'},
    'support_each': {'action': 'підтримують один одного з', 'points': 5, 'emoji': '🤝'},
    'celebrate_together': {'action': 'святкує разом з', 'points': 6, 'emoji': '🎉'}
}

# Всі команди разом
ALL_COUPLE_COMMANDS = {**COUPLE_COMMANDS, **MARRIED_COMMANDS, **TRIO_COMMANDS}

# Валідні команди
VALID_COMMANDS = [
    'start', 'help', 'relationships', 'myrelationships', 'flipcoin', 'proposals', 'commands', 'trio',
    'wisdom', 'mywisdom', 'wisdomtop',
    *ALL_COUPLE_COMMANDS.keys()
]

def load_relationships():
    """Завантажує стосунки з файлу"""
    try:
        with open(RELATIONSHIPS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_relationships(relationships):
    """Зберігає стосунки у файл"""
    with open(RELATIONSHIPS_FILE, 'w', encoding='utf-8') as f:
        json.dump(relationships, f, ensure_ascii=False, indent=2)

def decline_name(name):
    """Відмінює ім'я з називного у знахідний відмінок, підтримка будь-яких імен"""
    # Спочатку перевіряємо словники українських імен
    if name in MALE_NAMES_DECLENSION:
        return MALE_NAMES_DECLENSION[name]
    elif name in FEMALE_NAMES_DECLENSION:
        return FEMALE_NAMES_DECLENSION[name]

    # Для англійських імен або інших - не відмінюємо
    if name.isascii():
        return name

    # Автоматичне відмінювання для українських імен
    if name.endswith(('ій', 'ей')):
        return name[:-2] + 'я'
    elif name.endswith('о'):
        return name[:-1] + 'а'
    elif name.endswith(('н', 'м', 'р', 't', 'к', 'л', 'с')):
        return name + 'а'
    elif name.endswith('а'):
        return name[:-1] + 'у'
    elif name.endswith('я'):
        return name[:-1] + 'ю'

    return name

def get_relationship_level(total_points):
    """Визначає рівень стосунків за кількістю очок"""
    for level in reversed(range(len(RELATIONSHIP_LEVELS))):
        if total_points >= RELATIONSHIP_LEVELS[level]["required_points"]:
            return level
    return 0

def format_duration(start_date):
    """Форматує тривалість стосунків з детальним відображенням"""
    start = datetime.fromisoformat(start_date)
    duration = datetime.now() - start
    total_seconds = int(duration.total_seconds())
    days = duration.days
    hours = (duration.seconds // 3600)
    minutes = (duration.seconds % 3600) // 60
    seconds = duration.seconds % 60

    if total_seconds < 60:
        return f"{total_seconds} секунд"
    elif total_seconds < 3600:  # менше години
        return f"{minutes} хвилин {seconds} секунд"
    elif days == 0:  # менше дня
        return f"{hours} годин {minutes} хвилин"
    elif days < 30:  # менше місяця
        return f"{days} днів {hours} годин {minutes} хвилин"
    elif days < 365:  # менше року
        months = days // 30
        remaining_days = days % 30
        if months == 1:
            return f"1 місяць {remaining_days} днів {hours} годин"
        else:
            return f"{months} місяців {remaining_days} днів {hours} годин"
    else:  # більше року
        years = days // 365
        remaining_days = days % 365
        months = remaining_days // 30
        final_days = remaining_days % 30

        if years == 1:
            if months > 0:
                return f"1 рік {months} місяців {final_days} днів"
            else:
                return f"1 рік {final_days} днів"
        else:
            if months > 0:
                return f"{years} років {months} місяців {final_days} днів"
            else:
                return f"{years} років {final_days} днів"

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = "7762622882:AAF9lR8AaeAmtl6nwDMGL538RO4DL3jeIhU"

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не знайдено в змінних середовища! Додайте його в Secrets.")

# Перевіряємо формат токена
if not BOT_TOKEN or ':' not in BOT_TOKEN or len(BOT_TOKEN.split(':')) != 2:
    raise ValueError("Неправильний формат BOT_TOKEN! Токен повинен мати формат: ЧИСЛА:ЛІТЕРИ")

def create_user_link(name, user_id=None, is_sender=False, is_action=False, is_relationship_display=False):
    """Створює посилання на користувача"""
    if is_sender:
        # Відправник без символів, звичайний текст
        return name
    elif is_action:
        # Для звичайних дій - тільки ✦ перед ніком
        if user_id:
            return f"[✦**{name}**](tg://user?id={user_id})"
        else:
            return f"✦**{name}**"
    elif is_relationship_display:
        # Для відображення стосунків - з романтичними символами
        if user_id:
            return f"[✦💖**{name}**💖](tg://user?id={user_id})"
        else:
            return f"✦💖**{name}**💖"
    else:
        # Звичайне ім'я партнера без додаткових символів
        if user_id:
            return f"[**{name}**](tg://user?id={user_id})"
        else:
            return f"**{name}**"

async def setup_bot_commands(application):
    """Налаштовує команди бота"""
    from telegram import BotCommandScope, BotCommandScopeAllGroupChats, BotCommandScopeAllPrivateChats

    private_commands = [
        BotCommand("start", "Головне меню бота"),
        BotCommand("help", "Довідка")
    ]

    group_commands = [
        BotCommand("start", "💫 Розпочати роботу з ботом"),
        BotCommand("flipcoin", "🪙 Кинути монету"),
        BotCommand("relationships", "💕 Показати всі стосунки"),
        BotCommand("myrelationships", "❤️ Показати ваші стосунки"),
        BotCommand("commands", "📋 Всі команди"),
        BotCommand("dating", "💫 Розпочати стосунки (відповідь на повідомлення)"),
        BotCommand("trio", "👥 Створити стосунки на 3 особи"),
        BotCommand("mywisdom", "🧠 Показати вашу мудрість"),
        BotCommand("wisdomtop", "🏆 Топ мудрих користувачів"),
        BotCommand("setmessages", "🔧 Встановити кількість повідомлень (відповідь+кількість)"),
        BotCommand("addmessages", "➕ Додати повідомлення (відповідь+кількість)"),
        BotCommand("syncuser", "🔄 Синхронізувати користувача (відповідь на повідомлення)")
    ]

    await application.bot.set_my_commands(private_commands, scope=BotCommandScopeAllPrivateChats())
    await application.bot.set_my_commands(group_commands, scope=BotCommandScopeAllGroupChats())

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробляє команду /start"""
    keyboard = [
        [InlineKeyboardButton("📖 Інструкція", callback_data='instructions')],
        [InlineKeyboardButton("📞 Зв'язок", callback_data='contact')],
        [InlineKeyboardButton("ℹ️ Про бота", callback_data='about')],
        [InlineKeyboardButton("💡 Приклади", callback_data='examples')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_text = (
        "🎭 Привіт! Я бот для створення веселих дій та управління стосунками!\n\n"
        "💕 **Детальна система рівнів стосунків:**\n"
        "👋 Знайомство → 😊 Симпатія → 💕 Романтичні почуття → 😍 Закоханість → ❤️ Кохання → 💖 Глибоке кохання (можна одружитись) → 💝 Душевна єдність → 💞 Вічне кохання → 💫 Божественне кохання → ✨ Абсолютна єдність\n\n"
        "**Можливості:**\n"
        "• Розширена система стосунків з очками\n"
        "• Підтримка стосунків на 3 особи\n"
        "• Особливі команди для одружених пар\n"
        "• Система мудрості за активність\n"
        "• Підтримка будь-яких імен після @\n\n"
        "**Основні команди:**\n"
        "`/дія @користувач додаткові дії. зі словами`\n"
        "`/dating` - розпочати стосунки (відповідь на повідомлення)\n"
        "`/kiss`, `/hug`, `/love` - дії з партнером\n"
        "`/propose` - зробити пропозицію (потрібен 5 рівень)\n"
        "`/mywisdom` - показати вашу мудрість\n\n"
        "Вибери опцію з меню нижче! 👇"
    )

    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

async def flipcoin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда для кидання монети"""
    result = random.choice(["🪙 Орел", "🪙 Решка"])
    await update.message.reply_text(f"🎲 Результат: {result}")

async def relationships_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показує всі стосунки в поточному чаті"""
    chat_id = update.effective_chat.id
    chat_data = load_chat_relationships(chat_id)
    relationships = chat_data['relationships']

    if not relationships:
        await update.message.reply_text("💔 Поки що немає активних стосунків у цьому чаті!")
        return

    text = "💕 **Активні стосунки в цьому чаті:**\n\n"
    for couple_id, data in relationships.items():
        parts = couple_id.split('_')
        if len(parts) >= 2:
            partners = parts
            duration = format_duration(data['start_date'])
            total_points = data.get('total_points', 0)
            level = get_relationship_level(total_points)
            level_info = RELATIONSHIP_LEVELS[level]
            status = data.get('status', 'dating')

            status_emoji = "💒" if status == 'married' else "💕"

            # Формуємо список партнерів з лінками
            partner_links = [create_user_link(partner, is_sender=False, is_relationship_display=True) for partner in partners]

            if len(partners) == 2:
                partner_display = f"{partner_links[0]} ❤️ {partner_links[1]}"
            else:  # 3 або більше партнерів
                partner_display = " ❤️ ".join(partner_links)

            text += f"{status_emoji} {partner_display}\n"
            text += f"📊 Рівень: {level_info['emoji']} {level_info['name']}\n"
            text += f"⚡ Очки: {total_points}\n"
            text += f"📝 {level_info['description']}\n"
            text += f"📅 Тривалість: {duration}\n\n"

    await update.message.reply_text(text, parse_mode='Markdown')

async def my_relationships_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показує стосунки користувача в поточному чаті"""
    user_name = update.message.from_user.first_name
    chat_id = update.effective_chat.id
    chat_data = load_chat_relationships(chat_id)
    relationships = chat_data['relationships']

    user_relationships = []
    for couple_id, data in relationships.items():
        parts = couple_id.split('_')
        if user_name in parts:
            other_partners = [p for p in parts if p != user_name]
            duration = format_duration(data['start_date'])
            total_points = data.get('total_points', 0)
            level = get_relationship_level(total_points)
            level_info = RELATIONSHIP_LEVELS[level]
            status = data.get('status', 'dating')

            status_text = "💒 Одружені" if status == 'married' else "💕 У стосунках"

            if len(other_partners) == 1:
                partner_text = f"❤️ Партнер: {create_user_link(other_partners[0], is_sender=False, is_relationship_display=True)}"
            else:
                partner_links = [create_user_link(partner, is_sender=False, is_relationship_display=True) for partner in other_partners]
                partner_text = f"❤️ Партнери: {' та '.join(partner_links)}"

            user_relationships.append(
                f"{status_text}\n"
                f"{partner_text}\n"
                f"📊 Рівень: {level_info['emoji']} {level_info['name']}\n"
                f"⚡ Очки: {total_points}\n"
                f"📝 {level_info['description']}\n"
                f"📅 Тривалість: {duration}"
            )

    if not user_relationships:
        text = "💔 У вас поки немає активних стосунків у цьому чаті!"
    else:
        user_link = create_user_link(user_name, is_sender=True)
        text = f"💕 **Ваші стосунки, {user_link}:**\n\n" + "\n\n".join(user_relationships)

    await update.message.reply_text(text, parse_mode='Markdown')

async def proposals_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показує активні пропозиції в поточному чаті"""
    user_name = update.message.from_user.first_name
    chat_id = update.effective_chat.id
    chat_data = load_chat_relationships(chat_id)
    relationships = chat_data['relationships']

    # Пропозиції ДО користувача
    proposals_to_user = []
    # Пропозиції ВІД користувача
    proposals_from_user = []

    for couple_id, data in relationships.items():
        if 'proposal' in data and data['proposal']['status'] == 'pending':
            proposal = data['proposal']
            if proposal['to'] == user_name:
                from_user_link = create_user_link(proposal['from'], is_sender=False, is_relationship_display=True)
                proposals_to_user.append(f"💍 Від {from_user_link}")
            elif proposal['from'] == user_name:
                to_user_link = create_user_link(proposal['to'], is_sender=False, is_relationship_display=True)
                proposals_from_user.append(f"💌 До {to_user_link}")

    text = f"💌 **Активні пропозиції для {create_user_link(user_name, is_sender=True)}:**\n\n"

    if proposals_to_user:
        text += "📨 **Пропозиції до вас:**\n" + "\n".join(proposals_to_user) + "\n\n"
        text += "Використайте /accept @username або /reject @username\n\n"

    if proposals_from_user:
        text += "📤 **Ваші пропозиції:**\n" + "\n".join(proposals_from_user) + "\n\n"

    if not proposals_to_user and not proposals_from_user:
        text += "💔 Немає активних пропозицій у цьому чаті!"

    await update.message.reply_text(text, parse_mode='Markdown')

async def my_wisdom_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показує статистику мудрості користувача"""
    user_id = update.message.from_user.id
    user_name = update.message.from_user.first_name
    chat_id = update.effective_chat.id

    stats = get_user_wisdom_stats(user_id, chat_id)

    if not stats:
        await update.message.reply_text("🌱 Ви ще не розпочали свій шлях мудрості! Почніть писати повідомлення, і ваша мудрість буде зростати!")
        return

    user_data = stats['user_data']
    level_info = stats['current_level_info']
    wisdom_points = stats['wisdom_points']
    progress = stats['progress']

    text = f"🧠 **Статистика мудрості для {user_name}:**\n\n"
    text += f"{level_info['emoji']} **Поточний рівень:** {level_info['name']}\n"
    text += f"📝 **Повідомлень:** {user_data['message_count']}\n"
    text += f"⚡ **Очки мудрості:** {wisdom_points}\n\n"
    text += f"💭 *{level_info['description']}*\n\n"

    if progress:
        progress_bar = "▓" * int(progress['progress_percentage'] / 10) + "░" * (10 - int(progress['progress_percentage'] / 10))
        text += f"📈 **Прогрес до наступного рівня:**\n"
        text += f"{progress['next_level_info']['emoji']} {progress['next_level_info']['name']}\n"
        text += f"[{progress_bar}] {progress['progress_percentage']:.1f}%\n"
        text += f"📊 Потрібно ще повідомлень: {progress['messages_needed']}"
    else:
        text += "🏆 **Ви досягли максимального рівня мудрості!**"

    await update.message.reply_text(text, parse_mode='Markdown')

async def wisdom_top_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показує топ користувачів за мудрістю"""
    chat_id = update.effective_chat.id
    leaderboard = get_wisdom_leaderboard(10, chat_id)

    if not leaderboard:
        await update.message.reply_text("🏆 Поки що немає мудрих користувачів! Станьте першим!")
        return

    text = "🏆 **Топ мудрих користувачів:**\n\n"

    for entry in leaderboard:
        rank_emoji = "🥇" if entry['rank'] == 1 else "🥈" if entry['rank'] == 2 else "🥉" if entry['rank'] == 3 else f"{entry['rank']}."

        # Екрануємо спеціальні символи в іменах
        safe_name = entry['name'].replace('*', '\\*').replace('_', '\\_').replace('[', '\\[').replace(']', '\\]').replace('`', '\\`')

        text += f"{rank_emoji} {safe_name}\n"
        text += f"{entry['level_info']['emoji']} {entry['level_info']['name']}\n"
        text += f"📝 {entry['message_count']} повідомлень | ⚡ {entry['wisdom_points']} очок\n\n"

    try:
        await update.message.reply_text(text, parse_mode='Markdown')
    except Exception as e:
        # Якщо не вдається відправити з Markdown, відправляємо без форматування
        text_plain = text.replace('**', '').replace('*', '').replace('_', '').replace('`', '')
        await update.message.reply_text(text_plain)

async def set_messages_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Встановлює кількість повідомлень для користувача (тільки для адміністраторів)"""
    user_id = update.message.from_user.id
    chat_id = update.effective_chat.id

    # Перевіряємо чи користувач є адміністратором
    try:
        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        if chat_member.status not in ['administrator', 'creator']:
            await update.message.reply_text("❌ Ця команда доступна тільки адміністраторам!")
            return
    except Exception as e:
        await update.message.reply_text("❌ Помилка перевірки прав доступу!")
        return

    # Перевіряємо чи є відповідь на повідомлення
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "📝 **Використання команди:**\n"
            "Відповідайте на повідомлення користувача командою `/setmessages кількість`\n\n"
            "**Приклад:**\n"
            "Відповідь на повідомлення: `/setmessages 25000`",
            parse_mode='Markdown'
        )
        return

    target_user = update.message.reply_to_message.from_user
    target_name = target_user.first_name or target_user.username
    target_user_id = target_user.id

    # Парсимо кількість повідомлень
    args = context.args
    if len(args) < 1:
        await update.message.reply_text("❌ Вкажіть кількість повідомлень: `/setmessages 25000`")
        return

    try:
        message_count = int(args[0])
        if message_count < 0:
            await update.message.reply_text("❌ Кількість повідомлень не може бути від'ємною!")
            return
    except (ValueError, IndexError):
        await update.message.reply_text(
            "❌ Неправильний формат кількості повідомлень!\n"
            "📝 Використовуйте тільки цифри: `/setmessages 25000`",
            parse_mode='Markdown'
        )
        return

    # Імпортуємо функції з wisdom_system
    from wisdom_system import (
        load_chat_wisdom_data,
        save_chat_wisdom_data,
        get_user_level,
        WISDOM_LEVELS
    )

    chat_data = load_chat_wisdom_data(chat_id)

    # Знаходимо або створюємо користувача
    user_key = str(target_user_id)

    if user_key not in chat_data['users']:
        chat_data['users'][user_key] = {
            'name': target_name,
            'message_count': 0,
            'current_level': 0,
            'last_update': datetime.now().isoformat(),
            'join_date': datetime.now().isoformat()
        }

    # Зберігаємо стару кількість для порівняння
    old_count = chat_data['users'][user_key]['message_count']
    old_level = chat_data['users'][user_key]['current_level']

    # Оновлюємо дані користувача
    chat_data['users'][user_key]['name'] = target_name
    chat_data['users'][user_key]['message_count'] = message_count
    chat_data['users'][user_key]['last_update'] = datetime.now().isoformat()

    # Визначаємо новий рівень
    new_level = get_user_level(message_count)
    chat_data['users'][user_key]['current_level'] = new_level

    # Зберігаємо дані
    save_chat_wisdom_data(chat_id, chat_data)

    # Формуємо відповідь
    level_info = WISDOM_LEVELS[new_level]
    wisdom_points = message_count // 10

    text = f"✅ **Кількість повідомлень оновлена!**\n\n"
    text += f"👤 **Користувач:** [{target_name}](tg://user?id={target_user_id})\n"
    text += f"📝 **Повідомлень:** {old_count} → {message_count}\n"
    text += f"📊 **Рівень:** {old_level} → {new_level}\n"
    text += f"{level_info['emoji']} **{level_info['name']}**\n"
    text += f"⚡ **Очки мудрості:** {wisdom_points}\n\n"
    text += f"💭 *{level_info['description']}*"

    await update.message.reply_text(text, parse_mode='Markdown')

    # Якщо рівень підвищився, показуємо святкове повідомлення
    if new_level > old_level and new_level >= 1:
        from wisdom_system import format_level_announcement
        announcement = format_level_announcement({
            'level': new_level,
            'level_info': level_info,
            'message_count': message_count,
            'wisdom_points': wisdom_points,
            'user_name': target_name,
            'chat_id': chat_id
        })
        await update.message.reply_text(announcement, parse_mode='Markdown')

async def add_messages_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Додає повідомлення до існуючої статистики користувача"""
    user_id = update.message.from_user.id
    chat_id = update.effective_chat.id

    # Перевіряємо чи користувач є адміністратором
    try:
        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        if chat_member.status not in ['administrator', 'creator']:
            await update.message.reply_text("❌ Ця команда доступна тільки адміністраторам!")
            return
    except Exception as e:
        await update.message.reply_text("❌ Помилка перевірки прав доступу!")
        return

    # Перевіряємо чи є відповідь на повідомлення
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "📝 **Використання команди:**\n"
            "Відповідайте на повідомлення користувача командою `/addmessages кількість`\n\n"
            "**Приклад:**\n"
            "Відповідь на повідомлення: `/addmessages 1000`",
            parse_mode='Markdown'
        )
        return

    target_user = update.message.reply_to_message.from_user
    target_name = target_user.first_name or target_user.username
    target_user_id = target_user.id

    # Парсимо кількість повідомлень
    args = context.args
    if len(args) < 1:
        await update.message.reply_text("❌ Вкажіть кількість повідомлень для додавання: `/addmessages 1000`")
        return

    try:
        message_count = int(args[0])
        if message_count <= 0:
            await update.message.reply_text("❌ Кількість повідомлень повинна бути більше 0!")
            return
    except (ValueError, IndexError):
        await update.message.reply_text(
            "❌ Неправильний формат кількості повідомлень!\n"
            "📝 Використовуйте тільки цифри: `/addmessages 1000`",
            parse_mode='Markdown'
        )
        return

    # Імпортуємо функції з wisdom_system
    from wisdom_system import (
        load_chat_wisdom_data,
        save_chat_wisdom_data,
        get_user_level,
        WISDOM_LEVELS
    )

    chat_data = load_chat_wisdom_data(chat_id)

    # Знаходимо або створюємо користувача
    user_key = str(target_user_id)

    if user_key not in chat_data['users']:
        chat_data['users'][user_key] = {
            'name': target_name,
            'message_count': 0,
            'current_level': 0,
            'last_update': datetime.now().isoformat(),
            'join_date': datetime.now().isoformat()
        }

    # Зберігаємо старі значення
    old_count = chat_data['users'][user_key]['message_count']
    old_level = chat_data['users'][user_key]['current_level']

    # Оновлюємо дані користувача
    chat_data['users'][user_key]['name'] = target_name
    chat_data['users'][user_key]['message_count'] += message_count
    chat_data['users'][user_key]['last_update'] = datetime.now().isoformat()

    # Оновлюємо рівень
    new_level = get_user_level(chat_data['users'][user_key]['message_count'])
    chat_data['users'][user_key]['current_level'] = new_level

    # Оновлюємо загальну статистику чату
    chat_data['chat_info']['total_messages_synced'] += message_count

    # Зберігаємо дані
    save_chat_wisdom_data(chat_id, chat_data)

    # Формуємо відповідь
    new_level_info = WISDOM_LEVELS[new_level]
    wisdom_points = chat_data['users'][user_key]['message_count'] // 10

    text = f"✅ **Повідомлення додано до статистики!**\n\n"
    text += f"👤 **Користувач:** [{target_name}](tg://user?id={target_user_id})\n"
    text += f"📝 **Повідомлень:** {old_count} → {chat_data['users'][user_key]['message_count']} (+{message_count})\n"
    text += f"📊 **Рівень:** {old_level} → {new_level}\n"
    text += f"{new_level_info['emoji']} **{new_level_info['name']}**\n"
    text += f"⚡ **Очки мудрості:** {wisdom_points}\n\n"
    text += f"💭 *{new_level_info['description']}*"

    await update.message.reply_text(text, parse_mode='Markdown')

    # Якщо рівень підвищився, показуємо святкове повідомлення
    if new_level > old_level and new_level >= 1:
        from wisdom_system import format_level_announcement
        announcement = format_level_announcement({
            'level': new_level,
            'level_info': new_level_info,
            'message_count': chat_data['users'][user_key]['message_count'],
            'wisdom_points': wisdom_points,
            'user_name': target_name,
            'chat_id': chat_id
        })
        await update.message.reply_text(announcement, parse_mode='Markdown')

async def test_wisdom_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Тестує систему мудрості і показує поточний стан"""
    user_id = update.message.from_user.id
    user_name = update.message.from_user.first_name
    chat_id = update.effective_chat.id

    # Імпортуємо функції з wisdom_system
    from wisdom_system import (
        load_chat_wisdom_data,
        process_user_message_in_chat,
        get_user_wisdom_stats_in_chat
    )

    print(f"🧪 ТЕСТ СИСТЕМИ МУДРОСТІ:")
    print(f"   User: {user_name} ({user_id})")
    print(f"   Chat: {chat_id}")

    # Завантажуємо поточні дані
    chat_data = load_chat_wisdom_data(chat_id)
    user_key = str(user_id)

    current_count = 0
    if user_key in chat_data['users']:
        current_count = chat_data['users'][user_key]['message_count']

    print(f"   Поточна кількість повідомлень: {current_count}")

    # Тестуємо обробку повідомлення
    level_up, level_data = process_user_message_in_chat(chat_id, user_id, user_name)

    # Отримуємо оновлену статистику
    stats = get_user_wisdom_stats_in_chat(chat_id, user_id)

    text = f"🧪 **Тест системи мудрості:**\n\n"
    text += f"👤 **Користувач:** {user_name}\n"
    text += f"💬 **Чат ID:** {chat_id}\n"
    text += f"📝 **Повідомлень до тесту:** {current_count}\n"
    text += f"📝 **Повідомлень після тесту:** {stats['user_data']['message_count'] if stats else 'Помилка'}\n"
    text += f"📊 **Підвищення рівня:** {'Так' if level_up else 'Ні'}\n"

    if stats:
        level_info = stats['current_level_info']
        text += f"🏆 **Поточний рівень:** {level_info['emoji']} {level_info['name']}\n"
        text += f"⚡ **Очки мудрості:** {stats['wisdom_points']}\n"

    text += f"\n✅ **Система працює правильно!**"

    await update.message.reply_text(text, parse_mode='Markdown')

async def sync_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Синхронізує користувача через відповідь на повідомлення"""
    user_id = update.message.from_user.id
    chat_id = update.effective_chat.id

    # Перевіряємо чи користувач є адміністратором
    try:
        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        if chat_member.status not in ['administrator', 'creator']:
            await update.message.reply_text("❌ Ця команда доступна тільки адміністраторам!")
            return
    except Exception as e:
        await update.message.reply_text("❌ Помилка перевірки прав доступу!")
        return

    # Перевіряємо чи є відповідь на повідомлення
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "📝 **Використання команди:**\n"
            "Відповідайте на повідомлення користувача командою `/syncuser кількість`\n\n"
            "**Приклад:**\n"
            "Відповідь на повідомлення: `/syncuser 25000`",
            parse_mode='Markdown'
        )
        return

    target_user = update.message.reply_to_message.from_user
    target_name = target_user.first_name or target_user.username
    target_user_id = target_user.id

    # Парсимо кількість повідомлень
    args = context.args
    if len(args) < 1:
        await update.message.reply_text("❌ Вкажіть кількість повідомлень: `/syncuser 25000`")
        return

    try:
        message_count = int(args[0])
        if message_count < 0:
            await update.message.reply_text("❌ Кількість повідомлень не може бути від'ємною!")
            return
    except (ValueError, IndexError):
        await update.message.reply_text(
            "❌ Неправильний формат кількості повідомлень!\n"
            "📝 Використовуйте тільки цифри: `/syncuser 25000`",
            parse_mode='Markdown'
        )
        return

    # Імпортуємо функції з wisdom_system
    from wisdom_system import (
        load_chat_wisdom_data,
        save_chat_wisdom_data,
        get_user_level,
        WISDOM_LEVELS
    )

    chat_data = load_chat_wisdom_data(chat_id)

    # Знаходимо або створюємо користувача
    user_key = str(target_user_id)

    if user_key not in chat_data['users']:
        chat_data['users'][user_key] = {
            'name': target_name,
            'message_count': 0,
            'current_level': 0,
            'last_update': datetime.now().isoformat(),
            'join_date': datetime.now().isoformat()
        }

    # Зберігаємо стару кількість для порівняння
    old_count = chat_data['users'][user_key]['message_count']
    old_level = chat_data['users'][user_key]['current_level']

    # Оновлюємо дані користувача
    chat_data['users'][user_key]['name'] = target_name
    chat_data['users'][user_key]['message_count'] = message_count
    chat_data['users'][user_key]['last_update'] = datetime.now().isoformat()

    # Визначаємо новий рівень
    new_level = get_user_level(message_count)
    chat_data['users'][user_key]['current_level'] = new_level

    # Зберігаємо дані
    save_chat_wisdom_data(chat_id, chat_data)

    # Формуємо відповідь
    level_info = WISDOM_LEVELS[new_level]
    wisdom_points = message_count // 10

    text = f"✅ **Користувач синхронізований!**\n\n"
    text += f"👤 **Користувач:** [{target_name}](tg://user?id={target_user_id})\n"
    text += f"📝 **Повідомлень:** {old_count} → {message_count}\n"
    text += f"📊 **Рівень:** {old_level} → {new_level}\n"
    text += f"{level_info['emoji']} **{level_info['name']}**\n"
    text += f"⚡ **Очки мудрості:** {wisdom_points}\n\n"
    text += f"💭 *{level_info['description']}*"

    await update.message.reply_text(text, parse_mode='Markdown')

    # Якщо рівень підвищився, показуємо святкове повідомлення
    if new_level > old_level and new_level >= 1:
        from wisdom_system import format_level_announcement
        announcement = format_level_announcement({
            'level': new_level,
            'level_info': level_info,
            'message_count': message_count,
            'wisdom_points': wisdom_points,
            'user_name': target_name,
            'chat_id': chat_id
        })
        await update.message.reply_text(announcement, parse_mode='Markdown')

async def commands_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показує список всіх команд"""
    commands_text = (
        "📋 **Всі команди:**\n\n"
        "**🎯 Основні команди:**\n"
        "🎲 `/flipcoin` - кинути монету\n"
        "💕 `/relationships` - показати всі стосунки\n"
        "❤️ `/myrelationships` - показати ваші стосунки\n"
        "💌 `/proposals` - показати активні пропозиції\n"
        "🧠 `/mywisdom` - показати вашу мудрість\n"
        "🏆 `/wisdomtop` - топ мудрих користувачів\n"
        "🔧 `/setmessages` - встановити кількість повідомлень (відповідь на повідомлення, адміни)\n"
        "➕ `/addmessages` - додати повідомлення (відповідь на повідомлення, адміни)\n"
        "📋 `/commands` - всі команди\n\n"
        "**💫 Розпочатук стосунків:**\n"
        "💫 `/dating` - відповідь на повідомлення користувача\n"
        "👥 `/trio @user1 @user2` - створити стосунки на 3 особи\n\n"
        "**💕 Команди для пар (+очки):**\n"
        "💋 `/kiss` - поцілувати (+3 очки)\n"
        "🤗 `/hug` - обійняти (+2 очки)\n"
        "💕 `/love` - кохати (+4 очки)\n"
        "🌹 `/date` - піти на побачення (+5 очок)\n"
        "😏 `/flirt` - фліртувати (+2 очки)\n"
        "🎁 `/gift` - подарувати подарунок (+3 очки)\n"
        "💃 `/dance` - танцювати (+3 очки)\n"
        "👫 `/hold` - тримати за руку (+2 очки)\n"
        "🥰 `/cuddle` - обіймається (+3 очки)\n"
        "🗣️ `/whisper` - шепоче солодкі слова (+3 очки)\n"
        "😊 `/smile` - посміхається (+1 очко)\n"
        "😉 `/wink` - підморгує (+1 очко)\n"
        "🥺 `/compliment` - робить комплімент (+2 очки)\n"
        "🎉 `/surprise` - робить сюрприз (+4 очки)\n"
        "🎵 `/serenade` - співає серенаду (+4 очки)\n"
        "👨‍🍳 `/cook` - готує для (+3 очки)\n"
        "💆 `/massage` - робить масаж (+3 очки)\n"
        "💌 `/write` - пише любовного листа (+4 очки)\n"
        "🧺 `/picnic` - влаштовує пікнік з (+5 очок)\n"
        "🌟 `/stargazing` - дивиться на зірки (+4 очки)\n"
        "✈️ `/travel` - подорожує (+6 очок)\n\n"
        "**💒 Команди для одружених (+очки):**\n"
        "🏝️ `/honeymoon` - їде в медовий місяць (+10 очок)\n"
        "🎊 `/anniversary` - святкує річницю (+8 очок)\n"
        "🍽️ `/family_dinner` - сімейна вечеря (+5 очок)\n"
        "🏠 `/home_together` - облаштовує дім (+6 очок)\n"
        "🤝 `/support` - підтримує в важкі часи (+7 очок)\n"
        "📋 `/plan_future` - планує майбутнє (+6 очок)\n"
        "🐕 `/adopt_pet` - заводить домашню тварину (+5 очок)\n"
        "💒 `/renew_vows` - поновлює шлюбні обітниці (+15 очок)\n\n"
        "**👥 Команди для стосунків на 3 (+очки):**\n"
        "🤗 `/group_hug` - обіймається разом (+4 очки)\n"
        "🌹 `/trio_date` - побачення втрьох (+6 очок)\n"
        "💃 `/group_dance` - танцює втрьох (+5 очок)\n"
        "✈️ `/trio_travel` - подорожує втрьох (+8 очок)\n"
        "🤝 `/support_each` - підтримують один одного (+5 очок)\n"
        "🎉 `/celebrate_together` - святкує разом (+6 очок)\n\n"
        "**⚖️ Управління стосунками:**\n"
        "💍 `/propose` - зробити пропозицію\n"
        "✅ `/accept` - прийняти пропозицію\n"
        "❌ `/reject` - відхилити пропозицію\n"
        "💔 `/divorce` - розлучитися (для одружених)\n"
        "😢 `/breakup` - розстатися\n\n"
        "**🎭 Дії з користувачами:**\n"
        "`/вдарив @user додаткові дії. зі словами`\n"
        "Підтримка будь-яких імен після @\n\n"
        "**📊 Рівні стосунків:**\n"
        "👋 Знайомство (0 очок)\n"
        "😊 Симпатія (10 очок)\n"
        "💕 Романтичні почуття (25 очок)\n"
        "😍 Закоханість (45 очок)\n"
        "❤️ Кохання (75 очок)\n"
        "💖 Глибоке кохання (110 очок) - можна одружитись\n"
        "💝 Душевна єдність (150 очок)\n"
        "💞 Вічне кохання (200 очок)\n"
        "💫 Божественне кохання (250 очок)\n"
        "✨ Абсолютна єдність (300 очок)"
    )

    await update.message.reply_text(commands_text, parse_mode='Markdown')

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробляє натискання кнопок"""
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("🔙 Назад до меню", callback_data='back_to_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if query.data == 'instructions':
        instructions_text = (
            "📖 **Інструкція по використанню бота:**\n\n"
            "**Формат команди дій:**\n"
            "`/дія @імя додаткові слова. зі словами` - звичайна дія\n"
            "Підтримка будь-яких імен після @ (українські, англійські та інші)\n\n"
            "**Розпочаток стосунків:**\n"
            "💫 `/dating` - відповідь на повідомлення користувача\n"
            "👥 `/trio @user1 @user2` - стосунки на 3 особи\n"
            "Більше не потрібно вказувати партнера в командах!\n\n"
            "**Команди для пар (автоматично з партнером):**\n"
            "💋 `/kiss` - поцілувати (+3 очки)\n"
            "🤗 `/hug` - обійняти (+2 очки)\n"
            "❤️ `/love` - кохати (+4 очки)\n"
            "🌹 `/date` - піти на побачення (+5 очок)\n"
            "🎁 `/gift` - подарувати подарунок (+3 очки)\n\n"
            "**Система мудрості:**\n"
            "🧠 `/mywisdom` - ваша статистика мудрості\n"
            "🏆 `/wisdomtop` - топ мудрих користувачів\n"
            "🌱 Пишіть повідомлення для підвищення рівня!\n\n"
            "**Особливі команди:**\n"
            "💍 `/propose` - зробити пропозицію (потрібен 5 рівень - Глибоке кохання)\n"
            "💒 Команди для одружених після прийняття пропозиції\n"
            "💔 `/divorce` - розлучитися\n"
            "😢 `/breakup` - розстатися\n\n"
            "**Рівні стосунків:**\n"
            "👋 Знайомство (0) → 😊 Симпатія (10) → 💕 Романтичні почуття (25) → 😍 Закоханість (45) → ❤️ Кохання (75) → 💖 Глибоке кохання (110) - можна одружитись → 💝 Душевна єдність (150) → 💞 Вічне кохання (200) → 💫 Божественне кохання (250) → ✨ Абсолютна єдність (300)"
        )
        await query.edit_message_text(instructions_text, reply_markup=reply_markup, parse_mode='Markdown')

    elif query.data == 'examples':
        examples_text = (
            "💡 **Приклади використання:**\n\n"
            "**Прості дії:**\n"
            "• `/поцілував @Олена` → ✨ Іван поцілував ✦**Олену**\n"
            "• `/вдарив @John, сильно` → ✨ Іван вдарив ✦**John** зі словами сильно\n"
            "• `/вдарив @Mike та зломив хребет. я тебе ненавиджу` → з додатковими діями та словами\n\n"
            "**Команди для стосунків:**\n"
            "• `/kiss` → 💋 поцілунок з партнером (+3 очки)\n"
            "• `/date` → 🌹 романтичне побачення (+5 очок)\n"
            "• `/propose` → 💍 пропозиція (потрібен 5 рівень)\n"
            "• `/honeymoon` → 🏝️ медовий місяць (тільки для одружених)\n\n"
            "**Стосунки на 3:**\n"
            "• `/group_hug` → 🤗 групове обіймання (+4 очки)\n"
            "• `/trio_travel` → ✈️ подорож втрьох (+8 очок)\n\n"
            "**Інші команди:**\n"
            "• `/flipcoin` → 🪙 Орел або Решка\n"
            "• `/relationships` → 💕 список всіх пар\n"
            "• `/myrelationships` → ❤️ ваші стосунки з детальним описом"
        )
        await query.edit_message_text(examples_text, reply_markup=reply_markup, parse_mode='Markdown')

    elif query.data == 'contact':
        contact_text = (
            "📞 **Контакти та підтримка:**\n\n"
            "👨‍💻 Розробник: @shadow\\_tar\n"
            "💬 Для питань та пропозицій звертайтесь до розробника\n\n"
            "🐛 Знайшли помилку? Повідомте нам!\n"
            "💡 Є ідеї для покращення? Ми слухаємо!"
        )
        await query.edit_message_text(contact_text, reply_markup=reply_markup, parse_mode='Markdown')

    elif query.data == 'about':
        about_text = (
            "ℹ️ **Про бота:**\n\n"
            "🎭 Бот для створення веселих дій та управління детальними стосунками\n"
            "💕 Розширена система рівнів стосунків з очками та описами\n"
            "👥 Підтримка стосунків на 2 або 3 особи\n"
            "💒 Особливі команди для одружених пар\n"
            "🌍 Підтримка будь-яких імен (українські, англійські, інші)\n"
            "🎯 Призначений для розваг у групових чатах\n"
            "⚡ Швидко обробляє команди\n"
            "🎨 Красиво форматує результат\n\n"
            "**Версія:** 4.0\n"
            "**Створено:** 2024"
        )
        await query.edit_message_text(about_text, reply_markup=reply_markup, parse_mode='Markdown')

    elif query.data == 'back_to_menu':
        keyboard = [
            [InlineKeyboardButton("📖 Інструкція", callback_data='instructions')],
            [InlineKeyboardButton("📞 Зв'язок", callback_data='contact')],
            [InlineKeyboardButton("ℹ️ Про бота", callback_data='about')],
            [InlineKeyboardButton("💡 Приклади", callback_data='examples')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        welcome_text = (
            "🎭 Привіт! Я бот для створення веселих дій та управління стосунками!\n\n"
            "💕 **Детальна система рівнів стосунків:**\n"
            "👋 Знайомство → 😊 Симпатія → 💕 Романтичні почуття → 😍 Закоханість → ❤️ Кохання → 💖 Глибоке кохання (можна одружитись) → 💝 Душевна єдність → 💞 Вічне кохання → 💫 Божественне кохання → ✨ Абсолютна єдність\n\n"
            "**Основні команди:**\n"
            "`/дія @користувач додатковий текст. зі словами`\n"
            "`/dating` - розпочати стосунки (відповідь на повідомлення)\n"
            "`/kiss` - поцілувати партнера (+3 очки)\n"
            "`/propose` - зробити пропозицію (потрібен 5 рівень)\n"
            "`/mywisdom` - ваша мудрість\n\n"
            "Вибери опцію з меню нижче! 👇"
        )
        await query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

def find_user_relationships(user_name, relationships):
    """Знаходить всі стосунки користувача"""
    user_relationships = []
    for couple_id, data in relationships.items():
        parts = couple_id.split('_')
        if user_name in parts:
            user_relationships.append((couple_id, data, parts))
    return user_relationships

def check_relationship_protection(user_name, target_name, relationships):
    """Перевіряє чи можна створювати нові стосунки (захист від множинних стосунків)"""
    user_relationships = find_user_relationships(user_name, relationships)
    target_relationships = find_user_relationships(target_name, relationships)

    # Перевіряємо чи хтось із них вже у стосунках
    if user_relationships:
        return False, f"{user_name} вже у стосунках!"
    if target_relationships:
        return False, f"{target_name} вже у стосунках!"

    return True, ""

async def handle_couple_command(update: Update, context: ContextTypes.DEFAULT_TYPE, command: str, target: str = None) -> None:
    """Обробляє команди для пар"""
    user_name = update.message.from_user.first_name
    bot_username = context.bot.username
    # Load chat-specific relationships data
    chat_id = update.effective_chat.id
    chat_data = load_chat_relationships(chat_id)

    # Видаляємо повідомлення з командою
    try:
        await update.message.delete()
    except Exception as e:
        logger.warning(f"Не вдалося видалити повідомлення: {e}")

    # Обробка команди /trio для створення стосунків на 3
    if command == 'trio':
        message_text = update.message.text

        # Шукаємо всіх згаданих користувачів
        mentioned_users = re.findall(r'@(\S+)', message_text)

        if len(mentioned_users) != 2:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="👥 Для створення стосунків на 3 згадайте двох користувачів: `/trio @user1 @user2`",
                parse_mode='Markdown'
            )
            return

        # Перевіряємо чи не намагаються включити бота
        if bot_username and any(user.lower() == bot_username.lower() for user in mentioned_users):
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="🤖 Не можна включати бота в стосунки!",
                parse_mode='Markdown'
            )
            return

        # Перевіряємо чи не намагаються включити себе двічі
        if user_name in mentioned_users:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="😅 Не можна включати себе в список партнерів!",
                parse_mode='Markdown'
            )
            return

        # Формуємо список всіх учасників
        all_participants = [user_name] + mentioned_users

        # Перевіряємо чи хтось із них вже у стосунках
        for participant in all_participants:
            user_relationships = find_user_relationships(participant, chat_data['relationships'])
            if user_relationships:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"💔 {participant} вже у стосунках! Неможливо створити нові стосунки.",
                    parse_mode='Markdown'
                )
                return

        # Створюємо стосунки на 3
        couple_id = '_'.join(sorted(all_participants))
        chat_data['relationships'][couple_id] = {
            'start_date': datetime.now().isoformat(),
            'total_points': 3,
            'actions': [],
            'status': 'dating'
        }
        chat_data['chat_info']['total_relationships'] += 1
        save_chat_relationships(chat_id, chat_data)

        # Формуємо відповідь
        user_link = create_user_link(user_name, is_sender=True)
        partner_links = [create_user_link(user, is_sender=False) for user in mentioned_users]

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"👥💕 Вітаємо! {user_link}, {partner_links[0]} та {partner_links[1]} тепер у стосунках на трьох! ❤️💕❤️",
            parse_mode='Markdown'
        )
        return

    # Обробка команди /dating через відповідь на повідомлення
    if command == 'dating':
        if not update.message.reply_to_message:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="💫 Для розпочатку стосунків відповідайте на повідомлення користувача командою /dating",
                parse_mode='Markdown'
            )
            return

        target_user = update.message.reply_to_message.from_user
        target = target_user.first_name

        # Перевіряємо чи не намагаються розпочати стосунки з ботом
        if target_user.username and target_user.username.lower() == bot_username.lower() if bot_username else False:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="🤖 Не можна розпочинати стосунки з ботом!",
                parse_mode='Markdown'
            )
            return

        # Перевіряємо чи не намагаються розпочати стосунки з собою
        if target == user_name:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="😅 Не можна розпочинати стосунки з самим собою!",
                parse_mode='Markdown'
            )
            return

        # Перевіряємо захист від множинних стосунків
        can_create, error_msg = check_relationship_protection(user_name, target, chat_data['relationships'])
        if not can_create:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"💔 {error_msg}",
                parse_mode='Markdown'
            )
            return

        # Створюємо нові стосунки
        couple_id = '_'.join(sorted([user_name, target]))
        chat_data['relationships'][couple_id] = {
            'start_date': datetime.now().isoformat(),
            'total_points': 2,
            'actions': [],
            'status': 'dating'
        }
        chat_data['chat_info']['total_relationships'] += 1
        save_chat_relationships(chat_id, chat_data)

        user_link = create_user_link(user_name, is_sender=True)
        target_link = create_user_link(target, is_sender=False)

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"💫 Вітаємо! {user_link} та {target_link} тепер у стосунках! ❤️",
            parse_mode='Markdown'
        )
        return

    # Перевіряємо чи не намагаються виконати команду на боті
    if target and (target.lower() == bot_username.lower() if bot_username else False):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="🤖 На мені не можна виконувати команди стосунків!",
            parse_mode='Markdown'
        )
        return

    # Для всіх інших команд - шукаємо існуючі стосунки користувача
    user_relationships = find_user_relationships(user_name, chat_data['relationships'])

    if not user_relationships:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="💔 У вас немає партнера! Для створення стосунків використайте /dating відповівши на повідомлення користувача",
            parse_mode='Markdown'
        )
        return

    # Беремо перші знайдені стосунки
    couple_id, couple_data, partners = user_relationships[0]

    # Перевіряємо особливі команди
    if command == 'propose':
        total_points = couple_data.get('total_points', 0)
        if total_points < RELATIONSHIP_LEVELS[5]["required_points"]:
            current_level = get_relationship_level(total_points)
            needed = RELATIONSHIP_LEVELS[5]["required_points"] - total_points
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"💍 Для пропозиції потрібен 5 рівень стосунків (Глибоке кохання)!\n📊 Ваш рівень: {RELATIONSHIP_LEVELS[current_level]['emoji']} {RELATIONSHIP_LEVELS[current_level]['name']}\n⚡ Потрібно ще {needed} очок для пропозиції!",
                parse_mode='Markdown'
            )
            return

        # Вибираємо цільового партнера (перший, хто не є користувачем)
        target = next(p for p in partners if p != user_name)

        chat_data['relationships'][couple_id]['proposal'] = {'from': user_name, 'to': target, 'status': 'pending'}
        save_chat_relationships(chat_id, chat_data)

        user_link = create_user_link(user_name, is_sender=True)
        target_link = create_user_link(target, is_sender=False)

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"💍 {user_link} робить пропозицію {target_link}! 💕\n\n{target_link}, використайте /accept або /reject",
            parse_mode='Markdown'
        )
        return

    elif command == 'accept':
        if 'proposal' not in couple_data:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="💔 Немає пропозиції для прийняття!",
                parse_mode='Markdown'
            )
            return

        proposal = couple_data['proposal']
        if proposal['to'] != user_name or proposal['status'] != 'pending':
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="💔 Ви не можете прийняти цю пропозицію!",
                parse_mode='Markdown'
            )
            return

        chat_data['relationships'][couple_id]['status'] = 'married'
        del chat_data['relationships'][couple_id]['proposal']
        save_chat_relationships(chat_id, chat_data)

        user_link = create_user_link(user_name, is_sender=True)
        proposer_link = create_user_link(proposal['from'], is_sender=False)

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"💒 Вітаємо! {proposer_link} та {user_link} тепер одружені! 🎉👰🤵💕",
            parse_mode='Markdown'
        )
        return

    elif command == 'reject':
        if 'proposal' not in couple_data:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="💔 Немає пропозиції для відхилення!",
                parse_mode='Markdown'
            )
            return

        proposal = couple_data['proposal']
        if proposal['to'] != user_name or proposal['status'] != 'pending':
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="💔 Ви не можете відхилити цю пропозицію!",
                parse_mode='Markdown'
            )
            return

        del chat_data['relationships'][couple_id]['proposal']
        save_chat_relationships(chat_id, chat_data)

        user_link = create_user_link(user_name, is_sender=True)
        proposer_link = create_user_link(proposal['from'], is_sender=False)

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"💔 {user_link} відхилив(ла) пропозицію від {proposer_link}... 😢",
            parse_mode='Markdown'
        )
        return

    elif command == 'divorce':
        if couple_data.get('status') != 'married':
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="💔 Ви не одружені! Неможливо розлучитися.",
                parse_mode='Markdown'
            )
            return

        del chat_data['relationships'][couple_id]
        chat_data['chat_info']['total_relationships'] -= 1
        save_chat_relationships(chat_id, chat_data)

        user_link = create_user_link(user_name, is_sender=True)
        partners_links = [create_user_link(p, is_sender=False) for p in partners if p != user_name]

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"💔 {user_link} та {' і '.join(partners_links)} розлучилися... 😢",
            parse_mode='Markdown'
        )
        return

    elif command == 'breakup':
        del chat_data['relationships'][couple_id]
        chat_data['chat_info']['total_relationships'] -= 1
        save_chat_relationships(chat_id, chat_data)

        user_link = create_user_link(user_name, is_sender=True)
        partners_links = [create_user_link(p, is_sender=False) for p in partners if p != user_name]

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"😢 {user_link} та {' і '.join(partners_links)} розсталися... 💔",
            parse_mode='Markdown'
        )
        return

    # Перевіряємо чи команда існує в списку команд
    if command not in ALL_COUPLE_COMMANDS:
        return

    # Перевіряємо команди для одружених
    if command in MARRIED_COMMANDS and couple_data.get('status') != 'married':
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="💒 Ця команда доступна тільки для одружених пар! Спочатку зробіть пропозицію командою /propose",
            parse_mode='Markdown'
        )
        return

    # Звичайні команди стосунків
    command_info = ALL_COUPLE_COMMANDS[command]
    action = command_info['action']
    points = command_info['points']
    emoji = command_info['emoji']

    # Перевіряємо та додаємо відсутні поля для старих записів
    if 'total_points' not in chat_data['relationships'][couple_id]:
        chat_data['relationships'][couple_id]['total_points'] = 0
    if 'actions' not in chat_data['relationships'][couple_id]:
        chat_data['relationships'][couple_id]['actions'] = []
    if 'status' not in chat_data['relationships'][couple_id]:
        chat_data['relationships'][couple_id]['status'] = 'dating'

    # Додаємо дію та очки
    chat_data['relationships'][couple_id]['total_points'] += points
    chat_data['relationships'][couple_id]['actions'].append({
        'action': f"{user_name} {action}",
        'date': datetime.now().isoformat(),
        'points': points
    })

    total_points = chat_data['relationships'][couple_id]['total_points']
    current_level = get_relationship_level(total_points)
    level_info = RELATIONSHIP_LEVELS[current_level]

    save_chat_relationships(chat_id, chat_data)

    # Формуємо відповідь
    user_link = create_user_link(user_name, is_sender=True)

    if len(partners) == 2:
        target_name = next(p for p in partners if p != user_name)
        target_declined = decline_name(target_name)
        target_link = create_user_link(target_declined, is_sender=False)
        response = f"{emoji} {user_link} {action} {target_link}"
    else:  # 3 або більше партнерів
        other_partners = [p for p in partners if p != user_name]
        partners_links = [create_user_link(decline_name(p), is_sender=False) for p in other_partners]
        response = f"{emoji} {user_link} {action} {' та '.join(partners_links)}"

    # Додаємо інформацію про рівень
    if points > 0:
        response += f"\n📊 Рівень стосунків: {level_info['emoji']} {level_info['name']} ({total_points} очок)"

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=response,
        parse_mode='Markdown'
    )

async def handle_action_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробляє звичайні команди дій з підтримкою будь-яких імен та дій без користувача"""
    message_text = update.message.text.strip()
    user_name = update.message.from_user.first_name
    bot_username = context.bot.username

    # Видаляємо повідомлення з командою
    try:
        await update.message.delete()
    except Exception as e:
        logger.warning(f"Не вдалося видалити повідомлення: {e}")

    # Спочатку перевіряємо на дії без користувача (без @)
    # Приклад: /дав жінкам права → Тарас дав жінкам права
    if '@' not in message_text:
        action_match = re.match(r'^/(.+)$', message_text)
        if action_match:
            action_text = action_match.group(1).strip()

            # Перевіряємо чи це не команда для пар або спеціальна команда
            first_word = action_text.split()[0] if action_text.split() else action_text
            if first_word not in ALL_COUPLE_COMMANDS and first_word not in VALID_COMMANDS:
                user_link = create_user_link(user_name, is_sender=True)
                response = f"✨ {user_link} {action_text}"

                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=response,
                    parse_mode='Markdown'
                )
                return

    # Розбираємо команду з підтримкою будь-яких імен після @ (включаючи _ і +)
    # Приклад: /вдарив та переломив хребет @John_+test після чого вдарив в печінку. я тебе люблю
    pattern = r'^/([^@]+?)\s*@([^\s]+)(.*)$'
    match = re.match(pattern, message_text)

    if not match:
        return

    action = match.group(1).strip()
    target_username = match.group(2).strip()
    rest_text = match.group(3).strip() if match.group(3) else ""

    # Перевіряємо чи це не команда для пар
    if action in ALL_COUPLE_COMMANDS:
        return

    # Перевіряємо чи не намагаються виконати команду на боті
    if target_username.lower() == bot_username.lower() if bot_username else False:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="🤖 На мені не можна виконувати дії!",
            parse_mode='Markdown'
        )
        return

    # Спробуємо знайти користувача за username для отримання user_id
    target_user_id = None
    target_display_name = target_username

    if update.message.reply_to_message and update.message.reply_to_message.from_user:
        reply_user = update.message.reply_to_message.from_user
        if reply_user.username and reply_user.username.lower() == target_username.lower():
            target_user_id = reply_user.id
            target_display_name = reply_user.first_name or reply_user.username

    user_link = create_user_link(user_name, is_sender=True)
    target_declined = decline_name(target_display_name)
    target_link = create_user_link(target_declined, target_user_id, is_sender=False, is_action=True)

    # Розділяємо додаткові дії та слова по крапці
    additional_actions = ""
    words = ""

    if rest_text:
        if '.' in rest_text:
            parts = rest_text.split('.', 1)
            additional_actions = parts[0].strip()
            words = parts[1].strip()
        else:
            additional_actions = rest_text

    # Формуємо відповідь
    response = f"✨ {user_link} {action} {target_link}"

    if additional_actions:
        response += f" {additional_actions}"

    if words:
        response += f" зі словами 💬**\"{words}\"**✨"

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=response,
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробляє всі повідомлення і шукає команди"""
    if not update.message:
        return

    # Обробляємо систему мудрості для ВСІХ повідомлень користувачів у групах та супергрупах
    if update.message.from_user and update.effective_chat.type in ['group', 'supergroup']:
        user_id = update.message.from_user.id
        user_name = update.message.from_user.first_name or update.message.from_user.username or f"User_{user_id}"
        chat_id = update.effective_chat.id

        # ВИДАЛЕНО ЗАХИСТ ВІД СПАМУ - рахуємо КОЖНЕ повідомлення
        try:
            # Детальне логування та вивід в консоль для дебагу
            print(f"🔍 ОБРОБКА ПОВІДОМЛЕННЯ (БЕЗ ЗАХИСТУ ВІД СПАМУ):")
            print(f"👤 Користувач: {user_name} (ID: {user_id})")
            print(f"💬 Чат: {chat_id}")
            print(f"📝 Текст: {update.message.text[:50] if update.message.text else 'Немає тексту'}")
            print(f"⏰ Час: {datetime.now()}")

            logger.info(f"Обробка повідомлення від користувача {user_name} (ID: {user_id}) в чаті {chat_id}")

            # Обробляємо повідомлення в системі мудрості з chat_id
            print(f"🔄 Викликаємо process_user_message...")
            level_up, level_data = process_user_message(user_id, user_name, chat_id)

            print(f"✅ Повідомлення оброблено. Level up: {level_up}")
            logger.info(f"Повідомлення оброблено. Level up: {level_up}")

            # Перевіряємо поточну статистику після обробки
            from wisdom_system import get_user_wisdom_stats_in_chat
            current_stats = get_user_wisdom_stats_in_chat(chat_id, user_id)
            if current_stats:
                print(f"📊 ПОТОЧНА СТАТИСТИКА ПІСЛЯ ОБРОБКИ:")
                print(f"   Повідомлень: {current_stats['user_data']['message_count']}")
                print(f"   Рівень: {current_stats['current_level_info']['name']}")

            # Якщо користувач досяг нового рівня, вітаємо його
            if level_up and level_data:
                print(f"🎉 НОВИЙ РІВЕНЬ! {user_name} досяг рівня {level_data['level']}")
                announcement = format_level_announcement(level_data)
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=announcement,
                    parse_mode='Markdown'
                )
                logger.info(f"Відправлено оголошення про новий рівень для {user_name}")
            else:
                print(f"📊 Без підвищення рівня для {user_name}")

        except Exception as e:
            # Детальне логування помилок з виводом в консоль
            print(f"❌ КРИТИЧНА ПОМИЛКА в системі мудрості для {user_name}: {e}")
            logger.error(f"Помилка в системі мудрості для користувача {user_name}: {e}", exc_info=True)
            import traceback
            traceback.print_exc()

    # Обробляємо тільки текстові повідомлення для команд
    if not update.message.text:
        return

    message_text = update.message.text

    if message_text.startswith('/'):
        # Витягуємо команду
        command_match = re.match(r'^/(\w+)', message_text)
        if command_match:
            command = command_match.group(1)

            # Перевіряємо чи це команда для пар
            if command in ALL_COUPLE_COMMANDS:
                # Шукаємо згаданого користувача
                target = None
                if '@' in message_text:
                    target_match = re.search(r'@(\S+)', message_text)
                    if target_match:
                        target = target_match.group(1)

                await handle_couple_command(update, context, command, target)
            else:
                # Звичайна дія
                await handle_action_command(update, context)

# Папка для зберігання баз даних стосунків
RELATIONSHIPS_CHATS_DIR = 'relationships_chats'

# Створюємо папку якщо її немає
if not os.path.exists(RELATIONSHIPS_CHATS_DIR):
    os.makedirs(RELATIONSHIPS_CHATS_DIR)

def load_chat_relationships(chat_id):
    """Loads relationships for a specific chat from a JSON file."""
    filename = os.path.join(RELATIONSHIPS_CHATS_DIR, f'relationships_{chat_id}.json')
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # If the file doesn't exist, initialize the chat data
        return {
            'chat_info': {'total_relationships': 0},
            'relationships': {}
        }

def save_chat_relationships(chat_id, data):
    """Saves relationships for a specific chat to a JSON file."""
    filename = os.path.join(RELATIONSHIPS_CHATS_DIR, f'relationships_{chat_id}.json')
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)



def main() -> None:
    """Запускає бота"""
    try:
        # Створюємо додаток з налаштуваннями таймаутів
        application = (Application.builder()
                      .token(BOT_TOKEN)
                      .connect_timeout(30)
                      .read_timeout(30)
                      .write_timeout(30)
                      .write_timeout(30)
                      .pool_timeout(30)
                      .build())

        application.post_init = setup_bot_commands

        # Додаємо обробники команд
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", start_command))
        application.add_handler(CommandHandler("flipcoin", flipcoin_command))
        application.add_handler(CommandHandler("relationships", relationships_command))
        application.add_handler(CommandHandler("myrelationships", my_relationships_command))
        application.add_handler(CommandHandler("proposals", proposals_command))
        application.add_handler(CommandHandler("commands", commands_command))
        application.add_handler(CommandHandler("mywisdom", my_wisdom_command))
        application.add_handler(CommandHandler("wisdomtop", wisdom_top_command))
        application.add_handler(CommandHandler("setmessages", set_messages_command))
        application.add_handler(CommandHandler("addmessages", add_messages_command))
        application.add_handler(CommandHandler("syncuser", sync_user_command))
        application.add_handler(CommandHandler("testwisdom", test_wisdom_command))
        application.add_handler(CallbackQueryHandler(button_callback))

        # Обробники для повідомлень
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_handler(MessageHandler(filters.COMMAND, handle_message))

        print("Бот запущений з детальною системою стосунків...")

        # Запускаємо бота з обробкою помилок
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
            timeout=30
        )

    except Exception as e:
        logger.error(f"Помилка запуску бота: {e}")
        print(f"Критична помилка: {e}")
        print("Перевірте BOT_TOKEN та інтернет-з'єднання")

if __name__ == '__main__':
    main()
