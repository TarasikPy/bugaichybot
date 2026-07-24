import re
import html
from datetime import datetime
from config.names import MALE_NAMES_DECLENSION, FEMALE_NAMES_DECLENSION
from config.levels import RELATIONSHIP_LEVELS

def escape_html(text: str) -> str:
    """Екранує спеціальні символи HTML (<, >, &)"""
    if not text:
        return ""
    return html.escape(str(text))

def escape_markdown(text: str) -> str:
    """Екранує спеціальні символи Markdown (наприклад, _, *, [, ], `)"""
    if not text:
        return ""
    return re.sub(r'([_*`\[\]])', r'\\\1', str(text))

def decline_name(name: str) -> str:
    """Відмінює ім'я з називного у знахідний відмінок, підтримка будь-яких імен та юзернеймів"""
    if not name:
        return ""

    if name in MALE_NAMES_DECLENSION:
        return MALE_NAMES_DECLENSION[name]
    elif name in FEMALE_NAMES_DECLENSION:
        return FEMALE_NAMES_DECLENSION[name]

    # Для англійських імен або юзернеймів
    if name.isascii():
        return name

    # Автоматичне відмінювання для українських імен
    if name.endswith(('ій', 'ей')):
        return name[:-2] + 'я'
    elif name.endswith('о'):
        return name[:-1] + 'а'
    elif name.endswith(('н', 'м', 'р', 't', 'к', 'л', 'с')):
        return name + 'а'
    elif name.endswith('а'):
        return name[:-1] + 'у'
    elif name.endswith('я'):
        return name[:-1] + 'ю'

    return name

def get_relationship_level(total_points: int) -> int:
    """Визначає рівень стосунків за кількістю очок"""
    for level in reversed(range(len(RELATIONSHIP_LEVELS))):
        if total_points >= RELATIONSHIP_LEVELS[level]["required_points"]:
            return level
    return 0

def format_duration(start_date: str) -> str:
    """Форматує тривалість стосунків з детальним відображенням"""
    start = datetime.fromisoformat(start_date)
    duration = datetime.now() - start
    total_seconds = int(duration.total_seconds())
    days = duration.days
    hours = (duration.seconds // 3600)
    minutes = (duration.seconds % 3600) // 60
    seconds = duration.seconds % 60

    if total_seconds < 60:
        return f"{total_seconds} секунд"
    elif total_seconds < 3600:
        return f"{minutes} хвилин {seconds} секунд"
    elif days == 0:
        return f"{hours} годин {minutes} хвилин"
    elif days < 30:
        return f"{days} днів {hours} годин {minutes} хвилин"
    elif days < 365:
        months = days // 30
        remaining_days = days % 30
        if months == 1:
            return f"1 місяць {remaining_days} днів {hours} годин"
        else:
            return f"{months} місяців {remaining_days} днів {hours} годин"
    else:
        years = days // 365
        remaining_days = days % 365
        months = remaining_days // 30
        final_days = remaining_days % 30

        if years == 1:
            if months > 0:
                return f"1 рік {months} місяців {final_days} днів"
            else:
                return f"1 рік {final_days} днів"
        else:
            if months > 0:
                return f"{years} років {months} місяців {final_days} днів"
            else:
                return f"{years} років {final_days} днів"

def create_html_user_link(name: str, user_id=None) -> str:
    """Створює клікабельне HTML-посилання на профіль користувача (tg://user?id=)"""
    safe_name = escape_html(name)
    if user_id:
        return f'<a href="tg://user?id={user_id}">{safe_name}</a>'
    else:
        return f'<b>{safe_name}</b>'

def create_user_link(name: str, user_id=None, is_sender=False, is_action=False, is_relationship_display=False) -> str:
    """Створює безпечне посилання на користувача з екрануванням спецсимволів (Markdown)"""
    safe_name = escape_markdown(name)
    if is_sender:
        return safe_name
    elif is_action:
        if user_id:
            return f"[✦**{safe_name}**](tg://user?id={user_id})"
        else:
            return f"✦**{safe_name}**"
    elif is_relationship_display:
        if user_id:
            return f"[✦💖**{safe_name}**💖](tg://user?id={user_id})"
        else:
            return f"✦💖**{safe_name}**💖"
    else:
        if user_id:
            return f"[**{safe_name}**](tg://user?id={user_id})"
        else:
            return f"**{safe_name}**"

def find_user_relationships(user_name: str, relationships: dict) -> list:
    """Знаходить всі стосунки користувача"""
    user_relationships = []
    for couple_id, data in relationships.items():
        parts = couple_id.split('_')
        if user_name in parts:
            user_relationships.append((couple_id, data, parts))
    return user_relationships

def check_relationship_protection(user_name: str, target_name: str, relationships: dict):
    """Перевіряє чи можна створювати нові стосунки (захист від множинних стосунків)"""
    user_relationships = find_user_relationships(user_name, relationships)
    target_relationships = find_user_relationships(target_name, relationships)

    if user_relationships:
        return False, f"{user_name} вже у стосунках!"
    if target_relationships:
        return False, f"{target_name} вже у стосунках!"

    return True, ""
