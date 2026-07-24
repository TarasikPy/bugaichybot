import re
import logging
from telegram import Update
from telegram.ext import ContextTypes

from config.names import USERS_MAP
from config.levels import ALL_COUPLE_COMMANDS, VALID_COMMANDS
from utils.helpers import decline_name, create_html_user_link, escape_html
from handlers.relationships import handle_couple_command
from storage.user_cache import update_user_cache, get_user_info_by_username

logger = logging.getLogger(__name__)

async def _send_html_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str) -> None:
    """Відправляє повідомлення у чат у форматі HTML з fallback на чистий текст"""
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode='HTML'
        )
    except Exception as e:
        logger.warning(f"Не вдалося відправити HTML повідомлення ({e}), відправляємо чистий текст")
        plain_text = re.sub(r'<[^>]*>', '', text)
        await context.bot.send_message(
            chat_id=chat_id,
            text=plain_text
        )

async def handle_action_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробляє звичайні команди дій з підтримкою REPLY (відповіді на повідомлення), @username згадок, USERS_MAP та клікабельних HTML посилань tg://user?id="""
    message_text = update.message.text.strip()
    from_user = update.message.from_user
    bot_username = context.bot.username

    sender_id = from_user.id if from_user else None
    sender_username = from_user.username.lower() if from_user and from_user.username else ""

    # Ім'я відправника з USERS_MAP або first_name
    if sender_username and sender_username in USERS_MAP:
        sender_name = USERS_MAP[sender_username]
    else:
        sender_name = from_user.first_name or from_user.username or "Користувач"

    # Завжди оновлюємо динамічний кеш юзерів
    if from_user and from_user.username:
        await update_user_cache(from_user.username, sender_name, sender_id)

    # МИТТЄВО намагаємося видалити вихідне повідомлення користувача
    try:
        await update.message.delete()
    except Exception as e:
        logger.warning(f"Не вдалося видалити повідомлення: {e}")

    if not (message_text.startswith('/') or message_text.startswith('!')):
        return

    target_user_id = None
    target_display_name = None
    action = ""
    rest_text = ""

    # ВАРІАНТ А: Дія через REPLY (Відповідь на повідомлення користувача)
    if update.message.reply_to_message and update.message.reply_to_message.from_user:
        reply_user = update.message.reply_to_message.from_user
        target_user_id = reply_user.id

        if reply_user.username and reply_user.username.lower() in USERS_MAP:
            target_display_name = USERS_MAP[reply_user.username.lower()]
        else:
            target_display_name = reply_user.first_name or reply_user.username or "Користувач"

        # Парсимо дію та додатковий текст (наприклад "!вдарив лопатою по голові")
        match_reply = re.match(r'^[/\!](\S+)\s*(.*)$', message_text, re.DOTALL)
        if match_reply:
            action = match_reply.group(1).strip()
            rest_text = match_reply.group(2).strip()

    # ВАРІАНТ Б: Дія через ЗГАДКУ (@username або entities)
    elif '@' in message_text:
        pattern = r'^[/\!]([^@]+?)\s*@([^\s]+)(.*)$'
        match_mention = re.match(pattern, message_text, re.DOTALL)

        if match_mention:
            action = match_mention.group(1).strip()
            raw_target = match_mention.group(2).strip().lstrip('@')
            rest_text = match_mention.group(3).strip() if match_mention.group(3) else ""

            # а) Перевірка text_mention в entities
            if update.message.entities:
                for entity in update.message.entities:
                    if entity.type == 'text_mention' and entity.user:
                        target_user_id = entity.user.id
                        target_display_name = entity.user.first_name or entity.user.username
                        break

            # б) Пошук у статичному USERS_MAP
            if not target_display_name and raw_target.lower() in USERS_MAP:
                target_display_name = USERS_MAP[raw_target.lower()]

            # в) Пошук у динамічному кеші юзерів
            if not target_user_id or not target_display_name:
                cached_name, cached_id = await get_user_info_by_username(raw_target)
                if cached_name and not target_display_name:
                    target_display_name = cached_name
                if cached_id and not target_user_id:
                    target_user_id = cached_id

            # г) Fallback
            if not target_display_name:
                target_display_name = raw_target

    # ВАРІАНТ В: Дії без отримувача (наприклад /дав жінкам права або !дав жінкам права)
    else:
        action_match = re.match(r'^[/\!](.+)$', message_text)
        if action_match:
            action_text = action_match.group(1).strip()
            first_word = action_text.split()[0] if action_text.split() else action_text
            if first_word not in ALL_COUPLE_COMMANDS and first_word not in VALID_COMMANDS:
                sender_link = create_html_user_link(sender_name, user_id=sender_id)
                response = f"✨ {sender_link} {escape_html(action_text)}"

                await _send_html_message(context, update.effective_chat.id, response)
                return

    if not action or action in ALL_COUPLE_COMMANDS:
        return

    # Захист від виконання дії на боті
    if bot_username and target_display_name and target_display_name.lower() == bot_username.lower():
        await _send_html_message(context, update.effective_chat.id, "🤖 На мені не можна виконувати дії!")
        return

    # Обов'язково відміняємо ім'я отримувача ("Арма" -> "Арму", "Сергій" -> "Сергія")
    target_declined = decline_name(target_display_name) if target_display_name else ""

    # Генеруємо HTML-посилання для ВІДПРАВНИКА та ОТРИМУВАЧА
    sender_link = create_html_user_link(sender_name, user_id=sender_id)

    if target_user_id:
        target_link = f'<a href="tg://user?id={target_user_id}">{escape_html(target_declined)}</a>'
    else:
        target_link = f'<b>{escape_html(target_declined)}</b>'

    # Формування підсумкового речення:
    # ✨ <a href="tg://user?id=111">KIYOTAKA</a> вдарив <a href="tg://user?id=222">Арму</a> лопатою по голові
    response = f"✨ {sender_link} {escape_html(action)} {target_link}"

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
