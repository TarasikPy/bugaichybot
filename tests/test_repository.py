"""Unit tests for repository data layer."""

import pytest

from src.infrastructure.db.repository import (
    load_chat_relationships,
    load_history_analytics,
    save_chat_relationships,
)


@pytest.mark.asyncio
async def test_load_history_analytics() -> None:
    """Verify chat analytics loads profiles properly."""
    data = load_history_analytics()
    assert isinstance(data, dict)
    profiles = data.get("profiles", {})
    assert len(profiles) > 0
    # Test known user profile
    assert "2005833676" in profiles or "1318789006" in profiles


@pytest.mark.asyncio
async def test_load_save_relationships() -> None:
    """Verify chat relationships loading and atomic saving."""
    test_chat_id = -999999999
    data = await load_chat_relationships(test_chat_id)
    assert "relationships" in data
    assert "chat_info" in data

    # Test save
    data["chat_info"]["total_relationships"] = 1
    await save_chat_relationships(test_chat_id, data)

    reloaded = await load_chat_relationships(test_chat_id)
    assert reloaded["chat_info"]["total_relationships"] == 1

    # Cleanup test file
    import os

    from src.core.config import get_settings

    test_file = get_settings().RELATIONSHIPS_DIR / f"relationships_{test_chat_id}.json"
    if test_file.exists():
        os.remove(test_file)
