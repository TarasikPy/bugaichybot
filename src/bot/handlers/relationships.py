"""Relationship and couple command handlers."""

import re
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from src.core.logger import get_logger
from src.infrastructure.constants.levels import (
    ALL_COUPLE_COMMANDS,
    RELATIONSHIP_LEVELS,
)
from src.infrastructure.constants.names import USERS_MAP
from src.infrastructure.db.repository import (
    get_first_name_by_username,
    load_chat_relationships,
    save_chat_relationships,
)
from src.infrastructure.utils.formatting import create_user_link
from src.services.dating_service import (
    PROPOSAL_NAMES_CACHE,
    build_chat_relationships_overview,
    build_user_relationships_overview,
    get_relationship_level,
)

logger = get_logger(__name__)


async def _send_html_message(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    """Send HTML message with plain-text fallback."""
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="HTML",
            reply_markup=reply_markup,
        )
    except Exception as e:
        logger.warning(f"Failed to send HTML message ({e}), falling back to plain text")
        plain_text = re.sub(r"<[^>]*>", "", text)
        await context.bot.send_message(
            chat_id=chat_id,
            text=plain_text,
            reply_markup=reply_markup,
        )


async def relationships_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show list of all couples in current chat."""
    if not update.effective_chat:
        return
    chat_id = update.effective_chat.id
    overview = await build_chat_relationships_overview(chat_id)
    await _send_html_message(context, chat_id, overview)


async def my_relationships_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show personal relationship card for user."""
    if not update.message or not update.message.from_user or not update.effective_chat:
        return
    user = update.message.from_user
    chat_id = update.effective_chat.id
    overview = await build_user_relationships_overview(chat_id, user.id, user.first_name)
    await _send_html_message(context, chat_id, overview)


async def dating_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Initiate a relationship proposal."""
    await handle_couple_command(update, context, "dating")


async def proposals_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Alias for viewing personal relationships."""
    await my_relationships_command(update, context)


async def trio_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Inform users about trio relationships."""
    if not update.effective_chat:
        return
    await _send_html_message(
        context,
        update.effective_chat.id,
        "👥 Для створення стосунків використовуйте /dating або !пропозиція!",
    )


async def breakup_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Initiate breakup confirmation."""
    if not update.message or not update.message.from_user or not update.effective_chat:
        return

    from_user = update.message.from_user
    chat_id = update.effective_chat.id
    chat_data = await load_chat_relationships(chat_id)
    relationships = chat_data.get("relationships", {})

    target_couple_id = None
    partner_id = None
    partner_name = None
    status = "dating"

    for couple_id, data in relationships.items():
        if from_user.id in (data.get("user1_id"), data.get("user2_id")):
            target_couple_id = couple_id
            status = data.get("status", "dating")
            if from_user.id == data.get("user1_id"):
                partner_id = data.get("user2_id")
                partner_name = data.get("user2_name")
            else:
                partner_id = data.get("user1_id")
                partner_name = data.get("user1_name")
            break

    if not target_couple_id:
        await _send_html_message(
            context, chat_id, "💔 У вас немає активних стосунків у цьому чаті!"
        )
        return

    user_link = create_user_link(from_user.id, from_user.first_name)
    partner_link = create_user_link(partner_id, partner_name or "Партнер")

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "💔 Розірвати",
                    callback_data=f"breakup_confirm:{target_couple_id}:{from_user.id}",
                ),
                InlineKeyboardButton(
                    "↩️ Скасувати",
                    callback_data=f"breakup_cancel:{target_couple_id}:{from_user.id}",
                ),
            ]
        ]
    )

    action_word = "розлучитися з" if status == "married" else "розірвати стосунки з"
    text = f"⚠️ {user_link}, ви впевнені, що хочете {action_word} {partner_link}?"
    await _send_html_message(context, chat_id, text, reply_markup=keyboard)


async def handle_couple_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    command: str,
    target: str | None = None,
) -> None:
    """Handle couple commands and proposals."""
    if not update.message or not update.message.from_user or not update.effective_chat:
        return

    from_user = update.message.from_user
    chat_id = update.effective_chat.id
    chat_data = await load_chat_relationships(chat_id)
    relationships = chat_data.setdefault("relationships", {})

    # 1. /dating or !пропозиція
    if command == "dating":
        target_user_id = None
        target_name = None
        target_username = None

        # Reply
        if update.message.reply_to_message and update.message.reply_to_message.from_user:
            reply_user = update.message.reply_to_message.from_user
            target_user_id = reply_user.id
            target_name = reply_user.first_name
            target_username = reply_user.username

        # Target string or @mention
        elif target or (update.message.text and "@" in update.message.text):
            raw_target = target
            if not raw_target and update.message.text:
                m = re.search(r"@(\S+)", update.message.text)
                if m:
                    raw_target = m.group(1)

            if raw_target:
                raw_target = raw_target.lstrip("@")
                target_username = raw_target

                if raw_target.lower() in USERS_MAP:
                    target_name = USERS_MAP[raw_target.lower()]

                cached_name, cached_id = await get_first_name_by_username(raw_target)
                if cached_name and not target_name:
                    target_name = cached_name
                if cached_id and not target_user_id:
                    target_user_id = cached_id

                if not target_name:
                    target_name = raw_target

        if not target_user_id and not target_name:
            await _send_html_message(
                context,
                chat_id,
                "💫 Вкажіть користувача через @ або дайте відповідь на його повідомлення: <code>/dating @user</code>",
            )
            return

        if target_user_id and target_user_id == from_user.id:
            await _send_html_message(
                context, chat_id, "😅 Не можна створювати стосунки з самим собою!"
            )
            return

        if (
            context.bot.username
            and target_name
            and target_name.lower() == context.bot.username.lower()
        ):
            await _send_html_message(context, chat_id, "🤖 З ботом не можна розпочати стосунки!")
            return

        # Check existing relationships
        for c_data in relationships.values():
            if from_user.id in (c_data.get("user1_id"), c_data.get("user2_id")):
                await _send_html_message(
                    context,
                    chat_id,
                    f"💔 {create_user_link(from_user.id, from_user.first_name)} вже у стосунках!",
                )
                return
            if target_user_id and target_user_id in (
                c_data.get("user1_id"),
                c_data.get("user2_id"),
            ):
                await _send_html_message(
                    context,
                    chat_id,
                    f"💔 {create_user_link(target_user_id, target_name)} вже у стосунках!",
                )
                return

        PROPOSAL_NAMES_CACHE[from_user.id] = from_user.first_name
        target_spec = str(target_user_id) if target_user_id else f"u_{target_username}"

        sender_link = create_user_link(from_user.id, from_user.first_name)
        target_link = create_user_link(target_user_id, target_name)

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "❤️ Прийняти",
                        callback_data=f"rel_accept:{from_user.id}:{target_spec}",
                    ),
                    InlineKeyboardButton(
                        "❌ Відхилити",
                        callback_data=f"rel_decline:{from_user.id}:{target_spec}",
                    ),
                ]
            ]
        )

        proposal_text = f"💌 {sender_link} пропонує {target_link} розпочати стосунки!"
        await _send_html_message(context, chat_id, proposal_text, reply_markup=keyboard)
        return

    # 2. Couple actions (+points)
    active_couple_id = None
    couple_info = None

    for c_id, c_data in relationships.items():
        if from_user.id in (c_data.get("user1_id"), c_data.get("user2_id")):
            active_couple_id = c_id
            couple_info = c_data
            break

    if not couple_info:
        await _send_html_message(
            context,
            chat_id,
            "❌ Ви не перебуваєте в стосунках! Використайте /dating, щоб запропонувати комусь зустрічатися.",
        )
        return

    cmd_info = ALL_COUPLE_COMMANDS.get(
        command, {"action": "провели час разом", "points": 3, "emoji": "💕"}
    )
    points_add = cmd_info.get("points", 3)

    old_points = couple_info.get("total_points", 0)
    new_points = old_points + points_add
    couple_info["total_points"] = new_points

    old_level = get_relationship_level(old_points)
    new_level = get_relationship_level(new_points)

    await save_chat_relationships(chat_id, chat_data)

    p1_link = create_user_link(
        couple_info.get("user1_id"),
        couple_info.get("user1_name", "Партнер 1"),
    )
    p2_link = create_user_link(
        couple_info.get("user2_id"),
        couple_info.get("user2_name", "Партнер 2"),
    )

    msg = f"{cmd_info['emoji']} {p1_link} {cmd_info['action']} {p2_link}! (+{points_add} очок, всього: {new_points})"

    if new_level > old_level:
        level_data = RELATIONSHIP_LEVELS[new_level]
        msg += f"\n\n🎉 <b>Вітаємо! Новий рівень стосунків:</b> {level_data['emoji']} <b>{level_data['name']}</b>!"

    await _send_html_message(context, chat_id, msg)


async def handle_relationship_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button clicks for dating proposals and breakups."""
    query = update.callback_query
    if not query or not query.data or not query.message:
        return

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

        if clicker_id == sender_id:
            await query.answer(
                "Ви не можете відповісти на власну пропозицію!",
                show_alert=True,
            )
            return

        is_target = False
        if target_spec.startswith("u_"):
            target_uname = target_spec[2:].lower()
            is_target = clicker_username == target_uname
        else:
            target_id = int(target_spec)
            is_target = (clicker_id == target_id) if target_id != 0 else True

        if not is_target:
            await query.answer(
                "Ця пропозиція адресована не тобі!",
                show_alert=True,
            )
            return

        await query.answer()
        sender_name = PROPOSAL_NAMES_CACHE.get(sender_id, "Користувач")

        if action_type == "rel_accept":
            chat_data = await load_chat_relationships(chat_id)
            relationships = chat_data.setdefault("relationships", {})

            for c_data in relationships.values():
                if sender_id in (
                    c_data.get("user1_id"),
                    c_data.get("user2_id"),
                ) or clicker_id in (
                    c_data.get("user1_id"),
                    c_data.get("user2_id"),
                ):
                    await query.edit_message_text(
                        "💔 Один із користувачів вже перебуває у стосунках!",
                        parse_mode="HTML",
                    )
                    return

            couple_id = f"{min(sender_id, clicker_id)}_{max(sender_id, clicker_id)}"
            relationships[couple_id] = {
                "user1_id": sender_id,
                "user1_name": sender_name,
                "user2_id": clicker_id,
                "user2_name": clicker.first_name,
                "start_date": datetime.now().isoformat(),
                "total_points": 0,
                "status": "dating",
            }
            await save_chat_relationships(chat_id, chat_data)

            s_link = create_user_link(sender_id, sender_name)
            t_link = create_user_link(clicker_id, clicker.first_name)
            win_text = f"🎉 <b>Вітаємо!</b> {s_link} та {t_link} тепер офіційно у стосунках! 💕"
            await query.edit_message_text(text=win_text, parse_mode="HTML")

        elif action_type == "rel_decline":
            s_link = create_user_link(sender_id, sender_name)
            t_link = create_user_link(clicker_id, clicker.first_name)
            decline_text = f"💔 {t_link} відхилив(ла) пропозицію стосунків від {s_link}."
            await query.edit_message_text(text=decline_text, parse_mode="HTML")

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
        relationships = chat_data.get("relationships", {})
        couple_data = relationships.get(couple_id, {})

        if action_type == "breakup_confirm":
            if couple_id in relationships:
                u1_id = couple_data.get("user1_id")
                u1_name = couple_data.get("user1_name")
                u2_id = couple_data.get("user2_id")
                u2_name = couple_data.get("user2_name")

                del relationships[couple_id]
                await save_chat_relationships(chat_id, chat_data)

                u1_link = create_user_link(u1_id, u1_name)
                u2_link = create_user_link(u2_id, u2_name)
                done_text = f"💔 Стосунки між {u1_link} та {u2_link} успішно розірвано."
            else:
                done_text = "💔 Стосунки вже були розірвані."

            await query.edit_message_text(text=done_text, parse_mode="HTML")

        elif action_type == "breakup_cancel":
            cancel_text = "✨ Розірвання стосунків скасовано."
            await query.edit_message_text(text=cancel_text, parse_mode="HTML")
