import re
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes

from config.levels import RELATIONSHIP_LEVELS, MARRIED_COMMANDS, ALL_COUPLE_COMMANDS
from utils.helpers import (
    decline_name,
    get_relationship_level,
    format_duration,
    create_user_link,
    find_user_relationships,
    check_relationship_protection
)
from storage.json_db import load_chat_relationships, save_chat_relationships

logger = logging.getLogger(__name__)

async def relationships_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показує всі стосунки в поточному чаті"""
    chat_id = update.effective_chat.id
    chat_data = await load_chat_relationships(chat_id)
    relationships = chat_data['relationships']

    if not relationships:
        await update.message.reply_text("💔 Поки що немає активних стосунків у цьому чаті!")
        return

    text = "💕 **Активні стосунки в цьому чаті:**\n\n"
    for couple_id, data in relationships.items():
        parts = couple_id.split('_')
        if len(parts) >= 2:
            partners = parts
            duration = format_duration(data['start_date'])
            total_points = data.get('total_points', 0)
            level = get_relationship_level(total_points)
            level_info = RELATIONSHIP_LEVELS[level]
            status = data.get('status', 'dating')

            status_emoji = "💒" if status == 'married' else "💕"

            partner_links = [create_user_link(partner, is_sender=False, is_relationship_display=True) for partner in partners]

            if len(partners) == 2:
                partner_display = f"{partner_links[0]} ❤️ {partner_links[1]}"
            else:
                partner_display = " ❤️ ".join(partner_links)

            text += f"{status_emoji} {partner_display}\n"
            text += f"📊 Рівень: {level_info['emoji']} {level_info['name']}\n"
            text += f"⚡ Очки: {total_points}\n"
            text += f"📝 {level_info['description']}\n"
            text += f"📅 Тривалість: {duration}\n\n"

    await update.message.reply_text(text, parse_mode='Markdown')

async def my_relationships_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показує стосунки користувача в поточному чаті"""
    user_name = update.message.from_user.first_name
    chat_id = update.effective_chat.id
    chat_data = await load_chat_relationships(chat_id)
    relationships = chat_data['relationships']

    user_relationships = []
    for couple_id, data in relationships.items():
        parts = couple_id.split('_')
        if user_name in parts:
            other_partners = [p for p in parts if p != user_name]
            duration = format_duration(data['start_date'])
            total_points = data.get('total_points', 0)
            level = get_relationship_level(total_points)
            level_info = RELATIONSHIP_LEVELS[level]
            status = data.get('status', 'dating')

            status_text = "💒 Одружені" if status == 'married' else "💕 У стосунках"

            if len(other_partners) == 1:
                partner_text = f"❤️ Партнер: {create_user_link(other_partners[0], is_sender=False, is_relationship_display=True)}"
            else:
                partner_links = [create_user_link(partner, is_sender=False, is_relationship_display=True) for partner in other_partners]
                partner_text = f"❤️ Партнери: {' та '.join(partner_links)}"

            user_relationships.append(
                f"{status_text}\n"
                f"{partner_text}\n"
                f"📊 Рівень: {level_info['emoji']} {level_info['name']}\n"
                f"⚡ Очки: {total_points}\n"
                f"📝 {level_info['description']}\n"
                f"📅 Тривалість: {duration}"
            )

    if not user_relationships:
        text = "💔 У вас поки немає активних стосунків у цьому чаті!"
    else:
        user_link = create_user_link(user_name, is_sender=True)
        text = f"💕 **Ваші стосунки, {user_link}:**\n\n" + "\n\n".join(user_relationships)

    await update.message.reply_text(text, parse_mode='Markdown')

async def proposals_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показує активні пропозиції в поточному чаті"""
    user_name = update.message.from_user.first_name
    chat_id = update.effective_chat.id
    chat_data = await load_chat_relationships(chat_id)
    relationships = chat_data['relationships']

    proposals_to_user = []
    proposals_from_user = []

    for couple_id, data in relationships.items():
        if 'proposal' in data and data['proposal']['status'] == 'pending':
            proposal = data['proposal']
            if proposal['to'] == user_name:
                from_user_link = create_user_link(proposal['from'], is_sender=False, is_relationship_display=True)
                proposals_to_user.append(f"💍 Від {from_user_link}")
            elif proposal['from'] == user_name:
                to_user_link = create_user_link(proposal['to'], is_sender=False, is_relationship_display=True)
                proposals_from_user.append(f"💌 До {to_user_link}")

    text = f"💌 **Активні пропозиції для {create_user_link(user_name, is_sender=True)}:**\n\n"

    if proposals_to_user:
        text += "📨 **Пропозиції до вас:**\n" + "\n".join(proposals_to_user) + "\n\n"
        text += "Використайте /accept або /reject\n\n"

    if proposals_from_user:
        text += "📤 **Ваші пропозиції:**\n" + "\n".join(proposals_from_user) + "\n\n"

    if not proposals_to_user and not proposals_from_user:
        text += "💔 Немає активних пропозицій у цьому чаті!"

    await update.message.reply_text(text, parse_mode='Markdown')

async def dating_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обгортка для команди /dating"""
    await handle_couple_command(update, context, 'dating')

async def trio_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обгортка для команди /trio"""
    await handle_couple_command(update, context, 'trio')

async def handle_couple_command(update: Update, context: ContextTypes.DEFAULT_TYPE, command: str, target: str = None) -> None:
    """Обробляє всі команди для пар асинхронно"""
    user_name = update.message.from_user.first_name
    bot_username = context.bot.username
    chat_id = update.effective_chat.id
    chat_data = await load_chat_relationships(chat_id)

    try:
        await update.message.delete()
    except Exception as e:
        logger.warning(f"Не вдалося видалити повідомлення: {e}")

    if command == 'trio':
        message_text = update.message.text
        mentioned_users = re.findall(r'@(\S+)', message_text)

        if len(mentioned_users) != 2:
            await context.bot.send_message(
                chat_id=chat_id,
                text="👥 Для створення стосунків на 3 згадайте двох користувачів: `/trio @user1 @user2`",
                parse_mode='Markdown'
            )
            return

        if bot_username and any(user.lower() == bot_username.lower() for user in mentioned_users):
            await context.bot.send_message(
                chat_id=chat_id,
                text="🤖 Не можна включати бота в стосунки!",
                parse_mode='Markdown'
            )
            return

        if user_name in mentioned_users:
            await context.bot.send_message(
                chat_id=chat_id,
                text="😅 Не можна включати себе в список партнерів!",
                parse_mode='Markdown'
            )
            return

        all_participants = [user_name] + mentioned_users

        for participant in all_participants:
            user_relationships = find_user_relationships(participant, chat_data['relationships'])
            if user_relationships:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"💔 {participant} вже у стосунках! Неможливо створити нові стосунки.",
                    parse_mode='Markdown'
                )
                return

        couple_id = '_'.join(sorted(all_participants))
        chat_data['relationships'][couple_id] = {
            'start_date': datetime.now().isoformat(),
            'total_points': 3,
            'actions': [],
            'status': 'dating'
        }
        chat_data['chat_info']['total_relationships'] += 1
        await save_chat_relationships(chat_id, chat_data)

        user_link = create_user_link(user_name, is_sender=True)
        partner_links = [create_user_link(user, is_sender=False) for user in mentioned_users]

        await context.bot.send_message(
            chat_id=chat_id,
            text=f"👥💕 Вітаємо! {user_link}, {partner_links[0]} та {partner_links[1]} тепер у стосунках на трьох! ❤️💕❤️",
            parse_mode='Markdown'
        )
        return

    if command == 'dating':
        if not update.message.reply_to_message:
            await context.bot.send_message(
                chat_id=chat_id,
                text="💫 Для розпочатку стосунків відповідайте на повідомлення користувача командою /dating",
                parse_mode='Markdown'
            )
            return

        target_user = update.message.reply_to_message.from_user
        target = target_user.first_name

        if target_user.username and bot_username and target_user.username.lower() == bot_username.lower():
            await context.bot.send_message(
                chat_id=chat_id,
                text="🤖 Не можна розпочинати стосунки з ботом!",
                parse_mode='Markdown'
            )
            return

        if target == user_name:
            await context.bot.send_message(
                chat_id=chat_id,
                text="😅 Не можна розпочинати стосунки з самим собою!",
                parse_mode='Markdown'
            )
            return

        can_create, error_msg = check_relationship_protection(user_name, target, chat_data['relationships'])
        if not can_create:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"💔 {error_msg}",
                parse_mode='Markdown'
            )
            return

        couple_id = '_'.join(sorted([user_name, target]))
        chat_data['relationships'][couple_id] = {
            'start_date': datetime.now().isoformat(),
            'total_points': 2,
            'actions': [],
            'status': 'dating'
        }
        chat_data['chat_info']['total_relationships'] += 1
        await save_chat_relationships(chat_id, chat_data)

        user_link = create_user_link(user_name, is_sender=True)
        target_link = create_user_link(target, is_sender=False)

        await context.bot.send_message(
            chat_id=chat_id,
            text=f"💫 Вітаємо! {user_link} та {target_link} тепер у стосунках! ❤️",
            parse_mode='Markdown'
        )
        return

    if target and bot_username and target.lower() == bot_username.lower():
        await context.bot.send_message(
            chat_id=chat_id,
            text="🤖 На мені не можна виконувати команди стосунків!",
            parse_mode='Markdown'
        )
        return

    user_relationships = find_user_relationships(user_name, chat_data['relationships'])

    if not user_relationships:
        await context.bot.send_message(
            chat_id=chat_id,
            text="💔 У вас немає партнера! Для створення стосунків використайте /dating відповівши на повідомлення користувача",
            parse_mode='Markdown'
        )
        return

    couple_id, couple_data, partners = user_relationships[0]

    if command == 'propose':
        total_points = couple_data.get('total_points', 0)
        if total_points < RELATIONSHIP_LEVELS[5]["required_points"]:
            current_level = get_relationship_level(total_points)
            needed = RELATIONSHIP_LEVELS[5]["required_points"] - total_points
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"💍 Для пропозиції потрібен 5 рівень стосунків (Глибоке кохання)!\n📊 Ваш рівень: {RELATIONSHIP_LEVELS[current_level]['emoji']} {RELATIONSHIP_LEVELS[current_level]['name']}\n⚡ Потрібно ще {needed} очок для пропозиції!",
                parse_mode='Markdown'
            )
            return

        target = next(p for p in partners if p != user_name)

        chat_data['relationships'][couple_id]['proposal'] = {'from': user_name, 'to': target, 'status': 'pending'}
        await save_chat_relationships(chat_id, chat_data)

        user_link = create_user_link(user_name, is_sender=True)
        target_link = create_user_link(target, is_sender=False)

        await context.bot.send_message(
            chat_id=chat_id,
            text=f"💍 {user_link} робить пропозицію {target_link}! 💕\n\n{target_link}, використайте /accept або /reject",
            parse_mode='Markdown'
        )
        return

    elif command == 'accept':
        if 'proposal' not in couple_data:
            await context.bot.send_message(
                chat_id=chat_id,
                text="💔 Немає пропозиції для прийняття!",
                parse_mode='Markdown'
            )
            return

        proposal = couple_data['proposal']
        if proposal['to'] != user_name or proposal['status'] != 'pending':
            await context.bot.send_message(
                chat_id=chat_id,
                text="💔 Ви не можете прийняти цю пропозицію!",
                parse_mode='Markdown'
            )
            return

        chat_data['relationships'][couple_id]['status'] = 'married'
        del chat_data['relationships'][couple_id]['proposal']
        await save_chat_relationships(chat_id, chat_data)

        user_link = create_user_link(user_name, is_sender=True)
        proposer_link = create_user_link(proposal['from'], is_sender=False)

        await context.bot.send_message(
            chat_id=chat_id,
            text=f"💒 Вітаємо! {proposer_link} та {user_link} тепер одружені! 🎉👰🤵💕",
            parse_mode='Markdown'
        )
        return

    elif command == 'reject':
        if 'proposal' not in couple_data:
            await context.bot.send_message(
                chat_id=chat_id,
                text="💔 Немає пропозиції для відхилення!",
                parse_mode='Markdown'
            )
            return

        proposal = couple_data['proposal']
        if proposal['to'] != user_name or proposal['status'] != 'pending':
            await context.bot.send_message(
                chat_id=chat_id,
                text="💔 Ви не можете відхилити цю пропозицію!",
                parse_mode='Markdown'
            )
            return

        del chat_data['relationships'][couple_id]['proposal']
        await save_chat_relationships(chat_id, chat_data)

        user_link = create_user_link(user_name, is_sender=True)
        proposer_link = create_user_link(proposal['from'], is_sender=False)

        await context.bot.send_message(
            chat_id=chat_id,
            text=f"💔 {user_link} відхилив(ла) пропозицію від {proposer_link}... 😢",
            parse_mode='Markdown'
        )
        return

    elif command == 'divorce':
        if couple_data.get('status') != 'married':
            await context.bot.send_message(
                chat_id=chat_id,
                text="💔 Ви не одружені! Неможливо розлучитися.",
                parse_mode='Markdown'
            )
            return

        del chat_data['relationships'][couple_id]
        chat_data['chat_info']['total_relationships'] -= 1
        await save_chat_relationships(chat_id, chat_data)

        user_link = create_user_link(user_name, is_sender=True)
        partners_links = [create_user_link(p, is_sender=False) for p in partners if p != user_name]

        await context.bot.send_message(
            chat_id=chat_id,
            text=f"💔 {user_link} та {' і '.join(partners_links)} розлучилися... 😢",
            parse_mode='Markdown'
        )
        return

    elif command == 'breakup':
        del chat_data['relationships'][couple_id]
        chat_data['chat_info']['total_relationships'] -= 1
        await save_chat_relationships(chat_id, chat_data)

        user_link = create_user_link(user_name, is_sender=True)
        partners_links = [create_user_link(p, is_sender=False) for p in partners if p != user_name]

        await context.bot.send_message(
            chat_id=chat_id,
            text=f"😢 {user_link} та {' і '.join(partners_links)} розсталися... 💔",
            parse_mode='Markdown'
        )
        return

    if command not in ALL_COUPLE_COMMANDS:
        return

    if command in MARRIED_COMMANDS and couple_data.get('status') != 'married':
        await context.bot.send_message(
            chat_id=chat_id,
            text="💒 Ця команда доступна тільки для одружених пар! Спочатку зробіть пропозицію командою /propose",
            parse_mode='Markdown'
        )
        return

    command_info = ALL_COUPLE_COMMANDS[command]
    action = command_info['action']
    points = command_info['points']
    emoji = command_info['emoji']

    if 'total_points' not in chat_data['relationships'][couple_id]:
        chat_data['relationships'][couple_id]['total_points'] = 0
    if 'actions' not in chat_data['relationships'][couple_id]:
        chat_data['relationships'][couple_id]['actions'] = []
    if 'status' not in chat_data['relationships'][couple_id]:
        chat_data['relationships'][couple_id]['status'] = 'dating'

    chat_data['relationships'][couple_id]['total_points'] += points
    chat_data['relationships'][couple_id]['actions'].append({
        'action': f"{user_name} {action}",
        'date': datetime.now().isoformat(),
        'points': points
    })

    total_points = chat_data['relationships'][couple_id]['total_points']
    current_level = get_relationship_level(total_points)
    level_info = RELATIONSHIP_LEVELS[current_level]

    await save_chat_relationships(chat_id, chat_data)

    user_link = create_user_link(user_name, is_sender=True)

    if len(partners) == 2:
        target_name = next(p for p in partners if p != user_name)
        target_declined = decline_name(target_name)
        target_link = create_user_link(target_declined, is_sender=False)
        response = f"{emoji} {user_link} {action} {target_link}"
    else:
        other_partners = [p for p in partners if p != user_name]
        partners_links = [create_user_link(decline_name(p), is_sender=False) for p in other_partners]
        response = f"{emoji} {user_link} {action} {' та '.join(partners_links)}"

    if points > 0:
        response += f"\n📊 Рівень стосунків: {level_info['emoji']} {level_info['name']} ({total_points} очок)"

    await context.bot.send_message(
        chat_id=chat_id,
        text=response,
        parse_mode='Markdown'
    )
