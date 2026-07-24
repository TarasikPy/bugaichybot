import re
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes

from storage.analytics_db import (
    get_today_top_users,
    get_user_live_stats,
    get_user_history_profile,
    get_history_summary,
    record_live_reaction
)
from storage.user_cache import get_user_info_by_username
from storage.json_db import load_chat_relationships
from utils.helpers import create_user_link, get_relationship_level, escape_html
from config.levels import RELATIONSHIP_LEVELS
from config.names import USERS_MAP

logger = logging.getLogger(__name__)

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Формує красиву картку користувача зі збереженим AI-портретом з chat_analytics.json + додає живу статистику за сьогодні"""
    if not update.message:
        return

    message_text = update.message.text or ""
    sender = update.message.from_user

    target_user_id = None
    target_name = None
    target_username = ""

    # 1. Спроба витягти цільового користувача з REPLY
    if update.message.reply_to_message and update.message.reply_to_message.from_user:
        reply_user = update.message.reply_to_message.from_user
        target_user_id = reply_user.id
        target_username = reply_user.username or ""
        if target_username.lower() in USERS_MAP:
            target_name = USERS_MAP[target_username.lower()]
        else:
            target_name = reply_user.first_name or target_username or f"User_{target_user_id}"

    # 2. Спроба витягти цільового користувача з ЗГАДКИ (@username або text_mention)
    elif '@' in message_text:
        match = re.search(r'@([^\s]+)', message_text)
        if match:
            raw_target = match.group(1).lstrip('@')
            target_username = raw_target

            # Entities check
            if update.message.entities:
                for entity in update.message.entities:
                    if entity.type == 'text_mention' and entity.user:
                        target_user_id = entity.user.id
                        target_name = entity.user.first_name or entity.user.username
                        break

            # USERS_MAP search
            if not target_name and raw_target.lower() in USERS_MAP:
                target_name = USERS_MAP[raw_target.lower()]

            # Dynamic cache search
            if not target_user_id or not target_name:
                cached_name, cached_id = await get_user_info_by_username(raw_target)
                if cached_name and not target_name:
                    target_name = cached_name
                if cached_id and not target_user_id:
                    target_user_id = cached_id

            if not target_name:
                target_name = raw_target

    # 3. Якщо цільовий користувач не вказаний — показуємо профіль відправника
    if not target_user_id and sender:
        target_user_id = sender.id
        target_username = sender.username or ""
        if target_username.lower() in USERS_MAP:
            target_name = USERS_MAP[target_username.lower()]
        else:
            target_name = sender.first_name or target_username or f"User_{sender.id}"

    if not target_user_id:
        await update.message.reply_text("❌ Не вдалося визначити користувача для відображення профілю.", parse_mode='HTML')
        return

    # Отримуємо AI-профіль з історією
    ai_profile = get_user_history_profile(target_user_id, target_username)
    # Отримуємо живу статистику за сьогодні
    live_stats = await get_user_live_stats(target_user_id)

    user_link = create_user_link(target_user_id, target_name)

    card_text = f"🎴 <b>ПСИХОЛОГІЧНИЙ ПРОФІЛЬ ТА СТАТИСТИКА</b>\n\n"
    card_text += f"👤 <b>Користувач:</b> {user_link}\n\n"

    # AI Портрет
    if ai_profile:
        role = ai_profile.get('role', 'Учасник чату')
        character = ai_profile.get('character', '')
        topics = ai_profile.get('topics', [])
        catchphrases = ai_profile.get('catchphrases', [])
        summary = ai_profile.get('summary', '')

        card_text += f"🎭 <b>Роль у чаті:</b> <code>{escape_html(role)}</code>\n"
        if character:
            card_text += f"🧠 <b>Характер:</b> <i>{escape_html(character)}</i>\n"
        if topics:
            topics_str = ", ".join([escape_html(t) for t in topics])
            card_text += f"💬 <b>Про що любить говорити:</b> {topics_str}\n"
        if catchphrases:
            phrases_str = ", ".join([f'"{escape_html(p)}"' for p in catchphrases])
            card_text += f"🗣️ <b>Коронні фрази:</b> {phrases_str}\n"
        if summary:
            card_text += f"✨ <b>Влучний висновок:</b> <i>{escape_html(summary)}</i>\n"
    else:
        card_text += "🎭 <b>Роль у чаті:</b> <code>Активний Учасник</code>\n"
        card_text += "🧠 <b>Характер:</b> <i>Створює атмосферу спільноти та бере активну участь у розмовах.</i>\n"

    card_text += "\n📊 <b>Жива статистика за сьогодні:</b>\n"
    if live_stats:
        msgs = live_stats.get('messages', 0)
        chars = live_stats.get('chars', 0)
        words = live_stats.get('words', 0)
        last_act = live_stats.get('last_active', '—')
        rx_given = live_stats.get('reactions_given', 0)

        card_text += f" • <b>Повідомлень:</b> {msgs:,}\n"
        card_text += f" • <b>Символів:</b> {chars:,}\n"
        card_text += f" • <b>Слів:</b> {words:,}\n"
        card_text += f" • <b>Реакцій поставлено:</b> {rx_given}\n"
        card_text += f" • <b>Останній актив:</b> {last_act}\n"
    else:
        card_text += " <i>Сьогодні повідомлень ще не зафіксовано.</i>\n"

    await update.message.reply_text(card_text, parse_mode='HTML')

async def chat_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Виводить топи чату, найактивніших дописувачів за сьогодні, найсильніші дуети та сленг"""
    chat_id = update.effective_chat.id
    history_data = get_history_summary()
    today_users = await get_today_top_users(limit=5)

    stats_text = "📊 <b>ГОЛОВНА АНАЛІТИКА ТА ТОПИ ЧАТУ</b>\n\n"

    # 1. ДЕННА СТАТИСТИКА (ТОП за сьогодні)
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

    # 2. НАЙСИЛЬНІШІ ДУЕТИ ЧАТУ (Reply Graph з офлайн-історії)
    duets = history_data.get('duets', [])
    if duets:
        stats_text += "💞 <b>Найсильніші дуети чату (Граф відповідей):</b>\n"
        for idx, duet in enumerate(duets[:5], 1):
            u1_id = duet.get('user1_id')
            u1_name = duet.get('user1_name') or f"User_{u1_id}"
            u2_id = duet.get('user2_id')
            u2_name = duet.get('user2_name') or f"User_{u2_id}"
            count = duet.get('replies_count', 0)

            link1 = create_user_link(u1_id, u1_name)
            link2 = create_user_link(u2_id, u2_name)
            stats_text += f"{idx}. {link1} 💬 {link2} — <b>{count:,}</b> відповідей\n"
        stats_text += "\n"

    # 3. ТОП АКТИВНОСТІ ЗА ВСІ ЧАСИ (Офлайн-історія)
    top_history_users = history_data.get('top_users', [])
    if top_history_users:
        stats_text += "👑 <b>Легенди історії чату (За весь час):</b>\n"
        for idx, hu in enumerate(top_history_users[:5], 1):
            uid = hu.get('user_id')
            uname = hu.get('name') or f"User_{uid}"
            msgs = hu.get('messages', 0)
            chars = hu.get('chars', 0)
            u_link = create_user_link(uid, uname)
            stats_text += f"{idx}. {u_link} — <b>{msgs:,}</b> смс ({chars:,} симв.)\n"
        stats_text += "\n"

    # 4. ТОП СЛЕНГУ ТА ЕМОДЗІ
    top_slang = history_data.get('top_slang', [])
    top_emojis = history_data.get('top_emojis', [])
    if top_slang or top_emojis:
        stats_text += "🔥 <b>Атмосфера та сленг чату:</b>\n"
        if top_emojis:
            emo_str = " ".join([e.get('emoji', '') for e in top_emojis[:8]])
            stats_text += f" • <b>Топ емодзі:</b> {emo_str}\n"
        if top_slang:
            slang_str = ", ".join([f"<code>{escape_html(s.get('word', ''))}</code>" for s in top_slang[:8]])
            stats_text += f" • <b>Топ сленгу:</b> {slang_str}\n"
        stats_text += "\n"

    # 5. АКТИВНІ СТОСУНКИ ЧАТУ (Забезпечуємо збереження логіки пара)
    chat_data = await load_chat_relationships(chat_id)
    relationships = chat_data.get('relationships', {})
    total_relationships = len(relationships)
    stats_text += f"💕 <b>Активні стосунки чату:</b> (всього: {total_relationships})\n"
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
