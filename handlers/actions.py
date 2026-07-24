import re
import logging
from telegram import Update
from telegram.ext import ContextTypes

from config.levels import ALL_COUPLE_COMMANDS, VALID_COMMANDS
from utils.helpers import decline_name, create_user_link
from handlers.relationships import handle_couple_command

logger = logging.getLogger(__name__)

async def handle_action_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробляє звичайні команди дій з підтримкою будь-яких імен, префіксів / та !"""
    message_text = update.message.text.strip()
    sender_name = update.message.from_user.first_name or update.message.from_user.username or "Користувач"
    bot_username = context.bot.username

    # МИТТЄВО намагаємося видалити вихідне повідомлення користувача
    try:
        await update.message.delete()
    except Exception as e:
        logger.warning(f"Не вдалося видалити повідомлення: {e}")

    # Перевіряємо дію без згадки користувача (без @)
    # Приклад: /дав жінкам права або !дав жінкам права
    if '@' not in message_text:
        action_match = re.match(r'^[/\!](.+)$', message_text)
        if action_match:
            action_text = action_match.group(1).strip()
            first_word = action_text.split()[0] if action_text.split() else action_text
            if first_word not in ALL_COUPLE_COMMANDS and first_word not in VALID_COMMANDS:
                user_link = create_user_link(sender_name, is_sender=True)
                response = f"✨ {user_link} {action_text}"

                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=response,
                    parse_mode='Markdown'
                )
                return

    # Розбираємо команду з підтримкою префіксів / та ! і будь-яких імен після @
    # Приклад: /вдарив @User або !вдарив @User дуже сильно. зі словами
    pattern = r'^[/\!]([^@]+?)\s*@([^\s]+)(.*)$'
    match = re.match(pattern, message_text)

    if not match:
        return

    action = match.group(1).strip()
    target_username = match.group(2).strip()
    rest_text = match.group(3).strip() if match.group(3) else ""

    # Перевіряємо чи це не команда для пар
    if action in ALL_COUPLE_COMMANDS:
        return

    # Захист від виконання дії на боті
    if bot_username and target_username.lower() == bot_username.lower():
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="🤖 На мені не можна виконувати дії!",
            parse_mode='Markdown'
        )
        return

    # Отримуємо ім'я отримувача: з відповіді (reply) або зі згадки
    target_user_id = None
    target_display_name = target_username

    if update.message.reply_to_message and update.message.reply_to_message.from_user:
        reply_user = update.message.reply_to_message.from_user
        if reply_user.username and reply_user.username.lower() == target_username.lower():
            target_user_id = reply_user.id
            target_display_name = reply_user.first_name or reply_user.username
        elif not reply_user.username and reply_user.first_name:
            target_user_id = reply_user.id
            target_display_name = reply_user.first_name

    # Обов'язково пропускаємо ім'я через функцію відмінювання decline_name()
    user_link = create_user_link(sender_name, is_sender=True)
    target_declined = decline_name(target_display_name)
    target_link = create_user_link(target_declined, target_user_id, is_sender=False, is_action=True)

    additional_actions = ""
    words = ""

    if rest_text:
        if '.' in rest_text:
            parts = rest_text.split('.', 1)
            additional_actions = parts[0].strip()
            words = parts[1].strip()
        else:
            additional_actions = rest_text

    # Формуємо результат відповіді
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
    """Головний обробник текстових повідомлень з підтримкою префіксів / та !"""
    if not update.message or not update.message.text:
        return

    message_text = update.message.text.strip()

    # Обробляємо команди з префіксом / або !
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
