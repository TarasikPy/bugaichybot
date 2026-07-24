from telegram import Update
from telegram.ext import ContextTypes
from storage.json_db import load_chat_relationships

async def chat_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показує аналітику та статистику активності чату"""
    chat_id = update.effective_chat.id

    relationships_data = await load_chat_relationships(chat_id)
    relationships = relationships_data.get('relationships', {})

    total_relationships = len(relationships)
    married_couples = sum(
        1 for data in relationships.values()
        if data.get('status') == 'married'
    )

    stats_text = (
        f"📊 **Аналітика та статистика чату:**\n\n"
        f"💕 **Всього активних стосунків:** {total_relationships}\n"
        f"💒 **Одружених пар:** {married_couples}\n\n"
        f"✨ *Продовжуйте спілкуватися та розвивати свій чат!*"
    )

    await update.message.reply_text(stats_text, parse_mode='Markdown')
