from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from storage.json_db import load_chat_relationships
from utils.helpers import create_user_link, get_relationship_level
from config.levels import RELATIONSHIP_LEVELS

async def chat_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показує аналітику активності чату (топ активності за сьогодні) та інформацію про стосунки в кінці"""
    chat_id = update.effective_chat.id
    from_user = update.message.from_user if update.message else None

    chat_data = await load_chat_relationships(chat_id)
    today_str = datetime.now().strftime('%Y-%m-%d')
    daily_stats = chat_data.get('daily_stats', {})

    stats_text = "📊 <b>Аналітика активності чату:</b>\n\n"

    # 1. ДЕННА СТАТИСТИКА (ТОП-5 активності за сьогодні)
    if daily_stats.get('date') == today_str and daily_stats.get('users'):
        users_daily = list(daily_stats['users'].values())
        sorted_users = sorted(users_daily, key=lambda x: x.get('messages', 0), reverse=True)[:5]

        stats_text += "🏆 <b>Топ активності за сьогодні:</b>\n"
        for idx, u_stat in enumerate(sorted_users, 1):
            uid = u_stat.get('user_id')
            uname = u_stat.get('name') or "Користувач"
            msgs = u_stat.get('messages', 0)
            chars = u_stat.get('chars', 0)
            formatted_chars = f"{chars:,}"

            user_link = create_user_link(uid, uname)
            stats_text += f"{idx}. {user_link} — {msgs} смс ({formatted_chars} символів)\n"
        stats_text += "\n"
    else:
        stats_text += "🏆 <b>Топ активності за сьогодні:</b>\n<i>Сьогодні повідомлень ще не було зафіксовано. Напишіть щось!</i>\n\n"

    # 2. ПРОФІЛЬ КОРИСТУВАЧА
    relationships = chat_data.get('relationships', {})
    if from_user:
        user_link = create_user_link(from_user.id, from_user.first_name)
        stats_text += f"👤 <b>Ваш профіль ({user_link}):</b>\n"

        # Денна активність юзера
        u_key = str(from_user.id)
        if daily_stats.get('date') == today_str and u_key in daily_stats.get('users', {}):
            my_stat = daily_stats['users'][u_key]
            stats_text += f" • <b>Активність сьогодні:</b> {my_stat.get('messages', 0)} смс ({my_stat.get('chars', 0):,} символів)\n"

        # Стосунки юзера
        user_couple = None
        for couple in relationships.values():
            if from_user.id in (couple.get('user1_id'), couple.get('user2_id')):
                user_couple = couple
                break

        if user_couple:
            partner_id = user_couple.get('user2_id') if from_user.id == user_couple.get('user1_id') else user_couple.get('user1_id')
            partner_name = user_couple.get('user2_name') if from_user.id == user_couple.get('user1_id') else user_couple.get('user1_name')
            p_link = create_user_link(partner_id, partner_name or "Партнер")
            pts = user_couple.get('total_points', 0)
            lvl = get_relationship_level(pts)
            lvl_info = RELATIONSHIP_LEVELS[lvl]
            stats_text += f" • <b>Пара:</b> {p_link} ({lvl_info['emoji']} {lvl_info['name']}, {pts} очок)\n"
        else:
            stats_text += " • <b>Пара:</b> Не перебуваєте в стосунках 💔\n"
        stats_text += "\n"

    # 3. БЛОК СТОСУНКІВ У САМОМУ КІНЦІ (ДРУГОРЯДНА ІНФОРМАЦІЯ)
    total_relationships = len(relationships)
    stats_text += f"💕 <b>Активні стосунки чату (додатково):</b> (всього: {total_relationships})\n"
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
        stats_text += "<i>Поки немає активних пара в цьому чаті.</i>\n"

    await update.message.reply_text(stats_text, parse_mode='HTML')
