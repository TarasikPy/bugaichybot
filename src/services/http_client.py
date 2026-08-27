"""Centralized asynchronous HTTP client session manager using aiohttp."""

import asyncio

import aiohttp

from src.core.config import get_settings
from src.core.logger import get_logger

logger = get_logger(__name__)

_session: aiohttp.ClientSession | None = None
_session_lock = asyncio.Lock()


async def get_http_session() -> aiohttp.ClientSession:
    """Return or initialize the singleton aiohttp.ClientSession."""
    global _session
    if _session is None or _session.closed:
        async with _session_lock:
            if _session is None or _session.closed:
                settings = get_settings()
                connector = aiohttp.TCPConnector(
                    limit=100,
                    limit_per_host=20,
                    ttl_dns_cache=300,
                    enable_cleanup_closed=True,
                )
                timeout = aiohttp.ClientTimeout(
                    total=settings.HTTP_TIMEOUT_SECONDS,
                    connect=10.0,
                )
                _session = aiohttp.ClientSession(
                    connector=connector,
                    timeout=timeout,
                    headers=settings.default_headers,
                )
                logger.info("🌐 Centralized aiohttp.ClientSession initialized.")
    return _session


async def close_http_session() -> None:
    """Gracefully close the active aiohttp session."""
    global _session
    if _session and not _session.closed:
        logger.info("Closing aiohttp.ClientSession...")
        await _session.close()
        _session = None
