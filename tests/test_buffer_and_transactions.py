"""Unit tests for transaction manager, AnalyticsBuffer, and TTLCache."""

from unittest.mock import MagicMock

import pytest

from src.core.config import get_settings
from src.infrastructure.db.repository import (
    chat_relationship_transaction,
    load_chat_relationships,
)
from src.infrastructure.utils.cache import TTLCache
from src.services.analytics_buffer import AnalyticsBuffer
from src.services.rp_service import RPService


def test_ttl_cache() -> None:
    """Test TTL cache insertion, retrieval, and expiration."""
    cache: TTLCache[int, str] = TTLCache(ttl_seconds=0.1, maxsize=2)
    cache.set(1, "Alpha")
    cache.set(2, "Beta")

    assert cache.get(1) == "Alpha"
    assert cache.get(2) == "Beta"

    # Test maxsize eviction
    cache.set(3, "Gamma")
    assert len(cache) == 2


@pytest.mark.asyncio
async def test_chat_relationship_transaction() -> None:
    """Test atomic mutation of chat relationship data via context manager."""
    test_chat_id = -888888888
    async with chat_relationship_transaction(test_chat_id) as data:
        data["chat_info"]["total_relationships"] = 5
        data["relationships"]["1_2"] = {"total_points": 10}

    reloaded = await load_chat_relationships(test_chat_id)
    assert reloaded["chat_info"]["total_relationships"] == 5
    assert reloaded["relationships"]["1_2"]["total_points"] == 10

    # Cleanup
    file_path = get_settings().RELATIONSHIPS_DIR / f"relationships_{test_chat_id}.json"
    if file_path.exists():
        file_path.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_analytics_buffer_record_and_flush() -> None:
    """Test memory accumulation and disk flush in AnalyticsBuffer."""
    buffer = AnalyticsBuffer()
    await buffer.record_message(
        chat_id=-1001,
        user_id=99999,
        name="Tester",
        username="test_user",
        text="Hello world test message",
    )
    await buffer.record_reaction(
        chat_id=-1001,
        user_id=99999,
        name="Tester",
        emoji="🔥",
    )

    # Flush deltas to disk
    await buffer.flush()


@pytest.mark.asyncio
async def test_rp_action_with_bot_username_suffix() -> None:
    """Test group command with bot username suffix e.g. /hug@BugaichyBot @target."""
    mock_from = MagicMock()
    mock_from.id = 12345
    mock_from.first_name = "Тарас"
    mock_from.username = "taras_user"

    result = await RPService.process_rp_action(
        message_text="/привітав@BugaichyBot @shadow_tar",
        from_user=mock_from,
        bot_username="BugaichyBot",
    )

    assert result is not None
    assert "Тарас" in result
    assert "Кійотаку" in result  # declined target name
    assert "привітав" in result
