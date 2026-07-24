import os
import json
import asyncio
import aiofiles

WISDOM_CHATS_DIR = 'wisdom_chats'

if not os.path.exists(WISDOM_CHATS_DIR):
    os.makedirs(WISDOM_CHATS_DIR, exist_ok=True)

_wisdom_locks = {}

def _get_wisdom_lock(chat_id: int) -> asyncio.Lock:
    if chat_id not in _wisdom_locks:
        _wisdom_locks[chat_id] = asyncio.Lock()
    return _wisdom_locks[chat_id]

async def load_chat_wisdom_data(chat_id: int) -> dict:
    """Асинхронно завантажує дані мудрості для чату"""
    lock = _get_wisdom_lock(chat_id)
    async with lock:
        filename = os.path.join(WISDOM_CHATS_DIR, f'wisdom_{chat_id}.json')
        try:
            async with aiofiles.open(filename, 'r', encoding='utf-8') as f:
                content = await f.read()
                return json.loads(content)
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                'chat_info': {'total_messages_synced': 0},
                'users': {}
            }

async def save_chat_wisdom_data(chat_id: int, data: dict) -> None:
    """Асинхронно зберігає дані мудрості для чату"""
    lock = _get_wisdom_lock(chat_id)
    async with lock:
        filename = os.path.join(WISDOM_CHATS_DIR, f'wisdom_{chat_id}.json')
        async with aiofiles.open(filename, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(data, ensure_ascii=False, indent=2))
