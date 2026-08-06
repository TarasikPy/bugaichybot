import os
import json
import asyncio
import aiofiles

USER_CACHE_FILE = 'storage/users_cache.json'
_cache_lock = asyncio.Lock()

async def update_user_cache(username: str, first_name: str, user_id: int = None) -> None:
    """Оновлює або зберігає мапінг юзернейма та ID на first_name користувача"""
    if not first_name:
        return

    async with _cache_lock:
        try:
            async with aiofiles.open(USER_CACHE_FILE, 'r', encoding='utf-8') as f:
                content = await f.read()
                data = json.loads(content)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {}

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
                    if isinstance(user_info, dict):
                        first_name = user_info.get('first_name') or user_info.get('name')
                        user_id = user_info.get('user_id') or user_info.get('id')
                        return first_name, user_id
                    return user_info, None
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    return None, None

def load_user_cache_sync() -> dict:
    """Синхронно завантажує кеш користувачів з storage/users_cache.json"""
    try:
        if os.path.exists(USER_CACHE_FILE):
            with open(USER_CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {}

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

# Аліас для зворотної сумісності з імпортами
get_user_info_by_username = get_first_name_by_username
