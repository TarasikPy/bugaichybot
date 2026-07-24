from datetime import datetime

WISDOM_LEVELS = {
    0: {"name": "Початківець", "emoji": "🌱", "min_messages": 0, "description": "Перші кроки у чаті"},
    1: {"name": "Говірка душа", "emoji": "💬", "min_messages": 100, "description": "Активний учасник розмов"},
    2: {"name": "Балакун", "emoji": "🗣️", "min_messages": 500, "description": "Постійний співрозмовник"},
    3: {"name": "Оратор", "emoji": "📖", "min_messages": 1500, "description": "Майстер красномовства"},
    4: {"name": "Мислитель", "emoji": "🧠", "min_messages": 3500, "description": "Глибокі думки та ідеї"},
    5: {"name": "Філософ", "emoji": "📜", "min_messages": 7000, "description": "Шукач істини у суперечках"},
    6: {"name": "Мудрець", "emoji": "🧙", "min_messages": 12000, "description": "Джерело знань для чату"},
    7: {"name": "Магістр слова", "emoji": "🏛️", "min_messages": 20000, "description": "Визнаний авторитет"},
    8: {"name": "Великий Гуру", "emoji": "👑", "min_messages": 35000, "description": "Легенда спільноти"},
    9: {"name": "Божество Думок", "emoji": "✨", "min_messages": 50000, "description": "Абсолютний пік мудрості"}
}

def get_user_level(message_count: int) -> int:
    """Визначає рівень мудрості за кількістю повідомлень"""
    for level in reversed(range(len(WISDOM_LEVELS))):
        if message_count >= WISDOM_LEVELS[level]["min_messages"]:
            return level
    return 0

def process_user_message_in_chat(chat_data: dict, user_id: int, user_name: str):
    """Обробляє повідомлення користувача у чаті та перевіряє підвищення рівня"""
    user_key = str(user_id)
    if user_key not in chat_data['users']:
        chat_data['users'][user_key] = {
            'name': user_name,
            'message_count': 0,
            'current_level': 0,
            'last_update': datetime.now().isoformat(),
            'join_date': datetime.now().isoformat()
        }

    chat_data['users'][user_key]['name'] = user_name
    chat_data['users'][user_key]['message_count'] += 1
    chat_data['users'][user_key]['last_update'] = datetime.now().isoformat()
    chat_data['chat_info']['total_messages_synced'] = chat_data['chat_info'].get('total_messages_synced', 0) + 1

    old_level = chat_data['users'][user_key]['current_level']
    new_level = get_user_level(chat_data['users'][user_key]['message_count'])
    chat_data['users'][user_key]['current_level'] = new_level

    level_up = new_level > old_level
    level_data = None
    if level_up:
        level_data = {
            'level': new_level,
            'level_info': WISDOM_LEVELS[new_level],
            'message_count': chat_data['users'][user_key]['message_count'],
            'wisdom_points': chat_data['users'][user_key]['message_count'] // 10,
            'user_name': user_name,
            'user_id': user_id
        }

    return level_up, level_data

def get_user_wisdom_stats_in_chat(chat_data: dict, user_id: int):
    """Отримує статистику мудрості користувача"""
    user_key = str(user_id)
    if user_key not in chat_data['users']:
        return None

    user_data = chat_data['users'][user_key]
    current_level = user_data['current_level']
    current_level_info = WISDOM_LEVELS[current_level]
    wisdom_points = user_data['message_count'] // 10

    progress = None
    if current_level + 1 in WISDOM_LEVELS:
        next_level_info = WISDOM_LEVELS[current_level + 1]
        messages_needed = next_level_info['min_messages'] - user_data['message_count']
        current_level_min = current_level_info['min_messages']
        next_level_min = next_level_info['min_messages']
        progress_range = next_level_min - current_level_min
        progress_current = user_data['message_count'] - current_level_min
        progress_percentage = (progress_current / progress_range) * 100 if progress_range > 0 else 100

        progress = {
            'next_level_info': next_level_info,
            'messages_needed': max(0, messages_needed),
            'progress_percentage': min(100.0, max(0.0, progress_percentage))
        }

    return {
        'user_data': user_data,
        'current_level_info': current_level_info,
        'wisdom_points': wisdom_points,
        'progress': progress
    }

def get_wisdom_leaderboard(chat_data: dict, top_n: int = 10):
    """Формує топ користувачів за очками мудрості в чаті"""
    users_list = []
    for user_id, user_data in chat_data.get('users', {}).items():
        users_list.append({
            'user_id': user_id,
            'name': user_data['name'],
            'message_count': user_data['message_count'],
            'wisdom_points': user_data['message_count'] // 10,
            'current_level': user_data['current_level'],
            'level_info': WISDOM_LEVELS[user_data['current_level']]
        })

    users_list.sort(key=lambda x: x['message_count'], reverse=True)

    for i, user in enumerate(users_list[:top_n], 1):
        user['rank'] = i

    return users_list[:top_n]

def format_level_announcement(data: dict) -> str:
    """Форматує оголошення про новий рівень мудрості"""
    level_info = data['level_info']
    return (
        f"🎉 **ВІТАЄМО В ЗОНІ МУДРОСТІ!** 🎉\n\n"
        f"👤 [{data['user_name']}](tg://user?id={data.get('user_id', '')}) досяг(ла) нових висот!\n"
        f"{level_info['emoji']} **Новий рівень:** {level_info['name']}\n"
        f"📝 **Всього повідомлень:** {data['message_count']}\n"
        f"⚡ **Очки мудрості:** {data['wisdom_points']}\n\n"
        f"💭 *{level_info['description']}*"
    )
