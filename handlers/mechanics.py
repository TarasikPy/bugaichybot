import re
import logging
from telegram import Update
from telegram.ext import ContextTypes

from config.names import USERS_MAP
from utils.helpers import create_user_link, escape_html, send_safe_html_reply, resolve_clean_user_name
from storage.analytics_db import get_user_history_profile
from utils.bugaichyk_ai import (
    get_bugaichyk_roast,
    get_bugaichyk_judge,
    get_random_quote,
    check_and_get_quote,
    get_random_risk
)

logger = logging.getLogger(__name__)

async def roast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /roast — генерує саркастичний підкол для target юзера чи відправника"""
    if not update.message:
        return

    sender = update.message.from_user
    target_name = resolve_clean_user_name(sender, "Користувач")
    target_id = sender.id if sender else None
    target_lore = ""

    # Reply перевірка
    if update.message.reply_to_message and update.message.reply_to_message.from_user:
        reply_user = update.message.reply_to_message.from_user
        target_name = resolve_clean_user_name(reply_user, "Користувач")
        target_id = reply_user.id
        prof = get_user_history_profile(target_id, reply_user.username or "")
        if prof:
            target_lore = prof.get('role', '') or prof.get('style', '')

    response = await get_bugaichyk_roast(target_name, target_lore)
    await send_safe_html_reply(update, response)

async def judge_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /judge або /суд — ШІ-Суддя для срачів з аналізом останніх 20+ повідомлень чату"""
    from storage.analytics_db import get_recent_chat_messages

    if not update.message:
        return

    chat_id = update.effective_chat.id
    sender = update.message.from_user
    user1 = resolve_clean_user_name(sender, "Користувач")

    user2 = None
    argument_text = ""

    # 1. Спроба витягти user2 з reply
    if update.message.reply_to_message:
        reply_msg = update.message.reply_to_message
        if reply_msg.from_user:
            user2 = resolve_clean_user_name(reply_msg.from_user)
        argument_text = (reply_msg.text or reply_msg.caption or "").strip()

    # 2. Аргументи з тексту команди
    command_args = ""
    if context.args:
        command_args = " ".join(context.args).strip()
    else:
        text = update.message.text or update.message.caption or ""
        words = text.strip().split()
        if len(words) > 1:
            command_args = " ".join(words[1:]).strip()

    # Згадка @user у command_args
    if not user2 and "@" in command_args:
        match = re.search(r'@(\S+)', command_args)
        if match:
            raw_u = match.group(1).lstrip('@')
            user2 = resolve_clean_user_name(raw_name=raw_u)

    # Отримуємо останні 20 повідомлень чату
    recent_history = get_recent_chat_messages(chat_id, limit=20)

    # 3. Якщо user2 досі не визначено — беремо останнього активного спікера з історії (ігноруючи команди бота)
    if not user2 and recent_history:
        lines = recent_history.split('\n')
        for line in reversed(lines):
            match = re.search(r'\]\s*([^:]+):\s*(.*)', line)
            if match:
                speaker_name = resolve_clean_user_name(raw_name=match.group(1).strip())
                msg_body = match.group(2).strip()
                # Ігноруємо службові команди бота
                if msg_body.startswith(('/', '!')):
                    continue
                if speaker_name != user1 and speaker_name not in ("Користувач", "Гравець 1", "Суперник", "Опонент"):
                    user2 = speaker_name
                    break

    # 4. Якщо user2 досі немає і суперечки з іншою людиною в історії немає:
    if not user2 or user2 in ("Суперник", "Опонент", "Користувач", "Гравець 1"):
        hint = (
            "⚖️ <b>ЯК ВИКЛИКАТИ ШІ-СУДДЮ ДЛЯ СРАЧУ:</b>\n\n"
            "📌 <b>Дайте відповідь (reply)</b> на повідомлення вашого опонента і напишіть <code>/judge</code> (або <code>!суд</code>).\n"
            "📌 Або тегніть опонента в команді: <code>/judge @username чий крим</code>\n\n"
            "<i>Бугайчик прочитає живі репліки з чату та винесе безкомпромісну українську базу!</i>"
        )
        await send_safe_html_reply(update, hint)
        return

    if command_args:
        if argument_text:
            argument_text = f"Повідомлення {user2}: '{argument_text}' | Претензія {user1}: '{command_args}'"
        else:
            argument_text = command_args

    if not argument_text:
        argument_text = "Суперечка про те, хто навалив бази, а хто спіймав крінж"

    verdict_text = await get_bugaichyk_judge(argument_text, user1, user2, recent_history)
    await send_safe_html_reply(update, verdict_text)

async def quote_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /цитата або /quote — Золотий фонд чату з денним лімітом (1 раз на день)"""
    if not update.message or not update.message.from_user:
        return

    user_id = update.message.from_user.id
    success, quote_text = await check_and_get_quote(user_id)

    if not success:
        await send_safe_html_reply(update, f"⚠️ {quote_text}")
    else:
        await send_safe_html_reply(update, quote_text)

async def risk_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /ризик або /risk — РП-Рулетка"""
    if not update.message:
        return

    user_name = update.message.from_user.first_name if update.message.from_user else "Користувач"
    risk_text = get_random_risk(user_name)
    await send_safe_html_reply(update, risk_text)

