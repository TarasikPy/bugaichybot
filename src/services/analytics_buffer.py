"""Asynchronous in-memory write-back buffer for high-throughput live analytics."""

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.core.logger import get_logger
from src.infrastructure.db.repository import (
    chat_relationship_transaction,
    load_live_analytics,
    save_live_analytics,
)

logger = get_logger(__name__)


@dataclass
class UserActivityDelta:
    """Accumulated activity delta for a single user."""

    user_id: int
    name: str = "Користувач"
    username: str = ""
    messages: int = 0
    chars: int = 0
    words: int = 0
    last_active: str = ""
    reactions_given: int = 0
    reactions_detail: dict[str, int] = field(default_factory=lambda: defaultdict(int))


class AnalyticsBuffer:
    """In-memory aggregator collecting live chat activity and flushing to disk in batches."""

    def __init__(self) -> None:
        self._user_deltas: dict[int, UserActivityDelta] = {}
        self._chat_user_deltas: dict[int, dict[int, dict[str, Any]]] = defaultdict(dict)
        self._lock = asyncio.Lock()
        self._flusher_task: asyncio.Task[None] | None = None
        self._running = False

    async def record_message(
        self,
        chat_id: int,
        user_id: int,
        name: str,
        username: str,
        text: str,
    ) -> None:
        """Accumulate message statistics in memory."""
        if not user_id:
            return

        now_time = datetime.now().strftime("%H:%M:%S")
        chars_count = len(text)
        words_count = len(text.split())

        async with self._lock:
            if user_id not in self._user_deltas:
                self._user_deltas[user_id] = UserActivityDelta(
                    user_id=user_id,
                    name=name,
                    username=username,
                    last_active=now_time,
                )

            delta = self._user_deltas[user_id]
            delta.name = name
            if username:
                delta.username = username
            delta.messages += 1
            delta.chars += chars_count
            delta.words += words_count
            delta.last_active = now_time

            chat_map = self._chat_user_deltas[chat_id]
            if user_id not in chat_map:
                chat_map[user_id] = {
                    "name": name,
                    "user_id": user_id,
                    "messages": 0,
                    "chars": 0,
                }
            c_stat = chat_map[user_id]
            c_stat["name"] = name
            c_stat["messages"] += 1
            c_stat["chars"] += chars_count

    async def record_reaction(
        self,
        chat_id: int,
        user_id: int,
        name: str,
        emoji: str,
    ) -> None:
        """Accumulate user reaction in memory."""
        if not user_id or not emoji:
            return

        now_time = datetime.now().strftime("%H:%M:%S")

        async with self._lock:
            if user_id not in self._user_deltas:
                self._user_deltas[user_id] = UserActivityDelta(
                    user_id=user_id,
                    name=name,
                    last_active=now_time,
                )

            delta = self._user_deltas[user_id]
            delta.name = name
            delta.last_active = now_time
            delta.reactions_given += 1
            delta.reactions_detail[emoji] = delta.reactions_detail.get(emoji, 0) + 1

    async def flush(self) -> None:
        """Atomically extract in-memory deltas and persist them to disk."""
        async with self._lock:
            if not self._user_deltas and not self._chat_user_deltas:
                return

            user_snapshot = dict(self._user_deltas)
            chat_snapshot = {cid: dict(udata) for cid, udata in self._chat_user_deltas.items()}

            self._user_deltas.clear()
            self._chat_user_deltas.clear()

        try:
            if user_snapshot:
                live_data = await load_live_analytics()
                today_str = datetime.now().strftime("%Y-%m-%d")
                if live_data.get("date") != today_str:
                    live_data = {"date": today_str, "users": {}}

                users = live_data.setdefault("users", {})
                for uid, delta in user_snapshot.items():
                    u_key = str(uid)
                    if u_key not in users:
                        users[u_key] = {
                            "user_id": uid,
                            "name": delta.name,
                            "username": delta.username,
                            "messages": 0,
                            "chars": 0,
                            "words": 0,
                            "last_active": delta.last_active,
                            "reactions_given": 0,
                            "reactions_detail": {},
                        }

                    u_stat = users[u_key]
                    u_stat["name"] = delta.name
                    if delta.username:
                        u_stat["username"] = delta.username
                    u_stat["messages"] += delta.messages
                    u_stat["chars"] += delta.chars
                    u_stat["words"] += delta.words
                    u_stat["last_active"] = delta.last_active
                    u_stat["reactions_given"] = (
                        u_stat.get("reactions_given", 0) + delta.reactions_given
                    )

                    rx_detail = u_stat.setdefault("reactions_detail", {})
                    for em, count in delta.reactions_detail.items():
                        rx_detail[em] = rx_detail.get(em, 0) + count

                await save_live_analytics(live_data)

            for cid, udata in chat_snapshot.items():
                if not udata:
                    continue
                today_str = datetime.now().strftime("%Y-%m-%d")
                async with chat_relationship_transaction(cid) as chat_data:
                    daily = chat_data.setdefault("daily_stats", {})
                    if daily.get("date") != today_str:
                        daily["date"] = today_str
                        daily["users"] = {}

                    users_daily = daily.setdefault("users", {})
                    for uid, stat in udata.items():
                        u_key = str(uid)
                        if u_key not in users_daily:
                            users_daily[u_key] = {
                                "name": stat["name"],
                                "user_id": uid,
                                "messages": 0,
                                "chars": 0,
                            }
                        users_daily[u_key]["name"] = stat["name"]
                        users_daily[u_key]["messages"] += stat["messages"]
                        users_daily[u_key]["chars"] += stat["chars"]

            logger.debug("AnalyticsBuffer successfully flushed to disk.")

        except Exception as e:
            logger.error(f"Error flushing AnalyticsBuffer to disk: {e}", exc_info=True)

    async def _periodic_flush_worker(self, interval_seconds: float) -> None:
        """Background worker triggering periodic disk flush."""
        logger.info(f"AnalyticsBuffer worker started (interval: {interval_seconds}s).")
        while self._running:
            try:
                await asyncio.sleep(interval_seconds)
                await self.flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Unexpected error in AnalyticsBuffer worker: {e}")

    def start(self, interval_seconds: float = 30.0) -> None:
        """Start the background flush task."""
        if not self._running:
            self._running = True
            self._flusher_task = asyncio.create_task(self._periodic_flush_worker(interval_seconds))

    async def stop(self) -> None:
        """Stop background worker and execute final flush."""
        if self._running:
            self._running = False
            if self._flusher_task:
                self._flusher_task.cancel()
                try:
                    await self._flusher_task
                except asyncio.CancelledError:
                    pass
                self._flusher_task = None
            # Guarantee final flush before process terminates
            await self.flush()
            logger.info("AnalyticsBuffer stopped and final flush completed.")


# Singleton instance
_analytics_buffer = AnalyticsBuffer()


def get_analytics_buffer() -> AnalyticsBuffer:
    """Return the global AnalyticsBuffer singleton."""
    return _analytics_buffer
