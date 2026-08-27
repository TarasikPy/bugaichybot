"""Legacy user cache bridge forwarding to src.infrastructure.db.repository."""

from src.infrastructure.db.repository import (
    get_first_name_by_username,
    get_user_info_by_username,
    get_user_name_by_id_sync,
    load_user_cache_sync,
    update_user_cache,
)

__all__ = [
    "get_first_name_by_username",
    "get_user_info_by_username",
    "get_user_name_by_id_sync",
    "load_user_cache_sync",
    "update_user_cache",
]
