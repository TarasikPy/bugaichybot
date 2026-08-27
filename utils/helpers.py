"""Legacy helpers bridge forwarding to src modules."""

from src.infrastructure.utils.declension import decline_name
from src.infrastructure.utils.formatting import (
    create_html_user_link,
    create_user_link,
    escape_html,
    escape_markdown,
    format_duration,
)
from src.services.dating_service import (
    find_user_relationships,
    get_relationship_level,
)
from src.services.user_profiler import (
    resolve_clean_user_name,
    resolve_target_user_info,
    resolve_user_name_by_id_or_name,
)

__all__ = [
    "create_html_user_link",
    "create_user_link",
    "decline_name",
    "escape_html",
    "escape_markdown",
    "find_user_relationships",
    "format_duration",
    "get_relationship_level",
    "resolve_clean_user_name",
    "resolve_target_user_info",
    "resolve_user_name_by_id_or_name",
]
