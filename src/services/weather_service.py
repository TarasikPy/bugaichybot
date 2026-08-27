"""Weather forecast service with Open-Meteo and wttr.in fallback."""

from typing import Any

import aiohttp

from src.core.logger import get_logger
from src.infrastructure.constants.weather_codes import WEATHER_CODES
from src.infrastructure.utils.formatting import escape_html
from src.services.http_client import get_http_session

logger = get_logger(__name__)


class WeatherService:
    """Service providing weather forecasts with multi-source fallback."""

    @staticmethod
    async def _fetch_wttr_weather(city_query: str) -> dict[str, Any] | None:
        """Fallback weather provider using wttr.in."""
        try:
            session = await get_http_session()
            wttr_url = f"https://wttr.in/{city_query}?format=j1"
            timeout = aiohttp.ClientTimeout(total=10.0)
            async with session.get(wttr_url, timeout=timeout) as resp:
                if resp.status == 200:
                    data = await resp.json()
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
                        "country": "",
                    }
        except Exception as e:
            logger.warning(f"wttr.in fallback error for {city_query}: {e}")
        return None

    @classmethod
    async def get_weather_card(cls, city_query: str = "Львів") -> str:
        """Fetch and format weather information card for given city."""
        clean_query = city_query.strip() if city_query.strip() else "Львів"

        try:
            session = await get_http_session()
            timeout = aiohttp.ClientTimeout(total=10.0)

            # 1. Geocode city via Open-Meteo
            geo_url = (
                f"https://geocoding-api.open-meteo.com/v1/search?"
                f"name={clean_query}&count=1&language=uk"
            )
            async with session.get(geo_url, timeout=timeout) as geo_resp:
                if geo_resp.status == 200:
                    geo_data = await geo_resp.json()
                    results = geo_data.get("results", [])

                    if results:
                        city_info = results[0]
                        lat = city_info.get("latitude")
                        lon = city_info.get("longitude")
                        city_name = city_info.get("name", clean_query)
                        country = city_info.get("country", "")

                        # 2. Forecast via Open-Meteo
                        weather_url = (
                            f"https://api.open-meteo.com/v1/forecast?"
                            f"latitude={lat}&longitude={lon}&"
                            f"current_weather=true&"
                            f"hourly=temperature_2m,relative_humidity_2m,apparent_temperature"
                        )
                        async with session.get(weather_url, timeout=timeout) as weather_resp:
                            if weather_resp.status == 200:
                                weather_data = await weather_resp.json()
                                current = weather_data.get("current_weather", {})

                                temp = current.get("temperature", 0)
                                windspeed = current.get("windspeed", 0)
                                weathercode = current.get("weathercode", 0)
                                current_time = current.get("time", "")

                                hourly = weather_data.get("hourly", {})
                                times = hourly.get("time", [])
                                humidity = "—"
                                feels_like = temp

                                if current_time and current_time in times:
                                    idx = times.index(current_time)
                                    humidities = hourly.get("relative_humidity_2m", [])
                                    if idx < len(humidities):
                                        humidity = humidities[idx]
                                    apparent_temps = hourly.get("apparent_temperature", [])
                                    if idx < len(apparent_temps):
                                        feels_like = apparent_temps[idx]

                                emoji, desc = WEATHER_CODES.get(weathercode, ("🌤", "Погода"))
                                country_str = f" ({country})" if country else ""

                                return (
                                    f"{emoji} <b>Погода в місті {escape_html(city_name)}{country_str}:</b>\n\n"
                                    f"🌡 <b>Температура:</b> {temp}°C (відчувається як {feels_like}°C)\n"
                                    f"💨 <b>Вітер:</b> {windspeed} км/год\n"
                                    f"💧 <b>Вологість:</b> {humidity}%\n"
                                    f"📝 <b>Стан:</b> {desc}"
                                )

            # 3. Fallback to wttr.in
            wttr = await cls._fetch_wttr_weather(clean_query)
            if wttr:
                city_name = wttr["city_name"]
                temp = wttr["temp"]
                feels_like = wttr["feels_like"]
                humidity = wttr["humidity"]
                windspeed = wttr["windspeed"]
                desc = wttr["desc"]
                emoji = wttr["emoji"]

                return (
                    f"{emoji} <b>Погода в місті {escape_html(city_name)}:</b>\n\n"
                    f"🌡 <b>Температура:</b> {temp}°C (відчувається як {feels_like}°C)\n"
                    f"💨 <b>Вітер:</b> {windspeed} км/год\n"
                    f"💧 <b>Вологість:</b> {humidity}%\n"
                    f"📝 <b>Стан:</b> {desc}"
                )

            safe_city = escape_html(clean_query)
            return f"❌ Не вдалося знайти інформацію про погоду для міста <b>{safe_city}</b>."

        except Exception as e:
            logger.error(f"Error fetching weather for {clean_query}: {e}")
            return "❌ Помилка отримання погоди."
