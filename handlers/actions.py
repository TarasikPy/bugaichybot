import re
import asyncio
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes

from config.names import USERS_MAP
from config.levels import ALL_COUPLE_COMMANDS, VALID_COMMANDS
from utils.helpers import (
    decline_name,
    create_user_link,
    escape_html,
    send_safe_html_reply,
    resolve_clean_user_name,
    format_ai_response_to_html
)
from utils.bugaichyk_ai import (
    get_bugaichyk_news_commentary,
    get_bugaichyk_chat_reply
)
from storage.analytics_db import (
    get_recent_chat_messages,
    record_live_message,
    rescan_and_sync_analytics,
    get_all_active_chat_ids
)
from storage.user_cache import update_user_cache, get_user_info_by_username
from storage.json_db import load_chat_relationships, save_chat_relationships
from utils.video_downloader import download_and_send_video

from handlers.relationships import relationships_command, my_relationships_command, breakup_command, handle_couple_command
from handlers.analytics import chat_stats_command, profile_command
from handlers.weather import weather_command
from handlers.mechanics import roast_command, judge_command, quote_command, risk_command

logger = logging.getLogger(__name__)

import random

# Мапінг українських аліасів для зручності користувачів
COMMAND_ALIASES = {
    'пропозиція': 'dating',
    'стосунки': 'relationships',
    'моїстосунки': 'myrelationships',
    'стата': 'chatstats',
    'профіль': 'profile',
    'profile': 'profile',
    'розлучення': 'breakup',
    'розрив': 'breakup',
    'допомога': 'commands',
    'погода': 'weather',
    'weather': 'weather',
    'roast': 'roast',
    'прожарка': 'roast',
    'judge': 'judge',
    'суд': 'judge',
    'цитата': 'quote',
    'мудрість': 'quote',
    'quote': 'quote',
    'ризик': 'risk',
    'рулетка': 'risk',
    'risk': 'risk',
    'ід': 'id',
    'id': 'id',
    'whois': 'id',
    'інфо': 'id',
}

async def _send_html_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str) -> None:
    """Відправляє повідомлення у чат у форматі HTML з fallback на чистий текст"""
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode='HTML'
        )
    except Exception as e:
        logger.warning(f"Не вдалося відправити HTML повідомлення ({e}), відправляємо чистий текст")
        plain_text = re.sub(r'<[^>]*>', '', text)
        await context.bot.send_message(
            chat_id=chat_id,
            text=plain_text
        )

async def handle_action_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробляє звичайні команди дій з підтримкою REPLY (відповіді на повідомлення), @username згадок, USERS_MAP та клікабельних HTML посилань tg://user?id="""
    if not update.message:
        return

    message_text = update.message.text.strip()
    from_user = update.message.from_user
    bot_username = context.bot.username

    sender_id = from_user.id if from_user else None
    sender_username = from_user.username.lower() if from_user and from_user.username else ""

    # Ім'я відправника з USERS_MAP або first_name
    if sender_username and sender_username in USERS_MAP:
        sender_name = USERS_MAP[sender_username]
    else:
        sender_name = from_user.first_name or from_user.username or "Користувач" if from_user else "Користувач"

    # Завжди оновлюємо динамічний кеш юзерів
    if from_user and from_user.username:
        await update_user_cache(from_user.username, sender_name, sender_id)

    # Намагаємося видалити вихідне повідомлення користувача (для чистоти чату)
    try:
        await update.message.delete()
    except Exception as e:
        logger.warning(f"Не вдалося видалити повідомлення: {e}")

    if not (message_text.startswith('/') or message_text.startswith('!')):
        return

    target_user_id = None
    target_display_name = None
    action = ""
    rest_text = ""

    # ВАРІАНТ А: Дія через REPLY (Відповідь на повідомлення користувача)
    if update.message.reply_to_message and update.message.reply_to_message.from_user:
        reply_user = update.message.reply_to_message.from_user
        target_user_id = reply_user.id

        if reply_user.username and reply_user.username.lower() in USERS_MAP:
            target_display_name = USERS_MAP[reply_user.username.lower()]
        else:
            target_display_name = reply_user.first_name or reply_user.username or "Користувач"

        # Парсимо дію та додатковий текст (наприклад "!вдарив лопатою по голові")
        match_reply = re.match(r'^[/\!](\S+)\s*(.*)$', message_text, re.DOTALL)
        if match_reply:
            action = match_reply.group(1).strip()
            rest_text = match_reply.group(2).strip()

    # ВАРІАНТ Б: Дія через ЗГАДКУ (@username або entities)
    elif '@' in message_text:
        pattern = r'^[/\!]([^@]+?)\s*@([^\s]+)(.*)$'
        match_mention = re.match(pattern, message_text, re.DOTALL)

        if match_mention:
            action = match_mention.group(1).strip()
            raw_target = match_mention.group(2).strip().lstrip('@')
            rest_text = match_mention.group(3).strip() if match_mention.group(3) else ""

            # а) Перевірка text_mention в entities
            if update.message.entities:
                for entity in update.message.entities:
                    if entity.type == 'text_mention' and entity.user:
                        target_user_id = entity.user.id
                        target_display_name = entity.user.first_name or entity.user.username
                        break

            # б) Пошук у статичному USERS_MAP
            if not target_display_name and raw_target.lower() in USERS_MAP:
                target_display_name = USERS_MAP[raw_target.lower()]

            # в) Пошук у динамічному кеші юзерів
            if not target_user_id or not target_display_name:
                cached_name, cached_id = await get_user_info_by_username(raw_target)
                if cached_name and not target_display_name:
                    target_display_name = cached_name
                if cached_id and not target_user_id:
                    target_user_id = cached_id

            # г) Fallback
            if not target_display_name:
                target_display_name = raw_target

    # ВАРІАНТ В: Дії без отримувача
    else:
        action_match = re.match(r'^[/\!](.+)$', message_text)
        if action_match:
            action_text = action_match.group(1).strip()
            first_word = action_text.split()[0] if action_text.split() else action_text
            if first_word not in ALL_COUPLE_COMMANDS and first_word not in VALID_COMMANDS:
                sender_link = create_user_link(sender_id, sender_name)
                response = f"✨ {sender_link} {escape_html(action_text)}"

                await _send_html_message(context, update.effective_chat.id, response)
                return

    if not action or action in ALL_COUPLE_COMMANDS:
        return

    # Захист від виконання дії на боті
    if bot_username and target_display_name and target_display_name.lower() == bot_username.lower():
        await _send_html_message(context, update.effective_chat.id, "🤖 На мені не можна виконувати дії!")
        return

    # Відмінюємо ім'я отримувача ("Арма" -> "Арму", "Сергій" -> "Сергія")
    target_declined = decline_name(target_display_name) if target_display_name else ""

    # Генеруємо HTML-посилання для ВІДПРАВНИКА та ОТРИМУВАЧА через create_user_link
    sender_link = create_user_link(sender_id, sender_name)
    target_link = create_user_link(target_user_id, target_declined)

    # Формування підсумкового речення з клікабельними посиланнями
    response = f"✨ {sender_link} {escape_html(action)} {target_link}"

    if rest_text:
        response += f" {escape_html(rest_text)}"

    await _send_html_message(context, update.effective_chat.id, response)

MEDIA_GROUP_BUFFERS = {}

async def process_media_group_after_delay(media_group_id: str, delay: float = 1.0) -> None:
    """Очікує 1 секунду, щоб назбирати весь підпис з усіх 10 відео альбому, і робить ОДНУ відповідь"""
    await asyncio.sleep(delay)

    group_data = MEDIA_GROUP_BUFFERS.pop(media_group_id, None)
    if not group_data:
        return

    update = group_data["update"]
    msg_content = group_data["text"].strip()

    input_text = msg_content if msg_content else "[Користувач переслав медіа/файл/пост без тексту]"
    comment = await get_bugaichyk_news_commentary(input_text)
    if comment:
        await send_safe_html_reply(update, comment)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Головний обробник текстових повідомлень з підтримкою кешування юзерів, трекінгу активності та префіксів / та !"""
    if not update.message:
        return

    # Оновлюємо кеш юзернейма та first_name при будь-якому повідомленні
    sender_name = resolve_clean_user_name(update.message.from_user) if update.message.from_user else "Користувач"
    if update.message.from_user:
        user = update.message.from_user
        first_name = user.first_name or user.username or "Користувач"
        if user.username:
            await update_user_cache(user.username, first_name, user.id)

    # Живий трекінг статистики у storage/analytics_db.py
    msg_content = (update.message.text or update.message.caption or "").strip()

    # 0. Перевірка на таємні команди від власника в ЛС бота (!пиши, !скан, /rescan)
    if update.effective_chat.type == 'private':
        sender_id = update.message.from_user.id if update.message and update.message.from_user else 0
        if sender_id == 1318789006:
            # Таємна команда пересканування статистики для власника
            if re.match(r'^(?:!скан|/rescan|!синхрон)', msg_content, re.IGNORECASE):
                counts = rescan_and_sync_analytics()
                info = "\n".join([f"• <b>{k}</b>: {v} смс" for k, v in counts.items()]) if counts else "Немає нових повідомлень."
                await update.message.reply_text(f"📊 <b>Аналітику та статистику успішно проскановано й оновлено!</b>\n\n{info}", parse_mode='HTML')
                return

        say_match = re.match(r'^(?:!пиши|/пиши|/say)\s+(.+)', msg_content, re.DOTALL | re.IGNORECASE)
        if say_match:
            if sender_id != 1318789006:
                return  # Мовчки ігноруємо для всіх інших користувачів

            broadcast_text = say_match.group(1).strip()
            formatted_text = format_ai_response_to_html(broadcast_text)
            target_chats = get_all_active_chat_ids()
            sent_count = 0

            for cid in target_chats:
                try:
                    await context.bot.send_message(chat_id=cid, text=formatted_text, parse_mode='HTML')
                    sent_count += 1
                except Exception as e:
                    logger.error(f"Помилка трансляції в {cid}: {e}")

            if sent_count > 0:
                await update.message.reply_text(f"✅ <b>Повідомлення анонімно відправлено в {sent_count} чат(ів)!</b>", parse_mode='HTML')
            return

    if update.message.from_user and update.effective_chat:
        chat_id = update.effective_chat.id
        user = update.message.from_user

        try:
            await record_live_message(chat_id, user, msg_content)

            # Також оновлюємо сумісний daily_stats у relationships_chats
            chat_data = await load_chat_relationships(chat_id)
            today_str = datetime.now().strftime('%Y-%m-%d')
            daily = chat_data.setdefault('daily_stats', {})

            if daily.get('date') != today_str:
                daily['date'] = today_str
                daily['users'] = {}

            users_daily = daily.setdefault('users', {})
            u_key = str(user.id)

            if u_key not in users_daily:
                users_daily[u_key] = {
                    'name': user.first_name or user.username or "Користувач",
                    'user_id': user.id,
                    'messages': 0,
                    'chars': 0
                }

            users_daily[u_key]['name'] = user.first_name or user.username or "Користувач"
            users_daily[u_key]['messages'] += 1
            users_daily[u_key]['chars'] += len(msg_content)

            await save_chat_relationships(chat_id, chat_data)
        except Exception as e:
            logger.warning(f"Помилка оновлення статистики: {e}")

    if not msg_content:
        return

    # 1. ОБРОБКА КОМАНД ТА РП-ДІЙ (префікси / та !)
    if msg_content.startswith('/') or msg_content.startswith('!'):
        command_match = re.match(r'^[/\!](\S+)', msg_content)
        if command_match:
            raw_cmd = command_match.group(1).lower()
            command = COMMAND_ALIASES.get(raw_cmd, raw_cmd)

            # Перенаправлення аліасів до відповідних команд
            if command == 'relationships':
                await relationships_command(update, context)
                return
            elif command == 'myrelationships':
                await my_relationships_command(update, context)
                return
            elif command == 'chatstats':
                await chat_stats_command(update, context)
                return
            elif command == 'profile':
                await profile_command(update, context)
                return
            elif command == 'breakup':
                await breakup_command(update, context)
                return
            elif command == 'weather':
                await weather_command(update, context)
                return
            elif command == 'roast':
                await roast_command(update, context)
                return
            elif command == 'judge':
                await judge_command(update, context)
                return
            elif command == 'quote':
                await quote_command(update, context)
                return
            elif command == 'risk':
                await risk_command(update, context)
                return

            if command in ALL_COUPLE_COMMANDS or command in ('dating', 'trio'):
                target = None
                if '@' in msg_content:
                    target_match = re.search(r'@(\S+)', msg_content)
                    if target_match:
                        target = target_match.group(1)

                await handle_couple_command(update, context, command, target)
            else:
                await handle_action_command(update, context)
        return

    # 2. ОБРОБКА ВСІХ ФОРВАРДІВ (текст, медіа, канали, користувачі)
    is_forward = bool(
        getattr(update.message, 'forward_origin', None) or
        getattr(update.message, 'forward_from_chat', None) or
        getattr(update.message, 'forward_date', None) or
        getattr(update.message, 'forward_from', None)
    )

    media_group_id = getattr(update.message, 'media_group_id', None)

    # Якщо це форвард-альбом з кількох відео/фото, збираємо весь підпис протягом 1 сек і робимо 1 реакцію
    if is_forward and media_group_id:
        if media_group_id in MEDIA_GROUP_BUFFERS:
            if len(msg_content) > len(MEDIA_GROUP_BUFFERS[media_group_id]["text"]):
                MEDIA_GROUP_BUFFERS[media_group_id]["text"] = msg_content
                MEDIA_GROUP_BUFFERS[media_group_id]["update"] = update
            return

        MEDIA_GROUP_BUFFERS[media_group_id] = {
            "update": update,
            "text": msg_content
        }
        asyncio.create_task(process_media_group_after_delay(media_group_id, delay=1.0))
        return

    recent_history = get_recent_chat_messages(update.effective_chat.id, limit=35) if update.effective_chat else ""

    # 1. Перевірка на посилання відео/тікток/shorts/reels — завантажуємо відео у чат (навіть якщо повідомлення переслане)!
    raw_urls = re.findall(r'https?://[^\s>"]+', msg_content, re.IGNORECASE)
    video_keywords = ['tiktok.com', 'instagram.com', 'instagr.am', 'youtube.com/shorts', 'youtu.be', 'x.com', 'twitter.com']

    for url in raw_urls:
        if any(kw in url.lower() for kw in video_keywords):
            await download_and_send_video(update, context, url)
            return

    # 2. Переслані новини/пости -> Коментар від Бугайчика
    if is_forward:
        input_text = msg_content if msg_content else "[Користувач переслав медіа/файл/пост без тексту]"
        comment = await get_bugaichyk_news_commentary(input_text, sender_name, recent_history)
        if comment:
            await send_safe_html_reply(update, comment)
        return

    # Перевіряємо, чи це продовження діалогу з Бугайчиком (якщо минулу репліку дав Бугайчик цьому ж користувачу)
    is_dialogue_continuation = False
    if recent_history and not is_reply_to_bot and not has_bot_keyword:
        lines = [l.strip() for l in recent_history.strip().splitlines() if l.strip()]
        if len(lines) >= 2:
            last_line = lines[-1]
            prev_line = lines[-2]
            if "Бугайчик:" in last_line and (sender_name in prev_line or "Користувач:" in prev_line):
                msg_low = msg_content.lower().strip()
                if any(kw in msg_low for kw in ['що ти', 'шо ти', 'як ти', 'чому', 'а ти', 'ти де', 'де ти', 'розкажи', 'а що', 'а шо', 'як справи', 'що робиш', 'шо робиш', 'чому ти', 'чого ти']):
                    is_dialogue_continuation = True

    # 3. БОТ ВІДПОВІДАЄ ТІЛЬКИ ПРИ ПРЯМОМУ ЗВЕРНЕННІ, REPLAY АБО ПРИ ПРОДОВЖЕННІ ДІАЛОГУ!
    if has_bot_keyword or is_reply_to_bot or is_dialogue_continuation:
        reply_text = await get_bugaichyk_chat_reply(sender_name, msg_content, recent_history)
        if reply_text:
            await send_safe_html_reply(update, reply_text)
            return

    # На всі інші звичайні повідомлення чату без ім'я бота і без reply — БОТ САМ ВЗАГАЛІ НЕ ПИШЕ (0% СПАМУ)!
    return

