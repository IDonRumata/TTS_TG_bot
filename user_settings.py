from dataclasses import dataclass, field
from typing import Dict

# Доступные голоса по языкам
VOICE_OPTIONS: dict[str, list[tuple[str, str]]] = {
    "ru": [
        ("ru-RU-SvetlanaNeural", "Светлана 👩"),
        ("ru-RU-DmitryNeural",   "Дмитрий 👨"),
    ],
    "en": [
        ("en-US-JennyNeural", "Jenny 👩"),
        ("en-US-GuyNeural",   "Guy 👨"),
    ],
}

LANG_LABELS = {
    "ru": "🇷🇺 Русский",
    "en": "🇺🇸 English",
}

DEFAULT_LANG  = "ru"
DEFAULT_VOICE = VOICE_OPTIONS["ru"][0][0]


@dataclass
class UserConfig:
    language: str = DEFAULT_LANG
    voice:    str = DEFAULT_VOICE


_settings: Dict[int, UserConfig] = {}


def get(user_id: int) -> UserConfig:
    if user_id not in _settings:
        _settings[user_id] = UserConfig()
    return _settings[user_id]


def set_language(user_id: int, lang: str) -> None:
    cfg = get(user_id)
    cfg.language = lang
    cfg.voice = VOICE_OPTIONS[lang][0][0]   # сбрасываем на первый голос языка


def set_voice(user_id: int, voice: str) -> None:
    get(user_id).voice = voice
