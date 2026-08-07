import os
import json
import asyncio
from config.names import USERS_MAP

USER_CACHE_FILE = 'storage/users_cache.json'
_cache_lock = asyncio.Lock()

def _load_cache_file() -> dict:
    try:
        if os.path.exists(USER_CACHE_FILE):
            with open(USER_CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def _save_cache_file(data: dict) -> None:
    try:
        os.makedirs(os.path.dirname(USER_CACHE_FILE), exist_ok=True)
        with open(USER_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

async def update_user_cache(username: str, first_name: str, user_id: int = None) -> None:
    """Оновлює або зберігає мапінг юзернейма та ID на first_name користувача"""
    if not first_name:
        return

    async with _cache_lock:
        data = await asyncio.to_thread(_load_cache_file)

        if username:
            username_clean = username.lstrip('@').lower()
            data[username_clean] = {
                'first_name': first_name,
                'user_id': user_id,
                'name': first_name,
                'id': user_id
            }

        if user_id:
            data[str(user_id)] = first_name

        await asyncio.to_thread(_save_cache_file, data)

async def get_first_name_by_username(username: str):
    """Шукає справжній first_name та user_id користувача за його юзернеймом"""
    if not username:
        return None, None

    username_clean = username.lstrip('@').lower()
    if username_clean in USERS_MAP:
        name = USERS_MAP[username_clean]
        # Check if ID exists in cache
        data = await asyncio.to_thread(_load_cache_file)
        user_info = data.get(username_clean, {})
        user_id = user_info.get('user_id') if isinstance(user_info, dict) else None
        return name, user_id

    async with _cache_lock:
        data = await asyncio.to_thread(_load_cache_file)
        if username_clean in data:
            user_info = data[username_clean]
            if isinstance(user_info, dict):
                first_name = user_info.get('first_name') or user_info.get('name')
                user_id = user_info.get('user_id') or user_info.get('id')
                return first_name, user_id
            return user_info, None

    return None, None

def load_user_cache_sync() -> dict:
    """Синхронно завантажує кеш користувачів з storage/users_cache.json"""
    return _load_cache_file()

def get_user_name_by_id_sync(user_id: int) -> str:
    """Шукає first_name за user_id у кеші"""
    if not user_id:
        return ""
    data = load_user_cache_sync()
    val = data.get(str(user_id))
    if isinstance(val, str):
        return val
    if isinstance(val, dict):
        return val.get('first_name') or val.get('name') or ""
    return ""

get_user_info_by_username = get_first_name_by_username
