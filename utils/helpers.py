import re
import html
from datetime import datetime
from config.names import MALE_NAMES_DECLENSION, FEMALE_NAMES_DECLENSION
from config.levels import RELATIONSHIP_LEVELS

import unicodedata

def escape_html(text: str) -> str:
    """Екранує спеціальні символи HTML (<, >, &)"""
    if not text:
        return ""
    return html.escape(str(text))

def resolve_clean_user_name(user=None, raw_name: str = "") -> str:
    """Перетворює юзернейм або first_name з Юнікод-шрифтами у красиве українське ім'я з USERS_MAP"""
    from config.names import USERS_MAP
    if user:
        uname = (getattr(user, 'username', '') or '').lower()
        if uname in USERS_MAP:
            return USERS_MAP[uname]
        fname = getattr(user, 'first_name', '') or ''
        combined = f"{uname} {fname}"
    else:
        combined = raw_name or ""

    norm = unicodedata.normalize('NFKC', combined).lower()
    if 'bot dev' in norm or 'sp_mangment' in norm or 'arma' in norm:
        return 'Арма'
    if 'kiyotaka' in norm or 'shadow_tar' in norm:
        return 'Кійотака'

    for key, clean_val in USERS_MAP.items():
        if key in norm:
            return clean_val

    if user and getattr(user, 'first_name', None):
        clean = unicodedata.normalize('NFKC', user.first_name)
        clean_name = re.sub(r'[^\w\s\-\'’А-Яа-яІіЇїЄєA-Za-z0-9]', '', clean).strip()
        if clean_name:
            return clean_name
        return user.first_name.strip()

    if raw_name and raw_name not in ("Користувач", "Партнер 1", "Партнер 2", "Суперник", "Опонент"):
        clean = unicodedata.normalize('NFKC', raw_name)
        clean_name = re.sub(r'[^\w\s\-\'’А-Яа-яІіЇїЄєA-Za-z0-9]', '', clean).strip()
        if clean_name:
            return clean_name

    return raw_name or "Користувач"

def resolve_user_name_by_id_or_name(user_id: int, current_name: str = "") -> str:
    """Знаходить справжнє ім'я користувача за його Telegram ID або кешем (усуває 'Користувач')"""
    from storage.user_cache import get_user_name_by_id_sync

    cached_name = get_user_name_by_id_sync(user_id)
    if cached_name and cached_name not in ("Користувач", "Партнер 1", "Партнер 2"):
        return resolve_clean_user_name(raw_name=cached_name)

    if current_name and current_name not in ("Користувач", "Партнер 1", "Партнер 2"):
        return resolve_clean_user_name(raw_name=current_name)

    return f"Гравець_{user_id}" if user_id else "Користувач"

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

def create_user_link(user_id=None, name: str = None, **kwargs) -> str:
    """Створює клікабельне HTML-посилання на профіль користувача (tg://user?id=).
    Гнучка функція: підтримує як create_user_link(user_id, name), так і create_user_link(name, user_id).
    """
    if isinstance(user_id, str) and (isinstance(name, int) or name is None):
        user_id, name = name, user_id

    if not name and user_id:
        name = str(user_id)
    elif not name:
        name = "Користувач"

    safe_name = escape_html(str(name))
    if user_id:
        return f'<a href="tg://user?id={user_id}">{safe_name}</a>'
    else:
        return f'<b>{safe_name}</b>'

def create_html_user_link(name: str, user_id=None) -> str:
    """Сумісний аліас для створення клікабельного HTML-посилання"""
    return create_user_link(user_id=user_id, name=name)

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

async def send_safe_html_reply(update, text: str) -> None:
    """Відправляє відповідь на повідомлення у чат у форматі HTML з fallback на чистий текст"""
    if not update or not update.message:
        return
    try:
        await update.message.reply_text(text, parse_mode='HTML')
    except Exception as e:
        import re, logging
        logging.getLogger(__name__).warning(f"Не вдалося відправити HTML повідомлення ({e}), відправляємо чистий текст")
        plain_text = re.sub(r'<[^>]*>', '', text)
        await update.message.reply_text(plain_text)

def format_ai_response_to_html(text: str) -> str:
    """Перетворює Markdown від ШІ на валідний HTML для Telegram без подвійного екранування <b>, <i>, <code>, <a>"""
    if not text:
        return ""

    s = str(text)

    # 1. Захищаємо вже наявні дійсні HTML теги Telegram
    tags = []
    def save_tag(m):
        tags.append(m.group(0))
        return f'__TAG_{len(tags)-1}__'

    valid_pattern = r'</?(?:b|i|u|s|code|pre|blockquote)(?:\s+[^>]*)?>|<a\s+href="[^"]*">'
    s = re.sub(valid_pattern, save_tag, s, flags=re.IGNORECASE)

    # 2. Конвертуємо Markdown **жирний** та *курсив*
    s = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', s)
    s = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<i>*\1*</i>', s)

    # 3. Екрануємо залишки небезпечних знаків <, >, &
    s = html.escape(s, quote=False)

    # 4. Відновлюємо валідні теги Telegram
    for i, tag in enumerate(tags):
        ph_esc = html.escape(f'__TAG_{i}__', quote=False)
        s = s.replace(ph_esc, tag).replace(f'__TAG_{i}__', tag)

    s = s.replace('&lt;b&gt;', '<b>').replace('&lt;/b&gt;', '</b>')
    s = s.replace('&lt;i&gt;', '<i>').replace('&lt;/i&gt;', '</i>')

    return s

async def resolve_target_user_info(update) -> tuple:
    """Універсальний резолвер цільового користувача (по reply, @username, id, text_mention, USERS_MAP, USERS_CACHE)"""
    from config.names import USERS_MAP
    from storage.user_cache import get_user_info_by_username

    if not update or not update.message:
        return None, "Користувач", ""

    message_text = (update.message.text or update.message.caption or "").strip()
    sender = update.message.from_user

    target_user_id = None
    target_name = None
    target_username = ""

    # 1. З REPLY
    if update.message.reply_to_message and update.message.reply_to_message.from_user:
        reply_user = update.message.reply_to_message.from_user
        target_user_id = reply_user.id
        target_username = (reply_user.username or "").lstrip('@').lower()
        target_name = resolve_clean_user_name(reply_user)
        return target_user_id, target_name, target_username

    # 2. З аргументів / тегу / ID
    words = message_text.split()
    args = words[1:] if len(words) > 1 else []

    if args:
        raw_arg = args[0].strip()
        raw_target = raw_arg.lstrip('@').lower()
        target_username = raw_target

        # 2a. text_mention entities
        if update.message.entities:
            for entity in update.message.entities:
                if entity.type == 'text_mention' and entity.user:
                    target_user_id = entity.user.id
                    target_username = (entity.user.username or "").lstrip('@').lower()
                    target_name = resolve_clean_user_name(entity.user)
                    return target_user_id, target_name, target_username

        # 2b. Числовий Telegram ID
        if raw_target.isdigit():
            target_user_id = int(raw_target)

        # 2c. USERS_MAP
        if raw_target in USERS_MAP:
            target_name = USERS_MAP[raw_target]

        # 2d. USERS_CACHE (storage/users_cache.json)
        if not target_user_id or not target_name:
            cached_name, cached_id = await get_user_info_by_username(raw_target)
            if cached_name and not target_name:
                target_name = resolve_clean_user_name(raw_name=cached_name)
            if cached_id and not target_user_id:
                target_user_id = cached_id

        # 2e. Пошук в офлайн аналітиці (chat_analytics.json)
        if not target_user_id or not target_name:
            from storage.analytics_db import load_history_analytics
            history_data = load_history_analytics()
            profiles = history_data.get('profiles', {})

            target_key = str(target_user_id or raw_target)
            if target_key in profiles:
                p_data = profiles[target_key]
                target_user_id = p_data.get('user_id') or (int(target_key) if target_key.isdigit() else None)
                target_name = resolve_clean_user_name(raw_name=p_data.get('name', target_name))
            else:
                for p_id_str, p_data in profiles.items():
                    p_uname = (p_data.get('username') or '').lstrip('@').lower()
                    p_name = (p_data.get('name') or '').lower()
                    p_code = (p_data.get('code_name') or '').lower()
                    if (target_username and p_uname == target_username) or (p_name == raw_target) or (p_code == raw_target):
                        target_user_id = p_data.get('user_id') or (int(p_id_str) if p_id_str.isdigit() else None)
                        target_name = resolve_clean_user_name(raw_name=p_data.get('name', target_name))
                        break

        if not target_name:
            target_name = resolve_clean_user_name(raw_name=raw_arg)

    # 3. Відправник за замовчуванням
    else:
        if sender:
            target_user_id = sender.id
            target_username = (sender.username or "").lstrip('@').lower()
            target_name = resolve_clean_user_name(sender)

    return target_user_id, target_name or "Користувач", target_username


