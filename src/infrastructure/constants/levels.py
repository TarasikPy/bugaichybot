"""Relationship levels configuration and couple command definitions."""

from typing import TypedDict


class RelationshipLevelInfo(TypedDict):
    name: str
    emoji: str
    required_points: int
    description: str


class CoupleCommandInfo(TypedDict):
    action: str
    points: int
    emoji: str


# Progression system for community relationship points
RELATIONSHIP_LEVELS: dict[int, RelationshipLevelInfo] = {
    0: {
        "name": "Знайомство",
        "emoji": "👋",
        "required_points": 0,
        "description": "Початковий етап знайомства, перші кроки до зближення",
    },
    1: {
        "name": "Симпатія",
        "emoji": "😊",
        "required_points": 10,
        "description": "З'являється взаємний інтерес та приємне спілкування",
    },
    2: {
        "name": "Романтичні почуття",
        "emoji": "💕",
        "required_points": 25,
        "description": "Перші романтичні моменти та особливі відчуття",
    },
    3: {
        "name": "Закоханість",
        "emoji": "😍",
        "required_points": 45,
        "description": "Глибока емоційна прив'язаність та частка думок один про одного",
    },
    4: {
        "name": "Кохання",
        "emoji": "❤️",
        "required_points": 75,
        "description": "Міцні почуття та готовність до серйозних стосунків",
    },
    5: {
        "name": "Глибоке кохання",
        "emoji": "💖",
        "required_points": 110,
        "description": "Безумовна любов та повне розуміння один одного, можна одружитись",
    },
    6: {
        "name": "Душевна єдність",
        "emoji": "💝",
        "required_points": 150,
        "description": "Ідеальна гармонія та духовний зв'язок",
    },
    7: {
        "name": "Вічне кохання",
        "emoji": "💞",
        "required_points": 200,
        "description": "Нерозривний зв'язок душ та серць на все життя",
    },
    8: {
        "name": "Божественне кохання",
        "emoji": "💫",
        "required_points": 250,
        "description": "Вищий рівень духовного з'єднання та любові",
    },
    9: {
        "name": "Абсолютна єдність",
        "emoji": "✨",
        "required_points": 300,
        "description": "Досконала гармонія двох душ як одне ціле",
    },
}

# General couple commands with relationship points bonus
COUPLE_COMMANDS: dict[str, CoupleCommandInfo] = {
    "kiss": {"action": "поцілував", "points": 3, "emoji": "💋"},
    "hug": {"action": "обійняв", "points": 2, "emoji": "🤗"},
    "love": {"action": "кохає", "points": 4, "emoji": "💕"},
    "date": {"action": "ходить на побачення з", "points": 5, "emoji": "🌹"},
    "flirt": {"action": "фліртує з", "points": 2, "emoji": "😏"},
    "gift": {"action": "дарує подарунок", "points": 3, "emoji": "🎁"},
    "dance": {"action": "танцює з", "points": 3, "emoji": "💃"},
    "hold": {"action": "тримає за руку", "points": 2, "emoji": "👫"},
    "cuddle": {"action": "обіймається з", "points": 3, "emoji": "🥰"},
    "whisper": {"action": "шепоче солодкі слова", "points": 3, "emoji": "🗣️"},
    "smile": {"action": "посміхається", "points": 1, "emoji": "😊"},
    "wink": {"action": "підморгує", "points": 1, "emoji": "😉"},
    "compliment": {"action": "робить комплімент", "points": 2, "emoji": "🥺"},
    "surprise": {"action": "робить сюрприз", "points": 4, "emoji": "🎉"},
    "serenade": {"action": "співає серенаду", "points": 4, "emoji": "🎵"},
    "cook": {"action": "готує для", "points": 3, "emoji": "👨‍🍳"},
    "massage": {"action": "робить масаж", "points": 3, "emoji": "💆"},
    "write": {"action": "пише любовного листа", "points": 4, "emoji": "💌"},
    "picnic": {"action": "влаштовує пікнік з", "points": 5, "emoji": "🧺"},
    "stargazing": {"action": "дивиться на зірки з", "points": 4, "emoji": "🌟"},
    "travel": {"action": "подорожує з", "points": 6, "emoji": "✈️"},
    "propose": {"action": "робить пропозицію", "points": 0, "emoji": "💍"},
    "accept": {"action": "приймає пропозицію від", "points": 0, "emoji": "✅"},
    "reject": {"action": "відхиляє пропозицію від", "points": 0, "emoji": "❌"},
    "dating": {"action": "розпочинає стосунки з", "points": 2, "emoji": "💫"},
    "breakup": {"action": "розстається з", "points": 0, "emoji": "😢"},
    "divorce": {"action": "розлучається з", "points": 0, "emoji": "💔"},
}

# Special actions for married couples
MARRIED_COMMANDS: dict[str, CoupleCommandInfo] = {
    "honeymoon": {"action": "їде в медовий місяць з", "points": 10, "emoji": "🏝️"},
    "anniversary": {"action": "святкує річницю з", "points": 8, "emoji": "🎊"},
    "family_dinner": {"action": "влаштовує сімейну вечерю з", "points": 5, "emoji": "🍽️"},
    "home_together": {"action": "облаштовує дім разом з", "points": 6, "emoji": "🏠"},
    "support": {"action": "підтримує в важкі часи", "points": 7, "emoji": "🤝"},
    "plan_future": {"action": "планує майбутнє з", "points": 6, "emoji": "📋"},
    "adopt_pet": {"action": "заводить домашню тварину з", "points": 5, "emoji": "🐕"},
    "renew_vows": {"action": "поновлює шлюбні обітниці з", "points": 15, "emoji": "💒"},
}

# Trio group commands
TRIO_COMMANDS: dict[str, CoupleCommandInfo] = {
    "group_hug": {"action": "обіймається разом з", "points": 4, "emoji": "🤗"},
    "trio_date": {"action": "йде на побачення втрьох з", "points": 6, "emoji": "🌹"},
    "group_dance": {"action": "танцює втрьох з", "points": 5, "emoji": "💃"},
    "trio_travel": {"action": "подорожує втрьох з", "points": 8, "emoji": "✈️"},
    "support_each": {"action": "підтримують один одного з", "points": 5, "emoji": "🤝"},
    "celebrate_together": {"action": "святкує разом з", "points": 6, "emoji": "🎉"},
}

# Combined dictionary of all couple actions
ALL_COUPLE_COMMANDS: dict[str, CoupleCommandInfo] = {
    **COUPLE_COMMANDS,
    **MARRIED_COMMANDS,
    **TRIO_COMMANDS,
}

# Recognized standard commands
VALID_COMMANDS: list[str] = [
    "start",
    "help",
    "relationships",
    "myrelationships",
    "flipcoin",
    "proposals",
    "commands",
    "trio",
    *ALL_COUPLE_COMMANDS.keys(),
]
