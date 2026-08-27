"""Analytics, profiles, and statistics command handlers."""

from telegram import Update
from telegram.ext import ContextTypes

from src.core.logger import get_logger
from src.infrastructure.constants.levels import RELATIONSHIP_LEVELS
from src.infrastructure.db.repository import (
    load_chat_relationships,
)
from src.infrastructure.utils.formatting import create_user_link, escape_html
from src.services.dating_service import get_relationship_level
from src.services.user_profiler import (
    build_profile_keyboard,
    get_history_summary,
    get_today_top_users,
    get_user_history_profile,
    get_user_live_stats,
    record_live_reaction,
    render_profile_tab,
    resolve_target_user_info,
    resolve_user_name_by_id_or_name,
)

logger = get_logger(__name__)


async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show interactive psychological profile card with tabbed navigation."""
    if not update.message:
        return

    target_user_id, target_name, target_username = await resolve_target_user_info(update)

    if not target_user_id:
        await update.message.reply_text(
            "❌ Не вдалося визначити користувача для відображення профілю.",
            parse_mode="HTML",
        )
        return

    ai_profile = get_user_history_profile(target_user_id, target_username)
    live_stats = await get_user_live_stats(target_user_id)

    card_text = render_profile_tab(
        target_user_id,
        target_name,
        target_username,
        "main",
        live_stats,
        ai_profile,
    )
    keyboard = build_profile_keyboard(target_user_id, active_tab="main")

    await update.message.reply_text(card_text, parse_mode="HTML", reply_markup=keyboard)


async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display user ID, role, active relationship, and daily stats."""
    if not update.message or not update.effective_chat:
        return

    target_user_id, target_name, target_username = await resolve_target_user_info(update)

    if not target_user_id:
        await update.message.reply_text(
            "❌ Не вдалося визначити користувача. Вкажіть @username або зробіть reply.",
            parse_mode="HTML",
        )
        return

    user_link = create_user_link(target_user_id, target_name)
    username_str = f"@{target_username}" if target_username else "немає"

    ai_profile = get_user_history_profile(target_user_id, target_username) or {}
    role = ai_profile.get("role", "Учасник чату")

    live_stats = await get_user_live_stats(target_user_id) or {}
    msgs = live_stats.get("messages", 0)
    chars = live_stats.get("chars", 0)

    # Lookup user's relationship
    chat_id = update.effective_chat.id
    chat_data = await load_chat_relationships(chat_id)
    relationships = chat_data.get("relationships", {})
    rel_status = "не перебуває у стосунках"

    for _couple_id, data in relationships.items():
        u1 = data.get("user1_id")
        u2 = data.get("user2_id")
        if target_user_id in (u1, u2):
            p_id = u2 if target_user_id == u1 else u1
            p_raw_name = data.get("user2_name") if target_user_id == u1 else data.get("user1_name")
            p_name = resolve_user_name_by_id_or_name(p_id, p_raw_name)
            p_link = create_user_link(p_id, p_name)
            st = "💒 одружений(а) з" if data.get("status") == "married" else "💕 у стосунках з"
            rel_status = f"{st} {p_link}"
            break

    card_text = (
        f"🪪 <b>ІНФОРМАЦІЯ ПРО КОРИСТУВАЧА:</b>\n\n"
        f"🆔 <b>Telegram ID:</b> <code>{target_user_id}</code>\n"
        f"👤 <b>Користувач:</b> {user_link} ({username_str})\n"
        f"🎭 <b>Роль у чаті:</b> <code>{escape_html(role)}</code>\n"
        f"📊 <b>Актив за сьогодні:</b> {msgs} смс ({chars:,} символів)\n"
        f"💕 <b>Стосунки:</b> {rel_status}"
    )

    await update.message.reply_text(card_text, parse_mode="HTML")


async def handle_profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle interactive tab switches on user profile card."""
    query = update.callback_query
    if not query or not query.data:
        return
    await query.answer()

    parts = query.data.split("_")
    if len(parts) < 3 or parts[0] != "prof":
        return

    tab = parts[1]
    try:
        target_user_id = int(parts[2])
    except ValueError:
        return

    ai_profile = get_user_history_profile(target_user_id) or {}
    target_name = ai_profile.get("name") or f"User_{target_user_id}"
    target_username = ai_profile.get("username", "")

    live_stats = await get_user_live_stats(target_user_id)

    card_text = render_profile_tab(
        target_user_id,
        target_name,
        target_username,
        tab,
        live_stats,
        ai_profile,
    )
    keyboard = build_profile_keyboard(target_user_id, active_tab=tab)

    try:
        await query.edit_message_text(card_text, parse_mode="HTML", reply_markup=keyboard)
    except Exception as e:
        logger.debug(f"Profile tab switch error ({tab}): {e}")


async def chat_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display aggregated chat activity and community rankings."""
    if not update.effective_chat or not update.message:
        return

    chat_id = update.effective_chat.id
    history_data = get_history_summary()
    today_users = await get_today_top_users(limit=5)

    stats_text = "📊 <b>ГОЛОВНА АНАЛІТИКА ТА ТОПИ ЧАТУ</b>\n\n"

    # 1. Top active users for today
    stats_text += "🏆 <b>Топ активності за сьогодні:</b>\n"
    if today_users:
        for idx, u_stat in enumerate(today_users, 1):
            uid = u_stat.get("user_id")
            uname = u_stat.get("name") or f"User_{uid}"
            msgs = u_stat.get("messages", 0)
            chars = u_stat.get("chars", 0)
            u_link = create_user_link(uid, uname)
            stats_text += f"{idx}. {u_link} — <b>{msgs}</b> смс ({chars:,} символів)\n"
    else:
        stats_text += "<i>Сьогодні повідомлень ще не було зафіксовано. Напишіть щось!</i>\n"
    stats_text += "\n"

    # 2. Reply graph duets
    duets = history_data.get("duets", [])
    stats_text += "🤝 <b>Найсильніші дуети/пари чату (з графу відповідей Reply Graph):</b>\n"
    if duets:
        for idx, duet in enumerate(duets[:5], 1):
            u1_id = duet.get("user1_id")
            u1_name = duet.get("user1_name") or f"User_{u1_id}"
            u2_id = duet.get("user2_id")
            u2_name = duet.get("user2_name") or f"User_{u2_id}"
            count = duet.get("replies_count", 0)

            link1 = create_user_link(u1_id, u1_name)
            link2 = create_user_link(u2_id, u2_name)
            stats_text += f"{idx}. {link1} 💬 {link2} — <b>{count:,}</b> відповідей\n"
    else:
        stats_text += "<i>Немає даних про дуети.</i>\n"
    stats_text += "\n"

    # 3. Slang and Emojis
    top_slang = history_data.get("top_slang", [])
    top_emojis = history_data.get("top_emojis", [])
    stats_text += "🔤 <b>Топ унікального сленгу та емодзі спільноти:</b>\n"
    if top_emojis:
        emo_str = " ".join([e.get("emoji", "") for e in top_emojis[:8]])
        stats_text += f" • <b>Топ емодзі:</b> {emo_str}\n"
    if top_slang:
        slang_str = ", ".join(
            [f"<code>{escape_html(s.get('word', ''))}</code>" for s in top_slang[:8]]
        )
        stats_text += f" • <b>Топ сленгу:</b> {slang_str}\n"
    if not top_emojis and not top_slang:
        stats_text += "<i>Немає даних про сленг та емодзі.</i>\n"
    stats_text += "\n"

    # 4. Active relationships
    chat_data = await load_chat_relationships(chat_id)
    relationships = chat_data.get("relationships", {})
    total_relationships = len(relationships)
    stats_text += (
        f"❤️ <b>Загальний блок активних стосунків у чаті:</b> (всього: {total_relationships})\n"
    )
    if relationships:
        sorted_couples = sorted(
            relationships.values(),
            key=lambda x: x.get("total_points", 0),
            reverse=True,
        )[:5]

        for couple in sorted_couples:
            u1_id = couple.get("user1_id")
            u2_id = couple.get("user2_id")
            u1_name = couple.get("user1_name") or "Користувач"
            u2_name = couple.get("user2_name") or "Користувач"
            points = couple.get("total_points", 0)
            level = get_relationship_level(points)
            rank_name = RELATIONSHIP_LEVELS[level]["name"]

            link1 = create_user_link(u1_id, u1_name)
            link2 = create_user_link(u2_id, u2_name)
            stats_text += f"• {link1} ❤️ {link2} — {points} оч. [{rank_name}]\n"
    else:
        stats_text += "<i>Поки немає активних пар у цьому чаті.</i>\n"

    await update.message.reply_text(stats_text, parse_mode="HTML")


async def handle_reaction_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Track user reaction interactions."""
    try:
        if not update.message_reaction:
            return

        mr = update.message_reaction
        user = mr.user
        chat = mr.chat

        if not user or user.is_bot or not chat:
            return

        user_name = user.first_name or user.username or f"User_{user.id}"

        for rx in mr.new_reaction:
            emoji = getattr(rx, "emoji", None)
            if emoji:
                await record_live_reaction(chat.id, user.id, user_name, emoji)
    except Exception as e:
        logger.warning(f"Error handling message reaction: {e}")
