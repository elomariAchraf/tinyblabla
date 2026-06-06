import re

_FRENCH_WORDS = frozenset([
    "je", "tu", "il", "elle", "nous", "vous", "ils", "elles",
    "le", "la", "les", "un", "une", "des", "du", "de", "et",
    "est", "sont", "que", "qui", "dans", "sur", "avec", "pour",
    "par", "mais", "ou", "donc", "ni", "car", "pas", "ne", "se",
])


def detect_language(text: str) -> str:
    """Return 'French' or 'English' based on accented characters and function words."""
    if re.search(r'[çœàâùûîïêëôéèæ]', text.lower()):
        return "French"
    words = set(re.findall(r'\b\w+\b', text.lower()))
    if len(words & _FRENCH_WORDS) >= 2:
        return "French"
    return "English"
