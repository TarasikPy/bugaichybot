import re
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from storage.analytics_db import (
    get_today_top_users,
    get_user_live_stats,
    get_user_history_profile,
    get_history_summary,
    load_history_analytics,
    record_live_reaction
)
from storage.user_cache import get_user_info_by_username
from storage.json_db import load_chat_relationships
from utils.helpers import create_user_link, get_relationship_level, escape_html
from config.levels import RELATIONSHIP_LEVELS
from config.names import USERS_MAP

logger = logging.getLogger(__name__)

def build_profile_keyboard(user_id: int, active_tab: str = "main") -> InlineKeyboardMarkup:
    """Генерує інлайн-клавіатуру з вкладками профілю"""
    buttons = [
        [
            InlineKeyboardButton("🏠 Огляд" if active_tab != "main" else "🏠 • Огляд •", callback_data=f"prof_main_{user_id}"),
            InlineKeyboardButton("🎭 Роль & Стиль" if active_tab != "role" else "🎭 • Роль & Стиль •", callback_data=f"prof_role_{user_id}")
        ],
        [
            InlineKeyboardButton("🧠 Психоаналіз" if active_tab != "char" else "🧠 • Психоаналіз •", callback_data=f"prof_char_{user_id}"),
            InlineKeyboardButton("💡 Справжні теми" if active_tab != "topics" else "💡 • Справжні теми •", callback_data=f"prof_topics_{user_id}")
        ],
        [
            InlineKeyboardButton("🗣 Сленг" if active_tab != "slang" else "🗣 • Сленг •", callback_data=f"prof_slang_{user_id}"),
            InlineKeyboardButton("🎯 Коронний підкол" if active_tab != "roast" else "🎯 • Коронний підкол •", callback_data=f"prof_roast_{user_id}")
        ],
        [
            InlineKeyboardButton("📖 Повний портрет" if active_tab != "full" else "📖 • Повний портрет •", callback_data=f"prof_full_{user_id}"),
            InlineKeyboardButton("📊 Статистика" if active_tab != "stats" else "📊 • Статистика •", callback_data=f"prof_stats_{user_id}")
        ]
    ]
    return InlineKeyboardMarkup(buttons)

def render_profile_tab(user_id: int, target_name: str, target_username: str, tab: str, live_stats: dict, ai_profile: dict = None) -> str:
    """Рендерить HTML-текст профілю для обраної вкладки"""
    user_link = create_user_link(user_id, target_name)
    
    if not ai_profile:
        ai_profile = get_user_history_profile(user_id, target_username) or {}

    role = ai_profile.get('role', 'Учасник чату')
    style = ai_profile.get('style', '')
    character = ai_profile.get('character', '')
    topics = ai_profile.get('topics', '')
    slang = ai_profile.get('slang', '')
    roast = ai_profile.get('roast', '')
    intro = ai_profile.get('intro', '')
    full_text = ai_profile.get('full_text', '')

    if tab == "role":
        text = f"🎭 <b>РОЛЬ ТА СТИЛЬ СПІЛКУВАННЯ</b>\n\n"
        text += f"👤 <b>Користувач:</b> {user_link}\n\n"
        text += f"🎭 <b>Роль у чаті:</b>\n<code>{escape_html(role)}</code>\n\n"
        if style:
            text += f"📊 <b>Стиль спілкування:</b>\n<i>{escape_html(style)}</i>\n"
        return text

    elif tab == "char":
        text = f"🧠 <b>ПСИХОЛОГІЧНИЙ ПОРТРЕТ (ПСИХОАНАЛІЗ)</b>\n\n"
        text += f"👤 <b>Користувач:</b> {user_link}\n\n"
        if character:
            text += f"<i>{escape_html(character)}</i>\n"
        else:
            text += "<i>Немає детального психоаналізу в базі.</i>\n"
        return text

    elif tab == "topics":
        text = f"💡 <b>СПРАВЖНІ ТЕМИ ТА ІНТЕРЕСИ</b>\n\n"
        text += f"👤 <b>Користувач:</b> {user_link}\n\n"
        if topics:
            if isinstance(topics, list):
                topics_str = "\n• " + "\n• ".join([escape_html(str(t)) for t in topics])
            else:
                topics_str = escape_html(str(topics))
            text += f"<i>{topics_str}</i>\n"
        else:
            text += "<i>Теми не зафіксовано.</i>\n"
        return text

    elif tab == "slang":
        text = f"🗣 <b>УЛЮБЛЕНИЙ СЛЕНГ ТА МАРКЕРИ</b>\n\n"
        text += f"👤 <b>Користувач:</b> {user_link}\n\n"
        if slang:
            if isinstance(slang, list):
                slang_str = ", ".join([escape_html(str(s)) for s in slang])
            else:
                slang_str = escape_html(str(slang))
            text += f"<i>{slang_str}</i>\n"
        else:
            text += "<i>Сленг не зафіксовано.</i>\n"
        return text

    elif tab == "roast":
        text = f"🎯 <b>КОРОННИЙ ПІДКОЛ / РЕЗЮМЕ</b>\n\n"
        text += f"👤 <b>Користувач:</b> {user_link}\n\n"
        if roast:
            text += f"<i>{escape_html(roast)}</i>\n"
        else:
            text += "<i>Підкол відсутній.</i>\n"
        return text

    elif tab == "full":
        text = f"📖 <b>ПОВНИЙ ПСИХОЛОГІЧНИЙ ПОРТРЕТ</b>\n\n"
        text += f"👤 <b>Користувач:</b> {user_link}\n\n"
        if full_text:
            clean_full = escape_html(full_text)
            text += f"<blockquote expandable>{clean_full}</blockquote>\n"
        else:
            text += "<i>Повний текст портрета відсутній.</i>\n"
        return text

    elif tab == "stats":
        text = f"📊 <b>ЖИВА СТАТИСТИКА АКТИВНОСТІ ЗА СЬОГОДНІ</b>\n\n"
        text += f"👤 <b>Користувач:</b> {user_link}\n\n"
        if live_stats:
            msgs = live_stats.get('messages', 0)
            chars = live_stats.get('chars', 0)
            words = live_stats.get('words', 0)
            last_act = live_stats.get('last_active', '—')
            rx_given = live_stats.get('reactions_given', 0)

            text += f" • <b>Повідомлень:</b> {msgs:,}\n"
            text += f" • <b>Символів:</b> {chars:,}\n"
            text += f" • <b>Слів:</b> {words:,}\n"
            text += f" • <b>Реакцій поставлено:</b> {rx_given}\n"
            text += f" • <b>Останній актив:</b> {last_act}\n"
        else:
            text += "<i>Сьогодні повідомлень ще не зафіксовано.</i>\n"
        return text

    # Головна вкладка ("main")
    card_text = f"🎴 <b>ПСИХОЛОГІЧНИЙ ПРОФІЛЬ ТА СТАТИСТИКА</b>\n\n"
    card_text += f"👤 <b>Користувач:</b> {user_link}\n\n"

    if ai_profile:
        card_text += f"🎭 <b>Роль у чаті:</b> <code>{escape_html(role)}</code>\n\n"
        if intro:
            card_text += f"📝 <i>{escape_html(intro)}</i>\n\n"
        if roast:
            card_text += f"🎯 <b>Коронний підкол:</b> <i>{escape_html(roast)}</i>\n"
    else:
        card_text += "🎭 <b>Роль у чаті:</b> <code>Учасник чату</code>\n"

    card_text += "\n📊 <b>Активність за сьогодні:</b>\n"
    if live_stats:
        msgs = live_stats.get('messages', 0)
        chars = live_stats.get('chars', 0)
        card_text += f" • <b>Повідомлень:</b> {msgs:,} | <b>Символів:</b> {chars:,}\n"
    else:
        card_text += " <i>Сьогодні активність відсутня.</i>\n"

    card_text += "\n👇 <i>Натискайте кнопки нижче для перегляду розділів:</i>"
    return card_text

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Формує красиву картку користувача з вкладинками та повним портретом з chat_analytics.json"""
    if not update.message:
        return

    from utils.helpers import resolve_target_user_info
    target_user_id, target_name, target_username = await resolve_target_user_info(update)

    if not target_user_id:
        await update.message.reply_text("❌ Не вдалося визначити користувача для відображення профілю.", parse_mode='HTML')
        return

    ai_profile = get_user_history_profile(target_user_id, target_username)
    live_stats = await get_user_live_stats(target_user_id)

    card_text = render_profile_tab(target_user_id, target_name, target_username, "main", live_stats, ai_profile)
    keyboard = build_profile_keyboard(target_user_id, active_tab="main")

    await update.message.reply_text(card_text, parse_mode='HTML', reply_markup=keyboard)

async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /id або !ід — виводить Telegram ID користувача, юзернейм, роль та стосунки"""
    from utils.helpers import resolve_target_user_info, create_user_link, resolve_user_name_by_id_or_name
    from storage.json_db import load_chat_relationships

    if not update.message:
        return

    target_user_id, target_name, target_username = await resolve_target_user_info(update)

    if not target_user_id:
        await update.message.reply_text("❌ Не вдалося визначити користувача. Вкажіть @username або зробіть reply.", parse_mode='HTML')
        return

    user_link = create_user_link(target_user_id, target_name)
    username_str = f"@{target_username}" if target_username else "немає"

    ai_profile = get_user_history_profile(target_user_id, target_username) or {}
    role = ai_profile.get('role', 'Учасник чату')

    live_stats = await get_user_live_stats(target_user_id) or {}
    msgs = live_stats.get('messages', 0)
    chars = live_stats.get('chars', 0)

    # Стосунки користувача
    chat_id = update.effective_chat.id
    chat_data = await load_chat_relationships(chat_id)
    relationships = chat_data.get('relationships', {})
    rel_status = "не перебуває у стосунках"

    for couple_id, data in relationships.items():
        u1 = data.get('user1_id')
        u2 = data.get('user2_id')
        if target_user_id in (u1, u2):
            p_id = u2 if target_user_id == u1 else u1
            p_raw_name = data.get('user2_name') if target_user_id == u1 else data.get('user1_name')
            p_name = resolve_user_name_by_id_or_name(p_id, p_raw_name)
            p_link = create_user_link(p_id, p_name)
            st = "💒 одружений(а) з" if data.get('status') == 'married' else "💕 у стосунках з"
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

    await update.message.reply_text(card_text, parse_mode='HTML')

async def handle_profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробляє натискання інлайн-кнопок у картці профілю"""
    query = update.callback_query
    if not query:
        return
    await query.answer()

    data = query.data or ""
    parts = data.split("_")
    if len(parts) < 3 or parts[0] != "prof":
        return

    tab = parts[1]
    try:
        target_user_id = int(parts[2])
    except ValueError:
        return

    ai_profile = get_user_history_profile(target_user_id) or {}
    target_name = ai_profile.get('name') or f"User_{target_user_id}"
    target_username = ai_profile.get('username', '')

    live_stats = await get_user_live_stats(target_user_id)

    card_text = render_profile_tab(target_user_id, target_name, target_username, tab, live_stats, ai_profile)
    keyboard = build_profile_keyboard(target_user_id, active_tab=tab)

    try:
        await query.edit_message_text(card_text, parse_mode='HTML', reply_markup=keyboard)
    except Exception as e:
        logger.debug(f"Помилка оновлення профілю при натисканні {tab}: {e}")


async def chat_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Виводить загальну статистику та топи чату без персональної інформації викликача"""
    chat_id = update.effective_chat.id
    history_data = get_history_summary()
    today_users = await get_today_top_users(limit=5)

    stats_text = "📊 <b>ГОЛОВНА АНАЛІТИКА ТА ТОПИ ЧАТУ</b>\n\n"

    # 1. 🏆 Топ активності за СЬОГОДНІ (повідомлення та символи)
    stats_text += "🏆 <b>Топ активності за сьогодні:</b>\n"
    if today_users:
        for idx, u_stat in enumerate(today_users, 1):
            uid = u_stat.get('user_id')
            uname = u_stat.get('name') or f"User_{uid}"
            msgs = u_stat.get('messages', 0)
            chars = u_stat.get('chars', 0)
            u_link = create_user_link(uid, uname)
            stats_text += f"{idx}. {u_link} — <b>{msgs}</b> смс ({chars:,} символів)\n"
    else:
        stats_text += "<i>Сьогодні повідомлень ще не було зафіксовано. Напишіть щось!</i>\n"
    stats_text += "\n"

    # 2. 🤝 Найсильніші дуети/пари чату (з графу відповідей Reply Graph)
    duets = history_data.get('duets', [])
    stats_text += "🤝 <b>Найсильніші дуети/пари чату (з графу відповідей Reply Graph):</b>\n"
    if duets:
        for idx, duet in enumerate(duets[:5], 1):
            u1_id = duet.get('user1_id')
            u1_name = duet.get('user1_name') or f"User_{u1_id}"
            u2_id = duet.get('user2_id')
            u2_name = duet.get('user2_name') or f"User_{u2_id}"
            count = duet.get('replies_count', 0)

            link1 = create_user_link(u1_id, u1_name)
            link2 = create_user_link(u2_id, u2_name)
            stats_text += f"{idx}. {link1} 💬 {link2} — <b>{count:,}</b> відповідей\n"
    else:
        stats_text += "<i>Немає даних про дуети.</i>\n"
    stats_text += "\n"

    # 3. 🔤 Топ унікального сленгу та емодзі спільноти
    top_slang = history_data.get('top_slang', [])
    top_emojis = history_data.get('top_emojis', [])
    stats_text += "🔤 <b>Топ унікального сленгу та емодзі спільноти:</b>\n"
    if top_emojis:
        emo_str = " ".join([e.get('emoji', '') for e in top_emojis[:8]])
        stats_text += f" • <b>Топ емодзі:</b> {emo_str}\n"
    if top_slang:
        slang_str = ", ".join([f"<code>{escape_html(s.get('word', ''))}</code>" for s in top_slang[:8]])
        stats_text += f" • <b>Топ сленгу:</b> {slang_str}\n"
    if not top_emojis and not top_slang:
        stats_text += "<i>Немає даних про сленг та емодзі.</i>\n"
    stats_text += "\n"

    # 4. ❤️ Загальний блок активних стосунків у чаті
    chat_data = await load_chat_relationships(chat_id)
    relationships = chat_data.get('relationships', {})
    total_relationships = len(relationships)
    stats_text += f"❤️ <b>Загальний блок активних стосунків у чаті:</b> (всього: {total_relationships})\n"
    if relationships:
        sorted_couples = sorted(
            relationships.values(),
            key=lambda x: x.get('total_points', 0),
            reverse=True
        )[:5]

        for couple in sorted_couples:
            u1_id = couple.get('user1_id')
            u2_id = couple.get('user2_id')
            u1_name = couple.get('user1_name') or "Користувач"
            u2_name = couple.get('user2_name') or "Користувач"
            points = couple.get('total_points', 0)
            level = get_relationship_level(points)
            rank_name = RELATIONSHIP_LEVELS[level]["name"]

            link1 = create_user_link(u1_id, u1_name)
            link2 = create_user_link(u2_id, u2_name)
            stats_text += f"• {link1} ❤️ {link2} — {points} оч. [{rank_name}]\n"
    else:
        stats_text += "<i>Поки немає активних пар у цьому чаті.</i>\n"

    await update.message.reply_text(stats_text, parse_mode='HTML')

async def handle_reaction_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробник реакцій користувачів у чаті"""
    try:
        if not update.message_reaction:
            return

        mr = update.message_reaction
        user = mr.user
        chat = mr.chat

        if not user or user.is_bot or not chat:
            return

        user_name = user.first_name or user.username or f"User_{user.id}"

        # Отримуємо додані реакції
        for rx in mr.new_reaction:
            emoji = getattr(rx, 'emoji', None)
            if emoji:
                await record_live_reaction(chat.id, user.id, user_name, emoji)
    except Exception as e:
        logger.warning(f"Помилка при обробці реакції: {e}")
