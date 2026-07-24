import os
import json
import asyncio
import aiofiles

USER_CACHE_FILE = 'storage/users_cache.json'
_cache_lock = asyncio.Lock()

async def update_user_cache(username: str, first_name: str, user_id: int = None) -> None:
    """Оновлює або зберігає мапінг юзернейма та ID на first_name користувача"""
    if not username or not first_name:
        return

    username_clean = username.lstrip('@').lower()
    async with _cache_lock:
        try:
            async with aiofiles.open(USER_CACHE_FILE, 'r', encoding='utf-8') as f:
                content = await f.read()
                data = json.loads(content)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {}

        data[username_clean] = {
            'first_name': first_name,
            'user_id': user_id
        }

        async with aiofiles.open(USER_CACHE_FILE, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(data, ensure_ascii=False, indent=2))

async def get_first_name_by_username(username: str):
    """Шукає справжній first_name та user_id користувача за його юзернеймом"""
    if not username:
        return None, None

    username_clean = username.lstrip('@').lower()
    async with _cache_lock:
        try:
            async with aiofiles.open(USER_CACHE_FILE, 'r', encoding='utf-8') as f:
                content = await f.read()
                data = json.loads(content)
                if username_clean in data:
                    user_info = data[username_clean]
                    return user_info.get('first_name'), user_info.get('user_id')
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    return None, None
