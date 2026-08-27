"""Domain schemas and data transfer objects using Pydantic v2."""

from datetime import datetime
from typing import Any, Union

from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    """Psychological and social profile model from offline/historical analytics."""

    user_id: int | None = None
    name: str = "Користувач"
    username: str | None = ""
    code_name: str | None = ""
    role: str = "Учасник чату"
    intro: str = ""
    roast: str = ""
    style: str = ""
    character: str = ""
    topics: Union[str, list[str]] = ""
    slang: Union[str, list[str]] = ""
    full_text: str = ""


class LiveUserStats(BaseModel):
    """Daily live statistics entry for an active user in a chat."""

    user_id: int
    name: str = "Користувач"
    username: str = ""
    messages: int = 0
    chars: int = 0
    words: int = 0
    last_active: str = Field(default_factory=lambda: datetime.now().strftime("%H:%M:%S"))
    reactions_given: int = 0
    reactions_detail: dict[str, int] = Field(default_factory=dict)


class LiveAnalyticsData(BaseModel):
    """Daily aggregate live analytics file schema."""

    date: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    users: dict[str, LiveUserStats] = Field(default_factory=dict)


class RelationshipData(BaseModel):
    """Model representing an active relationship or marriage in a chat."""

    user1_id: int
    user1_name: str
    user2_id: int
    user2_name: str
    start_date: str = Field(default_factory=lambda: datetime.now().isoformat())
    total_points: int = 0
    status: str = "dating"


class ChatDailyUser(BaseModel):
    """Daily user stats stored inside chat relationships file for backwards compatibility."""

    name: str = "Користувач"
    user_id: int
    messages: int = 0
    chars: int = 0


class ChatDailyStats(BaseModel):
    """Daily stats model inside chat relationships file."""

    date: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    users: dict[str, ChatDailyUser] = Field(default_factory=dict)


class ChatRelationshipsData(BaseModel):
    """Root model for per-chat relationships JSON files."""

    chat_info: dict[str, Any] = Field(default_factory=lambda: {"total_relationships": 0})
    relationships: dict[str, RelationshipData] = Field(default_factory=dict)
    daily_stats: ChatDailyStats | None = None


class HistoryAnalytics(BaseModel):
    """Schema for data/chat_analytics.json."""

    profiles: dict[str, UserProfile] = Field(default_factory=dict)
    summary: dict[str, Any] = Field(default_factory=dict)
    top_users: list[dict[str, Any]] = Field(default_factory=list)
    duets: list[dict[str, Any]] = Field(default_factory=list)
    top_emojis: list[dict[str, Any]] = Field(default_factory=list)
    top_slang: list[dict[str, Any]] = Field(default_factory=list)
    chats: dict[str, Any] = Field(default_factory=dict)
