import os
import json
import re

FULLLL_PATH = '/home/taras/Documents/Bugaichyk 3.0/bugaichybot/ФУЛЛЛЛ.txt'
ANALYTICS_PATH = '/home/taras/Documents/Bugaichyk 3.0/bugaichybot/data/chat_analytics.json'

USER_ID_MAP = {
    "MARIA": (2005833676, "Марія", "mariai_k"),
    "МАРІЯ": (2005833676, "Марія", "mariai_k"),
    "МАРІЯ ЛУБНИ": (2005833676, "Марія", "mariai_k"),
    "АНДРІЙ": (5730136104, "Андрій Тромб", "kazubrid"),
    "АНДРІЙ ТРОМБ": (5730136104, "Андрій Тромб", "kazubrid"),
    "КІЙОТАКА": (1318789006, "Кійотака", "shadow_tar"),
    "ВЛАДИСЛАВ": (1375996435, "Владислав Сидор", "lordworldss"),
    "ВЛАДИСЛАВ СИДОР": (1375996435, "Владислав Сидор", "lordworldss"),
    "ВЛАД": (1375996435, "Владислав Сидор", "lordworldss"),
    "МЯУ": (2045119679, "мяу", "poluni_chka"),
    "СЕРГІЙ": (1591084301, "Сергій Прокопчук", "ftcserhiy"),
    "СЕРГІЙ ПРОКОПЧУК": (1591084301, "Сергій Прокопчук", "ftcserhiy"),
    "АНГЕЛИК": (1922420385, "ангелик", "linali_0"),
    "АЛІНА": (7292577573, "Alina", "it_alina6"),
    "ALINA": (7292577573, "Alina", "it_alina6"),
    "РИТА": (1461200386, "Маргарита", "desomaro"),
    "МАРГАРИТА": (1461200386, "Маргарита", "desomaro"),
    "АДРІАНА": (1286527597, "Адріанікс🎀", "apankiv"),
    "АДРІАНІКС": (1286527597, "Адріанікс🎀", "apankiv"),
    "ЯРОСЛАВ": (878744016, "Ярослав", "petrovychyaroslav"),
    "АБ МАРІЯ ЕСТОНІЯ": (6266441947, "Марія Естонія", "ab"),
    "АБ": (6266441947, "Марія Естонія", "ab")
}

with open(FULLLL_PATH, 'r', encoding='utf-8') as f:
    text = f.read()

lines = text.split('\n')
blocks = []
current_header = None
current_body = []

for line in lines:
    line_clean = line.strip()
    if line_clean in USER_ID_MAP:
        if current_header and current_body:
            blocks.append((current_header, "\n".join(current_body)))
        current_header = line_clean
        current_body = []
    else:
        if current_header:
            current_body.append(line)

if current_header and current_body:
    blocks.append((current_header, "\n".join(current_body)))

profiles = {}

for header, block in blocks:
    user_id, clean_name, username = USER_ID_MAP[header]
    
    sections = {
        'role': '',
        'style': '',
        'character': '',
        'topics': '',
        'slang': '',
        'roast': ''
    }

    markers = [
        ('role', r'🎭\s*Роль у чаті:?'),
        ('style', r'📊\s*Стиль спілкування:?'),
        ('character', r'🧠\s*Психологічний портрет:?'),
        ('topics', r'💡\s*Справжні теми:?'),
        ('slang', r'🗣\s*Улюблений сленг(?: та маркери)?:?'),
        ('roast', r'🎯\s*Коронний підкол:?')
    ]

    marker_positions = []
    for key, regex in markers:
        match = re.search(regex, block)
        if match:
            marker_positions.append((match.start(), match.end(), key))

    marker_positions.sort(key=lambda x: x[0])

    for idx, (m_start, m_end, key) in enumerate(marker_positions):
        next_start = marker_positions[idx+1][0] if idx + 1 < len(marker_positions) else len(block)
        val = block[m_end:next_start].strip()
        sections[key] = val

    intro_sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', sections['character']) if s.strip()]
    intro = " ".join(intro_sentences[:2]) if intro_sentences else sections['character'][:200]

    full_text = f"🎭 РОЛЬ:\n{sections['role']}\n\n📊 СТИЛЬ:\n{sections['style']}\n\n🧠 ПСИХОАНАЛІЗ:\n{sections['character']}\n\n💡 ТЕМИ:\n{sections['topics']}\n\n🗣 СЛЕНГ:\n{sections['slang']}\n\n🎯 ПІДКОЛ:\n{sections['roast']}"

    profile_entry = {
        'user_id': user_id,
        'name': clean_name,
        'username': username,
        'role': sections['role'],
        'intro': intro,
        'roast': sections['roast'],
        'style': sections['style'],
        'character': sections['character'],
        'topics': sections['topics'],
        'slang': sections['slang'],
        'full_text': full_text
    }

    profiles[str(user_id)] = profile_entry
    if username:
        profiles[username.lower()] = profile_entry

analytics_data = {"profiles": profiles}

with open(ANALYTICS_PATH, 'w', encoding='utf-8') as f:
    json.dump(analytics_data, f, ensure_ascii=False, indent=2)

print(f"100% Cleaned and Updated! Exported {len(profiles)} profiles to {ANALYTICS_PATH}")
