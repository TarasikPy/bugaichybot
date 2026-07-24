from telegram import Update
from telegram.ext import ContextTypes
from storage.json_db import load_chat_relationships
from utils.helpers import create_user_link, get_relationship_level
from config.levels import RELATIONSHIP_LEVELS

async def chat_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показує аналітику та статистику активності чату, топи активності та профілі користувачів"""
    chat_id = update.effective_chat.id
    from_user = update.message.from_user if update.message else None

    relationships_data = await load_chat_relationships(chat_id)
    relationships = relationships_data.get('relationships', {})

    total_relationships = len(relationships)
    married_couples = sum(
        1 for data in relationships.values()
        if data.get('status') == 'married'
    )

    stats_text = (
        f"📊 <b>Аналітика та статистика чату:</b>\n\n"
        f"💕 <b>Всього активних стосунків:</b> {total_relationships}\n"
        f"💒 <b>Одружених пар:</b> {married_couples}\n"
    )

    # Топ активних пар
    if relationships:
        sorted_couples = sorted(
            relationships.values(),
            key=lambda x: x.get('total_points', 0),
            reverse=True
        )[:5]

        stats_text += "\n🏆 <b>Топ найактивніших пар:</b>\n"
        for idx, couple in enumerate(sorted_couples, 1):
            u1_id = couple.get('user1_id')
            u2_id = couple.get('user2_id')
            u1_name = couple.get('user1_name') or "Користувач"
            u2_name = couple.get('user2_name') or "Користувач"
            points = couple.get('total_points', 0)
            level = get_relationship_level(points)
            level_info = RELATIONSHIP_LEVELS[level]
            status = couple.get('status', 'dating')
            status_emoji = "💒" if status == 'married' else "💕"

            link1 = create_user_link(u1_id, u1_name)
            link2 = create_user_link(u2_id, u2_name)
            stats_text += f"{idx}. {status_emoji} {link1} ❤️ {link2} — {level_info['emoji']} <b>{points}</b> оч.\n"

    # Профіль користувача
    if from_user:
        user_link = create_user_link(from_user.id, from_user.first_name)
        stats_text += f"\n👤 <b>Профіль користувача {user_link}:</b>\n"

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
            st_name = "Одружені 💒" if user_couple.get('status') == 'married' else "У стосунках 💕"
            stats_text += (
                f" • <b>Статус:</b> {st_name}\n"
                f" • <b>Партнер:</b> {p_link}\n"
                f" • <b>Рівень:</b> {lvl_info['emoji']} {lvl_info['name']} ({pts} очок)\n"
            )
        else:
            stats_text += " • <b>Статус:</b> Поки що без пари 💔\n"

    stats_text += f"\n✨ <i>Продовжуйте спілкуватися та розвивати свій чат!</i>"

    await update.message.reply_text(stats_text, parse_mode='HTML')
