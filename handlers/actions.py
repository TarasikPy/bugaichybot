import re
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes

from config.levels import ALL_COUPLE_COMMANDS, VALID_COMMANDS
from utils.helpers import decline_name, create_user_link
from utils.wisdom_core import process_user_message_in_chat, format_level_announcement
from storage.wisdom_db import load_chat_wisdom_data, save_chat_wisdom_data
from handlers.relationships import handle_couple_command

logger = logging.getLogger(__name__)

async def handle_action_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробляє звичайні команди дій з підтримкою будь-яких імен та дій без користувача"""
    message_text = update.message.text.strip()
    user_name = update.message.from_user.first_name
    bot_username = context.bot.username

    try:
        await update.message.delete()
    except Exception as e:
        logger.warning(f"Не вдалося видалити повідомлення: {e}")

    if '@' not in message_text:
        action_match = re.match(r'^/(.+)$', message_text)
        if action_match:
            action_text = action_match.group(1).strip()
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

    pattern = r'^/([^@]+?)\s*@([^\s]+)(.*)$'
    match = re.match(pattern, message_text)

    if not match:
        return

    action = match.group(1).strip()
    target_username = match.group(2).strip()
    rest_text = match.group(3).strip() if match.group(3) else ""

    if action in ALL_COUPLE_COMMANDS:
        return

    if bot_username and target_username.lower() == bot_username.lower():
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="🤖 На мені не можна виконувати дії!",
            parse_mode='Markdown'
        )
        return

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

    additional_actions = ""
    words = ""

    if rest_text:
        if '.' in rest_text:
            parts = rest_text.split('.', 1)
            additional_actions = parts[0].strip()
            words = parts[1].strip()
        else:
            additional_actions = rest_text

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
    """Обробляє всі повідомлення, підраховує мудрість та викликає роутинг команд"""
    if not update.message:
        return

    if update.message.from_user and update.effective_chat.type in ['group', 'supergroup']:
        user_id = update.message.from_user.id
        user_name = update.message.from_user.first_name or update.message.from_user.username or f"User_{user_id}"
        chat_id = update.effective_chat.id

        try:
            chat_wisdom_data = await load_chat_wisdom_data(chat_id)
            level_up, level_data = process_user_message_in_chat(chat_wisdom_data, user_id, user_name)
            await save_chat_wisdom_data(chat_id, chat_wisdom_data)

            if level_up and level_data:
                announcement = format_level_announcement(level_data)
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=announcement,
                    parse_mode='Markdown'
                )

        except Exception as e:
            logger.error(f"Помилка в системі мудрості для {user_name}: {e}", exc_info=True)

    if not update.message.text:
        return

    message_text = update.message.text

    if message_text.startswith('/'):
        command_match = re.match(r'^/(\w+)', message_text)
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
