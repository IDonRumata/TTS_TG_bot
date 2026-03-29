import logging
import os
import tempfile
from pathlib import Path
from gtts import gTTS

logger = logging.getLogger(__name__)


def text_to_ogg(text: str) -> str:
    """Озвучивает текст и возвращает путь к .ogg файлу."""
    tmp = tempfile.NamedTemporaryFile(suffix=".ogg", delete=False)
    tmp.close()
    try:
        tts = gTTS(text=text, lang="ru", slow=False)
        tts.save(tmp.name)
        logger.info("Аудио сохранено: %s (%d символов)", tmp.name, len(text))
        return tmp.name
    except Exception as e:
        # Удаляем файл при ошибке
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)
        logger.error("Ошибка TTS: %s", e)
        raise


def cleanup_file(filepath: str) -> None:
    """Удаляет временный файл."""
    try:
        if os.path.exists(filepath):
            os.unlink(filepath)
    except OSError as e:
        logger.warning("Не удалось удалить %s: %s", filepath, e)
