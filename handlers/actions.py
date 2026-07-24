import re
import logging
from telegram import Update
from telegram.ext import ContextTypes

from config.names import USERS_MAP
from config.levels import ALL_COUPLE_COMMANDS, VALID_COMMANDS
from utils.helpers import decline_name, create_html_user_link, escape_html
from handlers.relationships import handle_couple_command
from storage.user_cache import update_user_cache, get_first_name_by_username

logger = logging.getLogger(__name__)

async def _send_html_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str) -> None:
    """Відправляє повідомлення у чат у форматі HTML"""
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode='HTML'
        )
    except Exception as e:
        logger.warning(f"Не вдалося відправити HTML повідомлення ({e}), відправляємо звичайний текст")
        plain_text = re.sub(r'<[^>]*>', '', text)
        await context.bot.send_message(
            chat_id=chat_id,
            text=plain_text
        )

async def handle_action_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробляє звичайні команди дій з підтримкою префіксів / та !, USERS_MAP, first_name за @username та жирного шрифту HTML"""
    message_text = update.message.text.strip()
    from_user = update.message.from_user
    bot_username = context.bot.username

    # Відправник: ім'я зі словника USERS_MAP або first_name
    sender_username = from_user.username.lower() if from_user and from_user.username else ""
    if sender_username and sender_username in USERS_MAP:
        sender_name = USERS_MAP[sender_username]
    else:
        sender_name = from_user.first_name or from_user.username or "Користувач"

    # Оновлюємо кеш юзерів
    if from_user and from_user.username:
        await update_user_cache(from_user.username, sender_name, from_user.id)

    # МИТТЄВО намагаємося видалити вихідне повідомлення користувача
    try:
        await update.message.delete()
    except Exception as e:
        logger.warning(f"Не вдалося видалити повідомлення: {e}")

    # 1. Дії без згадки користувача (без @)
    # Приклад: /дав жінкам права або !дав жінкам права
    if '@' not in message_text:
        action_match = re.match(r'^[/\!](.+)$', message_text)
        if action_match:
            action_text = action_match.group(1).strip()
            first_word = action_text.split()[0] if action_text.split() else action_text
            if first_word not in ALL_COUPLE_COMMANDS and first_word not in VALID_COMMANDS:
                user_link = create_html_user_link(sender_name, is_sender=True)
                response = f"✨ {user_link} {escape_html(action_text)}"

                await _send_html_message(context, update.effective_chat.id, response)
                return

    # 2. Дії зі згадкою користувача (@username)
    # Парсинг: [Префікс][ACTION] @[TARGET] [REST_OF_TEXT]
    # Приклад: /вдарив @sp_mangment по голові або !вдарив @username
    pattern = r'^[/\!]([^@]+?)\s*@([^\s]+)(.*)$'
    match = re.match(pattern, message_text, re.DOTALL)

    if not match:
        return

    action = match.group(1).strip()
    raw_target = match.group(2).strip().lstrip('@')
    rest_text = match.group(3).strip() if match.group(3) else ""

    if action in ALL_COUPLE_COMMANDS:
        return

    # Перевірка на бота
    if bot_username and raw_target.lower() == bot_username.lower():
        await _send_html_message(context, update.effective_chat.id, "🤖 На мені не можна виконувати дії!")
        return

    # Логіка визначення імені Отримувача (Target)
    target_user_id = None
    target_display_name = None

    # а) Спочатку шукаємо юзернейм у статичному USERS_MAP
    if raw_target.lower() in USERS_MAP:
        target_display_name = USERS_MAP[raw_target.lower()]

    # б) Перевірка text_mention в entities
    if not target_display_name and update.message.entities:
        for entity in update.message.entities:
            if entity.type == 'text_mention' and entity.user:
                target_display_name = entity.user.first_name or entity.user.username
                target_user_id = entity.user.id
                break

    # в) Перевірка reply_to_message
    if not target_display_name and update.message.reply_to_message and update.message.reply_to_message.from_user:
        reply_user = update.message.reply_to_message.from_user
        if reply_user.username and reply_user.username.lower() == raw_target.lower():
            target_display_name = reply_user.first_name or reply_user.username
            target_user_id = reply_user.id
        elif not reply_user.username:
            target_display_name = reply_user.first_name
            target_user_id = reply_user.id

    # г) Пошук у динамічному кеші юзерів
    if not target_display_name:
        cached_name, cached_id = await get_first_name_by_username(raw_target)
        if cached_name:
            target_display_name = cached_name
            target_user_id = cached_id

    # д) Fallback на чистий юзернейм
    if not target_display_name:
        target_display_name = raw_target

    # Обов'язково відміняємо ім'я отримувача ("Арма" -> "Арму")
    target_declined = decline_name(target_display_name)

    user_link = create_html_user_link(sender_name, is_sender=True)
    target_link = create_html_user_link(target_declined, target_user_id, is_sender=False, is_action=True)

    # Формування підсумкового речення в HTML:
    # ✨ <b>[Відправник]</b> [дія] <b>[Отримувач]</b> [додатковий текст]
    response = f"✨ {user_link} {escape_html(action)} {target_link}"

    if rest_text:
        response += f" {escape_html(rest_text)}"

    await _send_html_message(context, update.effective_chat.id, response)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Головний обробник текстових повідомлень з підтримкою кешування юзерів та префіксів / та !"""
    if not update.message:
        return

    # Завжди оновлюємо кеш юзернейма та first_name при будь-якому повідомленні
    if update.message.from_user:
        user = update.message.from_user
        first_name = user.first_name or user.username or "Користувач"
        if user.username:
            await update_user_cache(user.username, first_name, user.id)

    if not update.message.text:
        return

    message_text = update.message.text.strip()

    if message_text.startswith('/') or message_text.startswith('!'):
        command_match = re.match(r'^[/\!](\w+)', message_text)
        if command_match:
            command = command_match.group(1)

            if command in ALL_COUPLE_COMMANDS or command == 'trio':
                target = None
                if '@' in message_text:
                    target_match = re.search(r'@(\S+)', message_text)
                    if target_match:
                        target = target_match.group(1)

                await handle_couple_command(update, context, command, target)
            else:
                await handle_action_command(update, context)
