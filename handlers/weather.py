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

async def fetch_wttr_weather(client: httpx.AsyncClient, city_query: str):
    """Резервне отримання погоди через wttr.in, якщо Open-Meteo віддає 429 або помилку"""
    try:
        wttr_url = f"https://wttr.in/{city_query}?format=j1"
        resp = await client.get(wttr_url)
        if resp.status_code == 200:
            data = resp.json()
            curr = data.get("current_condition", [{}])[0]
            temp = float(curr.get("temp_C", 0))
            feels_like = float(curr.get("FeelsLikeC", temp))
            humidity = curr.get("humidity", "—")
            windspeed = curr.get("windspeedKmph", 0)
            desc_list = curr.get("lang_uk", curr.get("weatherDesc", [{}]))
            desc = desc_list[0].get("value", "Погода") if desc_list else "Погода"
            return {
                "city_name": city_query,
                "temp": temp,
                "feels_like": feels_like,
                "humidity": humidity,
                "windspeed": windspeed,
                "desc": desc,
                "emoji": "🌤",
                "country": ""
            }
    except Exception as e:
        logger.warning(f"wttr.in fallback error: {e}")
    return None


async def weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отримує поточну погоду для вказаного міста через Open-Meteo або резервний wttr.in"""
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
            # 1. Геокодування міста через Open-Meteo
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city_query}&count=1&language=uk"
            geo_resp = await client.get(geo_url)
            
            if geo_resp.status_code == 200:
                geo_data = geo_resp.json()
                results = geo_data.get('results', [])

                if results:
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
                    if weather_resp.status_code == 200:
                        weather_data = weather_resp.json()
                        current = weather_data.get('current_weather', {})

                        temp = current.get('temperature', 0)
                        windspeed = current.get('windspeed', 0)
                        weathercode = current.get('weathercode', 0)
                        current_time = current.get('time', '')

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

                        card_text = (
                            f"{emoji} <b>Погода в місті {escape_html(city_name)}{country_str}:</b>\n\n"
                            f"🌡 <b>Температура:</b> {temp}°C (відчувається як {feels_like}°C)\n"
                            f"💨 <b>Вітер:</b> {windspeed} км/год\n"
                            f"💧 <b>Вологість:</b> {humidity}%\n"
                            f"📝 <b>Стан:</b> {desc}"
                        )
                        await update.message.reply_text(card_text, parse_mode='HTML')
                        return

            # Якщо Open-Meteo віддав 429 або помилку — використовуємо резервний wttr.in!
            wttr = await fetch_wttr_weather(client, city_query)
            if wttr:
                city_name = wttr["city_name"]
                temp = wttr["temp"]
                feels_like = wttr["feels_like"]
                humidity = wttr["humidity"]
                windspeed = wttr["windspeed"]
                desc = wttr["desc"]
                emoji = wttr["emoji"]

                card_text = (
                    f"{emoji} <b>Погода в місті {escape_html(city_name)}:</b>\n\n"
                    f"🌡 <b>Температура:</b> {temp}°C (відчувається як {feels_like}°C)\n"
                    f"💨 <b>Вітер:</b> {windspeed} км/год\n"
                    f"💧 <b>Вологість:</b> {humidity}%\n"
                    f"📝 <b>Стан:</b> {desc}"
                )
                await update.message.reply_text(card_text, parse_mode='HTML')
                return

            safe_city = escape_html(city_query)
            await update.message.reply_text(f"❌ Не вдалося знайти інформацію про погоду для міста <b>{safe_city}</b>.", parse_mode='HTML')

    except Exception as e:
        logger.error(f"Помилка в weather_command: {e}")
        await update.message.reply_text("❌ Помилка отримання погоди.", parse_mode='HTML')
