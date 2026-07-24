import os
import sys
import re
import json
import httpx
from datetime import datetime
from collections import Counter, defaultdict

# Додаємо корінь проекту до sys.path для імпорту конфігів
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from config.settings import GEMINI_API_KEY
except ImportError:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

STOP_WORDS = {
    'і', 'в', 'на', 'бути', 'могти', 'та', 'що', 'з', 'за', 'до', 'по', 'як', 'це', 'ти',
    'я', 'він', 'вона', 'вони', 'ми', 'ви', 'але', 'чи', 'не', 'так', 'ні', 'то', 'от',
    'ще', 'у', 'ж', 'же', 'бо', 'де', 'хто', 'який', 'свій', 'для', 'про', 'при', 'від',
    'об', 'під', 'над', 'перед', 'через', 'між', 'після', 'поки', 'якщо', 'хай', 'нехай',
    'лише', 'тільки', 'теж', 'також', 'навіть', 'вже', 'ну', 'ось', 'просто', 'там', 'тут',
    'коли', 'тоді', 'тому', 'чому', 'все', 'всі', 'весь', 'всього', 'мені', 'тебе', 'мене',
    'його', 'її', 'нас', 'вас', 'їх', 'собі', 'тобі', 'йому', 'їй', 'їм', 'свого', 'своїх',
    'є', 'был', 'было', 'быть', 'это', 'как', 'так', 'что', 'для', 'или', 'если', 'уже',
    'просто', 'тоже', 'только', 'меня', 'тебя', 'его', 'ее', 'их', 'нам', 'вам', 'все',
    'мне', 'тебе', 'ему', 'ей', 'им', 'тут', 'там', 'где', 'когда', 'тогда', 'почему',
    'да', 'нет', 'уж', 'еще', 'даже', 'ведь', 'вот', 'ну', 'ага', 'ппц', 'хз', 'блін',
    'http', 'https', 'com', 'org', 'ua', 'net', 'www'
}

EMOJI_REGEX = re.compile(
    r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF'
    r'\U0001F1E0-\U0001F1FF\U00002600-\U000026FF\U00002700-\U000027BF'
    r'\U0001F900-\U0001F9FF\U0001FA70-\U0001FAFF]'
)

def is_real_user(user_id: int, user_name: str) -> bool:
    """Перевіряє, чи є акаунт реальним користувачем (не бот, не безназваний ID, не видалений акаунт)"""
    if not user_id or user_id <= 0:
        return False

    name_lower = (user_name or "").strip().lower()

    # 1. Ігнорування ботів (слово "bot" в імені або "мафія")
    if 'bot' in name_lower or 'мафія' in name_lower or 'mafia' in name_lower:
        return False

    # 2. Ігнорування безназваних / видалених акаунтів
    if not user_name or name_lower in ('deleted account', 'видалений акаунт', 'user', 'користувач'):
        return False

    # Ігнорування імен формату User_1234567890
    if re.match(r'^user_\d+$', name_lower):
        return False

    return True

def extract_text(text_field) -> str:
    """Витягує чистий текст з поля text Telegram-експорту"""
    if isinstance(text_field, str):
        return text_field
    elif isinstance(text_field, list):
        parts = []
        for item in text_field:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and 'text' in item:
                parts.append(str(item['text']))
        return "".join(parts)
    return ""

def create_fallback_profile(user_name: str, sample_messages: list) -> dict:
    """Генерує дефолтний психологічний профіль при відсутності GEMINI_API_KEY"""
    roles = [
        "Душа Компанії", "Нічний Філософ", "Головний Інтелектуал",
        "Тіньовий Кардинал", "Генератор Мемів", "Майстер Дискусій",
        "Хранитель Чату", "Свідомий Критик"
    ]
    role_idx = sum(ord(c) for c in user_name) % len(roles)
    return {
        "role": roles[role_idx],
        "character": f"{user_name} — активний дописувач чату з вираженим унікальним стилем мовлення.",
        "topics": ["Чат та спільнота", "Актуальні події", "Гумор"],
        "catchphrases": sample_messages[:2] if sample_messages else ["База", "Йоу"],
        "summary": "Яскравий учасник спільноти, який робить чат живим та динамічним."
    }

def generate_gemini_profile(user_name: str, sample_messages: list, api_key: str) -> dict:
    """Викликає Gemini API для створення AI-психопрофілю користувача"""
    if not api_key or api_key.startswith("your_"):
        return create_fallback_profile(user_name, sample_messages)

    formatted_samples = "\n".join([f"- {msg}" for msg in sample_messages[:100]])
    prompt = f"""Ти — смішний, точний та спостережливий психолог Telegram-чату спільноти.
Проаналізуй вибірку з 100 реальних повідомлень користувача '{user_name}':

{formatted_samples}

Побудуй красивий, точний та смішний психологічний профіль людини в українському чаті.
Зверни увагу на її манеру спілкування, тему, сленг, роль у чаті.

Поверни ВИНЯТКОВО valid JSON (без слів довкола та без маркдаун огорож):
{{
  "role": "Яскрава та смішна назва ролі в чаті (наприклад: 'Головний Інтелектуал', 'Нічний Філософ', 'Підпільний Бізнесмен')",
  "character": "Дотепний та влучний опис характеру й поведінки в чаті (2-3 речення українською)",
  "topics": ["Улюблена тема 1", "Улюблена тема 2", "Улюблена тема 3"],
  "catchphrases": ["Коронна фраза 1", "Коронна фраза 2"],
  "summary": "Короткий влучний підсумковий висновок про людину (1 речення)"
}}"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                url,
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.7,
                        "responseMimeType": "application/json"
                    }
                }
            )
            if resp.status_code == 200:
                res_json = resp.json()
                raw_text = res_json['candidates'][0]['content']['parts'][0]['text'].strip()
                parsed = json.loads(raw_text)
                return {
                    "role": parsed.get("role", "Король Чату"),
                    "character": parsed.get("character", f"{user_name} — активна особистість чату."),
                    "topics": parsed.get("topics", ["Чат"]),
                    "catchphrases": parsed.get("catchphrases", []),
                    "summary": parsed.get("summary", "")
                }
            else:
                print(f"⚠️ Gemini API повернув статус {resp.status_code} для {user_name}")
    except Exception as e:
        print(f"⚠️ Не вдалося згенерувати Gemini профіль для {user_name}: {e}")

    return create_fallback_profile(user_name, sample_messages)

def main():
    json_path = os.path.join(PROJECT_ROOT, "result.json")
    if not os.path.exists(json_path):
        print(f"❌ Файл {json_path} не знайдено!")
        sys.exit(1)

    print(f"🚀 Завантаження та аналіз історії чату з {json_path}...")
    start_time = datetime.now()

    with open(json_path, 'r', encoding='utf-8') as f:
        export_data = json.load(f)

    messages = export_data.get('messages', [])
    print(f"📊 Знайдено {len(messages):,} записів у вивантаженні чату.")

    # 1. Фільтрація системних повідомлень та ініціалізація структур даних
    user_names = {}        # user_id -> latest name
    user_msg_count = Counter()
    user_char_count = Counter()
    user_samples = defaultdict(list)
    msg_id_to_user = {}

    reply_pairs = Counter()   # (min_id, max_id) -> reply count
    reply_direction = Counter() # (from_id, to_id) -> reply count

    emoji_counter = Counter()
    slang_counter = Counter()

    total_messages = 0
    total_chars = 0
    longreads = []

    print("🔎 Обробка математичних метрик, графу відповідей та сленгу...")

    for msg in messages:
        # Фільтрація системних повідомлень Telegram
        if msg.get('type') != 'message':
            continue

        from_id_raw = str(msg.get('from_id', ''))
        if not from_id_raw.startswith('user'):
            continue

        try:
            user_id = int(from_id_raw.replace('user', ''))
        except ValueError:
            continue

        text = extract_text(msg.get('text', '')).strip()
        if not text:
            continue

        msg_id = msg.get('id')
        name = msg.get('from') or f"User_{user_id}"
        user_names[user_id] = name
        msg_id_to_user[msg_id] = user_id

        total_messages += 1
        text_len = len(text)
        total_chars += text_len

        user_msg_count[user_id] += 1
        user_char_count[user_id] += text_len

        # Вибірка найцікавіших повідомлень для AI-профілю (> 10 символів)
        if text_len >= 10 and len(user_samples[user_id]) < 150:
            user_samples[user_id].append(text)

        # Лонгріди (найдовші повідомлення від реальних користувачів)
        if text_len > 300 and is_real_user(user_id, name):
            longreads.append({
                'user_id': user_id,
                'name': name,
                'len': text_len,
                'snippet': text[:150] + "...",
                'date': msg.get('date', '')
            })

        # Граф відповідей (Reply Graph)
        reply_to_id = msg.get('reply_to_message_id')
        if reply_to_id and reply_to_id in msg_id_to_user:
            target_user_id = msg_id_to_user[reply_to_id]
            if target_user_id != user_id:
                pair = tuple(sorted([user_id, target_user_id]))
                reply_pairs[pair] += 1
                reply_direction[(user_id, target_user_id)] += 1

        # Емодзі
        emojis = EMOJI_REGEX.findall(text)
        for emo in emojis:
            emoji_counter[emo] += 1

        # Сленг та слова (очищення від стоп-слів)
        clean_text = re.sub(r'[^\w\s]', ' ', text.lower())
        words = clean_text.split()
        for w in words:
            if len(w) >= 3 and not w.isdigit() and w not in STOP_WORDS:
                slang_counter[w] += 1

    avg_msg_len = round(total_chars / total_messages, 1) if total_messages > 0 else 0
    top_longreads = sorted(longreads, key=lambda x: x['len'], reverse=True)[:5]

    # 2. Формування ТОП-20 РЕАЛЬНИХ користувачів (без ботів та видалених акаунтів)
    real_top_users_ids = []
    for uid, _ in user_msg_count.most_common():
        uname = user_names.get(uid, "")
        if is_real_user(uid, uname):
            real_top_users_ids.append(uid)
            if len(real_top_users_ids) == 20:
                break

    top_users_data = []
    for uid in real_top_users_ids:
        msgs = user_msg_count[uid]
        chars = user_char_count[uid]
        avg_c = round(chars / msgs, 1) if msgs > 0 else 0
        top_users_data.append({
            'user_id': uid,
            'name': user_names.get(uid, f"User_{uid}"),
            'messages': msgs,
            'chars': chars,
            'avg_chars': avg_c
        })

    # 3. Формування ТОП дуетів виключно між реальними людьми
    top_duets = []
    for (u1, u2), count in reply_pairs.most_common():
        name1 = user_names.get(u1, "")
        name2 = user_names.get(u2, "")
        if is_real_user(u1, name1) and is_real_user(u2, name2):
            top_duets.append({
                'user1_id': u1,
                'user1_name': name1,
                'user2_id': u2,
                'user2_name': name2,
                'replies_count': count
            })
            if len(top_duets) == 10:
                break

    # 4. AI Психоаналіз ТОП-20 РЕАЛЬНИХ користувачів через Gemini API
    print(f"🧠 Генерируємо AI психологічні профілі для {len(real_top_users_ids)} реальних користувачів...")
    ai_profiles = {}
    for idx, uid in enumerate(real_top_users_ids, 1):
        uname = user_names.get(uid, f"User_{uid}")
        samples = user_samples[uid]
        print(f"  [{idx}/{len(real_top_users_ids)}] Аналіз портрета для: {uname} ({len(samples)} повідомлень)...")
        profile = generate_gemini_profile(uname, samples, GEMINI_API_KEY)
        profile['user_id'] = uid
        profile['name'] = uname
        ai_profiles[str(uid)] = profile

    # 5. Збереження результатів у data/chat_analytics.json
    output_dir = os.path.join(PROJECT_ROOT, "data")
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "chat_analytics.json")

    analytics_result = {
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total_messages": total_messages,
            "total_chars": total_chars,
            "avg_message_len": avg_msg_len,
            "total_users": len(user_msg_count)
        },
        "top_users": top_users_data,
        "duets": top_duets,
        "top_emojis": [{"emoji": e, "count": c} for e, c in emoji_counter.most_common(15)],
        "top_slang": [{"word": w, "count": c} for w, c in slang_counter.most_common(20)],
        "longreads": top_longreads,
        "profiles": ai_profiles
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(analytics_result, f, ensure_ascii=False, indent=2)

    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"✅ Аналіз завершено за {elapsed:.2f} сек!")
    print(f"📁 Результат збережено у: {output_file}")

if __name__ == '__main__':
    main()
