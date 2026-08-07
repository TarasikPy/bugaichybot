import os
import json
import re

FULL_LORE_PATH = '/home/taras/Documents/Bugaichyk 3.0/bugaichybot/data/users_export/FULL_LORE.txt'
ANALYTICS_PATH = '/home/taras/Documents/Bugaichyk 3.0/bugaichybot/data/chat_analytics.json'

with open(FULL_LORE_PATH, 'r', encoding='utf-8') as f:
    text = f.read()

header_regex = re.compile(r'^[^\n\[]+\s*\[Нік:\s*(.*?)\s*\|\s*ID:\s*(\d+)\]', re.MULTILINE)
matches = list(header_regex.finditer(text))

lore_profiles = {}

for i, m in enumerate(matches):
    nick = m.group(1).strip()
    user_id = int(m.group(2))
    start_pos = m.end()
    end_pos = matches[i+1].start() if i + 1 < len(matches) else len(text)
    block = text[start_pos:end_pos].strip()

    def extract_section(marker):
        pattern = rf'{marker}:?\s*\n?(.*?)(?=\n(?:🎭|📊|🧠|💡|🗣|🎯|\Z))'
        match = re.search(pattern, block, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""

    role = extract_section('🎭 Роль у чаті')
    style = extract_section('📊 Стиль спілкування')
    character = extract_section('🧠 Психологічний портрет')
    topics = extract_section('💡 Справжні теми')
    slang = extract_section('🗣 Улюблений сленг(?: та маркери)?')
    roast = extract_section('🎯 Коронний підкол')

    intro_sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', character) if s.strip()]
    intro = " ".join(intro_sentences[:2]) if intro_sentences else character[:200]

    full_text = f"🎭 РОЛЬ:\n{role}\n\n📊 СТИЛЬ:\n{style}\n\n🧠 ПСИХОАНАЛІЗ:\n{character}\n\n💡 ТЕМИ:\n{topics}\n\n🗣 СЛЕНГ:\n{slang}\n\n🎯 ПІДКОЛ:\n{roast}"

    lore_profiles[str(user_id)] = {
        "user_id": user_id,
        "name": nick,
        "role": role,
        "style": style,
        "character": character,
        "topics": topics,
        "slang": slang,
        "roast": roast,
        "intro": intro,
        "full_text": full_text
    }

print(f"Parsed {len(lore_profiles)} lore profiles.")

# Load chat_analytics.json
with open(ANALYTICS_PATH, 'r', encoding='utf-8') as f:
    content = f.read().replace('}-', '}')
    analytics_data = json.loads(content)

profiles_dict = analytics_data.setdefault("profiles", {})

# Overwrite / update with full lore data
for uid, pdata in lore_profiles.items():
    profiles_dict[uid] = pdata

# For any remaining profiles in chat_analytics.json that are missing roast/style/slang/full_text,
# generate clean fallback values so NO user has missing buttons or empty fields
for uid, pdata in profiles_dict.items():
    if not pdata.get("role"):
        pdata["role"] = "Учасник чату"
    if not pdata.get("character"):
        pdata["character"] = f"{pdata.get('name', 'Користувач')} — активний дописувач спільноти."
    if not pdata.get("intro"):
        pdata["intro"] = pdata["character"][:200]
    if not pdata.get("style"):
        pdata["style"] = "Активний дописувач з унікальною манерою спілкування."
    if not pdata.get("topics"):
        pdata["topics"] = "Спілкування, обговорення подій чату, гумор"
    if not pdata.get("slang"):
        pdata["slang"] = "База, крінж, ппц, лол"
    if not pdata.get("roast"):
        pdata["roast"] = f"Учасник, який робить чат живим та динамічним!"
    if not pdata.get("full_text"):
        pdata["full_text"] = f"🎭 РОЛЬ:\n{pdata['role']}\n\n📊 СТИЛЬ:\n{pdata['style']}\n\n🧠 ПСИХОАНАЛІЗ:\n{pdata['character']}\n\n💡 ТЕМИ:\n{pdata['topics']}\n\n🗣 СЛЕНГ:\n{pdata['slang']}\n\n🎯 ПІДКОЛ:\n{pdata['roast']}"

with open(ANALYTICS_PATH, 'w', encoding='utf-8') as f:
    json.dump(analytics_data, f, ensure_ascii=False, indent=2)

print("All profiles in chat_analytics.json now have 100% complete fields!")
