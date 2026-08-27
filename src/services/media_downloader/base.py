"""Abstract base class and streaming utilities for media downloaders."""

from abc import ABC, abstractmethod
from pathlib import Path

import aiofiles

from src.core.config import get_settings
from src.core.logger import get_logger
from src.services.http_client import get_http_session

logger = get_logger(__name__)


class BaseMediaDownloader(ABC):
    """Base interface for all social media video download engines."""

    @abstractmethod
    async def download(self, url: str, target_dir: Path) -> Path | None:
        """Attempt downloading video from given URL into target directory.

        Returns the Path to the downloaded file if successful, otherwise None.
        """
        pass

    async def _stream_download_file(
        self,
        direct_url: str,
        output_file: Path,
        max_size_bytes: int | None = None,
    ) -> bool:
        """Stream download a remote file with size bounds using aiohttp."""
        settings = get_settings()
        max_size = max_size_bytes or settings.MAX_VIDEO_SIZE_BYTES

        try:
            session = await get_http_session()
            async with session.get(direct_url, allow_redirects=True) as resp:
                if resp.status != 200:
                    logger.debug(f"HTTP {resp.status} while downloading from {direct_url}")
                    return False

                content_length = resp.headers.get("Content-Length")
                if content_length and int(content_length) > max_size:
                    logger.warning(f"File exceeds size limit: {content_length} bytes > {max_size}")
                    return False

                downloaded = 0
                async with aiofiles.open(output_file, "wb") as f:
                    async for chunk in resp.content.iter_chunked(65536):
                        downloaded += len(chunk)
                        if downloaded > max_size:
                            logger.warning(
                                f"Aborted download: exceeded size limit {max_size} bytes"
                            )
                            return False
                        await f.write(chunk)

                if output_file.exists() and output_file.stat().st_size > 1000:
                    return True
                return False
        except Exception as e:
            logger.warning(f"Error streaming media from {direct_url}: {e}")
            return False
