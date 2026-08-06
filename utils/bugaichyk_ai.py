import random
import logging
import httpx
import json
import asyncio
from datetime import datetime
from config.settings import GEMINI_API_KEY
from config.bugaichyk_prompt import get_bugaichyk_prompt_for_user

logger = logging.getLogger(__name__)

# Текстова статистика щоденних цитат per user_id
_daily_quotes_cache = {
    "date": "",
    "users": set()
}

CHARACTERS_LIST = [
    ("Марія (Лубни)", "Полтавщина/Лубни, біологія, чорний гумор про шаурму з людей та анатомію"),
    ("Влад (Владислав Сидор)", "Львів/Захід, качок, любитель заліза та машин, бик, сапання бульби"),
    ("Ярослав", "Київ/КНУБА, архітектор, естет, clean look, малює натюрморти, вирубається на підлозі"),
    ("Маргарита (Рита)", "Київ/Краснокутськ, інженерка КАІ, технар, авіація, вишуканий сарказм, дупа України"),
    ("Вероніка (мяу)", "Київ, філологиня, мова, бусічки/пупсіки, капс, ховає вразливість за епатажем"),
    ("Лук'ян", "Берлін/Німеччина, закордонний тусовщик, спірні вкиди, пояснення за європейську базу"),
    ("Сергій Прокопчук", "Київ, філософ-айтішник, Ніцше, Сковорода, код/IT, високі технології"),
    ("Тарас", "творчий засновник/власник тусовки, техніка, кодинг, гаджети, авторитетна база"),
    ("Кійотака", "Карпати/Польща, мівіна, 7л зупи, малина в Польщі, Python, хастл"),
    ("Андрій Тромб", "Либохора/Карпати, маса, пельмені з пивом, капс АХАХАХАХ, лоукіки"),
    ("Ангеліна (ангелик)", "Польща, студентка-дипломатка, міжнародна політика, ZNOHUB, кнопка бану"),
    ("Аліна (Alina) / Аніка", "Хмельниччина, булочка чату, штатний психолог, танці, спортзал"),
    ("Адріана (Адріанікс)", "Калуш/Варшава, медикиня-кар'єристка, біохімія, медицина, анатомія, дедлайни 24/7"),
    ("Ab/Марія", "Естонія, естонська B2/C1, монополія, депресія через невідкриту сметану")
]

RISK_EVENTS = [
    "🎉 *Марія зжалилася і не продала тебе на анатомічні препарати.* Отримуєш +100 респекту!",
    "💀 *Ти спробував передушнити філософію.* Твій мозок закипів, втрачаєш 50 ґрошей.",
    "🔥 *Ангеліна поділилася шпаргалками з ZNOHUB.* Ти відчуваєш себе генієм на 5 хвилин!",
    "🥩 *Андрій Тромб покликав тебе на маса-збір* і змусив з'їсти 3 баняки зупи з пивом.",
    " малиновий хастл: *Кійотака змусив тебе пахати на плантаціях у Польщі 12 годин.*",
    "👑 *Влад призначив тебе Міністром Підвальної Качалки* у своїй майбутній Галактичній Імперії!",
    "💅 *Вероніка (мяу) назвала тебе 'бусічкою'* і відправила 10 сердечок у чат.",
    "📖 *Маргарита присвятила тобі сатиричну оду.* Твоя самооцінка впала на -50.",
    "🩺 *Адріана провела тобі експрес-огляд анатомії* і діагностувала хронічний недосип.",
    "🎨 *Ярослав навчив тебе виживати в гуртожитку КНУБА* та дозволив спати на підлозі ^^",
    "🥨 *Лук'ян прислав тобі листівку з Берліна* з підписом 'Пояснюю за базу!'."
]

MODELS_TO_TRY = ["gemini-flash-latest", "gemini-flash-lite-latest", "gemini-pro-latest"]

def _clean_truncated_text(text: str) -> str:
    """Гарантує, що текст не обрізано на півслові/півреченні"""
    if not text:
        return ""

    text = text.strip()

    # Якщо текст закінчується на розділовий знак або зірочку/дужку — все ок
    valid_endings = ('.', '!', '?', '*', '"', '»', '…', '🛑', '✨', '🔥', '👑', '💖', ')', ']', '}')
    if text.endswith(valid_endings):
        return text

    # Якщо речення перервалося, шукаємо останній закінчений розділовий знак
    last_punct = max(
        text.rfind('.'),
        text.rfind('!'),
        text.rfind('?'),
        text.rfind('*'),
        text.rfind('»'),
        text.rfind('"')
    )

    if last_punct > 15:
        # Обрізаємо по останій крапці/знаку
        return text[:last_punct + 1].strip()
    else:
        # Якщо знака не було, додаємо трикрапку
        return text + "..."

async def call_gemini_api(system_instruction: str, user_prompt: str) -> str:
    """Викликає Google Gemini API з розширеним ротейшеном моделей та обробкою 429"""
    if not GEMINI_API_KEY:
        return ""

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": f"{system_instruction}\n\nВАЖЛИВО: Будь 100% оригінальним, відповідай колоритною українською мовою Бойка з Карпат з часткою 'ся'! Відповідай ПРЯМО ТА ТОЧНО НА ПИТАННЯ ВИТОНЧЕНО ТА З ПІДЙОБАМИ!\nНЕ починай кожне повідомлення з вигуку 'Ба як!'! Уникай повторів!\n\nЗАВДАННЯ: {user_prompt}"}]
            }
        ],
        "generationConfig": {
            "temperature": 0.85,
            "maxOutputTokens": 800
        }
    }

    models_to_try = [
        "gemini-flash-latest",
        "gemini-flash-lite-latest",
        "gemini-pro-latest"
    ]

    async with httpx.AsyncClient(timeout=8.0) as client:
        for model_name in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
            for attempt in range(2):
                try:
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            content = candidates[0].get("content", {})
                            parts = content.get("parts", [])
                            text_parts = [
                                p.get("text", "")
                                for p in parts
                                if p.get("text") and not p.get("thought", False)
                            ]
                            full_text = " ".join(text_parts).strip()
                            if full_text:
                                return _clean_truncated_text(full_text)
                    elif resp.status_code == 429:
                        await asyncio.sleep(1.2)
                        continue
                except Exception as e:
                    logger.debug(f"Gemini API model {model_name} error: {e}")
                    break
    return ""

async def get_bugaichyk_roast(target_name: str, target_lore: str = "") -> str:
    """Генерує свіжий саркастичний роуст від Бугайчика"""
    prompt = f"Зроби унікальний, саркастичний, але дружній роуст (2-3 речення) для {target_name}. Використовуй РП-дії у зірочках *...* та живий молодіжний сленг. Лор: {target_lore}"
    system = get_bugaichyk_prompt_for_user(target_name)
    ai_resp = await call_gemini_api(system, prompt)
    if ai_resp:
        return ai_resp

    return f"*закотив очі та підморгнув* О, {target_name} знову на зв'язку! Ти дивуєш чат з кожним днем усе більше. Менше крінжувай, краще видай базу!"

async def get_bugaichyk_weather_commentary(city: str, temp: float, desc: str, feels_like: float) -> str:
    """Генерує 100% унікальний коментар Бугайчика до погоди з урахуванням географії персонажів"""
    city_lower = city.lower()
    char_hint = ""

    if "львів" in city_lower or "lviv" in city_lower:
        char_hint = "Це Львів! Прив'яжи коментар до Влада (качок, підвальна качалка, бруківка, кава)."
    elif "лубни" in city_lower or "полтав" in city_lower:
        char_hint = "Це Полтавщина/Лубни! Прив'яжи коментар до Марії (біологія, шаурма з людей, дрова)."
    elif "берлін" in city_lower or "berlin" in city_lower:
        char_hint = "Це Берлін! Прив'яжи коментар до Лук'яна (європейська база, тусовки)."
    elif "київ" in city_lower or "kyiv" in city_lower:
        char_hint = "Це Київ! Прив'яжи коментар до Ярослава (КНУБА, натюрморти) або Маргарити (інженерка КАІ) чи Вероніки."
    elif "калуш" in city_lower or "варшав" in city_lower:
        char_hint = "Це Калуш/Варшава! Прив'яжи коментар до Адріани (медикиня, дедлайни) чи Ангеліни (дипломатка)."
    elif "хмельницьк" in city_lower:
        char_hint = "Це Хмельниччина! Прив'яжи коментар до Аліни (булочка чату, танці, спортзал)."
    elif "краснокутськ" in city_lower:
        char_hint = "Це Краснокутськ! Прив'яжи коментар до Маргарити (дупа України, інженерія)."
    elif "естон" in city_lower or "таллін" in city_lower:
        char_hint = "Це Естонія! Прив'яжи коментар до Ab/Марії (монополія, іспит B2, сметана)."
    elif "польщ" in city_lower or "карпат" in city_lower or "либохор" in city_lower:
        char_hint = "Це Карпати/Польща! Прив'яжи коментар до Андрія Тромба (маса, пельмені) чи Кійотаки (малина, мівіна)."

    prompt = f"Напиши 100% УНІКАЛЬНИЙ зухвалий коментар від Бугайчика (1-2 речення) до погоди в місті {city}: температура {temp}°C (відчувається {feels_like}°C), стан: {desc}. {char_hint} ЗАБОРОНЕНО згадувати 'Сергій перестав душнити'!"
    system = get_bugaichyk_prompt_for_user()
    ai_resp = await call_gemini_api(system, prompt)
    if ai_resp:
        return ai_resp

    return f"*протягнув каву* У місті {city} зараз {temp}°C ({desc}). Погода саме для того, щоб вийти на свіже повітря й не спіймати крінж!"

async def get_bugaichyk_news_commentary(news_text: str) -> str:
    """Прокоментовує новину/форвард у зухвалому стилі Бугайчика з прив'язкою до тематичних персонажів"""
    from utils.helpers import format_ai_response_to_html

    prompt = f"""Користувач переслав новину/пост: '{news_text[:400]}'.
Напиши свіжу, зухвалу, живу реакцію від Бугайчика (1-3 речення).

ОБОВ'ЯЗКОВО залучай 1-2 персонажів із нашого чату, які ТЕМАТИЧНО відповідають цій новині:
- Політика / Геополітика / Закони / Дипломатія -> Ангеліна (дипломатка, ZNOHUB) або Лук'ян (Берлін) або Сергій.
- Технології / Інженерія / Авіація / Зброя / Заводи / IT -> Маргарита (інженерка КАІ, технар), Сергій (філософ-айтішник), Тарас або Кійотака (Python).
- Медицина / Біохімія / Анатомія / Віруси / Здоров'я -> Адріана (медикиня, дедлайни 24/7) або Марія (біологія, шаурма з людей, органи).
- Філологія / Мова / Освіта / ЗНО -> Вероніка (філологиня, капс, бусічки) або Ангеліна чи Ярослав (КНУБА).
- Психологія / Спорт / Лайфстайл -> Аліна / Аніка (психолог, спортзал) або Влад (підвальна качалка).
- Військові новини / Бавовна / Фронт -> Маргарита (технар), Влад (підвальна качалка), Андрій Тромб (лоукіки) чи Ангеліна.

КАТЕГОРИЧНО ЗАБОРОНЕНО щоразу згадувати тільки Лук'яна чи Влада! Підбирай людей тематично під суть новини."""

    system = get_bugaichyk_prompt_for_user()
    ai_resp = await call_gemini_api(system, prompt)
    if ai_resp:
        return format_ai_response_to_html(ai_resp)

    # Розумний динамічний фолбек за темою пересланого тексту
    text_lower = news_text.lower()
    if any(k in text_lower for k in ['війна', 'фронт', 'зброя', 'ракета', 'дрон', 'бавовна', 'удар', 'армія']):
        res = "<i>*спльокнув через зуби та затягнувся густим вейпом*</i>\n\n<b>Оце так бавовна в новинах!</b> Поки **Маргарита** розбирає техніку на гвинтики, а **Влад** качає підвальну масу, вороги нехай вчать бойківський діалект! 💣"
    elif any(k in text_lower for k in ['політика', 'закон', 'сша', 'європа', 'побуд', 'дипломат', 'президент', 'рада']):
        res = "<i>*припідняв капелюха та переглянув папери*</i>\n\n<b>Ба як, політичні двіжухи!</b> **Ангеліна** вже певно готує ноту протесту, а **Лук'ян** пояснює європейцям за справжню карпатську базу 📜!"
    elif any(k in text_lower for k in ['медицина', 'лікар', 'вірус', 'хвороба', 'здоров', 'аптека', 'біо']):
        res = "<i>*відставив чашку та покрутив головою*</i>\n\n<b>Ого, медичні новини!</b> **Адріана** вже готує дедлайни 24/7, а **Марія** шукає нові експерименти для своєї біології 🩺!"
    elif any(k in text_lower for k in ['it', 'код', 'програм', 'айті', 'гаджет', 'техно', 'python']):
        res = "<i>*поправив бойківського пояса і подивився на екран*</i>\n\n<b>Айтішні новини підвалили!</b> **Сергій Прокопчук** вже готує філософську душноту, а **Тарас** розгортає сервери на базі Python 💻!"
    else:
        res = "<i>*хрумкнув пальцями і перечитав переслане*</i>\n\n<b>Оце так новина в чаті!</b> Поки всі обговорюють цей вкид, наша база тримається міцно, а хастл не зупиняється ні на хвилину ☕!"

    return format_ai_response_to_html(res)

async def get_bugaichyk_judge(argument_text: str, user1: str, user2: str, recent_history: str = "") -> str:
    """Генерує вердикт ШІ-Судді для срачів з прямою відповіддю та аналізом історії повідомлень"""
    from utils.helpers import format_ai_response_to_html

    # Фільтруємо будь-які секретні команди з історії перед передачею в ШІ!
    clean_history = ""
    if recent_history:
        lines = recent_history.splitlines()
        clean_lines = [
            l for l in lines
            if not any(cmd in l.lower() for cmd in ['!пиши', '/say', '/пиши'])
        ]
        clean_history = "\n".join(clean_lines)

    history_block = f"\nІСТОРІЯ ОСТАННІХ ПОВІДОМЛЕНЬ У ЧАТІ:\n---\n{clean_history}\n---\n" if clean_history else ""

    prompt = f"""Ти — Бугайчик, зухвалий, суворий проукраїнський суддя чату.
Учасники суперечки: **{user1}** та **{user2}**.
Тема/Аргумент: '{argument_text}'.
{history_block}
КАТЕГОРИЧНІ ТА АБСОЛЮТНІ ПРАВИЛА:
1. **КАТЕГОРИЧНО ЗАБОРОНЕНО СЛОВА "Суперник", "Опонент", "Суперника", "Опонента" ТА ЮЗЕРНЕЙМИ З СОБАЧКОЮ!** Завжди вживай ТІЛЬКИ СВІТЛІ СПРАВЖНІ ІМЕНА: **{user1}** та **{user2}**!
2. **АНОНІМНІСТЬ ТА СЕКРЕТНІСТЬ**: КАТЕГОРИЧНО ТА АБСОЛЮТНО ЗАБОРОНЕНО згадувати будь-які секретні команди ('!пиши', '/say', '/пиши') або що хтось замовляв повідомлення через бота! Суди ТІЛЬКИ публічну суперечку про '{argument_text}'!
3. **ПРЯМА ВІДПОВІДЬ НА СУТЬ СПОРУ**:
   - Якщо суперечка торкається Криму — ПЕРШИМ ЖЕ РЕЧЕННЯМ голосно проголоси: **"КРИМ — ЦЕ БЕЗПЕРЕЧНО УКРАЇНА! КРАПКА!"**
   - Прочитай історію чату вище та процитуй конкретні репліки **{user1}** та **{user2}**, пояснюючи ХТО ЩО сказав і хто правий!
4. **ФОРМАТ ПЕРЕМОЖЦЯ ТА ЛУЗЕРА**:
   - 🏆 **Переможець срачу:** **{user1} ПЕРЕМІГ!** (*за що саме*)
   - 🤡 **Лузер / Крінжовик:** **{user2} ПРОГРАВ!** (*за що саме піймав крінж*)
5. **РП-ПОКАРАННЯ**: Признач конкретне смішне РП-покарання для **{user2}**.

Формат вердикту:
⚖️ **СУД БУГАЙЧИКА ВИНИС ВЕРДИКТ!**

(Пряма безкомпромісна відповідь з прямими цитатами реплік {user1} та {user2} з історії — 1-2 речення)

🏆 **Переможець срачу:** **{user1} ПЕРЕМІГ!** (*навалив суворої бази!*)
🤡 **Лузер / Крінжовик:** **{user2} ПРОГРАВ!** (*піймав конкретний крінж і йде геть!*)

📜 **РП-Покарання:** (кумедна РП-дія для {user2})"""

    system = get_bugaichyk_prompt_for_user()
    ai_resp = await call_gemini_api(system, prompt)
    if ai_resp:
        return format_ai_response_to_html(ai_resp)

    return format_ai_response_to_html(
        f"⚖️ **СУД БУГАЙЧИКА ВИНИС ВЕРДИКТ!**\n\n"
        f"**КРИМ — ЦЕ БЕЗПЕРЕЧНО УКРАЇНА! КРАПКА!**\n\n"
        f"🏆 **Переможець срачу:** **{user1} ПЕРЕМІГ!** (*навалив суворої бази*)\n"
        f"🤡 **Лузер / Крінжовик:** **{user2} ПРОГРАВ!** (*піймав конкретний крінж*)\n\n"
        f"📜 **РП-Покарання:** **{user2}** змушений сапати бульбу у Влада на плантаціях без права на вайфай!"
    )

async def check_and_get_quote(user_id: int) -> tuple[bool, str]:
    """Перевіряє денний ліміт цитат (1 раз на день для кожного користувача) та генерує ШІ-цитату"""
    from utils.helpers import escape_html
    today_str = datetime.now().strftime('%Y-%m-%d')
    if _daily_quotes_cache['date'] != today_str:
        _daily_quotes_cache['date'] = today_str
        _daily_quotes_cache['users'] = set()

    if user_id in _daily_quotes_cache['users']:
        refusal_prompt = "Користувач вже викликав /цитата сьогодні. Напиши відшив від Бугайчика (1-2 речення), що ліміт 1 цитата в день вичерпано. Скажи йому йти вчити вишмат або згадай органів через Марію."
        system = get_bugaichyk_prompt_for_user()
        ai_refusal = await call_gemini_api(system, refusal_prompt)
        if ai_refusal:
            return False, escape_html(ai_refusal)
        return False, "Еее, стоп-наркотик! Твоя лімітка мудрості на сьогодні всьо. Іди книжку почитай або вишмат повчи. 🛑"

    _daily_quotes_cache['users'].add(user_id)
    char_name, char_desc = random.choice(CHARACTERS_LIST)

    quote_prompt = f"Згенеруй 100% унікальну, філософсько-абсурдну, глибоку або крінжову цитату в стилі персонажа {char_name} ({char_desc}). Напиши ТІЛЬКИ текст цитати в лапках."
    system = get_bugaichyk_prompt_for_user()
    ai_quote = await call_gemini_api(system, quote_prompt)

    if not ai_quote:
        ai_quote = "Буття визначає свідомість, але якщо ти не видав базу, то навіщо взагалі заходив у чат?"

    res_text = f"📜 <b>ЗОЛОТИЙ ФОНД ЧАТУ (Мудрість дня):</b>\n\n<i>{escape_html(ai_quote)}</i>\n\n✍️ <b>© {escape_html(char_name)}</b>"
    return True, res_text

async def get_random_quote() -> str:
    """Генерує випадкову цитату з Золотого фонду через Gemini або локальний список"""
    from utils.helpers import escape_html
    char_name, char_desc = random.choice(CHARACTERS_LIST)
    quote_prompt = f"Згенеруй 100% унікальну, філософсько-абсурдну, глибоку або крінжову цитату в стилі персонажа {char_name} ({char_desc}). Напиши ТІЛЬКИ текст цитати в лапках."
    system = get_bugaichyk_prompt_for_user()
    ai_quote = await call_gemini_api(system, quote_prompt)

    if not ai_quote:
        ai_quote = "Буття визначає свідомість, але якщо ти не видав базу, то навіщо взагалі заходив у чат?"

    return f"📜 <b>ЗОЛОТИЙ ФОНД ЧАТУ (Мудрість дня):</b>\n\n<i>{escape_html(ai_quote)}</i>\n\n✍️ <b>© {escape_html(char_name)}</b>"

def get_random_risk(user_name: str) -> str:
    """Повертає РП-подію для рулетки"""
    event = random.choice(RISK_EVENTS)
    return f"🎰 <b>РП-РУЛЕТКА РИЗИКУ ДЛЯ {user_name.upper()}:</b>\n\n{event}"

async def get_bugaichyk_chat_reply(user_name: str, message_text: str, recent_history: str = "") -> str:
    """Генерує зухвалу, харизматичну та тематичну відповідь Бугайчика на тригер 'Бугайчик'"""
    from utils.helpers import format_ai_response_to_html

    history_block = f"\nІСТОРІЯ ПОВІДОМЛЕНЬ У ЧАТІ:\n---\n{recent_history}\n---\n" if recent_history else ""

    prompt = f"""Ти — Бугайчик, зухвалий, саркастичний та колоритний карпатський Бойко-газда.

Користувач {user_name} звернувся до тебе з повідомленням: '{message_text}'.
{history_block}
КАТЕГОРИЧНІ ПРАВИЛА ВІДПОВІДІ:
1. СТРУКТУРА ПОВІДОМЛЕННЯ:
   - Якщо є РП-дія (~40-50% шанс), запиши її в зірочках на першому рядку: *сплюнув шелуху від насіння*
   - ПІСЛЯ РП-ДІЇ СТАВ ПОРОЖНІЙ РЯДОК (\n\n)! Ніколи не зліплюй дію і розмову в один рядок!
   - Розмову починай з нового рядка чистим текстом!
2. Вживай влучний український матюк (курва, нахуй, бл*ть, зашквар) ТА частку `ся`!
3. Можеш додати 1 доречний смайлик (наприклад ☕, 🪵, ⚡, 🍺, 📜, 💣) інколи!
4. НІЯКИХ сирих юзернеймів з собачкою чи слів 'ШІ'!

Дай відповідь у 1-3 реченнях!"""

    system = get_bugaichyk_prompt_for_user(user_name)
    ai_resp = await call_gemini_api(system, prompt)
    if ai_resp:
        return format_ai_response_to_html(ai_resp)

    # Розумний динамічний фолбек, якщо API тимчасово на ліміті
    msg_lower = message_text.lower()
    if any(k in msg_lower for k in ['хто крутіш', 'хто кращ', 'хто кого', 'хто сильніш', 'я чи']):
        other_name = 'опонент'
        if 'андрій' in msg_lower or 'тромб' in msg_lower:
            other_name = 'Андрій Тромб'
        elif 'арма' in msg_lower:
            other_name = 'Арма'
        elif 'влад' in msg_lower:
            other_name = 'Влад'
        elif 'сергій' in msg_lower:
            other_name = 'Сергій'

        res = (
            f"<i>*поправив бойківського пояса і розреготався на увесь чат*</i>\n\n"
            f"<b>Та які тобі змагання, {user_name}!</b> Ти ниська зі своїм хастлом розриваєш чат, а {other_name} тільки й встигає масу на пельменях збирати! Обидва гарні, але ти ниська явно перченіший! ⚡"
        )
    elif any(k in msg_lower for k in ['як справи', 'шо ся маєш', 'як ся маєш', 'що робиш', 'шо робиш']):
        res = (
            f"<i>*затягнувся вейпом та припідняв капелюха*</i>\n\n"
            f"<b>Як ся маєш, {user_name}?</b> Робота кипить, гори стоять, а наша карпатська база тримається міцно! Тільки спокій та тотальна імба! ☕"
        )
    else:
        res = (
            f"<i>*хрумкнув пальцями і пильно глянув на {user_name}*</i>\n\n"
            f"<b>Ба як, {user_name}!</b> Ти питаєш за діло, тож слухай сюди: ниська все ся робить по факу, а хто сі сумніває — бодай би його шляк трафив! 🪵"
        )

    return format_ai_response_to_html(res)

