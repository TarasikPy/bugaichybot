"""Weather command handler."""

from telegram import Update
from telegram.ext import ContextTypes

from src.services.weather_service import WeatherService


async def weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /weather and !погода commands."""
    if not update.message:
        return

    city_query = "Львів"
    if context.args:
        city_query = " ".join(context.args).strip()
    else:
        text = update.message.text or ""
        words = text.strip().split()
        if len(words) > 1:
            city_query = " ".join(words[1:]).strip()

    if not city_query:
        city_query = "Львів"

    weather_card = await WeatherService.get_weather_card(city_query)
    await update.message.reply_text(weather_card, parse_mode="HTML")
