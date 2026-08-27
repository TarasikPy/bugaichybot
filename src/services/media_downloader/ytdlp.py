"""yt-dlp asynchronous media downloader engine."""

import asyncio
from pathlib import Path

import yt_dlp

from src.core.config import get_settings
from src.core.logger import get_logger
from src.services.media_downloader.base import BaseMediaDownloader

logger = get_logger(__name__)


def _sync_ytdlp_extract(
    url: str, output_template: str, max_size: int, user_agent: str
) -> Path | None:
    """Blocking yt-dlp download executed in worker thread."""
    ydl_opts = {
        "outtmpl": output_template,
        "format": (
            "bestvideo[ext=mp4][filesize<45M]+bestaudio[ext=m4a]/"
            "best[ext=mp4][filesize<45M]/"
            "best[filesize<45M]/best"
        ),
        "max_filesize": max_size,
        "no_playlist": True,
        "nocheckcertificate": True,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 15,
        "retries": 2,
        "user_agent": user_agent,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        target_dir = Path(output_template).parent
        downloaded = [
            f
            for f in target_dir.iterdir()
            if f.is_file() and f.suffix.lower() in (".mp4", ".mkv", ".webm", ".mov")
        ]
        return downloaded[0] if downloaded else None
    except Exception as e:
        logger.warning(f"yt-dlp download error for {url}: {e}")
        return None


class YtDlpDownloader(BaseMediaDownloader):
    """Local media extractor utilizing yt-dlp inside asyncio worker threads."""

    async def download(self, url: str, target_dir: Path) -> Path | None:
        """Asynchronously extract video with yt-dlp."""
        settings = get_settings()
        output_template = str(target_dir / "ytdlp_video.%(ext)s")

        return await asyncio.to_thread(
            _sync_ytdlp_extract,
            url=url,
            output_template=output_template,
            max_size=settings.MAX_VIDEO_SIZE_BYTES,
            user_agent=settings.DEFAULT_USER_AGENT,
        )
