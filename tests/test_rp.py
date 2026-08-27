"""Unit tests for Roleplay (RP) action parsing."""

from unittest.mock import MagicMock

import pytest

from src.services.rp_service import RPService


@pytest.mark.asyncio
async def test_rp_action_reply() -> None:
    """Test RP action via reply to user message."""
    mock_from = MagicMock()
    mock_from.id = 1318789006
    mock_from.first_name = "Кійотака"
    mock_from.username = "shadow_tar"

    mock_reply = MagicMock()
    mock_reply.id = 1591084301
    mock_reply.first_name = "Сергій"
    mock_reply.username = "ftcserhiy"

    result = await RPService.process_rp_action(
        message_text="!обняв міцно",
        from_user=mock_from,
        reply_user=mock_reply,
    )

    assert result is not None
    assert "Кійотака" in result
    assert "Сергія" in result  # declined name
    assert "обняв" in result
    assert "міцно" in result


@pytest.mark.asyncio
async def test_rp_action_standalone() -> None:
    """Test standalone RP action without recipient."""
    mock_from = MagicMock()
    mock_from.id = 1318789006
    mock_from.first_name = "Кійотака"
    mock_from.username = "shadow_tar"

    result = await RPService.process_rp_action(
        message_text="!пішов спати",
        from_user=mock_from,
    )

    assert result is not None
    assert "Кійотака" in result
    assert "пішов спати" in result
