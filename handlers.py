import logging
from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from config import ALLOWED_USERS, MAX_TEXT_LENGTH
from translate import translate_to_russian
from tts import text_to_ogg, cleanup_file
from utils import split_text, clean_text, RateLimiter

logger = logging.getLogger(__name__)
router = Router()
rate_limiter = RateLimiter()


@router.message(F.text == "/start")
async def cmd_start(message: Message):
    if not _is_allowed(message):
        return
    await message.answer(
        "Привет! Отправь мне текст, и я озвучу его голосовым сообщением.\n"
        "Поддерживаю русский и английский (переведу на русский).\n"
        f"Максимум {MAX_TEXT_LENGTH} символов."
    )


@router.message(F.text == "/help")
async def cmd_help(message: Message):
    if not _is_allowed(message):
        return
    await message.answer(
        "Просто отправь текст — получишь голосовое.\n"
        "Английский текст автоматически переведу на русский.\n"
        f"Лимит: {MAX_TEXT_LENGTH} символов."
    )


@router.message(F.text)
async def handle_text(message: Message):
    if not _is_allowed(message):
        return

    user_id = message.from_user.id
    text = message.text.strip()

    # Rate limit
    if not rate_limiter.is_allowed(user_id):
        await message.answer("Слишком много запросов. Подожди немного.")
        return

    # Проверка длины
    if len(text) > MAX_TEXT_LENGTH:
        await message.answer(f"Текст слишком длинный ({len(text)} символов). Максимум — {MAX_TEXT_LENGTH}.")
        return

    if not text:
        await message.answer("Пустое сообщение.")
        return

    await message.answer("Обрабатываю...")

    try:
        # Перевод если нужно
        russian_text = translate_to_russian(text)

        # Очистка от символов, которые TTS произносит вслух
        russian_text = clean_text(russian_text)

        # Разбиваем на части
        chunks = split_text(russian_text)

        for i, chunk in enumerate(chunks):
            ogg_path = None
            try:
                ogg_path = text_to_ogg(chunk)
                voice = FSInputFile(ogg_path)
                await message.answer_voice(voice)
            finally:
                if ogg_path:
                    cleanup_file(ogg_path)

        if len(chunks) > 1:
            await message.answer(f"Готово! Отправлено {len(chunks)} голосовых.")

    except Exception as e:
        logger.error("Ошибка обработки для user %s: %s", user_id, e)
        await message.answer("Произошла ошибка при обработке. Попробуй ещё раз.")


def _is_allowed(message: Message) -> bool:
    """Проверяет, есть ли пользователь в whitelist."""
    if ALLOWED_USERS and message.from_user.id not in ALLOWED_USERS:
        logger.warning("Доступ запрещён для user_id=%s", message.from_user.id)
        return False
    return True
