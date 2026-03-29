import logging
from aiogram import Router, F
from aiogram.types import (
    Message, FSInputFile, CallbackQuery,
    InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import ALLOWED_USERS, MAX_TEXT_LENGTH
from translate import translate_text
from tts import text_to_ogg, cleanup_file
from utils import split_text, clean_text, RateLimiter
from plans import PLANS, FREE_VOICES, plan_description, get_plan
from database import (
    get_or_create_user, update_user_settings,
    check_and_add_chars, get_user_stats
)
import user_settings as us
from payments_stars import plans_keyboard_stars

logger = logging.getLogger(__name__)
router = Router()
rate_limiter = RateLimiter()

# ── Постоянная клавиатура ─────────────────────────────────────────────────────

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="⚙️ Настройки"), KeyboardButton(text="📊 Мой статус")]],
    resize_keyboard=True,
    input_field_placeholder="Отправь текст для озвучки..."
)

# ── Вспомогательные функции ───────────────────────────────────────────────────

def settings_keyboard(user_id: int, cfg) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for code, label in us.LANG_LABELS.items():
        mark = " ✅" if cfg.language == code else ""
        builder.button(text=f"{label}{mark}", callback_data=f"lang:{code}")
    builder.adjust(2)
    for voice_id, voice_label in us.VOICE_OPTIONS[cfg.language]:
        mark = " ✅" if cfg.voice == voice_id else ""
        builder.button(text=f"{voice_label}{mark}", callback_data=f"voice:{voice_id}")
    builder.adjust(2, 2)
    return builder.as_markup()


def _is_allowed(message: Message) -> bool:
    if ALLOWED_USERS and message.from_user.id not in ALLOWED_USERS:
        logger.warning("Доступ запрещён для user_id=%s", message.from_user.id)
        return False
    return True


def _is_allowed_cb(callback: CallbackQuery) -> bool:
    if ALLOWED_USERS and callback.from_user.id not in ALLOWED_USERS:
        return False
    return True


# ── Команды ───────────────────────────────────────────────────────────────────

@router.message(F.text == "/start")
async def cmd_start(message: Message):
    if not _is_allowed(message):
        return
    await get_or_create_user(
        message.from_user.id,
        message.from_user.username or "",
        message.from_user.first_name or ""
    )
    await message.answer(
        "Привет! Отправь текст — озвучу голосовым сообщением.\n"
        "Поддерживаю 🇷🇺 русский и 🇺🇸 английский.\n\n"
        f"🆓 Бесплатно: 3 000 символов в день\n"
        f"💡 /plans — тарифы и оплата\n"
        f"📊 /status — твой лимит\n"
        f"⚙️ /settings — голос и язык",
        reply_markup=MAIN_KEYBOARD
    )


@router.message(F.text == "/help")
async def cmd_help(message: Message):
    if not _is_allowed(message):
        return
    await message.answer(
        "Просто отправь текст — получишь голосовое.\n"
        "Текст автоматически переводится на выбранный язык.\n\n"
        "📋 Команды:\n"
        "/settings — голос и язык\n"
        "/plans — тарифы и оплата\n"
        "/status — твой лимит и план\n"
        f"/paysupport — помощь с оплатой",
        reply_markup=MAIN_KEYBOARD
    )


@router.message(F.text.in_({"/status", "📊 Мой статус"}))
async def cmd_status(message: Message):
    if not _is_allowed(message):
        return
    await get_or_create_user(message.from_user.id)
    stats = await get_user_stats(message.from_user.id)

    day_info = (
        f"{stats['chars_today']:,} / {stats['limit_day']:,}"
        if stats['limit_day'] else f"{stats['chars_today']:,} / ∞"
    )
    month_info = (
        f"{stats['chars_month']:,} / {stats['limit_month']:,}"
        if stats['limit_month'] else "без лимита"
    )

    await message.answer(
        f"📊 *Твой статус*\n\n"
        f"Тариф: {stats['plan_name']}\n"
        f"Сегодня: {day_info} символов\n"
        f"В этом месяце: {month_info}\n\n"
        f"💡 /plans — сменить тариф",
        parse_mode="Markdown"
    )


@router.message(F.text == "/plans")
async def cmd_plans(message: Message):
    if not _is_allowed(message):
        return
    text = "💳 *Тарифные планы*\n\n"
    for pid, plan in PLANS.items():
        text += plan_description(pid) + "\n\n"
    text += "Оплата через Telegram Stars ⭐ (мгновенно, без комиссии):"

    await message.answer(text, parse_mode="Markdown", reply_markup=plans_keyboard_stars())


@router.message(F.text == "/paysupport")
async def cmd_paysupport(message: Message):
    """Обязательный хендлер по требованию Telegram для Stars."""
    if not _is_allowed(message):
        return
    await message.answer(
        "Если у тебя вопрос по оплате или нужен возврат средств — напиши сюда.\n"
        "Мы ответим в течение 24 часов."
    )


@router.message(F.text.in_({"/settings", "⚙️ Настройки"}))
async def cmd_settings(message: Message):
    if not _is_allowed(message):
        return
    await get_or_create_user(message.from_user.id)
    cfg = us.get(message.from_user.id)
    voice_label = next(
        (v for vid, v in us.VOICE_OPTIONS[cfg.language] if vid == cfg.voice), cfg.voice
    )
    await message.answer(
        f"⚙️ *Настройки*\n\n"
        f"🌍 Язык: {us.LANG_LABELS[cfg.language]}\n"
        f"🔊 Голос: {voice_label}",
        parse_mode="Markdown",
        reply_markup=settings_keyboard(message.from_user.id, cfg)
    )


# ── Callbacks настроек ────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("lang:"))
async def cb_language(callback: CallbackQuery):
    if not _is_allowed_cb(callback):
        return
    lang = callback.data.split(":")[1]
    us.set_language(callback.from_user.id, lang)
    cfg = us.get(callback.from_user.id)
    await update_user_settings(callback.from_user.id, cfg.language, cfg.voice)
    voice_label = next(
        (v for vid, v in us.VOICE_OPTIONS[cfg.language] if vid == cfg.voice), cfg.voice
    )
    await callback.message.edit_text(
        f"⚙️ *Настройки*\n\n"
        f"🌍 Язык: {us.LANG_LABELS[cfg.language]}\n"
        f"🔊 Голос: {voice_label}",
        parse_mode="Markdown",
        reply_markup=settings_keyboard(callback.from_user.id, cfg)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("voice:"))
async def cb_voice(callback: CallbackQuery):
    if not _is_allowed_cb(callback):
        return
    voice = callback.data.split(":")[1]

    # Проверка доступа к голосу по тарифу
    from database import get_user_plan
    plan_id = await get_user_plan(callback.from_user.id)
    plan = get_plan(plan_id)
    if not plan["all_voices"] and voice not in FREE_VOICES:
        await callback.answer(
            "Этот голос доступен на тарифе ⭐ Базовый и выше. /plans",
            show_alert=True
        )
        return

    us.set_voice(callback.from_user.id, voice)
    cfg = us.get(callback.from_user.id)
    await update_user_settings(callback.from_user.id, cfg.language, cfg.voice)
    voice_label = next(
        (v for vid, v in us.VOICE_OPTIONS[cfg.language] if vid == cfg.voice), cfg.voice
    )
    await callback.message.edit_text(
        f"⚙️ *Настройки*\n\n"
        f"🌍 Язык: {us.LANG_LABELS[cfg.language]}\n"
        f"🔊 Голос: {voice_label}",
        parse_mode="Markdown",
        reply_markup=settings_keyboard(callback.from_user.id, cfg)
    )
    await callback.answer(f"Голос: {voice_label}")


# ── Основной обработчик текста ────────────────────────────────────────────────

@router.message(F.text)
async def handle_text(message: Message):
    if not _is_allowed(message):
        return

    user_id = message.from_user.id
    text = message.text.strip()

    if not rate_limiter.is_allowed(user_id):
        await message.answer("⏳ Слишком много запросов. Подожди немного.")
        return

    if not text:
        await message.answer("Пустое сообщение.")
        return

    if len(text) > MAX_TEXT_LENGTH:
        await message.answer(
            f"⛔ Текст слишком длинный ({len(text):,} символов). Максимум — {MAX_TEXT_LENGTH:,}."
        )
        return

    # Убеждаемся, что пользователь есть в БД
    await get_or_create_user(
        user_id,
        message.from_user.username or "",
        message.from_user.first_name or ""
    )

    # Проверка лимита
    from database import get_user_plan
    plan_id = await get_user_plan(user_id)
    plan = get_plan(plan_id)

    if len(text) > plan["max_per_request"]:
        await message.answer(
            f"⛔ На тарифе {plan['name']} максимум {plan['max_per_request']:,} символов за запрос.\n"
            f"Твой текст: {len(text):,} символов.\n"
            f"💡 Обновите тариф: /plans"
        )
        return

    allowed, err_msg = await check_and_add_chars(user_id, len(text))
    if not allowed:
        await message.answer(err_msg)
        return

    await message.answer("⏳ Обрабатываю...")

    try:
        cfg = us.get(user_id)
        out_text = translate_text(text, cfg.language)
        out_text = clean_text(out_text)
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
            await message.answer(f"✅ Готово! Отправлено {len(chunks)} голосовых.")

    except Exception as e:
        logger.error("Ошибка обработки user=%s: %s", user_id, e)
        await message.answer("❌ Произошла ошибка. Попробуй ещё раз.")
