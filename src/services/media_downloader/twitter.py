"""Twitter / X fast media downloader engine using fxTwitter API."""

from pathlib import Path

import aiohttp

from src.core.logger import get_logger
from src.services.http_client import get_http_session
from src.services.media_downloader.base import BaseMediaDownloader

logger = get_logger(__name__)


class TwitterDownloader(BaseMediaDownloader):
    """Direct API downloader for Twitter/X videos via fxtwitter."""

    async def download(self, url: str, target_dir: Path) -> Path | None:
        """Download Twitter/X video via fxtwitter API."""
        try:
            clean_url = url.replace("twitter.com", "api.fxtwitter.com").replace(
                "x.com", "api.fxtwitter.com"
            )
            session = await get_http_session()
            timeout = aiohttp.ClientTimeout(total=10.0)

            async with session.get(clean_url, timeout=timeout) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                tweet = data.get("tweet", {})
                media = tweet.get("media", {})
                videos = media.get("videos", [])
                if videos:
                    direct_url = videos[0].get("url")
                    if direct_url:
                        output_file = target_dir / "twitter_video.mp4"
                        success = await self._stream_download_file(direct_url, output_file)
                        if success and output_file.exists() and output_file.stat().st_size > 1000:
                            logger.info(
                                f"Successfully downloaded Twitter video via API: {output_file}"
                            )
                            return output_file
        except Exception as e:
            logger.warning(f"Twitter API engine error for {url}: {e}")
        return None
