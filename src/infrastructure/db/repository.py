"""Repository layer providing thread-safe, atomic JSON data persistence."""

import asyncio
import json
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Union, cast

import aiofiles

from src.core.config import get_settings
from src.core.logger import get_logger
from src.infrastructure.constants.names import USERS_MAP

logger = get_logger(__name__)

# Concurrency locks
_chat_locks: dict[int, asyncio.Lock] = {}
_live_db_lock = asyncio.Lock()
_cache_lock = asyncio.Lock()

# History analytics caching
_history_cache: dict[str, Any] | None = None
_history_mtime: float = 0.0


def _get_chat_lock(chat_id: int) -> asyncio.Lock:
    """Retrieve or create an asyncio.Lock for a specific chat ID."""
    if chat_id not in _chat_locks:
        _chat_locks[chat_id] = asyncio.Lock()
    return _chat_locks[chat_id]


async def _atomic_write_json(file_path: Path, data: Any) -> None:
    """Write JSON data to a temporary file and atomically rename it."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = file_path.with_suffix(".tmp")

    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    async with aiofiles.open(temp_path, "w", encoding="utf-8") as f:
        await f.write(json_str)

    await asyncio.to_thread(os.replace, temp_path, file_path)


# =========================================================================
# Relationships Storage & Transaction Manager
# =========================================================================


@asynccontextmanager
async def chat_relationship_transaction(chat_id: int) -> AsyncIterator[dict[str, Any]]:
    """Context manager guaranteeing atomic Read-Modify-Write cycle for chat relationship data."""
    settings = get_settings()
    file_path = settings.RELATIONSHIPS_DIR / f"relationships_{chat_id}.json"
    lock = _get_chat_lock(chat_id)

    async with lock:
        data: dict[str, Any] = {
            "chat_info": {"total_relationships": 0},
            "relationships": {},
        }
        if file_path.exists():
            try:
                async with aiofiles.open(file_path, encoding="utf-8") as f:
                    content = await f.read()
                    data = cast(dict[str, Any], json.loads(content))
            except Exception as e:
                logger.warning(f"Error reading relationships for chat {chat_id}: {e}")

        yield data

        # Write mutated state back atomically before releasing lock
        await _atomic_write_json(file_path, data)


async def load_chat_relationships(chat_id: int) -> dict[str, Any]:
    """Asynchronously load relationship records for a specific chat."""
    settings = get_settings()
    file_path = settings.RELATIONSHIPS_DIR / f"relationships_{chat_id}.json"

    lock = _get_chat_lock(chat_id)
    async with lock:
        try:
            if not file_path.exists():
                return {
                    "chat_info": {"total_relationships": 0},
                    "relationships": {},
                }
            async with aiofiles.open(file_path, encoding="utf-8") as f:
                content = await f.read()
                return cast(dict[str, Any], json.loads(content))
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"Error reading relationships for chat {chat_id}: {e}")
            return {
                "chat_info": {"total_relationships": 0},
                "relationships": {},
            }


async def save_chat_relationships(chat_id: int, data: Union[dict[str, Any], Any]) -> None:
    """Asynchronously and atomically persist relationship records for a chat."""
    settings = get_settings()
    file_path = settings.RELATIONSHIPS_DIR / f"relationships_{chat_id}.json"

    payload = data.model_dump() if hasattr(data, "model_dump") else data
    lock = _get_chat_lock(chat_id)
    async with lock:
        await _atomic_write_json(file_path, payload)


# =========================================================================
# Live Analytics Storage
# =========================================================================


async def load_live_analytics() -> dict[str, Any]:
    """Asynchronously load live daily analytics."""
    settings = get_settings()
    file_path = settings.DATA_DIR / "live_analytics.json"
    today_str = datetime.now().strftime("%Y-%m-%d")

    async with _live_db_lock:
        try:
            if file_path.exists():
                async with aiofiles.open(file_path, encoding="utf-8") as f:
                    content = await f.read()
                    data = cast(dict[str, Any], json.loads(content))
                    if data.get("date") == today_str:
                        return data
        except Exception as e:
            logger.warning(f"Error loading live analytics: {e}")

        return {"date": today_str, "users": {}}


async def save_live_analytics(data: dict[str, Any]) -> None:
    """Asynchronously persist live daily analytics."""
    settings = get_settings()
    file_path = settings.DATA_DIR / "live_analytics.json"

    async with _live_db_lock:
        try:
            await _atomic_write_json(file_path, data)
        except Exception as e:
            logger.error(f"Error saving live analytics: {e}")


# =========================================================================
# History & Static Offline Analytics
# =========================================================================


def load_history_analytics() -> dict[str, Any]:
    """Synchronously load offline analytics with mtime caching."""
    global _history_cache, _history_mtime
    settings = get_settings()
    file_path = settings.DATA_DIR / "chat_analytics.json"

    try:
        if file_path.exists():
            mtime = os.path.getmtime(file_path)
            if _history_cache is None or mtime > _history_mtime:
                with open(file_path, encoding="utf-8") as f:
                    _history_cache = cast(dict[str, Any], json.load(f))
                _history_mtime = mtime
            return _history_cache or {}
    except Exception as e:
        logger.error(f"Error loading history analytics from {file_path}: {e}")
    return {}


# =========================================================================
# User Info Cache Storage
# =========================================================================


def _load_cache_file_sync() -> dict[str, Any]:
    settings = get_settings()
    file_path = settings.STORAGE_DIR / "users_cache.json"
    try:
        if file_path.exists():
            with open(file_path, encoding="utf-8") as f:
                return cast(dict[str, Any], json.load(f))
    except Exception:
        pass
    return {}


async def update_user_cache(username: str, first_name: str, user_id: int | None = None) -> None:
    """Update user metadata mapping in users_cache.json with atomic persistence."""
    if not first_name:
        return

    settings = get_settings()
    file_path = settings.STORAGE_DIR / "users_cache.json"

    async with _cache_lock:
        data = await asyncio.to_thread(_load_cache_file_sync)

        if username:
            clean_username = username.lstrip("@").lower()
            data[clean_username] = {
                "first_name": first_name,
                "user_id": user_id,
                "name": first_name,
                "id": user_id,
            }

        if user_id:
            data[str(user_id)] = first_name

        await _atomic_write_json(file_path, data)


async def get_first_name_by_username(
    username: str,
) -> tuple[str | None, int | None]:
    """Retrieve first_name and user_id by username from USERS_MAP or cache."""
    if not username:
        return None, None

    clean_username = username.lstrip("@").lower()
    if clean_username in USERS_MAP:
        name = USERS_MAP[clean_username]
        async with _cache_lock:
            data = await asyncio.to_thread(_load_cache_file_sync)
        user_info = data.get(clean_username, {})
        user_id = user_info.get("user_id") if isinstance(user_info, dict) else None
        return name, user_id

    async with _cache_lock:
        data = await asyncio.to_thread(_load_cache_file_sync)
        if clean_username in data:
            user_info = data[clean_username]
            if isinstance(user_info, dict):
                first_name = user_info.get("first_name") or user_info.get("name")
                user_id = user_info.get("user_id") or user_info.get("id")
                return first_name, user_id
            return user_info, None

    return None, None


get_user_info_by_username = get_first_name_by_username


def load_user_cache_sync() -> dict[str, Any]:
    """Synchronous load of user cache."""
    return _load_cache_file_sync()


def get_user_name_by_id_sync(user_id: int) -> str:
    """Synchronously lookup user's known display name by Telegram ID."""
    if not user_id:
        return ""
    data = load_user_cache_sync()
    val = data.get(str(user_id))
    if isinstance(val, str):
        return val
    if isinstance(val, dict):
        return cast(str, val.get("first_name") or val.get("name") or "")
    return ""
