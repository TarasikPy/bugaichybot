"""Legacy storage bridge forwarding to src.infrastructure.db.repository."""

from src.infrastructure.db.repository import (
    load_chat_relationships,
    save_chat_relationships,
)

__all__ = [
    "load_chat_relationships",
    "save_chat_relationships",
]
