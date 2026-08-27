import os
import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
FULLLL_PATH = BASE_DIR / 'ФУЛЛЛЛ.txt'
ANALYTICS_PATH = BASE_DIR / 'data' / 'chat_analytics.json'

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

if not FULLLL_PATH.exists():
    print(f"Source file {FULLLL_PATH} does not exist. Skipping import.")
    exit(0)

with open(FULLLL_PATH, 'r', encoding='utf-8') as f:
    text = f.read()

header_regex = re.compile(r'\[Нік:\s*(.*?)\s*\|\s*ID:\s*(\d+)(?:\s*\|\s*Username:\s*@?([^\s\]]+))?\]')
matches = list(header_regex.finditer(text))

profiles = {}

for i, m in enumerate(matches):
    nick = m.group(1).strip()
    user_id = int(m.group(2))
    username = (m.group(3) or "").strip().lstrip('@').lower()

    start_pos = m.end()
    end_pos = matches[i+1].start() if i + 1 < len(matches) else len(text)
    block = text[start_pos:end_pos].strip()

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
        'name': nick,
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
