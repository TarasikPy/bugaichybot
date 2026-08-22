import os
from dotenv import load_dotenv

# Завантажуємо змінні з .env
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не знайдено в змінних середовища! Створіть файл .env з BOT_TOKEN.")

if ':' not in BOT_TOKEN or len(BOT_TOKEN.split(':')) != 2:
    raise ValueError("Неправильний формат BOT_TOKEN! Токен повинен мати формат: ЧИСЛА:ЛІТЕРИ")

DEFAULT_CHAT_ID = os.getenv("DEFAULT_CHAT_ID", "-1004397346715")
