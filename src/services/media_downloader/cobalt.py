"""Cobalt API fallback video downloader engine."""

from pathlib import Path

import aiohttp

from src.core.config import get_settings
from src.core.logger import get_logger
from src.services.http_client import get_http_session
from src.services.media_downloader.base import BaseMediaDownloader

logger = get_logger(__name__)


class CobaltDownloader(BaseMediaDownloader):
    """Fallback video downloader utilizing public Cobalt API instances."""

    async def download(self, url: str, target_dir: Path) -> Path | None:
        """Iterate over configured Cobalt instances to download media."""
        settings = get_settings()
        session = await get_http_session()
        timeout = aiohttp.ClientTimeout(total=15.0)

        payload = {
            "url": url,
            "vQuality": "720",
            "filenamePattern": "basic",
        }
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        for endpoint in settings.COBALT_INSTANCES:
            try:
                async with session.post(
                    endpoint, json=payload, headers=headers, timeout=timeout
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        direct_url = data.get("url")
                        if direct_url:
                            output_file = target_dir / "cobalt_video.mp4"
                            success = await self._stream_download_file(direct_url, output_file)
                            if (
                                success
                                and output_file.exists()
                                and output_file.stat().st_size > 1000
                            ):
                                logger.info(
                                    f"Successfully downloaded video via Cobalt ({endpoint}): {output_file}"
                                )
                                return output_file
            except Exception as e:
                logger.debug(f"Cobalt instance failed ({endpoint}): {e}")
                continue

        return None
