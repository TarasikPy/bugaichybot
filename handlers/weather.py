import logging
import httpx
from telegram import Update
from telegram.ext import ContextTypes
from utils.helpers import escape_html

logger = logging.getLogger(__name__)

# Мапінг погодних кодів Open-Meteo до емодзі та опису
WEATHER_CODES = {
    0: ("☀️", "Ясно"),
    1: ("🌤", "Переважно ясно"),
    2: ("⛅", "Мінлива хмарність"),
    3: ("☁️", "Похмуро"),
    45: ("🌫", "Туман"),
    48: ("🌫", "Паморозь"),
    51: ("🌦", "Легкий мрячний дощ"),
    53: ("🌦", "Помірний мрячний дощ"),
    55: ("🌧", "Густий мрячний дощ"),
    61: ("🌧", "Невеликий дощ"),
    63: ("🌧", "Помірний дощ"),
    65: ("🌧", "Сильний дощ"),
    71: ("🌨", "Невеликий снігопад"),
    73: ("🌨", "Помірний снігопад"),
    75: ("❄️", "Сильний снігопад"),
    80: ("🌦", "Короткочасний дощ"),
    81: ("🌧", "Злива"),
    82: ("🌧", "Сильна злива"),
    85: ("🌨", "Невеликий сніговий шквал"),
    86: ("❄️", "Сильний сніговий шквал"),
    95: ("🌩", "Гроза"),
    96: ("⛈", "Гроза з невеликим градом"),
    99: ("⛈", "Гроза з сильним градом")
}

async def weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отримує поточну погоду для вказаного міста через безкоштовний Open-Meteo API"""
    if not update.message:
        return

    # Визначаємо місто (за замовчуванням Львів)
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

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 1. Геокодування міста
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city_query}&count=1&language=uk"
            geo_resp = await client.get(geo_url)
            if geo_resp.status_code != 200:
                await update.message.reply_text("❌ Помилка сервісу геокодування. Спробуйте пізніше.", parse_mode='HTML')
                return

            geo_data = geo_resp.json()
            results = geo_data.get('results', [])

            if not results:
                safe_city = escape_html(city_query)
                await update.message.reply_text(f"❌ Місто <b>{safe_city}</b> не знайдено. Перевірте назву.", parse_mode='HTML')
                return

            city_info = results[0]
            lat = city_info.get('latitude')
            lon = city_info.get('longitude')
            city_name = city_info.get('name', city_query)
            country = city_info.get('country', '')

            # 2. Отримання прогнозу погоди
            weather_url = (
                f"https://api.open-meteo.com/v1/forecast?"
                f"latitude={lat}&longitude={lon}&"
                f"current_weather=true&"
                f"hourly=temperature_2m,relative_humidity_2m,apparent_temperature"
            )
            weather_resp = await client.get(weather_url)
            if weather_resp.status_code != 200:
                await update.message.reply_text("❌ Помилка отримання даних погоди.", parse_mode='HTML')
                return

            weather_data = weather_resp.json()
            current = weather_data.get('current_weather', {})

            temp = current.get('temperature', 0)
            windspeed = current.get('windspeed', 0)
            weathercode = current.get('weathercode', 0)
            current_time = current.get('time', '')

            # Отримуємо вологість та відчувану температуру
            hourly = weather_data.get('hourly', {})
            times = hourly.get('time', [])
            humidity = "—"
            feels_like = temp

            if current_time and current_time in times:
                idx = times.index(current_time)
                humidities = hourly.get('relative_humidity_2m', [])
                if idx < len(humidities):
                    humidity = humidities[idx]
                apparent_temps = hourly.get('apparent_temperature', [])
                if idx < len(apparent_temps):
                    feels_like = apparent_temps[idx]

            emoji, desc = WEATHER_CODES.get(weathercode, ("🌤", "Погода"))
            country_str = f" ({country})" if country else ""

            from utils.bugaichyk_ai import get_bugaichyk_weather_commentary
            bugaichyk_comment = await get_bugaichyk_weather_commentary(city_name, temp, desc, feels_like)

            card_text = (
                f"{emoji} <b>Погода в місті {escape_html(city_name)}{country_str}:</b>\n\n"
                f"🌡 <b>Температура:</b> {temp}°C (відчувається як {feels_like}°C)\n"
                f"💨 <b>Вітер:</b> {windspeed} км/год\n"
                f"💧 <b>Вологість:</b> {humidity}%\n"
                f"📝 <b>Стан:</b> {desc}\n\n"
                f"💬 <b>Бугайчик каже:</b>\n<i>{escape_html(bugaichyk_comment)}</i>"
            )

            await update.message.reply_text(card_text, parse_mode='HTML')

    except Exception as e:
        logger.error(f"Помилка в weather_command: {e}")
        await update.message.reply_text("❌ Не вдалося отримати дані погоди через мережеву помилку.", parse_mode='HTML')
