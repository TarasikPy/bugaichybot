"""Legacy video downloader bridge forwarding to src.services.media_downloader."""

from src.services.media_downloader.pipeline import download_and_send_video

__all__ = [
    "download_and_send_video",
]
