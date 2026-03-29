import logging
from langdetect import detect, LangDetectException
from deep_translator import GoogleTranslator

logger = logging.getLogger(__name__)


def detect_language(text: str) -> str:
    """Определяет язык текста. Возвращает код языка ('ru', 'en', ...)."""
    try:
        lang = detect(text)
        logger.info("Определён язык: %s", lang)
        return lang
    except LangDetectException:
        logger.warning("Не удалось определить язык")
        return "ru"


def translate_text(text: str, target_lang: str) -> str:
    """Переводит текст на target_lang ('ru' или 'en'), если он уже на нём — возвращает как есть."""
    src_lang = detect_language(text)
    if src_lang == target_lang:
        return text
    try:
        translated = GoogleTranslator(source="auto", target=target_lang).translate(text)
        logger.info("Переведено с %s на %s", src_lang, target_lang)
        return translated
    except Exception as e:
        logger.error("Ошибка перевода: %s", e)
        raise
