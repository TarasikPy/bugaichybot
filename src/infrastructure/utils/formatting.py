"""Formatting helpers for HTML, Markdown, and duration strings."""

import html
import re
from datetime import datetime
from typing import Any


def escape_html(text: Any) -> str:
    """Escape special HTML characters (<, >, &)."""
    if text is None:
        return ""
    return html.escape(str(text))


def escape_markdown(text: Any) -> str:
    """Escape special Markdown characters (_, *, [, ], `)."""
    if text is None:
        return ""
    return re.sub(r"([_*`\[\]])", r"\\\1", str(text))


def create_user_link(
    user_id: int | str | None = None,
    name: str | int | None = None,
    **kwargs: Any,
) -> str:
    """Create a clickable HTML link (tg://user?id=...) for a user.

    Supports polymorphic argument order (user_id, name) or (name, user_id).
    """
    # Handle inverted parameter orders if passed dynamically
    if isinstance(user_id, str) and (isinstance(name, int) or name is None):
        user_id, name = name, user_id  # type: ignore[assignment]

    actual_user_id: int | None = int(user_id) if user_id and str(user_id).isdigit() else None
    actual_name: str = str(name).strip() if name else ""

    if not actual_name and actual_user_id:
        actual_name = str(actual_user_id)
    elif not actual_name:
        actual_name = "Користувач"

    safe_name = escape_html(actual_name)
    if actual_user_id:
        return f'<a href="tg://user?id={actual_user_id}">{safe_name}</a>'
    return f"<b>{safe_name}</b>"


def create_html_user_link(name: str, user_id: int | None = None) -> str:
    """Compatible alias for create_user_link."""
    return create_user_link(user_id=user_id, name=name)


def format_duration(start_date: str) -> str:
    """Format relationship duration from ISO date string into Ukrainian readable string."""
    try:
        start = datetime.fromisoformat(start_date)
    except (ValueError, TypeError):
        start = datetime.now()

    duration = datetime.now() - start
    total_seconds = int(duration.total_seconds())
    days = duration.days
    hours = duration.seconds // 3600
    minutes = (duration.seconds % 3600) // 60
    seconds = duration.seconds % 60

    if total_seconds < 60:
        return f"{total_seconds} секунд"
    elif total_seconds < 3600:
        return f"{minutes} хвилин {seconds} секунд"
    elif days == 0:
        return f"{hours} годин {minutes} хвилин"
    elif days < 30:
        return f"{days} днів {hours} годин {minutes} хвилин"
    elif days < 365:
        months = days // 30
        remaining_days = days % 30
        if months == 1:
            return f"1 місяць {remaining_days} днів {hours} годин"
        else:
            return f"{months} місяців {remaining_days} днів {hours} годин"
    else:
        years = days // 365
        remaining_days = days % 365
        months = remaining_days // 30
        final_days = remaining_days % 30

        if years == 1:
            if months > 0:
                return f"1 рік {months} місяців {final_days} днів"
            return f"1 рік {final_days} днів"
        else:
            if months > 0:
                return f"{years} років {months} місяців {final_days} днів"
            return f"{years} років {final_days} днів"
