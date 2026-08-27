"""Message dispatcher routing text, aliases, RP actions, and video links."""

import re
from datetime import datetime

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
from src.core.logger import get_logger
from src.infrastructure.constants.aliases import COMMAND_ALIASES
from src.infrastructure.constants.levels import ALL_COUPLE_COMMANDS
from src.infrastructure.db.repository import (
    load_chat_relationships,
    save_chat_relationships,
    update_user_cache,
)
from src.services.media_downloader.pipeline import download_and_send_video
from src.services.rp_service import RPService
from src.services.user_profiler import (
    get_all_active_chat_ids,
    record_live_message,
    rescan_and_sync_analytics,
)

logger = get_logger(__name__)


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

    # 1. Update user cache
    if from_user:
        first_name = from_user.first_name or from_user.username or "Користувач"
        if from_user.username:
            await update_user_cache(from_user.username, first_name, from_user.id)

    # 2. Owner secret commands in private messages (!скан, /rescan, !пиши, /say)
    if update.effective_chat and update.effective_chat.type == "private":
        sender_id = from_user.id if from_user else 0
        if sender_id == 1318789006:
            if re.match(r"^(?:!скан|/rescan|!синхрон)", msg_content, re.IGNORECASE):
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

            say_match = re.match(
                r"^(?:!пиши|/пиши|/say)\s+(.+)",
                msg_content,
                re.DOTALL | re.IGNORECASE,
            )
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

    # 3. Live analytics tracking in storage
    if from_user and update.effective_chat:
        chat_id = update.effective_chat.id
        try:
            await record_live_message(chat_id, from_user, msg_content)

            # Update daily_stats in chat relationships JSON
            chat_data = await load_chat_relationships(chat_id)
            today_str = datetime.now().strftime("%Y-%m-%d")
            daily = chat_data.setdefault("daily_stats", {})

            if daily.get("date") != today_str:
                daily["date"] = today_str
                daily["users"] = {}

            users_daily = daily.setdefault("users", {})
            u_key = str(from_user.id)

            if u_key not in users_daily:
                users_daily[u_key] = {
                    "name": from_user.first_name or from_user.username or "Користувач",
                    "user_id": from_user.id,
                    "messages": 0,
                    "chars": 0,
                }

            users_daily[u_key]["name"] = from_user.first_name or from_user.username or "Користувач"
            users_daily[u_key]["messages"] += 1
            users_daily[u_key]["chars"] += len(msg_content)

            await save_chat_relationships(chat_id, chat_data)
        except Exception as e:
            logger.warning(f"Error recording live analytics: {e}")

    if not msg_content:
        return

    # 4. Command and Roleplay processing (starts with / or !)
    if msg_content.startswith("/") or msg_content.startswith("!"):
        command_match = re.match(r"^[/\!](\S+)", msg_content)
        if command_match:
            raw_cmd = command_match.group(1).lower()
            command = COMMAND_ALIASES.get(raw_cmd, raw_cmd)

            # Routed aliases
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
                    target_match = re.search(r"@(\S+)", msg_content)
                    if target_match:
                        target = target_match.group(1)
                await handle_couple_command(update, context, command, target)
                return

            # Free-form RP actions
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

    # 5. Media URLs detection & download (TikTok / Instagram / Shorts / Twitter / X)
    raw_urls = re.findall(r"https?://[^\s>\"]+", msg_content, re.IGNORECASE)
    video_keywords = [
        "tiktok.com",
        "instagram.com",
        "instagr.am",
        "youtube.com/shorts",
        "youtu.be",
        "x.com",
        "twitter.com",
    ]

    for url in raw_urls:
        if any(kw in url.lower() for kw in video_keywords):
            await download_and_send_video(update, context, url)
            return

    # 6. Silent for all standard chat messages
    return
