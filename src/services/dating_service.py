"""Dating, marriage, and couple relationship business logic service."""

from datetime import datetime
from typing import Any

from src.core.logger import get_logger
from src.infrastructure.constants.levels import (
    RELATIONSHIP_LEVELS,
)
from src.infrastructure.db.repository import (
    load_chat_relationships,
)
from src.infrastructure.utils.formatting import create_user_link, format_duration
from src.services.user_profiler import resolve_user_name_by_id_or_name

logger = get_logger(__name__)

# In-memory cache for proposal sender display names
PROPOSAL_NAMES_CACHE: dict[int, str] = {}


def get_relationship_level(total_points: int) -> int:
    """Determine numeric relationship level index based on points."""
    for level in reversed(range(len(RELATIONSHIP_LEVELS))):
        if total_points >= RELATIONSHIP_LEVELS[level]["required_points"]:
            return level
    return 0


def find_user_relationships(
    user_id: int, relationships: dict[str, Any]
) -> list[tuple[str, dict[str, Any]]]:
    """Find all relationship entries involving the specified user ID."""
    found: list[tuple[str, dict[str, Any]]] = []
    for couple_id, data in relationships.items():
        if user_id in (data.get("user1_id"), data.get("user2_id")):
            found.append((couple_id, data))
    return found


async def build_chat_relationships_overview(chat_id: int) -> str:
    """Build formatted text of all active relationships in a chat."""
    chat_data = await load_chat_relationships(chat_id)
    relationships = chat_data.get("relationships", {})

    if not relationships:
        return "💔 Поки що немає активних стосунків у цьому чаті!"

    text = "💕 <b>Активні стосунки в цьому чаті:</b>\n\n"
    valid_count = 0

    for _couple_id, data in relationships.items():
        user1_id = data.get("user1_id")
        user2_id = data.get("user2_id")
        if not user1_id or not user2_id:
            continue

        valid_count += 1
        user1_name = resolve_user_name_by_id_or_name(user1_id, data.get("user1_name"))
        user2_name = resolve_user_name_by_id_or_name(user2_id, data.get("user2_name"))

        duration = format_duration(data.get("start_date", datetime.now().isoformat()))
        total_points = data.get("total_points", 0)
        level = get_relationship_level(total_points)
        level_info = RELATIONSHIP_LEVELS[level]
        status = data.get("status", "dating")

        status_emoji = "💒" if status == "married" else "💕"
        link1 = create_user_link(user1_id, user1_name)
        link2 = create_user_link(user2_id, user2_name)

        text += (
            f"{status_emoji} {link1} ❤️ {link2} — {total_points} оч. "
            f"[{level_info['emoji']} {level_info['name']}]\n"
        )
        text += f"📅 <b>Тривалість:</b> {duration}\n\n"

    if valid_count == 0:
        return "💔 Поки що немає активних стосунків у цьому чаті!"

    return text


async def build_user_relationships_overview(
    chat_id: int, user_id: int, user_first_name: str
) -> str:
    """Build personal relationship card text for a specific user."""
    user_name = resolve_user_name_by_id_or_name(user_id, user_first_name)
    user_link = create_user_link(user_id, user_name)

    chat_data = await load_chat_relationships(chat_id)
    relationships = chat_data.get("relationships", {})

    user_relationships: list[str] = []
    for _couple_id, data in relationships.items():
        u1_id = data.get("user1_id")
        u2_id = data.get("user2_id")

        if user_id in (u1_id, u2_id):
            partner_id = u2_id if user_id == u1_id else u1_id
            raw_pname = data.get("user2_name") if user_id == u1_id else data.get("user1_name")
            partner_name = resolve_user_name_by_id_or_name(partner_id, raw_pname)

            duration = format_duration(data.get("start_date", datetime.now().isoformat()))
            total_points = data.get("total_points", 0)
            level = get_relationship_level(total_points)
            level_info = RELATIONSHIP_LEVELS[level]
            status = data.get("status", "dating")

            status_text = "💒 Одружені" if status == "married" else "💕 У стосунках"
            partner_link = create_user_link(partner_id, partner_name)

            user_relationships.append(
                f"{status_text}\n"
                f"❤️ <b>Партнер:</b> {partner_link}\n"
                f"📊 <b>Рівень:</b> {level_info['emoji']} {level_info['name']}\n"
                f"⚡ <b>Очки:</b> {total_points}\n"
                f"📝 {level_info['description']}\n"
                f"📅 <b>Тривалість:</b> {duration}"
            )

    if not user_relationships:
        return f"💔 У вас, {user_link}, поки немає активних стосунків у цьому чаті!"

    return f"💕 <b>Ваші стосунки, {user_link}:</b>\n\n" + "\n\n".join(user_relationships)
