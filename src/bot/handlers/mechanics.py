"""Mechanics and risk roulette command handlers."""

import random

from telegram import Update
from telegram.ext import ContextTypes

from src.infrastructure.constants.risk_events import RISK_EVENTS
from src.infrastructure.utils.formatting import create_user_link


def get_random_risk(user_link: str) -> str:
    """Select a random event from the lore risk roulette."""
    event = random.choice(RISK_EVENTS)
    return f"🎰 <b>РП-Рулетка для {user_link}:</b>\n\n{event}"


async def risk_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /risk and !ризик commands."""
    if not update.message:
        return

    from_user = update.message.from_user
    user_name = from_user.first_name if from_user else "Користувач"
    user_link = create_user_link(from_user.id if from_user else 0, user_name)

    risk_text = get_random_risk(user_link)
    try:
        await update.message.reply_text(risk_text, parse_mode="HTML")
    except Exception:
        await update.message.reply_text(risk_text)
