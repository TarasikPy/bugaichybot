"""Unit tests for dating and relationship mechanics."""

from src.infrastructure.constants.levels import RELATIONSHIP_LEVELS
from src.services.dating_service import get_relationship_level


def test_relationship_levels_progression() -> None:
    """Verify points progression across all levels."""
    assert get_relationship_level(0) == 0
    assert get_relationship_level(9) == 0
    assert get_relationship_level(10) == 1
    assert get_relationship_level(25) == 2
    assert get_relationship_level(75) == 4
    assert get_relationship_level(300) == 9
    assert get_relationship_level(9999) == 9


def test_relationship_levels_descriptions() -> None:
    """Verify each level has valid non-empty fields."""
    for _lvl_idx, info in RELATIONSHIP_LEVELS.items():
        assert "name" in info
        assert "emoji" in info
        assert "required_points" in info
        assert "description" in info
