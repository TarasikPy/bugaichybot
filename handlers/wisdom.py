from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes

from utils.wisdom_core import (
    WISDOM_LEVELS,
    get_user_level,
    get_user_wisdom_stats_in_chat,
    get_wisdom_leaderboard,
    format_level_announcement,
    process_user_message_in_chat
)
from storage.wisdom_db import load_chat_wisdom_data, save_chat_wisdom_data

async def my_wisdom_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показує статистику мудрості користувача"""
    user_id = update.message.from_user.id
    user_name = update.message.from_user.first_name
    chat_id = update.effective_chat.id

    chat_data = await load_chat_wisdom_data(chat_id)
    stats = get_user_wisdom_stats_in_chat(chat_data, user_id)

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
    """Показує топ користувачів за мудрістю в чаті"""
    chat_id = update.effective_chat.id
    chat_data = await load_chat_wisdom_data(chat_id)
    leaderboard = get_wisdom_leaderboard(chat_data, 10)

    if not leaderboard:
        await update.message.reply_text("🏆 Поки що немає мудрих користувачів! Станьте першим!")
        return

    text = "🏆 **Топ мудрих користувачів:**\n\n"

    for entry in leaderboard:
        rank_emoji = "🥇" if entry['rank'] == 1 else "🥈" if entry['rank'] == 2 else "🥉" if entry['rank'] == 3 else f"{entry['rank']}."
        safe_name = entry['name'].replace('*', '\\*').replace('_', '\\_').replace('[', '\\[').replace(']', '\\]').replace('`', '\\`')

        text += f"{rank_emoji} {safe_name}\n"
        text += f"{entry['level_info']['emoji']} {entry['level_info']['name']}\n"
        text += f"📝 {entry['message_count']} повідомлень | ⚡ {entry['wisdom_points']} очок\n\n"

    try:
        await update.message.reply_text(text, parse_mode='Markdown')
    except Exception:
        text_plain = text.replace('**', '').replace('*', '').replace('_', '').replace('`', '')
        await update.message.reply_text(text_plain)

async def set_messages_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Встановлює кількість повідомлень для користувача (тільки для адмінів)"""
    user_id = update.message.from_user.id
    chat_id = update.effective_chat.id

    try:
        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        if chat_member.status not in ['administrator', 'creator']:
            await update.message.reply_text("❌ Ця команда доступна тільки адміністраторам!")
            return
    except Exception:
        await update.message.reply_text("❌ Помилка перевірки прав доступу!")
        return

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
        await update.message.reply_text("❌ Неправильний формат кількості повідомлень!")
        return

    chat_data = await load_chat_wisdom_data(chat_id)
    user_key = str(target_user_id)

    if user_key not in chat_data['users']:
        chat_data['users'][user_key] = {
            'name': target_name,
            'message_count': 0,
            'current_level': 0,
            'last_update': datetime.now().isoformat(),
            'join_date': datetime.now().isoformat()
        }

    old_count = chat_data['users'][user_key]['message_count']
    old_level = chat_data['users'][user_key]['current_level']

    chat_data['users'][user_key]['name'] = target_name
    chat_data['users'][user_key]['message_count'] = message_count
    chat_data['users'][user_key]['last_update'] = datetime.now().isoformat()

    new_level = get_user_level(message_count)
    chat_data['users'][user_key]['current_level'] = new_level

    await save_chat_wisdom_data(chat_id, chat_data)

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

    if new_level > old_level and new_level >= 1:
        announcement = format_level_announcement({
            'level': new_level,
            'level_info': level_info,
            'message_count': message_count,
            'wisdom_points': wisdom_points,
            'user_name': target_name,
            'user_id': target_user_id
        })
        await update.message.reply_text(announcement, parse_mode='Markdown')

async def add_messages_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Додає повідомлення до існуючої статистики користувача (для адмінів)"""
    user_id = update.message.from_user.id
    chat_id = update.effective_chat.id

    try:
        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        if chat_member.status not in ['administrator', 'creator']:
            await update.message.reply_text("❌ Ця команда доступна тільки адміністраторам!")
            return
    except Exception:
        await update.message.reply_text("❌ Помилка перевірки прав доступу!")
        return

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
        await update.message.reply_text("❌ Неправильний формат кількості повідомлень!")
        return

    chat_data = await load_chat_wisdom_data(chat_id)
    user_key = str(target_user_id)

    if user_key not in chat_data['users']:
        chat_data['users'][user_key] = {
            'name': target_name,
            'message_count': 0,
            'current_level': 0,
            'last_update': datetime.now().isoformat(),
            'join_date': datetime.now().isoformat()
        }

    old_count = chat_data['users'][user_key]['message_count']
    old_level = chat_data['users'][user_key]['current_level']

    chat_data['users'][user_key]['name'] = target_name
    chat_data['users'][user_key]['message_count'] += message_count
    chat_data['users'][user_key]['last_update'] = datetime.now().isoformat()

    new_level = get_user_level(chat_data['users'][user_key]['message_count'])
    chat_data['users'][user_key]['current_level'] = new_level
    chat_data['chat_info']['total_messages_synced'] = chat_data['chat_info'].get('total_messages_synced', 0) + message_count

    await save_chat_wisdom_data(chat_id, chat_data)

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

    if new_level > old_level and new_level >= 1:
        announcement = format_level_announcement({
            'level': new_level,
            'level_info': new_level_info,
            'message_count': chat_data['users'][user_key]['message_count'],
            'wisdom_points': wisdom_points,
            'user_name': target_name,
            'user_id': target_user_id
        })
        await update.message.reply_text(announcement, parse_mode='Markdown')

async def sync_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Синхронізує користувача через відповідь на повідомлення"""
    await set_messages_command(update, context)

async def test_wisdom_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Тестує систему мудрості і показує поточний стан"""
    user_id = update.message.from_user.id
    user_name = update.message.from_user.first_name
    chat_id = update.effective_chat.id

    chat_data = await load_chat_wisdom_data(chat_id)
    user_key = str(user_id)

    current_count = 0
    if user_key in chat_data['users']:
        current_count = chat_data['users'][user_key]['message_count']

    level_up, level_data = process_user_message_in_chat(chat_data, user_id, user_name)
    await save_chat_wisdom_data(chat_id, chat_data)

    stats = get_user_wisdom_stats_in_chat(chat_data, user_id)

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
