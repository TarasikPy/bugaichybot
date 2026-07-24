import re
import logging
from telegram import Update
from telegram.ext import ContextTypes

from config.levels import ALL_COUPLE_COMMANDS, VALID_COMMANDS
from utils.helpers import decline_name, create_user_link
from handlers.relationships import handle_couple_command

logger = logging.getLogger(__name__)

async def handle_action_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробляє звичайні команди дій з підтримкою префіксів / та !, відмінюванням отримувача та збереженням додаткового тексту"""
    message_text = update.message.text.strip()
    sender_name = update.message.from_user.first_name or update.message.from_user.username or "Користувач"
    bot_username = context.bot.username

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
                user_link = create_user_link(sender_name, is_sender=True)
                response = f"✨ {user_link} {action_text}"

                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=response,
                    parse_mode='Markdown'
                )
                return

    # 2. Дії зі згадкою користувача (@username)
    # Парсинг: [Префікс][ACTION] @[TARGET] [REST_OF_TEXT]
    # Приклад: /вдарив @sp_mangment по голові або !вдарив @username
    pattern = r'^[/\!]([^@]+?)\s*@([^\s]+)(.*)$'
    match = re.match(pattern, message_text, re.DOTALL)

    if not match:
        return

    action = match.group(1).strip()
    raw_target = match.group(2).strip()
    rest_text = match.group(3).strip() if match.group(3) else ""

    if action in ALL_COUPLE_COMMANDS:
        return

    # Перевірка на бота
    if bot_username and raw_target.lower() == bot_username.lower():
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="🤖 На мені не можна виконувати дії!",
            parse_mode='Markdown'
        )
        return

    # Визначення імені отримувача
    target_user_id = None
    target_display_name = raw_target

    # Якщо це відповідь (reply) на повідомлення, пробуємо взяти first_name отримувача
    if update.message.reply_to_message and update.message.reply_to_message.from_user:
        reply_user = update.message.reply_to_message.from_user
        if reply_user.username and reply_user.username.lower() == raw_target.lower():
            target_user_id = reply_user.id
            target_display_name = reply_user.first_name or reply_user.username
        elif not reply_user.username:
            target_user_id = reply_user.id
            target_display_name = reply_user.first_name or raw_target

    # Обов'язково відміняємо ім'я/юзернейм отримувача
    target_declined = decline_name(target_display_name)

    user_link = create_user_link(sender_name, is_sender=True)
    target_link = create_user_link(target_declined, target_user_id, is_sender=False, is_action=True)

    # Формування підсумкового речення:
    # [Ім'я Відправника] [дія] [Відміняне Ім'я Отримувача] [додатковий текст]
    response = f"✨ {user_link} {action} {target_link}"

    if rest_text:
        if '.' in rest_text:
            parts = rest_text.split('.', 1)
            additional = parts[0].strip()
            words = parts[1].strip()
            if additional:
                response += f" {additional}"
            if words:
                response += f" зі словами 💬**\"{words}\"**✨"
        else:
            response += f" {rest_text}"

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
