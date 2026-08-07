import os
import json
import re

FULLLL_PATH = '/home/taras/Documents/Bugaichyk 3.0/bugaichybot/ФУЛЛЛЛ.txt'
ANALYTICS_PATH = '/home/taras/Documents/Bugaichyk 3.0/bugaichybot/data/chat_analytics.json'

with open(FULLLL_PATH, 'r', encoding='utf-8') as f:
    text = f.read()

header_regex = re.compile(r'\[Нік:\s*(.*?)\s*\|\s*ID:\s*(\d+)\]')
matches = list(header_regex.finditer(text))

profiles = {}

for i, m in enumerate(matches):
    nick = m.group(1).strip()
    user_id = int(m.group(2))
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
    for key, pattern in markers:
        match = re.search(pattern, block)
        if match:
            marker_positions.append((match.start(), match.end(), key))

    marker_positions.sort(key=lambda x: x[0])

    for idx, (m_start, m_end, key) in enumerate(marker_positions):
        next_start = marker_positions[idx+1][0] if idx + 1 < len(marker_positions) else len(block)
        val = block[m_end:next_start].strip()
        # Clean up any trailing header name in roast or last section
        val = re.sub(r'\n+[A-ZА-Я0-9_./\s]+$', '', val).strip()
        sections[key] = val

    intro_sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', sections['character']) if s.strip()]
    intro = " ".join(intro_sentences[:2]) if intro_sentences else sections['character'][:200]

    full_text = f"🎭 РОЛЬ:\n{sections['role']}\n\n📊 СТИЛЬ:\n{sections['style']}\n\n🧠 ПСИХОАНАЛІЗ:\n{sections['character']}\n\n💡 ТЕМИ:\n{sections['topics']}\n\n🗣 СЛЕНГ:\n{sections['slang']}\n\n🎯 ПІДКОЛ:\n{sections['roast']}"

    profiles[str(user_id)] = {
        "user_id": user_id,
        "name": nick,
        "role": sections['role'],
        "style": sections['style'],
        "character": sections['character'],
        "topics": sections['topics'],
        "slang": sections['slang'],
        "roast": sections['roast'],
        "intro": intro,
        "full_text": full_text
    }

with open(ANALYTICS_PATH, 'r', encoding='utf-8') as f:
    analytics_data = json.loads(f.read().replace('}-', '}'))

analytics_data["profiles"] = profiles

with open(ANALYTICS_PATH, 'w', encoding='utf-8') as f:
    json.dump(analytics_data, f, ensure_ascii=False, indent=2)

print("100% Cleaned and Updated!")
