from telegram import Update
from telegram.ext import ContextTypes
from storage.json_db import load_chat_relationships
from storage.wisdom_db import load_chat_wisdom_data

async def chat_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показує розширену аналітику та статистику активності чату"""
    chat_id = update.effective_chat.id

    relationships_data = await load_chat_relationships(chat_id)
    wisdom_data = await load_chat_wisdom_data(chat_id)

    total_relationships = len(relationships_data.get('relationships', {}))
    total_users = len(wisdom_data.get('users', {}))
    total_messages = wisdom_data.get('chat_info', {}).get('total_messages_synced', 0)

    married_couples = sum(
        1 for data in relationships_data.get('relationships', {}).values()
        if data.get('status') == 'married'
    )

    stats_text = (
        f"📊 **Аналітика та статистика чату:**\n\n"
        f"💬 **Всього оброблено повідомлень:** {total_messages}\n"
        f"👥 **Активних учасників у системі:** {total_users}\n"
        f"💕 **Всього активних стосунків:** {total_relationships}\n"
        f"💒 **Одружених пар:** {married_couples}\n\n"
        f"✨ *Продовжуйте спілкуватися та розвивати свій чат!*"
    )

    await update.message.reply_text(stats_text, parse_mode='Markdown')
