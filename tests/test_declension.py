"""Unit tests for Ukrainian name declension."""

from src.infrastructure.utils.declension import decline_name


def test_male_declension() -> None:
    """Test male names declension."""
    assert decline_name("Андрій") == "Андрія"
    assert decline_name("Сергій") == "Сергія"
    assert decline_name("Тарас") == "Тараса"
    assert decline_name("Кійотака") == "Кійотаку"
    assert decline_name("Микола") == "Миколу"


def test_female_declension() -> None:
    """Test female names declension."""
    assert decline_name("Марія") == "Марію"
    assert decline_name("Аліна") == "Аліну"
    assert decline_name("Маргарита") == "Маргариту"
    assert decline_name("Ольга") == "Ольгу"


def test_ascii_and_edge_cases() -> None:
    """Test ASCII nicknames and empty strings."""
    assert decline_name("shadow_tar") == "shadow_tar"
    assert decline_name("Alina") == "Alina"
    assert decline_name("") == ""
