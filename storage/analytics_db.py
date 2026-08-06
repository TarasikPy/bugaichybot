import os
import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

DATA_DIR = 'data'
HISTORY_ANALYTICS_FILE = os.path.join(DATA_DIR, 'chat_analytics.json')
LIVE_ANALYTICS_FILE = os.path.join(DATA_DIR, 'live_analytics.json')

# Переконуємося, що директорія data існує
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR, exist_ok=True)

_live_db_lock = asyncio.Lock()
_history_cache: Optional[Dict[str, Any]] = None
_history_mtime: float = 0.0
_chat_recent_messages: Dict[int, list] = {}

def add_chat_recent_message(chat_id: int, user_name: str, text: str) -> None:
    """Додає повідомлення у циклічний буфер останніх повідомлень чату (до 50 шт)"""
    if not text or not text.strip():
        return
    text_lower = text.lower()
    if any(cmd in text_lower for cmd in ['!пиши', '/say', '/пиши']):
        return  # Секретні команди власника ніколи не потрапляють у буфер чату!

    now_str = datetime.now().strftime('%H:%M')
    msg_list = _chat_recent_messages.setdefault(chat_id, [])
    msg_list.append({
        'name': user_name,
        'text': text.strip()[:300],
        'time': now_str
    })
    if len(msg_list) > 50:
        _chat_recent_messages[chat_id] = msg_list[-50:]

def get_recent_chat_messages(chat_id: int, limit: int = 20) -> str:
    """Отримує останні повідомлення чату для аналізу ШІ-Суддею"""
    msg_list = _chat_recent_messages.get(chat_id, [])
    if not msg_list:
        return ""
    recent = msg_list[-limit:]
    formatted = []
    for m in recent:
        formatted.append(f"[{m['time']}] {m['name']}: {m['text']}")
    return "\n".join(formatted)

def load_history_analytics() -> Dict[str, Any]:
    """Завантажує офлайн-аналітику з data/chat_analytics.json (з кешуванням за mtime)"""
    global _history_cache, _history_mtime
    try:
        if os.path.exists(HISTORY_ANALYTICS_FILE):
            mtime = os.path.getmtime(HISTORY_ANALYTICS_FILE)
            if _history_cache is None or mtime > _history_mtime:
                with open(HISTORY_ANALYTICS_FILE, 'r', encoding='utf-8') as f:
                    _history_cache = json.load(f)
                _history_mtime = mtime
            return _history_cache or {}
    except Exception as e:
        logger.error(f"Помилка читання {HISTORY_ANALYTICS_FILE}: {e}")
    return {}

async def _load_live_analytics() -> Dict[str, Any]:
    """Внутрішня функція завантаження живої статистики"""
    today_str = datetime.now().strftime('%Y-%m-%d')
    try:
        if os.path.exists(LIVE_ANALYTICS_FILE):
            async with _live_db_lock:
                with open(LIVE_ANALYTICS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if data.get('date') == today_str:
                    return data
    except Exception as e:
        logger.warning(f"Не вдалося зчитати {LIVE_ANALYTICS_FILE}: {e}")

    return {'date': today_str, 'users': {}}

async def _save_live_analytics(data: Dict[str, Any]) -> None:
    """Внутрішня функція збереження живої статистики"""
    try:
        async with _live_db_lock:
            with open(LIVE_ANALYTICS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Помилка збереження {LIVE_ANALYTICS_FILE}: {e}")

async def record_live_message(chat_id: int, user: Any, text_content: str) -> None:
    """Фіксує живе повідомлення користувача (автоматичне скидання о 00:00)"""
    if not user or getattr(user, 'is_bot', False):
        return

    today_str = datetime.now().strftime('%Y-%m-%d')
    now_iso = datetime.now().strftime('%H:%M:%S')

    async with _live_db_lock:
        live_data = {'date': today_str, 'users': {}}
        try:
            if os.path.exists(LIVE_ANALYTICS_FILE):
                with open(LIVE_ANALYTICS_FILE, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                if content.get('date') == today_str:
                    live_data = content
        except Exception as e:
            logger.warning(f"Не вдалося зчитати {LIVE_ANALYTICS_FILE}: {e}")

        users = live_data.setdefault('users', {})
        u_key = str(user.id)

        from utils.helpers import resolve_clean_user_name
        name = resolve_clean_user_name(user)
        username = user.username or ""
        words_count = len(text_content.split()) if text_content else 0
        chars_count = len(text_content) if text_content else 0

        add_chat_recent_message(chat_id, name, text_content)

        if u_key not in users:
            users[u_key] = {
                'user_id': user.id,
                'name': name,
                'username': username,
                'messages': 0,
                'chars': 0,
                'words': 0,
                'last_active': now_iso,
                'reactions_given': 0,
                'reactions_detail': {}
            }

        u_stat = users[u_key]
        u_stat['name'] = name
        if username:
            u_stat['username'] = username
        u_stat['messages'] += 1
        u_stat['chars'] += chars_count
        u_stat['words'] += words_count
        u_stat['last_active'] = now_iso

        try:
            with open(LIVE_ANALYTICS_FILE, 'w', encoding='utf-8') as f:
                json.dump(live_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Помилка збереження {LIVE_ANALYTICS_FILE}: {e}")

async def record_live_reaction(chat_id: int, user_id: int, user_name: str, emoji: str) -> None:
    """Фіксує реакції (🔥, ❤️, 😭 тощо), які ставлять користувачі"""
    if not user_id:
        return

    today_str = datetime.now().strftime('%Y-%m-%d')

    async with _live_db_lock:
        live_data = {'date': today_str, 'users': {}}
        try:
            if os.path.exists(LIVE_ANALYTICS_FILE):
                with open(LIVE_ANALYTICS_FILE, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                if content.get('date') == today_str:
                    live_data = content
        except Exception as e:
            logger.warning(f"Не вдалося зчитати {LIVE_ANALYTICS_FILE}: {e}")

        users = live_data.setdefault('users', {})
        u_key = str(user_id)

        if u_key not in users:
            users[u_key] = {
                'user_id': user_id,
                'name': user_name or "Користувач",
                'username': "",
                'messages': 0,
                'chars': 0,
                'words': 0,
                'last_active': datetime.now().strftime('%H:%M:%S'),
                'reactions_given': 0,
                'reactions_detail': {}
            }

        u_stat = users[u_key]
        u_stat['reactions_given'] = u_stat.get('reactions_given', 0) + 1
        reactions_detail = u_stat.setdefault('reactions_detail', {})
        reactions_detail[emoji] = reactions_detail.get(emoji, 0) + 1

        try:
            with open(LIVE_ANALYTICS_FILE, 'w', encoding='utf-8') as f:
                json.dump(live_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Помилка збереження {LIVE_ANALYTICS_FILE}: {e}")

async def get_user_live_stats(user_id: int) -> Dict[str, Any]:
    """Отримує денну активність конкретного користувача"""
    today_str = datetime.now().strftime('%Y-%m-%d')
    live_data = await _load_live_analytics()
    if live_data.get('date') == today_str:
        return live_data.get('users', {}).get(str(user_id), {})
    return {}

async def get_today_top_users(limit: int = 10) -> list:
    """Отримує топ найактивніших дописувачів за сьогодні"""
    today_str = datetime.now().strftime('%Y-%m-%d')
    live_data = await _load_live_analytics()
    if live_data.get('date') != today_str:
        return []

    users_list = list(live_data.get('users', {}).values())
    sorted_users = sorted(users_list, key=lambda x: (x.get('messages', 0), x.get('chars', 0)), reverse=True)
    return sorted_users[:limit]

def get_user_history_profile(user_id: int, username: str = "") -> Optional[Dict[str, Any]]:
    """Повертає збережений AI-профіль з офлайн-аналітики"""
    history = load_history_analytics()
    profiles = history.get('profiles', {})

    # Пошук за ID
    if str(user_id) in profiles:
        return profiles[str(user_id)]

    # Пошук за username
    if username:
        clean_uname = username.lstrip('@').lower()
        for p in profiles.values():
            if p.get('username', '').lower() == clean_uname:
                return p

    return None

def get_history_summary() -> Dict[str, Any]:
    """Повертає загальні метрики історії"""
    history = load_history_analytics()
    return {
        'summary': history.get('summary', {}),
        'top_users': history.get('top_users', []),
        'duets': history.get('duets', []),
        'top_emojis': history.get('top_emojis', []),
        'top_slang': history.get('top_slang', [])
    }

def get_all_active_chat_ids() -> list:
    """Повертає список усіх ID групових чатів, де бот є активним"""
    chat_ids = set(_chat_recent_messages.keys())
    try:
        history = load_history_analytics()
        for cid_str in history.get("chats", {}).keys():
            try:
                chat_ids.add(int(cid_str))
            except ValueError:
                pass
    except Exception:
        pass

    group_chats = [cid for cid in chat_ids if cid < 0]
    if not group_chats:
        try:
            from config.settings import DEFAULT_CHAT_ID
            group_chats.append(int(DEFAULT_CHAT_ID))
        except Exception:
            group_chats.append(-1004397346715)
    return group_chats

def rescan_and_sync_analytics() -> Dict[str, int]:
    """Сканує накопичений буфер останніх смс і підраховує активність користувачів"""
    counts = {}
    for cid, msg_list in _chat_recent_messages.items():
        for m in msg_list:
            name = m.get('name', 'Користувач')
            counts[name] = counts.get(name, 0) + 1
    return counts

def purge_all_data() -> None:
    """Повністю очищує тестову аналітику та стосунки перед деплоєм в продакшн"""
    for fname in [LIVE_ANALYTICS_FILE, 'data/relationships.json', 'data/user_cache.json']:
        if os.path.exists(fname):
            try:
                os.remove(fname)
            except Exception:
                pass
