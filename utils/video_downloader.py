import os
import shutil
import logging
import asyncio
import tempfile
import yt_dlp
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

def _sync_download(url: str, temp_dir: str) -> str:
    """Синхронне завантаження відео через бібліотеку yt_dlp"""
    output_template = os.path.join(temp_dir, "video.%(ext)s")
    ydl_opts = {
        'outtmpl': output_template,
        'format': 'b/best',
        'max_filesize': 50 * 1024 * 1024, # 50 MB limit
        'no_playlist': True,
        'nocheckcertificate': True,
        'quiet': True,
        'no_warnings': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    downloaded = [os.path.join(temp_dir, f) for f in os.listdir(temp_dir) if os.path.isfile(os.path.join(temp_dir, f))]
    return downloaded[0] if downloaded else ""

async def download_and_send_video(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str) -> bool:
    """Завантажує відео з TikTok, Reels, Shorts та надсилає у чат Telegram"""
    if not update.message:
        return False

    chat_id = update.effective_chat.id
    status_msg = None
    temp_dir = tempfile.mkdtemp(prefix="bugaichyk_video_")

    try:
        status_msg = await update.message.reply_text("⏬ <i>Бугайчик завантажує відео...</i>", parse_mode='HTML')

        # Викликаємо завантажувач у фоновому потоці
        video_path = await asyncio.to_thread(_sync_download, url, temp_dir)

        if video_path and os.path.exists(video_path):
            caption = "🍿 <b>О, чергова порція деградації під'їхала! Завантажив, щоб уся туса страждала разом із тобою.</b>"
            reply_id = update.message.message_id

            try:
                with open(video_path, 'rb') as vf:
                    await context.bot.send_video(
                        chat_id=chat_id,
                        video=vf,
                        caption=caption,
                        parse_mode='HTML',
                        reply_to_message_id=reply_id
                    )
            except Exception as vid_err:
                logger.warning(f"Не вдалося відправити як send_video ({vid_err}), пробуємо send_document...")
                with open(video_path, 'rb') as vf:
                    await context.bot.send_document(
                        chat_id=chat_id,
                        document=vf,
                        caption=caption,
                        parse_mode='HTML',
                        reply_to_message_id=reply_id
                    )

            if status_msg:
                await status_msg.delete()

            shutil.rmtree(temp_dir, ignore_errors=True)
            return True

    except Exception as e:
        logger.error(f"Помилка завантаження відео з {url}: {e}")

    if status_msg:
        try:
            await status_msg.delete()
        except Exception:
            pass

    shutil.rmtree(temp_dir, ignore_errors=True)
    await update.message.reply_text("🍿 О, знову деградація в стрічці? Легше з брейнротом, дітваки.")
    return False
