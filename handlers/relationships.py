import re
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config.levels import RELATIONSHIP_LEVELS, ALL_COUPLE_COMMANDS
from config.names import USERS_MAP
from utils.helpers import (
    decline_name,
    get_relationship_level,
    format_duration,
    create_user_link,
    escape_html
)
from storage.json_db import load_chat_relationships, save_chat_relationships
from storage.user_cache import get_user_info_by_username, update_user_cache

logger = logging.getLogger(__name__)

# Тимчасовий кеш для імен відправників пропозицій
PROPOSAL_NAMES_CACHE = {}

async def _send_html_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str, reply_markup=None) -> None:
    """Відправляє повідомлення у чат у форматі HTML"""
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.warning(f"Помилка відправки HTML у стосунках: {e}")
        plain_text = re.sub(r'<[^>]*>', '', text)
        await context.bot.send_message(
            chat_id=chat_id,
            text=plain_text,
            reply_markup=reply_markup
        )

async def relationships_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показує всі активні стосунки в поточному чаті з клікабельними посиланнями"""
    chat_id = update.effective_chat.id
    chat_data = await load_chat_relationships(chat_id)
    relationships = chat_data.get('relationships', {})

    if not relationships:
        await _send_html_message(context, chat_id, "💔 Поки що немає активних стосунків у цьому чаті!")
        return

    text = "💕 <b>Активні стосунки в цьому чаті:</b>\n\n"
    for couple_id, data in relationships.items():
        user1_id = data.get('user1_id')
        user2_id = data.get('user2_id')
        user1_name = data.get('user1_name') or "Користувач"
        user2_name = data.get('user2_name') or "Користувач"

        duration = format_duration(data.get('start_date', datetime.now().isoformat()))
        total_points = data.get('total_points', 0)
        level = get_relationship_level(total_points)
        level_info = RELATIONSHIP_LEVELS[level]
        status = data.get('status', 'dating')

        status_emoji = "💒" if status == 'married' else "💕"
        link1 = create_user_link(user1_id, user1_name)
        link2 = create_user_link(user2_id, user2_name)

        text += f"{status_emoji} {link1} ❤️ {link2}\n"
        text += f"📊 <b>Рівень:</b> {level_info['emoji']} {level_info['name']}\n"
        text += f"⚡ <b>Очки:</b> {total_points}\n"
        text += f"📅 <b>Тривалість:</b> {duration}\n\n"

    await _send_html_message(context, chat_id, text)

async def my_relationships_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показує власні стосунки користувача"""
    user = update.message.from_user
    user_id = user.id
    user_name = user.first_name
    chat_id = update.effective_chat.id
    chat_data = await load_chat_relationships(chat_id)
    relationships = chat_data.get('relationships', {})

    user_relationships = []
    for couple_id, data in relationships.items():
        u1_id = data.get('user1_id')
        u2_id = data.get('user2_id')

        if user_id in (u1_id, u2_id):
            partner_id = u2_id if user_id == u1_id else u1_id
            partner_name = data.get('user2_name') if user_id == u1_id else data.get('user1_name')

            duration = format_duration(data.get('start_date', datetime.now().isoformat()))
            total_points = data.get('total_points', 0)
            level = get_relationship_level(total_points)
            level_info = RELATIONSHIP_LEVELS[level]
            status = data.get('status', 'dating')

            status_text = "💒 Одружені" if status == 'married' else "💕 У стосунках"
            partner_link = create_user_link(partner_id, partner_name or "Партнер")

            user_relationships.append(
                f"{status_text}\n"
                f"❤️ <b>Партнер:</b> {partner_link}\n"
                f"📊 <b>Рівень:</b> {level_info['emoji']} {level_info['name']}\n"
                f"⚡ <b>Очки:</b> {total_points}\n"
                f"📝 {level_info['description']}\n"
                f"📅 <b>Тривалість:</b> {duration}"
            )

    user_link = create_user_link(user_id, user_name)
    if not user_relationships:
        text = f"💔 У вас, {user_link}, поки немає активних стосунків у цьому чаті!"
    else:
        text = f"💕 <b>Ваші стосунки, {user_link}:</b>\n\n" + "\n\n".join(user_relationships)

    await _send_html_message(context, chat_id, text)

async def dating_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обгортка для створення пропозиції стосунків з інлайн кнопками"""
    await handle_couple_command(update, context, 'dating')

async def proposals_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обгортка для перегляду стосунків"""
    await my_relationships_command(update, context)

async def trio_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обгортка для створення стосунків на 3"""
    await _send_html_message(context, update.effective_chat.id, "👥 Для створення стосунків використовуйте /dating або !пропозиція!")

async def breakup_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда для розірвання стосунків з підтвердженням "Ви впевнені?" """
    from_user = update.message.from_user
    chat_id = update.effective_chat.id
    chat_data = await load_chat_relationships(chat_id)
    relationships = chat_data.get('relationships', {})

    target_couple_id = None
    partner_id = None
    partner_name = None
    status = 'dating'

    for couple_id, data in relationships.items():
        if from_user.id in (data.get('user1_id'), data.get('user2_id')):
            target_couple_id = couple_id
            status = data.get('status', 'dating')
            if from_user.id == data.get('user1_id'):
                partner_id = data.get('user2_id')
                partner_name = data.get('user2_name')
            else:
                partner_id = data.get('user1_id')
                partner_name = data.get('user1_name')
            break

    if not target_couple_id:
        await _send_html_message(context, chat_id, "💔 У вас немає активних стосунків у цьому чаті!")
        return

    user_link = create_user_link(from_user.id, from_user.first_name)
    partner_link = create_user_link(partner_id, partner_name or "Партнер")

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💔 Розірвати", callback_data=f"breakup_confirm:{target_couple_id}:{from_user.id}"),
            InlineKeyboardButton("↩️ Скасувати", callback_data=f"breakup_cancel:{target_couple_id}:{from_user.id}")
        ]
    ])

    action_word = "розлучитися з" if status == 'married' else "розірвати стосунки з"
    text = f"⚠️ {user_link}, ви впевнені, що хочете {action_word} {partner_link}?"
    await _send_html_message(context, chat_id, text, reply_markup=keyboard)

async def handle_couple_command(update: Update, context: ContextTypes.DEFAULT_TYPE, command: str, target: str = None) -> None:
    """Обробка команд для пар: /dating з пропозицією та інлайн-кнопками, або парних дій (+очки)"""
    from_user = update.message.from_user
    chat_id = update.effective_chat.id
    chat_data = await load_chat_relationships(chat_id)
    relationships = chat_data.setdefault('relationships', {})

    # 1. ОБРОБКА КОМАНДИ /dating або !пропозиція (ПРОПОЗИЦІЯ СТОСУНКІВ)
    if command == 'dating':
        target_user_id = None
        target_name = None
        target_username = None

        # а) З відповіді (reply)
        if update.message.reply_to_message and update.message.reply_to_message.from_user:
            reply_user = update.message.reply_to_message.from_user
            target_user_id = reply_user.id
            target_name = reply_user.first_name
            target_username = reply_user.username

        # б) Зі згадки або з параметра target
        elif target or '@' in update.message.text:
            raw_target = target or re.search(r'@(\S+)', update.message.text).group(1)
            raw_target = raw_target.lstrip('@')
            target_username = raw_target

            if raw_target.lower() in USERS_MAP:
                target_name = USERS_MAP[raw_target.lower()]

            cached_name, cached_id = await get_user_info_by_username(raw_target)
            if cached_name and not target_name:
                target_name = cached_name
            if cached_id and not target_user_id:
                target_user_id = cached_id

            if not target_name:
                target_name = raw_target

        if not target_user_id and not target_name:
            await _send_html_message(context, chat_id, "💫 Вкажіть користувача через @ або дайте відповідь на його повідомлення: <code>/dating @user</code>")
            return

        # Перевірки
        if target_user_id and target_user_id == from_user.id:
            await _send_html_message(context, chat_id, "😅 Не можна створювати стосунки з самим собою!")
            return

        if context.bot.username and target_name and target_name.lower() == context.bot.username.lower():
            await _send_html_message(context, chat_id, "🤖 З ботом не можна розпочати стосунки!")
            return

        # Перевірка чи вже хтось у стосунках
        for c_id, c_data in relationships.items():
            if from_user.id in (c_data.get('user1_id'), c_data.get('user2_id')):
                await _send_html_message(context, chat_id, f"💔 {create_user_link(from_user.id, from_user.first_name)} вже у стосунках!")
                return
            if target_user_id and target_user_id in (c_data.get('user1_id'), c_data.get('user2_id')):
                await _send_html_message(context, chat_id, f"💔 {create_user_link(target_user_id, target_name)} вже у стосунках!")
                return

        # Зберігаємо ім'я відправника у локальний кеш пропозицій
        PROPOSAL_NAMES_CACHE[from_user.id] = from_user.first_name

        # Формуємо специфікатор цільового юзера (ID або юзернейм)
        target_spec = str(target_user_id) if target_user_id else f"u_{target_username}"

        sender_link = create_user_link(from_user.id, from_user.first_name)
        target_link = create_user_link(target_user_id, target_name)

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("❤️ Прийняти", callback_data=f"rel_accept:{from_user.id}:{target_spec}"),
                InlineKeyboardButton("❌ Відхилити", callback_data=f"rel_decline:{from_user.id}:{target_spec}")
            ]
        ])

        proposal_text = f"💌 {sender_link} пропонує {target_link} розпочати стосунки!"
        await _send_html_message(context, chat_id, proposal_text, reply_markup=keyboard)
        return

    # 2. ОБРОБКА ДІЙ У ПАРАХ (+ОЧКИ)
    active_couple_id = None
    couple_info = None

    for c_id, c_data in relationships.items():
        if from_user.id in (c_data.get('user1_id'), c_data.get('user2_id')):
            active_couple_id = c_id
            couple_info = c_data
            break

    if not couple_info:
        await _send_html_message(context, chat_id, "💔 Цю команду можна виконувати тільки перебуваючи у стосунках! Використайте <code>/dating</code>")
        return

    cmd_info = ALL_COUPLE_COMMANDS.get(command, {'action': 'провели час разом', 'points': 3, 'emoji': '💕'})
    points_add = cmd_info.get('points', 3)

    old_points = couple_info.get('total_points', 0)
    new_points = old_points + points_add
    couple_info['total_points'] = new_points

    old_level = get_relationship_level(old_points)
    new_level = get_relationship_level(new_points)

    await save_chat_relationships(chat_id, chat_data)

    p1_link = create_user_link(couple_info.get('user1_id'), couple_info.get('user1_name', 'Партнер 1'))
    p2_link = create_user_link(couple_info.get('user2_id'), couple_info.get('user2_name', 'Партнер 2'))

    msg = f"{cmd_info['emoji']} {p1_link} {cmd_info['action']} {p2_link}! (+{points_add} очок, всього: {new_points})"

    if new_level > old_level:
        level_data = RELATIONSHIP_LEVELS[new_level]
        msg += f"\n\n🎉 <b>Вітаємо! Новий рівень стосунків:</b> {level_data['emoji']} <b>{level_data['name']}</b>!"

    await _send_html_message(context, chat_id, msg)

async def handle_relationship_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробник інлайн кнопок для пропозицій стосунків та підтвердження розірвання"""
    query = update.callback_query
    data = query.data
    chat_id = query.message.chat.id
    clicker = query.from_user
    clicker_id = clicker.id
    clicker_username = (clicker.username or "").lower()

    if data.startswith("rel_accept:") or data.startswith("rel_decline:"):
        parts = data.split(":")
        action_type = parts[0]
        sender_id = int(parts[1])
        target_spec = parts[2]

        # Захист від прийняття власної пропозиції
        if clicker_id == sender_id:
            await query.answer("Ви не можете відповісти на власну пропозицію!", show_alert=True)
            return

        # Перевірка чи натискає адресат
        is_target = False
        if target_spec.startswith("u_"):
            target_uname = target_spec[2:].lower()
            is_target = (clicker_username == target_uname)
        else:
            target_id = int(target_spec)
            is_target = (clicker_id == target_id) if target_id != 0 else True

        if not is_target:
            await query.answer("Ця пропозиція адресована не тобі!", show_alert=True)
            return

        await query.answer()

        sender_name = PROPOSAL_NAMES_CACHE.get(sender_id, "Користувач")

        if action_type == "rel_accept":
            chat_data = await load_chat_relationships(chat_id)
            relationships = chat_data.setdefault('relationships', {})

            # Повторна перевірка чи користувачі ще не у стосунках
            for c_id, c_data in relationships.items():
                if sender_id in (c_data.get('user1_id'), c_data.get('user2_id')) or clicker_id in (c_data.get('user1_id'), c_data.get('user2_id')):
                    await query.edit_message_text("💔 Один із користувачів вже перебуває у стосунках!", parse_mode='HTML')
                    return

            couple_id = f"{min(sender_id, clicker_id)}_{max(sender_id, clicker_id)}"
            relationships[couple_id] = {
                'user1_id': sender_id,
                'user1_name': sender_name,
                'user2_id': clicker_id,
                'user2_name': clicker.first_name,
                'start_date': datetime.now().isoformat(),
                'total_points': 0,
                'status': 'dating'
            }
            await save_chat_relationships(chat_id, chat_data)

            s_link = create_user_link(sender_id, sender_name)
            t_link = create_user_link(clicker_id, clicker.first_name)
            win_text = f"🎉 <b>Вітаємо!</b> {s_link} та {t_link} тепер офіційно у стосунках! 💕"
            await query.edit_message_text(text=win_text, parse_mode='HTML')

        elif action_type == "rel_decline":
            s_link = create_user_link(sender_id, sender_name)
            t_link = create_user_link(clicker_id, clicker.first_name)
            decline_text = f"💔 {t_link} відхилив(ла) пропозицію стосунків від {s_link}."
            await query.edit_message_text(text=decline_text, parse_mode='HTML')

    elif data.startswith("breakup_confirm:") or data.startswith("breakup_cancel:"):
        parts = data.split(":")
        action_type = parts[0]
        couple_id = parts[1]
        user_id = int(parts[2])

        if clicker_id != user_id:
            await query.answer("Ця дія стосується не тебе!", show_alert=True)
            return

        await query.answer()

        chat_data = await load_chat_relationships(chat_id)
        relationships = chat_data.get('relationships', {})
        couple_data = relationships.get(couple_id, {})

        if action_type == "breakup_confirm":
            if couple_id in relationships:
                u1_id = couple_data.get('user1_id')
                u1_name = couple_data.get('user1_name')
                u2_id = couple_data.get('user2_id')
                u2_name = couple_data.get('user2_name')

                del relationships[couple_id]
                await save_chat_relationships(chat_id, chat_data)

                u1_link = create_user_link(u1_id, u1_name)
                u2_link = create_user_link(u2_id, u2_name)
                done_text = f"💔 Стосунки між {u1_link} та {u2_link} успішно розірвано."
            else:
                done_text = "💔 Стосунки вже були розірвані."

            await query.edit_message_text(text=done_text, parse_mode='HTML')

        elif action_type == "breakup_cancel":
            cancel_text = f"✨ Розірвання стосунків скасовано."
            await query.edit_message_text(text=cancel_text, parse_mode='HTML')
