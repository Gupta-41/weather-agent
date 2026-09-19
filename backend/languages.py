"""Languages the assistant can answer in.

`speech_tag` is the BCP-47 tag the browser's Web Speech API wants for both
recognition and synthesis. `native` is what we show in the language picker —
people pick their own language faster when it's written in their own script.
"""

LANGUAGES = {
    "en": {"name": "English", "native": "English", "speech_tag": "en-IN"},
    "hi": {"name": "Hindi", "native": "हिन्दी", "speech_tag": "hi-IN"},
    "te": {"name": "Telugu", "native": "తెలుగు", "speech_tag": "te-IN"},
    "ta": {"name": "Tamil", "native": "தமிழ்", "speech_tag": "ta-IN"},
    "bn": {"name": "Bengali", "native": "বাংলা", "speech_tag": "bn-IN"},
    "mr": {"name": "Marathi", "native": "मराठी", "speech_tag": "mr-IN"},
    "kn": {"name": "Kannada", "native": "ಕನ್ನಡ", "speech_tag": "kn-IN"},
}

DEFAULT_LANGUAGE = "en"


def normalize(code: str | None) -> str:
    """Accept 'hi', 'hi-IN', 'HI' — anything else falls back to English."""
    if not code:
        return DEFAULT_LANGUAGE
    base = str(code).strip().lower().replace("_", "-").split("-")[0]
    return base if base in LANGUAGES else DEFAULT_LANGUAGE


def language_name(code: str) -> str:
    return LANGUAGES[normalize(code)]["name"]


def as_list() -> list[dict]:
    return [{"code": code, **meta} for code, meta in LANGUAGES.items()]
