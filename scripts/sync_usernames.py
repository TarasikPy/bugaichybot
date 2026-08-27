import os
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ANALYTICS_PATH = BASE_DIR / 'data' / 'chat_analytics.json'
CACHE_PATH = BASE_DIR / 'storage' / 'users_cache.json'

USER_MAPPINGS = {
    1318789006: {"name": "Кійотака", "username": "shadow_tar"},
    5730136104: {"name": "Андрій Тромб", "username": "kazubrid"},
    1286527597: {"name": "Адріанікс🎀", "username": "apankiv"},
    2005833676: {"name": "Марія", "username": "mariai_k"},
    7292577573: {"name": "Alina", "username": "it_alina6"},
    2045119679: {"name": "мяу", "username": "poluni_chka"},
    1375996435: {"name": "Владислав Сидор", "username": "lordworldss"},
    1591084301: {"name": "Сергій Прокопчук", "username": "ftcserhiy"},
    1922420385: {"name": "ангелик", "username": "linali_0"},
    1461200386: {"name": "Маргарита", "username": "desomaro"},
    878744016: {"name": "Ярослав", "username": "petrovychyaroslav"}
}

# Update chat_analytics.json
if ANALYTICS_PATH.exists():
    with open(ANALYTICS_PATH, 'r', encoding='utf-8') as f:
        analytics = json.load(f)
    profiles = analytics.get('profiles', {})
    for uid, info in USER_MAPPINGS.items():
        uid_str = str(uid)
        if uid_str in profiles:
            profiles[uid_str]['username'] = info['username']
            profiles[uid_str]['user_id'] = uid
    with open(ANALYTICS_PATH, 'w', encoding='utf-8') as f:
        json.dump(analytics, f, ensure_ascii=False, indent=2)
    print("Updated chat_analytics.json with usernames.")

# Update users_cache.json
CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
cache_data = {}
if CACHE_PATH.exists():
    try:
        with open(CACHE_PATH, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
    except Exception:
        cache_data = {}

for uid, info in USER_MAPPINGS.items():
    uname = info['username']
    name = info['name']
    cache_data[uname] = {
        'first_name': name,
        'user_id': uid,
        'name': name,
        'id': uid
    }
    cache_data[str(uid)] = name

with open(CACHE_PATH, 'w', encoding='utf-8') as f:
    json.dump(cache_data, f, ensure_ascii=False, indent=2)

print("Updated storage/users_cache.json with usernames and IDs.")
