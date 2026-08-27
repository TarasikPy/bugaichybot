"""Media download pipeline coordinating cascading downloaders and Telegram delivery."""

import asyncio
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from src.core.config import get_settings
from src.core.logger import get_logger
from src.infrastructure.utils.temp_files import async_temp_directory
from src.services.media_downloader.cobalt import CobaltDownloader
from src.services.media_downloader.tikwm import TikWMDownloader
from src.services.media_downloader.twitter import TwitterDownloader
from src.services.media_downloader.ytdlp import YtDlpDownloader

logger = get_logger(__name__)

# Concurrency semaphore for media downloads
_download_semaphore = asyncio.Semaphore(3)


class MediaDownloadPipeline:
    """Cascade orchestrator trying direct APIs first, yt-dlp second, and Cobalt fallback."""

    def __init__(self) -> None:
        self.tikwm = TikWMDownloader()
        self.twitter = TwitterDownloader()
        self.ytdlp = YtDlpDownloader()
        self.cobalt = CobaltDownloader()

    async def execute(self, url: str, temp_dir: Path) -> Path | None:
        """Execute cascading video download into temp_dir."""
        url_lower = url.lower()

        # 1. TikTok fast direct API
        if "tiktok.com" in url_lower:
            path = await self.tikwm.download(url, temp_dir)
            if path and path.exists():
                return path

        # 2. Twitter / X fast direct API
        if "twitter.com" in url_lower or "x.com" in url_lower:
            path = await self.twitter.download(url, temp_dir)
            if path and path.exists():
                return path

        # 3. yt-dlp local extractor (Instagram Reels, YouTube Shorts, etc.)
        path = await self.ytdlp.download(url, temp_dir)
        if path and path.exists():
            return path

        # 4. Cobalt API fallback
        path = await self.cobalt.download(url, temp_dir)
        if path and path.exists():
            return path

        return None


_pipeline = MediaDownloadPipeline()


async def download_and_send_video(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    url: str,
) -> bool:
    """Download video from URL and send to Telegram chat with automatic cleanup."""
    if not update.message or not update.effective_chat:
        return False

    chat_id = update.effective_chat.id
    reply_id = update.message.message_id
    settings = get_settings()

    async with _download_semaphore:
        status_msg = None
        try:
            status_msg = await update.message.reply_text(
                "⏳ <i>Завантажую відео...</i>",
                parse_mode="HTML",
            )
        except Exception:
            status_msg = None

        try:
            async with async_temp_directory(prefix="vanilla_video_") as temp_dir:
                video_path = await _pipeline.execute(url, temp_dir)

                if not video_path or not video_path.exists():
                    logger.warning(f"Failed to download video from {url}")
                    return False

                file_size = video_path.stat().st_size
                if file_size > settings.MAX_VIDEO_SIZE_BYTES:
                    logger.warning(
                        f"Video file exceeds Telegram limit: {file_size} bytes > {settings.MAX_VIDEO_SIZE_BYTES}"
                    )
                    return False

                # Send video to chat
                with open(video_path, "rb") as vf:
                    try:
                        await context.bot.send_video(
                            chat_id=chat_id,
                            video=vf,
                            reply_to_message_id=reply_id,
                            supports_streaming=True,
                        )
                    except Exception as vid_err:
                        logger.warning(
                            f"Failed to send as video ({vid_err}), attempting document upload..."
                        )
                        vf.seek(0)
                        await context.bot.send_document(
                            chat_id=chat_id,
                            document=vf,
                            reply_to_message_id=reply_id,
                        )

                return True

        except Exception as e:
            logger.error(f"Error in download_and_send_video for {url}: {e}")
            return False

        finally:
            if status_msg:
                try:
                    await status_msg.delete()
                except Exception:
                    pass
