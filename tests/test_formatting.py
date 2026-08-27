"""Unit tests for formatting helpers."""

from src.infrastructure.utils.formatting import (
    create_user_link,
    escape_html,
    escape_markdown,
    format_duration,
)


def test_escape_html() -> None:
    """Test HTML escaping of dangerous symbols."""
    assert (
        escape_html("<script>alert('xss')</script>")
        == "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;"
    )
    assert escape_html("Tom & Jerry") == "Tom &amp; Jerry"
    assert escape_html(None) == ""


def test_escape_markdown() -> None:
    """Test Markdown escaping."""
    assert (
        escape_markdown("*hello* _world_ [link]`code`") == r"\*hello\* \_world\_ \[link\]\`code\`"
    )
    assert escape_markdown(None) == ""


def test_create_user_link() -> None:
    """Test user link creation with tg:// user links."""
    link = create_user_link(123456, "Тарас")
    assert link == '<a href="tg://user?id=123456">Тарас</a>'

    bold = create_user_link(None, "Гість")
    assert bold == "<b>Гість</b>"

    # Inverted parameter order compatibility test
    inverted = create_user_link("Кійотака", 1318789006)
    assert inverted == '<a href="tg://user?id=1318789006">Кійотака</a>'


def test_format_duration() -> None:
    """Test duration formatting output."""
    res = format_duration("2020-01-01T00:00:00")
    assert "рік" in res or "років" in res
