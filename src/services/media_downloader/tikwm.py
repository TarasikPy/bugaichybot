"""TikWM high-speed watermark-free TikTok downloader engine."""

from pathlib import Path

import aiohttp

from src.core.logger import get_logger
from src.services.http_client import get_http_session
from src.services.media_downloader.base import BaseMediaDownloader

logger = get_logger(__name__)


class TikWMDownloader(BaseMediaDownloader):
    """Direct API downloader for TikTok videos without watermarks."""

    async def download(self, url: str, target_dir: Path) -> Path | None:
        """Download TikTok video via TikWM API."""
        try:
            session = await get_http_session()
            api_url = f"https://www.tikwm.com/api/?url={url}"
            timeout = aiohttp.ClientTimeout(total=10.0)

            async with session.get(api_url, timeout=timeout) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                if data.get("code") == 0:
                    video_info = data.get("data", {})
                    direct_url = video_info.get("play") or video_info.get("wmplay")
                    if direct_url:
                        output_file = target_dir / "tiktok_video.mp4"
                        success = await self._stream_download_file(direct_url, output_file)
                        if success and output_file.exists() and output_file.stat().st_size > 1000:
                            logger.info(
                                f"Successfully downloaded TikTok video via TikWM: {output_file}"
                            )
                            return output_file
        except Exception as e:
            logger.warning(f"TikWM engine error for {url}: {e}")
        return None
