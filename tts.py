import logging
import os
import subprocess
import tempfile

import edge_tts

logger = logging.getLogger(__name__)

VOICE = "ru-RU-SvetlanaNeural"  # женский, или "ru-RU-DmitryNeural" для мужского


async def text_to_ogg(text: str) -> str:
    """Озвучивает текст через edge-tts и возвращает путь к .ogg файлу."""
    tmp_mp3 = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tmp_mp3.close()
    tmp_ogg = tempfile.NamedTemporaryFile(suffix=".ogg", delete=False)
    tmp_ogg.close()

    try:
        communicate = edge_tts.Communicate(text, voice=VOICE)
        await communicate.save(tmp_mp3.name)

        subprocess.run(
            ["ffmpeg", "-i", tmp_mp3.name, "-c:a", "libvorbis",
             tmp_ogg.name, "-y", "-loglevel", "quiet"],
            check=True
        )
        logger.info("Аудио готово: %d символов", len(text))
        return tmp_ogg.name
    except Exception as e:
        if os.path.exists(tmp_ogg.name):
            os.unlink(tmp_ogg.name)
        logger.error("Ошибка TTS: %s", e)
        raise
    finally:
        if os.path.exists(tmp_mp3.name):
            os.unlink(tmp_mp3.name)


def cleanup_file(filepath: str) -> None:
    try:
        if os.path.exists(filepath):
            os.unlink(filepath)
    except OSError as e:
        logger.warning("Не удалось удалить %s: %s", filepath, e)
