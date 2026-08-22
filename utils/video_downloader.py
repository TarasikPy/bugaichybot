import os
import re
import shutil
import logging
import asyncio
import tempfile
from typing import Optional
import httpx
import yt_dlp
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# Семафор для обмеження кількості одночасних завантажень (запобігає навантаженню на сервер)
_download_semaphore = asyncio.Semaphore(3)

# Список публічних інстансів Cobalt API для резервного завантаження
COBALT_INSTANCES = [
    "https://api.cobalt.tools/api/json",
    "https://cobalt-api.kwiatekm.tokyo/api/json",
    "https://co.wuk.sh/api/json"
]

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "*/*",
}

async def _stream_download_file(client: httpx.AsyncClient, direct_url: str, output_path: str, max_size_bytes: int = 50 * 1024 * 1024) -> bool:
    """Завантажує файл потоком через HTTP з контролем максимального розміру"""
    try:
        async with client.stream("GET", direct_url, headers=DEFAULT_HEADERS, timeout=30.0, follow_redirects=True) as response:
            if response.status_code != 200:
                return False
            
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > max_size_bytes:
                logger.warning(f"Файл занадто великий: {content_length} байт > {max_size_bytes}")
                return False

            downloaded = 0
            with open(output_path, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=65536):
                    downloaded += len(chunk)
                    if downloaded > max_size_bytes:
                        logger.warning("Перевищено ліміт розміру під час завантаження.")
                        return False
                    f.write(chunk)
            return True
    except Exception as e:
        logger.warning(f"Помилка скачування потоку з {direct_url}: {e}")
        return False

async def _download_tiktok_tikwm(url: str, temp_dir: str) -> Optional[str]:
    """Швидке завантаження TikTok без водяного знака через TikWM API (<1-2 сек)"""
    try:
        api_url = f"https://www.tikwm.com/api/?url={url}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(api_url, headers=DEFAULT_HEADERS)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == 0:
                    video_info = data.get("data", {})
                    direct_url = video_info.get("play") or video_info.get("wmplay")
                    if direct_url:
                        output_path = os.path.join(temp_dir, "tiktok_video.mp4")
                        success = await _stream_download_file(client, direct_url, output_path)
                        if success and os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                            return output_path
    except Exception as e:
        logger.warning(f"TikWM Engine не зміг обробити {url}: {e}")
    return None

async def _download_twitter_api(url: str, temp_dir: str) -> Optional[str]:
    """Швидке завантаження відео з Twitter / X через fxtwitter / vxtwitter API"""
    try:
        clean_url = url
        clean_url = clean_url.replace("twitter.com", "api.fxtwitter.com").replace("x.com", "api.fxtwitter.com")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(clean_url, headers=DEFAULT_HEADERS)
            if resp.status_code == 200:
                data = resp.json()
                tweet = data.get("tweet", {})
                media = tweet.get("media", {})
                videos = media.get("videos", [])
                if videos:
                    direct_url = videos[0].get("url")
                    if direct_url:
                        output_path = os.path.join(temp_dir, "twitter_video.mp4")
                        success = await _stream_download_file(client, direct_url, output_path)
                        if success and os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                            return output_path
    except Exception as e:
        logger.warning(f"Twitter API Engine не зміг обробити {url}: {e}")
    return None

async def _download_cobalt(url: str, temp_dir: str) -> Optional[str]:
    """Резервне завантаження через Cobalt API (підтримує Reels, TikTok, Shorts, Twitter)"""
    for api_endpoint in COBALT_INSTANCES:
        try:
            payload = {
                "url": url,
                "vQuality": "720",
                "filenamePattern": "basic"
            }
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": DEFAULT_HEADERS["User-Agent"]
            }
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(api_endpoint, json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    direct_url = data.get("url")
                    if direct_url:
                        output_path = os.path.join(temp_dir, "cobalt_video.mp4")
                        success = await _stream_download_file(client, direct_url, output_path)
                        if success and os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                            return output_path
        except Exception as e:
            logger.debug(f"Cobalt instance {api_endpoint} failed: {e}")
            continue
    return None

def _sync_ytdlp_download(url: str, temp_dir: str) -> Optional[str]:
    """Оптимізоване локальне завантаження через yt-dlp з контролем розміру до 48MB"""
    output_template = os.path.join(temp_dir, "ytdlp_video.%(ext)s")
    ydl_opts = {
        'outtmpl': output_template,
        'format': 'bestvideo[ext=mp4][filesize<45M]+bestaudio[ext=m4a]/best[ext=mp4][filesize<45M]/best[filesize<45M]/best',
        'max_filesize': 50 * 1024 * 1024,
        'no_playlist': True,
        'nocheckcertificate': True,
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 15,
        'retries': 2,
        'user_agent': DEFAULT_HEADERS['User-Agent'],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        downloaded = [
            os.path.join(temp_dir, f)
            for f in os.listdir(temp_dir)
            if os.path.isfile(os.path.join(temp_dir, f)) and f.endswith(('.mp4', '.mkv', '.webm', '.mov'))
        ]
        return downloaded[0] if downloaded else None
    except Exception as e:
        logger.warning(f"yt-dlp error for {url}: {e}")
        return None

async def _download_video_pipeline(url: str, temp_dir: str) -> Optional[str]:
    """Багаторівневий конвеєр завантаження: Direct API -> yt-dlp -> Cobalt Fallback"""
    url_lower = url.lower()

    # 1. TikTok: першим пробуємо блискавичний TikWM API
    if "tiktok.com" in url_lower:
        video_path = await _download_tiktok_tikwm(url, temp_dir)
        if video_path:
            return video_path

    # 2. Twitter / X: першим пробуємо fxtwitter API
    if "twitter.com" in url_lower or "x.com" in url_lower:
        video_path = await _download_twitter_api(url, temp_dir)
        if video_path:
            return video_path

    # 3. Основний локальний yt-dlp (Reels, Shorts, YouTube, тощо)
    video_path = await asyncio.to_thread(_sync_ytdlp_download, url, temp_dir)
    if video_path and os.path.exists(video_path):
        return video_path

    # 4. Резервний рівень: Cobalt API
    video_path = await _download_cobalt(url, temp_dir)
    if video_path and os.path.exists(video_path):
        return video_path

    return None

async def download_and_send_video(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str) -> bool:
    """Головна точка входу: швидке та надійне завантаження і відправка відео у чат"""
    if not update.message:
        return False

    chat_id = update.effective_chat.id
    reply_id = update.message.message_id
    status_msg = None
    temp_dir = tempfile.mkdtemp(prefix="vanilla_video_")

    async with _download_semaphore:
        try:
            status_msg = await update.message.reply_text("⏳ <i>Завантажую відео...</i>", parse_mode='HTML')

            video_path = await _download_video_pipeline(url, temp_dir)

            if video_path and os.path.exists(video_path):
                file_size = os.path.getsize(video_path)
                if file_size > 50 * 1024 * 1024:
                    logger.warning(f"Відео перевищує ліміт Telegram 50MB ({file_size} байт)")
                    if status_msg:
                        await status_msg.delete()
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    return False

                try:
                    with open(video_path, 'rb') as vf:
                        await context.bot.send_video(
                            chat_id=chat_id,
                            video=vf,
                            reply_to_message_id=reply_id,
                            supports_streaming=True
                        )
                except Exception as vid_err:
                    logger.warning(f"Не вдалося відправити як send_video ({vid_err}), пробуємо як документ...")
                    with open(video_path, 'rb') as vf:
                        await context.bot.send_document(
                            chat_id=chat_id,
                            document=vf,
                            reply_to_message_id=reply_id
                        )

                if status_msg:
                    try:
                        await status_msg.delete()
                    except Exception:
                        pass

                shutil.rmtree(temp_dir, ignore_errors=True)
                return True

        except Exception as e:
            logger.error(f"Помилка у download_and_send_video для {url}: {e}")

        finally:
            if status_msg:
                try:
                    await status_msg.delete()
                except Exception:
                    pass
            shutil.rmtree(temp_dir, ignore_errors=True)

    return False

