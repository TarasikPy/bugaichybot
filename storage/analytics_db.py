"""Legacy analytics DB bridge forwarding to src.services.user_profiler and src.infrastructure.db.repository."""

from src.infrastructure.db.repository import (
    load_history_analytics,
    load_live_analytics,
    save_live_analytics,
)
from src.services.user_profiler import (
    add_chat_recent_message,
    get_all_active_chat_ids,
    get_history_summary,
    get_today_top_users,
    get_user_history_profile,
    get_user_live_stats,
    record_live_message,
    record_live_reaction,
    rescan_and_sync_analytics,
)

__all__ = [
    "add_chat_recent_message",
    "get_all_active_chat_ids",
    "get_history_summary",
    "get_today_top_users",
    "get_user_history_profile",
    "get_user_live_stats",
    "load_history_analytics",
    "load_live_analytics",
    "record_live_message",
    "record_live_reaction",
    "rescan_and_sync_analytics",
    "save_live_analytics",
]
