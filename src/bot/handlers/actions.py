"""Message dispatcher routing text, aliases, RP actions, and video links."""

import re

from telegram import Update
from telegram.ext import ContextTypes

from src.bot.handlers.analytics import chat_stats_command, id_command, profile_command
from src.bot.handlers.mechanics import risk_command
from src.bot.handlers.relationships import (
    breakup_command,
    handle_couple_command,
    my_relationships_command,
    relationships_command,
)
from src.bot.handlers.weather import weather_command
from src.core.config import get_settings
from src.core.logger import get_logger
from src.infrastructure.constants.aliases import COMMAND_ALIASES
from src.infrastructure.constants.levels import ALL_COUPLE_COMMANDS
from src.infrastructure.db.repository import update_user_cache
from src.services.analytics_buffer import get_analytics_buffer
from src.services.media_downloader.pipeline import download_and_send_video
from src.services.rp_service import RPService
from src.services.user_profiler import (
    add_chat_recent_message,
    get_all_active_chat_ids,
    rescan_and_sync_analytics,
    resolve_clean_user_name,
)

logger = get_logger(__name__)

# Precompiled regex patterns
_RE_RESCAN = re.compile(r"^(?:!скан|/rescan|!синхрон)", re.IGNORECASE)
_RE_SAY = re.compile(r"^(?:!пиши|/пиши|/say)\s+(.+)", re.DOTALL | re.IGNORECASE)
_RE_COMMAND_PREFIX = re.compile(r"^[/\!](\S+)")
_RE_TARGET_MENTION = re.compile(r"@(\S+)")
_RE_URL_DETECT = re.compile(r"https?://[^\s>\"]+", re.IGNORECASE)

_VIDEO_KEYWORDS = (
    "tiktok.com",
    "instagram.com",
    "instagr.am",
    "youtube.com/shorts",
    "youtu.be",
    "x.com",
    "twitter.com",
)


async def _send_html_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str) -> None:
    """Send an HTML-formatted message with fallback to plain text."""
    try:
        await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
    except Exception as e:
        logger.warning(f"Failed to send HTML message ({e}), falling back to plain text")
        plain_text = re.sub(r"<[^>]*>", "", text)
        await context.bot.send_message(chat_id=chat_id, text=plain_text)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Master handler for incoming messages: analytics, RP actions, and media download."""
    if not update.message:
        return

    from_user = update.message.from_user
    msg_content = (update.message.text or update.message.caption or "").strip()
    settings = get_settings()

    if from_user and from_user.username:
        first_name = from_user.first_name or from_user.username or "Користувач"
        await update_user_cache(from_user.username, first_name, from_user.id)

    if update.effective_chat and update.effective_chat.type == "private" and from_user:
        if from_user.id in settings.ADMIN_USER_IDS:
            if _RE_RESCAN.match(msg_content):
                counts = rescan_and_sync_analytics()
                info = (
                    "\n".join([f"• <b>{k}</b>: {v} смс" for k, v in counts.items()])
                    if counts
                    else "Немає нових повідомлень."
                )
                await update.message.reply_text(
                    f"📊 <b>Аналітику та статистику успішно проскановано й оновлено!</b>\n\n{info}",
                    parse_mode="HTML",
                )
                return

            say_match = _RE_SAY.match(msg_content)
            if say_match:
                broadcast_text = say_match.group(1).strip()
                target_chats = get_all_active_chat_ids()
                sent_count = 0

                for cid in target_chats:
                    try:
                        await context.bot.send_message(
                            chat_id=cid,
                            text=broadcast_text,
                            parse_mode="HTML",
                        )
                        sent_count += 1
                    except Exception as e:
                        logger.error(f"Broadcast error in chat {cid}: {e}")

                if sent_count > 0:
                    await update.message.reply_text(
                        f"✅ <b>Повідомлення анонімно відправлено в {sent_count} чат(ів)!</b>",
                        parse_mode="HTML",
                    )
                return

    if from_user and update.effective_chat and not from_user.is_bot:
        chat_id = update.effective_chat.id
        clean_name = resolve_clean_user_name(from_user)
        username = from_user.username or ""

        add_chat_recent_message(chat_id, clean_name, msg_content)

        buffer = get_analytics_buffer()
        await buffer.record_message(
            chat_id=chat_id,
            user_id=from_user.id,
            name=clean_name,
            username=username,
            text=msg_content,
        )

    if not msg_content:
        return

    if msg_content.startswith("/") or msg_content.startswith("!"):
        command_match = _RE_COMMAND_PREFIX.match(msg_content)
        if command_match:
            raw_cmd = command_match.group(1).lower()
            command = COMMAND_ALIASES.get(raw_cmd, raw_cmd)

            if command == "relationships":
                await relationships_command(update, context)
                return
            elif command == "myrelationships":
                await my_relationships_command(update, context)
                return
            elif command == "chatstats":
                await chat_stats_command(update, context)
                return
            elif command == "profile":
                await profile_command(update, context)
                return
            elif command == "breakup":
                await breakup_command(update, context)
                return
            elif command == "weather":
                await weather_command(update, context)
                return
            elif command == "risk":
                await risk_command(update, context)
                return
            elif command in ("id", "whois"):
                await id_command(update, context)
                return

            if command in ALL_COUPLE_COMMANDS or command in ("dating", "trio"):
                target = None
                if "@" in msg_content:
                    target_match = _RE_TARGET_MENTION.search(msg_content)
                    if target_match:
                        target = target_match.group(1)
                await handle_couple_command(update, context, command, target)
                return

            try:
                await update.message.delete()
            except Exception:
                pass

            reply_user = (
                update.message.reply_to_message.from_user
                if update.message.reply_to_message
                else None
            )
            rp_result = await RPService.process_rp_action(
                message_text=msg_content,
                from_user=from_user,
                reply_user=reply_user,
                entities=update.message.entities,
                bot_username=context.bot.username,
            )
            if rp_result and update.effective_chat:
                await _send_html_message(context, update.effective_chat.id, rp_result)
        return

    raw_urls = _RE_URL_DETECT.findall(msg_content)
    for url in raw_urls:
        if any(kw in url.lower() for kw in _VIDEO_KEYWORDS):
            await download_and_send_video(update, context, url)
            return

    return
