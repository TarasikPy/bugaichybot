import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ANALYTICS_PATH = BASE_DIR / 'data' / 'chat_analytics.json'

if not ANALYTICS_PATH.exists():
    print(f"File {ANALYTICS_PATH} does not exist.")
    exit(0)

with open(ANALYTICS_PATH, 'r', encoding='utf-8') as f:
    data = json.load(f)

profiles = data.get("profiles", {})

# List of all user header names that could accidentally leak into trailing text
HEADER_NAMES = [
    'MARIA', 'МАРАТА', 'МАРІЯ', 'АНДРІЙ', 'КІЙОТАКА', 'ВЛАДИСЛАВ', 
    'МЯУ', 'СЕРГІЙ', 'АНГЕЛИК', 'АЛІНА', 'ALINA', 'РИТА', 'МАРГАРИТА', 
    'АДРІАНА', 'АДРІАНІКС', 'ЯРОСЛАВ'
]

def clean_field_text(text: str) -> str:
    if not text:
        return ""
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        # Skip lines that are just standalone header names or numbers
        if stripped in HEADER_NAMES or stripped.upper() in HEADER_NAMES:
            continue
        if re.match(r'^[A-ZА-Я0-9_.\s\-#]+$', stripped) and len(stripped) < 25 and not stripped.startswith('•') and not stripped.startswith('1.'):
            # Check if it looks like a user header title e.g. "АЛІНА", "РИТА", "СЕРГІЙ", "#"
            if any(h in stripped.upper() for h in HEADER_NAMES) or stripped == '#':
                continue
        cleaned_lines.append(line)
    
    # Strip any trailing blank lines or header lines from the bottom
    result = "\n".join(cleaned_lines).strip()
    while result:
        last_line = result.split('\n')[-1].strip().upper()
        if last_line in HEADER_NAMES or last_line == '#' or (len(last_line) < 20 and any(h in last_line for h in HEADER_NAMES)):
            result = "\n".join(result.split('\n')[:-1]).strip()
        else:
            break
    return result

cleaned_count = 0
for uid, p in profiles.items():
    for field in ['role', 'style', 'character', 'topics', 'slang', 'roast']:
        old_val = p.get(field, '')
        new_val = clean_field_text(old_val)
        if old_val != new_val:
            print(f"Cleaned [{p.get('name', uid)}] field '{field}': removed trailing header tag!")
            p[field] = new_val
            cleaned_count += 1

    # Rebuild intro and full_text clean
    intro_sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', p.get('character', '')) if s.strip()]
    p['intro'] = " ".join(intro_sentences[:2]) if intro_sentences else p.get('character', '')[:200]
    p['full_text'] = f"🎭 РОЛЬ:\n{p.get('role', '')}\n\n📊 СТИЛЬ:\n{p.get('style', '')}\n\n🧠 ПСИХОАНАЛІЗ:\n{p.get('character', '')}\n\n💡 ТЕМИ:\n{p.get('topics', '')}\n\n🗣 СЛЕНГ:\n{p.get('slang', '')}\n\n🎯 ПІДКОЛ:\n{p.get('roast', '')}"

with open(ANALYTICS_PATH, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"\nFinished! Cleaned {cleaned_count} fields across all profiles.")
