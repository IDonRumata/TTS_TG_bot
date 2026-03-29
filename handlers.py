import logging
from aiogram import Router, F
from aiogram.types import Message, FSInputFile, CallbackQuery, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import ALLOWED_USERS, MAX_TEXT_LENGTH
from translate import translate_text
from tts import text_to_ogg, cleanup_file
from utils import split_text, clean_text, RateLimiter
import user_settings as us

logger = logging.getLogger(__name__)
router = Router()
rate_limiter = RateLimiter()


# ─── Клавиатура настроек ────────────────────────────────────────────────────

def settings_keyboard(user_id: int) -> InlineKeyboardMarkup:
    cfg = us.get(user_id)
    builder = InlineKeyboardBuilder()

    # Кнопки языка
    for code, label in us.LANG_LABELS.items():
        mark = " ✅" if cfg.language == code else ""
        builder.button(text=f"{label}{mark}", callback_data=f"lang:{code}")
    builder.adjust(2)

    # Кнопки голоса для текущего языка
    for voice_id, voice_label in us.VOICE_OPTIONS[cfg.language]:
        mark = " ✅" if cfg.voice == voice_id else ""
        builder.button(text=f"{voice_label}{mark}", callback_data=f"voice:{voice_id}")
    builder.adjust(2, 2)

    return builder.as_markup()


# ─── Команды ────────────────────────────────────────────────────────────────

@router.message(F.text == "/start")
async def cmd_start(message: Message):
    if not _is_allowed(message):
        return
    await message.answer(
        "Привет! Отправь текст — озвучу голосовым сообщением.\n"
        "Поддерживаю 🇷🇺 русский и 🇺🇸 английский.\n"
        f"Лимит: {MAX_TEXT_LENGTH} символов.\n\n"
        "⚙️ /settings — настройки голоса и языка"
    )


@router.message(F.text == "/help")
async def cmd_help(message: Message):
    if not _is_allowed(message):
        return
    await message.answer(
        "Просто отправь текст — получишь голосовое.\n"
        "Текст автоматически переводится на выбранный язык.\n\n"
        "⚙️ /settings — выбор языка и голоса\n"
        f"Лимит: {MAX_TEXT_LENGTH} символов."
    )


@router.message(F.text == "/settings")
async def cmd_settings(message: Message):
    if not _is_allowed(message):
        return
    cfg = us.get(message.from_user.id)
    lang_label  = us.LANG_LABELS[cfg.language]
    voice_label = next(
        (v for vid, v in us.VOICE_OPTIONS[cfg.language] if vid == cfg.voice),
        cfg.voice
    )
    await message.answer(
        f"⚙️ <b>Настройки</b>\n\n"
        f"🌍 Язык: {lang_label}\n"
        f"🔊 Голос: {voice_label}",
        parse_mode="HTML",
        reply_markup=settings_keyboard(message.from_user.id)
    )


# ─── Callbacks настроек ─────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("lang:"))
async def cb_language(callback: CallbackQuery):
    if not _is_allowed_cb(callback):
        return
    lang = callback.data.split(":")[1]
    us.set_language(callback.from_user.id, lang)
    cfg = us.get(callback.from_user.id)
    voice_label = next(
        (v for vid, v in us.VOICE_OPTIONS[cfg.language] if vid == cfg.voice),
        cfg.voice
    )
    await callback.message.edit_text(
        f"⚙️ <b>Настройки</b>\n\n"
        f"🌍 Язык: {us.LANG_LABELS[cfg.language]}\n"
        f"🔊 Голос: {voice_label}",
        parse_mode="HTML",
        reply_markup=settings_keyboard(callback.from_user.id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("voice:"))
async def cb_voice(callback: CallbackQuery):
    if not _is_allowed_cb(callback):
        return
    voice = callback.data.split(":")[1]
    us.set_voice(callback.from_user.id, voice)
    cfg = us.get(callback.from_user.id)
    voice_label = next(
        (v for vid, v in us.VOICE_OPTIONS[cfg.language] if vid == cfg.voice),
        cfg.voice
    )
    await callback.message.edit_text(
        f"⚙️ <b>Настройки</b>\n\n"
        f"🌍 Язык: {us.LANG_LABELS[cfg.language]}\n"
        f"🔊 Голос: {voice_label}",
        parse_mode="HTML",
        reply_markup=settings_keyboard(callback.from_user.id)
    )
    await callback.answer(f"Голос изменён: {voice_label}")


# ─── Основной обработчик текста ─────────────────────────────────────────────

@router.message(F.text)
async def handle_text(message: Message):
    if not _is_allowed(message):
        return

    user_id = message.from_user.id
    text = message.text.strip()

    if not rate_limiter.is_allowed(user_id):
        await message.answer("Слишком много запросов. Подожди немного.")
        return

    if len(text) > MAX_TEXT_LENGTH:
        await message.answer(f"Текст слишком длинный ({len(text)} символов). Максимум — {MAX_TEXT_LENGTH}.")
        return

    if not text:
        await message.answer("Пустое сообщение.")
        return

    await message.answer("⏳ Обрабатываю...")

    try:
        cfg = us.get(user_id)

        # Перевод на выбранный язык
        out_text = translate_text(text, cfg.language)

        # Очистка символов
        out_text = clean_text(out_text)

        # Разбиваем на части и озвучиваем
        chunks = split_text(out_text)
        for chunk in chunks:
            ogg_path = None
            try:
                ogg_path = await text_to_ogg(chunk, voice=cfg.voice)
                await message.answer_voice(FSInputFile(ogg_path))
            finally:
                if ogg_path:
                    cleanup_file(ogg_path)

        if len(chunks) > 1:
            await message.answer(f"Готово! Отправлено {len(chunks)} голосовых.")

    except Exception as e:
        logger.error("Ошибка обработки для user %s: %s", user_id, e)
        await message.answer("Произошла ошибка. Попробуй ещё раз.")


# ─── Вспомогательные функции ────────────────────────────────────────────────

def _is_allowed(message: Message) -> bool:
    if ALLOWED_USERS and message.from_user.id not in ALLOWED_USERS:
        logger.warning("Доступ запрещён для user_id=%s", message.from_user.id)
        return False
    return True


def _is_allowed_cb(callback: CallbackQuery) -> bool:
    if ALLOWED_USERS and callback.from_user.id not in ALLOWED_USERS:
        logger.warning("Доступ запрещён для user_id=%s (callback)", callback.from_user.id)
        return False
    return True
