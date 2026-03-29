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
        logger.warning("Не удалось определить язык, считаем русским")
        return "ru"


def translate_to_russian(text: str) -> str:
    """Переводит текст на русский, если он не на русском."""
    lang = detect_language(text)
    if lang == "ru":
        return text
    try:
        translated = GoogleTranslator(source="auto", target="ru").translate(text)
        logger.info("Текст переведён с %s на русский", lang)
        return translated
    except Exception as e:
        logger.error("Ошибка перевода: %s", e)
        raise
