"""Ukrainian name declension utility."""

from src.infrastructure.constants.names import (
    FEMALE_NAMES_DECLENSION,
    MALE_NAMES_DECLENSION,
)


def _decline_single_word(word: str) -> str:
    """Decline a single Ukrainian word or name component."""
    if not word:
        return ""

    if word in MALE_NAMES_DECLENSION:
        return MALE_NAMES_DECLENSION[word]
    if word in FEMALE_NAMES_DECLENSION:
        return FEMALE_NAMES_DECLENSION[word]

    # Return unchanged for ASCII English names or nicknames
    if word.isascii():
        return word

    # Automatic morphological heuristic for Ukrainian names
    if word.endswith(("ій", "ей")):
        return word[:-2] + "я"
    elif word.endswith("о"):
        return word[:-1] + "а"
    elif word.endswith(
        (
            "н",
            "м",
            "р",
            "к",
            "л",
            "с",
            "д",
            "б",
            "в",
            "г",
            "ж",
            "з",
            "п",
            "т",
            "ф",
            "х",
            "ц",
            "ч",
            "ш",
            "щ",
        )
    ):
        return word + "а"
    elif word.endswith("а"):
        return word[:-1] + "у"
    elif word.endswith("я"):
        return word[:-1] + "ю"

    return word


def decline_name(name: str) -> str:
    """Decline Ukrainian personal name from Nominative to Accusative case (кого/що).

    Supports predefined mappings and automatic Ukrainian grammatical rules.
    """
    if not name:
        return ""

    clean_name = name.strip()

    if clean_name in MALE_NAMES_DECLENSION:
        return MALE_NAMES_DECLENSION[clean_name]
    if clean_name in FEMALE_NAMES_DECLENSION:
        return FEMALE_NAMES_DECLENSION[clean_name]

    if " " in clean_name:
        parts = clean_name.split()
        return " ".join(_decline_single_word(p) for p in parts)

    return _decline_single_word(clean_name)
