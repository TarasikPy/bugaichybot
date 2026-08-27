"""User profiling, psychological portraits, and chat statistics service."""

import re
import unicodedata
from collections import defaultdict, deque
from datetime import datetime
from typing import Any, cast

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from src.core.config import get_settings
from src.core.logger import get_logger
from src.infrastructure.constants.names import (
    USER_ID_MAP,
    USERNAME_TO_ID_MAP,
    USERS_MAP,
)
from src.infrastructure.db.repository import (
    get_first_name_by_username,
    get_user_name_by_id_sync,
    load_history_analytics,
    load_live_analytics,
)
from src.infrastructure.utils.formatting import create_user_link, escape_html
from src.services.analytics_buffer import get_analytics_buffer

logger = get_logger(__name__)

# Cyclic buffer of recent chat messages (up to 50 items per chat)
_chat_recent_messages: dict[int, deque[dict[str, str]]] = defaultdict(lambda: deque(maxlen=50))


def add_chat_recent_message(chat_id: int, user_name: str, text: str) -> None:
    """Store message in cyclic buffer (up to 50 entries)."""
    if not text or not text.strip():
        return
    text_lower = text.lower()
    if any(cmd in text_lower for cmd in ("!пиши", "/say", "/пиши")):
        return

    now_str = datetime.now().strftime("%H:%M")
    _chat_recent_messages[chat_id].append(
        {
            "name": user_name,
            "text": text.strip()[:300],
            "time": now_str,
        }
    )


def get_all_active_chat_ids() -> list[int]:
    """Return all active group chat IDs recorded in buffer or analytics history."""
    settings = get_settings()
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
        group_chats.append(int(settings.DEFAULT_CHAT_ID))
    return group_chats


def rescan_and_sync_analytics() -> dict[str, int]:
    """Scan accumulated message buffer and return message counts per user."""
    counts: dict[str, int] = {}
    for msg_deque in _chat_recent_messages.values():
        for m in msg_deque:
            name = m.get("name", "Користувач")
            counts[name] = counts.get(name, 0) + 1
    return counts


def resolve_clean_user_name(user: Any = None, raw_name: str = "") -> str:
    """Normalize raw username or first_name to canonical community name."""
    if user:
        if getattr(user, "id", None) in USER_ID_MAP:
            return USER_ID_MAP[user.id]
        uname = (getattr(user, "username", "") or "").lower()
        if uname in USERS_MAP:
            return USERS_MAP[uname]
        fname = getattr(user, "first_name", "") or ""
        combined = f"{uname} {fname}"
    else:
        combined = raw_name or ""

    norm = unicodedata.normalize("NFKC", combined).lower()
    if "bot dev" in norm or "sp_mangment" in norm or "arma" in norm:
        return "Арма"
    if "kiyotaka" in norm or "shadow_tar" in norm:
        return "Кійотака"

    for key, clean_val in USERS_MAP.items():
        if key in norm:
            return clean_val

    if user and getattr(user, "first_name", None):
        clean = unicodedata.normalize("NFKC", user.first_name)
        clean_name = re.sub(r"[^\w\s\-\'’А-Яа-яІіЇїЄєA-Za-z0-9]", "", clean).strip()
        if clean_name:
            return clean_name
        return cast(str, user.first_name.strip())

    if raw_name and raw_name not in ("Користувач", "Партнер 1", "Партнер 2", "Суперник", "Опонент"):
        clean = unicodedata.normalize("NFKC", raw_name)
        clean_name = re.sub(r"[^\w\s\-\'’А-Яа-яІіЇїЄєA-Za-z0-9]", "", clean).strip()
        if clean_name:
            return clean_name

    return raw_name or "Користувач"


def resolve_user_name_by_id_or_name(user_id: int, current_name: str = "") -> str:
    """Find canonical user name by Telegram ID or cached display name."""
    if user_id in USER_ID_MAP:
        return USER_ID_MAP[user_id]

    cached_name = get_user_name_by_id_sync(user_id)
    if cached_name and cached_name not in ("Користувач", "Партнер 1", "Партнер 2"):
        return resolve_clean_user_name(raw_name=cached_name)

    if current_name and current_name not in ("Користувач", "Партнер 1", "Партнер 2"):
        return resolve_clean_user_name(raw_name=current_name)

    return f"Гравець_{user_id}" if user_id else "Користувач"


async def resolve_target_user_info(update: Any) -> tuple[int | None, str, str]:
    """Extract target user ID, clean name, and username from reply, mention, or argument."""
    if not update or not update.message:
        return None, "Користувач", ""

    message_text = (update.message.text or update.message.caption or "").strip()
    sender = update.message.from_user

    target_user_id: int | None = None
    target_name: str | None = None
    target_username: str = ""

    # 1. From Reply
    if update.message.reply_to_message and update.message.reply_to_message.from_user:
        reply_user = update.message.reply_to_message.from_user
        target_user_id = reply_user.id
        target_username = (reply_user.username or "").lstrip("@").lower()
        target_name = resolve_clean_user_name(reply_user)
        return target_user_id, target_name, target_username

    # 2. From arguments / entities
    words = message_text.split()
    args = words[1:] if len(words) > 1 else []

    if args:
        raw_arg = args[0].strip()
        raw_target = raw_arg.lstrip("@").lower()
        target_username = raw_target

        # 2a. text_mention in entities
        if update.message.entities:
            for entity in update.message.entities:
                if entity.type == "text_mention" and entity.user:
                    target_user_id = entity.user.id
                    target_username = (entity.user.username or "").lstrip("@").lower()
                    target_name = resolve_clean_user_name(entity.user)
                    return target_user_id, target_name, target_username

        # 2b. Numeric Telegram ID
        if raw_target.isdigit():
            target_user_id = int(raw_target)

        # 2c. Static USERS_MAP & USERNAME_TO_ID_MAP
        if raw_target in USERS_MAP:
            target_name = USERS_MAP[raw_target]
        if raw_target in USERNAME_TO_ID_MAP:
            target_user_id = USERNAME_TO_ID_MAP[raw_target]

        # 2d. Cached info
        if not target_user_id or not target_name:
            cached_name, cached_id = await get_first_name_by_username(raw_target)
            if cached_name and not target_name:
                target_name = resolve_clean_user_name(raw_name=cached_name)
            if cached_id and not target_user_id:
                target_user_id = cached_id

        # 2e. History profiles
        if not target_user_id or not target_name:
            history_data = load_history_analytics()
            profiles = history_data.get("profiles", {})
            target_key = str(target_user_id or raw_target)
            if target_key in profiles:
                p_data = profiles[target_key]
                target_user_id = p_data.get("user_id") or (
                    int(target_key) if target_key.isdigit() else None
                )
                target_name = resolve_clean_user_name(raw_name=p_data.get("name", target_name))
            else:
                for p_id_str, p_data in profiles.items():
                    p_uname = (p_data.get("username") or "").lstrip("@").lower()
                    p_name = (p_data.get("name") or "").lower()
                    p_code = (p_data.get("code_name") or "").lower()
                    if (
                        (target_username and p_uname == target_username)
                        or (p_name == raw_target)
                        or (p_code == raw_target)
                    ):
                        target_user_id = p_data.get("user_id") or (
                            int(p_id_str) if p_id_str.isdigit() else None
                        )
                        target_name = resolve_clean_user_name(
                            raw_name=p_data.get("name", target_name)
                        )
                        break

        if not target_name:
            target_name = resolve_clean_user_name(raw_name=raw_arg)

        return target_user_id, target_name or "Користувач", target_username

    # 3. Fallback to sender
    if sender:
        target_user_id = sender.id
        target_username = (sender.username or "").lstrip("@").lower()
        target_name = resolve_clean_user_name(sender)
        return target_user_id, target_name, target_username

    return None, "Користувач", ""


async def record_live_message(chat_id: int, user: Any, text_content: str) -> None:
    """Record live user message activity through in-memory write-back buffer."""
    if not user or getattr(user, "is_bot", False):
        return

    name = resolve_clean_user_name(user)
    username = user.username or ""

    add_chat_recent_message(chat_id, name, text_content)

    buffer = get_analytics_buffer()
    await buffer.record_message(
        chat_id=chat_id,
        user_id=user.id,
        name=name,
        username=username,
        text=text_content,
    )


async def record_live_reaction(chat_id: int, user_id: int, user_name: str, emoji: str) -> None:
    """Record user reaction into live buffer."""
    if not user_id or not emoji:
        return

    buffer = get_analytics_buffer()
    await buffer.record_reaction(chat_id, user_id, user_name, emoji)


async def get_user_live_stats(user_id: int) -> dict[str, Any]:
    """Fetch live stats of a single user for today."""
    today_str = datetime.now().strftime("%Y-%m-%d")
    live_data = await load_live_analytics()
    if live_data.get("date") == today_str:
        return cast(dict[str, Any], live_data.get("users", {}).get(str(user_id), {}))
    return {}


async def get_today_top_users(limit: int = 10) -> list[dict[str, Any]]:
    """Return top active users for today ordered by message and character count."""
    today_str = datetime.now().strftime("%Y-%m-%d")
    live_data = await load_live_analytics()
    if live_data.get("date") != today_str:
        return []

    users_list = list(live_data.get("users", {}).values())
    sorted_users = sorted(
        users_list,
        key=lambda x: (x.get("messages", 0), x.get("chars", 0)),
        reverse=True,
    )
    return cast(list[dict[str, Any]], sorted_users[:limit])


def get_user_history_profile(user_id: int, username: str = "") -> dict[str, Any] | None:
    """Lookup historical psychological profile for user by ID or username."""
    history = load_history_analytics()
    profiles = history.get("profiles", {})

    # 1. Search by Telegram ID
    if str(user_id) in profiles:
        return cast(dict[str, Any], profiles[str(user_id)])

    # 2. Search by username
    if username:
        clean_uname = username.lstrip("@").lower()
        for p in profiles.values():
            p_uname = (p.get("username") or "").lower()
            if p_uname and (clean_uname in p_uname or p_uname in clean_uname):
                return cast(dict[str, Any], p)

    # 3. Fallback for Maria
    if user_id in (6266441947, 2005833676) or (
        username and username.lower() in ("mashasu", "masha_su", "mariai_k")
    ):
        return cast(dict[str, Any], profiles.get("2005833676"))

    return None


def get_history_summary() -> dict[str, Any]:
    """Return aggregated offline analytics summary."""
    history = load_history_analytics()
    return {
        "summary": history.get("summary", {}),
        "top_users": history.get("top_users", []),
        "duets": history.get("duets", []),
        "top_emojis": history.get("top_emojis", []),
        "top_slang": history.get("top_slang", []),
    }


def build_profile_keyboard(user_id: int, active_tab: str = "main") -> InlineKeyboardMarkup:
    """Build interactive inline keyboard for profile tabs."""
    buttons = [
        [
            InlineKeyboardButton(
                "🏠 Огляд" if active_tab != "main" else "🏠 • Огляд •",
                callback_data=f"prof_main_{user_id}",
            ),
            InlineKeyboardButton(
                "🎭 Роль & Стиль" if active_tab != "role" else "🎭 • Роль & Стиль •",
                callback_data=f"prof_role_{user_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                "🧠 Психоаналіз" if active_tab != "char" else "🧠 • Психоаналіз •",
                callback_data=f"prof_char_{user_id}",
            ),
            InlineKeyboardButton(
                "💡 Справжні теми" if active_tab != "topics" else "💡 • Справжні теми •",
                callback_data=f"prof_topics_{user_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                "🗣 Сленг" if active_tab != "slang" else "🗣 • Сленг •",
                callback_data=f"prof_slang_{user_id}",
            ),
            InlineKeyboardButton(
                "🎯 Коронний підкол" if active_tab != "roast" else "🎯 • Коронний підкол •",
                callback_data=f"prof_roast_{user_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                "📖 Повний портрет" if active_tab != "full" else "📖 • Повний портрет •",
                callback_data=f"prof_full_{user_id}",
            ),
            InlineKeyboardButton(
                "📊 Статистика" if active_tab != "stats" else "📊 • Статистика •",
                callback_data=f"prof_stats_{user_id}",
            ),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def render_profile_tab(
    user_id: int,
    target_name: str,
    target_username: str,
    tab: str,
    live_stats: dict[str, Any],
    ai_profile: dict[str, Any] | None = None,
) -> str:
    """Render HTML response string for given profile tab."""
    user_link = create_user_link(user_id, target_name)
    if not ai_profile:
        ai_profile = get_user_history_profile(user_id, target_username) or {}

    role = ai_profile.get("role", "Учасник чату")
    style = ai_profile.get("style", "")
    character = ai_profile.get("character", "")
    topics = ai_profile.get("topics", "")
    slang = ai_profile.get("slang", "")
    roast = ai_profile.get("roast", "")
    intro = ai_profile.get("intro", "")
    full_text = ai_profile.get("full_text", "")

    if tab == "role":
        text = "🎭 <b>РОЛЬ ТА СТИЛЬ СПІЛКУВАННЯ</b>\n\n"
        text += f"👤 <b>Користувач:</b> {user_link}\n\n"
        text += f"🎭 <b>Роль у чаті:</b>\n<code>{escape_html(role)}</code>\n\n"
        if style:
            text += f"📊 <b>Стиль спілкування:</b>\n<i>{escape_html(style)}</i>\n"
        return text

    elif tab == "char":
        text = "🧠 <b>ПСИХОЛОГІЧНИЙ ПОРТРЕТ (ПСИХОАНАЛІЗ)</b>\n\n"
        text += f"👤 <b>Користувач:</b> {user_link}\n\n"
        if character:
            text += f"<i>{escape_html(character)}</i>\n"
        else:
            text += "<i>Немає детального психоаналізу в базі.</i>\n"
        return text

    elif tab == "topics":
        text = "💡 <b>СПРАВЖНІ ТЕМИ ТА ІНТЕРЕСИ</b>\n\n"
        text += f"👤 <b>Користувач:</b> {user_link}\n\n"
        if topics:
            if isinstance(topics, list):
                topics_str = "\n• " + "\n• ".join([escape_html(str(t)) for t in topics])
            else:
                topics_str = escape_html(str(topics))
            text += f"<i>{topics_str}</i>\n"
        else:
            text += "<i>Теми не зафіксовано.</i>\n"
        return text

    elif tab == "slang":
        text = "🗣 <b>УЛЮБЛЕНИЙ СЛЕНГ ТА МАРКЕРИ</b>\n\n"
        text += f"👤 <b>Користувач:</b> {user_link}\n\n"
        if slang:
            if isinstance(slang, list):
                slang_str = ", ".join([escape_html(str(s)) for s in slang])
            else:
                slang_str = escape_html(str(slang))
            text += f"<i>{slang_str}</i>\n"
        else:
            text += "<i>Сленг не зафіксовано.</i>\n"
        return text

    elif tab == "roast":
        text = "🎯 <b>КОРОННИЙ ПІДКОЛ / РЕЗЮМЕ</b>\n\n"
        text += f"👤 <b>Користувач:</b> {user_link}\n\n"
        if roast:
            text += f"<i>{escape_html(roast)}</i>\n"
        else:
            text += "<i>Підкол відсутній.</i>\n"
        return text

    elif tab == "full":
        text = "📖 <b>ПОВНИЙ ПСИХОЛОГІЧНИЙ ПОРТРЕТ</b>\n\n"
        text += f"👤 <b>Користувач:</b> {user_link}\n\n"
        if full_text:
            clean_full = escape_html(full_text[:3500])
            text += f"<blockquote expandable>{clean_full}</blockquote>\n"
        else:
            text += "<i>Повний текст портрета відсутній.</i>\n"
        return text

    elif tab == "stats":
        text = "📊 <b>ЖИВА СТАТИСТИКА АКТИВНОСТІ ЗА СЬОГОДНІ</b>\n\n"
        text += f"👤 <b>Користувач:</b> {user_link}\n\n"
        if live_stats:
            msgs = live_stats.get("messages", 0)
            chars = live_stats.get("chars", 0)
            words = live_stats.get("words", 0)
            last_act = live_stats.get("last_active", "—")
            rx_given = live_stats.get("reactions_given", 0)

            text += f" • <b>Повідомлень:</b> {msgs:,}\n"
            text += f" • <b>Символів:</b> {chars:,}\n"
            text += f" • <b>Слів:</b> {words:,}\n"
            text += f" • <b>Реакцій поставлено:</b> {rx_given}\n"
            text += f" • <b>Останній актив:</b> {last_act}\n"
        else:
            text += "<i>Сьогодні повідомлень ще не зафіксовано.</i>\n"
        return text

    # Default Main tab ("main")
    card_text = "🎴 <b>ПСИХОЛОГІЧНИЙ ПРОФІЛЬ ТА СТАТИСТИКА</b>\n\n"
    card_text += f"👤 <b>Користувач:</b> {user_link}\n\n"

    if ai_profile:
        card_text += f"🎭 <b>Роль у чаті:</b> <code>{escape_html(role)}</code>\n\n"
        if intro:
            intro_clean = escape_html(intro).strip()
            if not intro_clean.endswith("..."):
                intro_clean += "..."
            card_text += f"📝 <i>{intro_clean}</i>\n"
    else:
        card_text += "🎭 <b>Роль у чаті:</b> <code>Учасник чату</code>\n"

    card_text += "\n📊 <b>Активність за сьогодні:</b>\n"
    if live_stats:
        msgs = live_stats.get("messages", 0)
        chars = live_stats.get("chars", 0)
        card_text += f" • <b>Повідомлень:</b> {msgs:,} | <b>Символів:</b> {chars:,}\n"
    else:
        card_text += " <i>Сьогодні активність відсутня.</i>\n"

    card_text += "\n👇 <i>Натискайте кнопки нижче для перегляду розділів:</i>"
    return card_text
