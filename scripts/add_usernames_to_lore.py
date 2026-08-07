import os
import re

USERNAME_MAP = {
    "2005833676": "@Mariai_k",
    "5730136104": "@Kazubrid",
    "1318789006": "@shadow_tar",
    "1375996435": "@Lordworldss",
    "2045119679": "@poluni_chka",
    "1591084301": "@ftcserhiy",
    "1922420385": "@linali_0",
    "7292577573": "@It_alina6",
    "1461200386": "@desomaro",
    "1286527597": "@Apankiv",
    "878744016": "@PetrovychYaroslav",
    "6266441947": "@ab_maria"
}

files_to_update = [
    '/home/taras/Documents/Bugaichyk 3.0/bugaichybot/data/users_export/FULL_LORE.txt',
    '/home/taras/Documents/Bugaichyk 3.0/bugaichybot/ФУЛЛЛЛ.txt'
]

for filepath in files_to_update:
    if not os.path.exists(filepath):
        continue
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()

    def replace_header(m):
        full_match = m.group(0)
        nick = m.group(1)
        uid = m.group(2)
        if "Username:" in full_match:
            return full_match
        uname = USERNAME_MAP.get(uid, "")
        if uname:
            return f"[Нік: {nick} | ID: {uid} | Username: {uname}]"
        return full_match

    new_text = re.sub(r'\[Нік:\s*(.*?)\s*\|\s*ID:\s*(\d+)\]', replace_header, text)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_text)

print("Updated FULL_LORE.txt and ФУЛЛЛЛ.txt with usernames near IDs!")
