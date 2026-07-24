import os
import json
import asyncio
import aiofiles

RELATIONSHIPS_CHATS_DIR = 'relationships_chats'

# Створюємо директорію якщо її ще немає
if not os.path.exists(RELATIONSHIPS_CHATS_DIR):
    os.makedirs(RELATIONSHIPS_CHATS_DIR, exist_ok=True)

# Словник локів для уникнення race conditions при одночасному записі у один файл чату
_chat_locks = {}

def _get_chat_lock(chat_id: int) -> asyncio.Lock:
    if chat_id not in _chat_locks:
        _chat_locks[chat_id] = asyncio.Lock()
    return _chat_locks[chat_id]

async def load_chat_relationships(chat_id: int) -> dict:
    """Асинхронно завантажує стосунки для конкретного чату з JSON-файлу"""
    lock = _get_chat_lock(chat_id)
    async with lock:
        filename = os.path.join(RELATIONSHIPS_CHATS_DIR, f'relationships_{chat_id}.json')
        try:
            async with aiofiles.open(filename, 'r', encoding='utf-8') as f:
                content = await f.read()
                return json.loads(content)
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                'chat_info': {'total_relationships': 0},
                'relationships': {}
            }

async def save_chat_relationships(chat_id: int, data: dict) -> None:
    """Асинхронно зберігає стосунки для конкретного чату у JSON-файл"""
    lock = _get_chat_lock(chat_id)
    async with lock:
        filename = os.path.join(RELATIONSHIPS_CHATS_DIR, f'relationships_{chat_id}.json')
        async with aiofiles.open(filename, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(data, ensure_ascii=False, indent=2))
