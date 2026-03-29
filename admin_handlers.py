"""
Админ-команды для управления ботом прямо из Telegram.
Доступны только пользователям из ADMIN_IDS.
"""

import asyncio
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.filters import Command

from config import ADMIN_IDS
from plans import PLANS
from database import (
    admin_grant_plan, admin_revoke_plan,
    admin_ban_user, admin_unban_user,
    admin_get_stats, admin_get_user_info,
    admin_list_users, get_all_user_ids,
    get_or_create_user,
)

logger = logging.getLogger(__name__)
router = Router()

HELP_TEXT = """
🔧 *Админ-команды*

👤 *Пользователи:*
`/grant <id> <план> [дней]` — выдать план бесплатно
  Планы: `basic`, `pro`  |  Дней по умолчанию: 30
`/revoke <id>` — сбросить до бесплатного
`/ban <id>` — забанить пользователя
`/unban <id>` — разбанить
`/lookup <id>` — инфо о пользователе
`/users [страница]` — список пользователей

📊 *Статистика:*
`/stats` — общая статистика бота

📢 *Рассылка:*
`/broadcast <текст>` — отправить всем пользователям
"""


def _is_admin(message: Message) -> bool:
    return message.from_user.id in ADMIN_IDS


# ── Защита ────────────────────────────────────────────────────────────────────

async def _check_admin(message: Message) -> bool:
    if not _is_admin(message):
        logger.warning("Попытка вызова админ-команды: user=%s", message.from_user.id)
        return False
    return True


# ── /adminhelp ────────────────────────────────────────────────────────────────

@router.message(Command("adminhelp"))
async def cmd_adminhelp(message: Message):
    if not await _check_admin(message):
        return
    await message.answer(HELP_TEXT, parse_mode="Markdown")


# ── /grant <user_id> <план> [дней] ───────────────────────────────────────────

@router.message(Command("grant"))
async def cmd_grant(message: Message):
    if not await _check_admin(message):
        return

    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("Использование: `/grant <user_id> <basic|pro> [дней]`", parse_mode="Markdown")
        return

    try:
        user_id = int(parts[1])
        plan_id = parts[2].lower()
        days = int(parts[3]) if len(parts) > 3 else 30
    except ValueError:
        await message.answer("❌ Неверный формат. Пример: `/grant 123456789 basic 30`", parse_mode="Markdown")
        return

    if plan_id not in ("basic", "pro"):
        await message.answer("❌ План должен быть `basic` или `pro`", parse_mode="Markdown")
        return

    await get_or_create_user(user_id)
    await admin_grant_plan(user_id, plan_id, days)
    plan_name = PLANS[plan_id]["name"]

    await message.answer(
        f"✅ Пользователю `{user_id}` выдан план *{plan_name}* на {days} дней.",
        parse_mode="Markdown"
    )

    # Уведомляем пользователя
    try:
        await message.bot.send_message(
            user_id,
            f"🎁 Вам выдан бесплатный доступ к тарифу *{plan_name}* на {days} дней!\n"
            f"Проверь: /status",
            parse_mode="Markdown"
        )
    except Exception:
        await message.answer("⚠️ Не удалось уведомить пользователя (возможно, не запускал бота).")


# ── /revoke <user_id> ─────────────────────────────────────────────────────────

@router.message(Command("revoke"))
async def cmd_revoke(message: Message):
    if not await _check_admin(message):
        return

    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование: `/revoke <user_id>`", parse_mode="Markdown")
        return

    try:
        user_id = int(parts[1])
    except ValueError:
        await message.answer("❌ Неверный user_id")
        return

    await admin_revoke_plan(user_id)
    await message.answer(f"✅ Пользователь `{user_id}` переведён на бесплатный тариф.", parse_mode="Markdown")

    try:
        await message.bot.send_message(
            user_id,
            "ℹ️ Ваш платный тариф был изменён. Текущий тариф: 🆓 Бесплатный.\n"
            "Подключить тариф: /plans"
        )
    except Exception:
        pass


# ── /ban <user_id> ────────────────────────────────────────────────────────────

@router.message(Command("ban"))
async def cmd_ban(message: Message):
    if not await _check_admin(message):
        return

    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование: `/ban <user_id>`", parse_mode="Markdown")
        return

    try:
        user_id = int(parts[1])
    except ValueError:
        await message.answer("❌ Неверный user_id")
        return

    await admin_ban_user(user_id)
    await message.answer(f"🚫 Пользователь `{user_id}` заблокирован.", parse_mode="Markdown")


# ── /unban <user_id> ──────────────────────────────────────────────────────────

@router.message(Command("unban"))
async def cmd_unban(message: Message):
    if not await _check_admin(message):
        return

    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование: `/unban <user_id>`", parse_mode="Markdown")
        return

    try:
        user_id = int(parts[1])
    except ValueError:
        await message.answer("❌ Неверный user_id")
        return

    await admin_unban_user(user_id)
    await message.answer(f"✅ Пользователь `{user_id}` разблокирован.", parse_mode="Markdown")


# ── /lookup <user_id> ─────────────────────────────────────────────────────────

@router.message(Command("lookup"))
async def cmd_lookup(message: Message):
    if not await _check_admin(message):
        return

    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование: `/lookup <user_id>`", parse_mode="Markdown")
        return

    try:
        user_id = int(parts[1])
    except ValueError:
        await message.answer("❌ Неверный user_id")
        return

    info = await admin_get_user_info(user_id)
    if not info:
        await message.answer(f"❌ Пользователь `{user_id}` не найден.", parse_mode="Markdown")
        return

    username = f"@{info['username']}" if info.get("username") else "—"
    subs_text = ""
    for s in info.get("subscriptions", []):
        subs_text += f"\n  • {s['plan']} / {s['status']} до {s.get('expires_at','?')[:10]}"

    await message.answer(
        f"👤 *Пользователь {user_id}*\n\n"
        f"Имя: {info.get('first_name','—')}\n"
        f"Username: {username}\n"
        f"Тариф: {info['plan']}\n"
        f"Язык: {info['language']}\n"
        f"Создан: {info['created_at'][:10]}\n"
        f"Символов сегодня: {info['chars_today']:,}\n"
        f"Символов в месяце: {info['chars_month']:,}\n"
        f"Подписки:{subs_text or ' нет'}",
        parse_mode="Markdown"
    )


# ── /users [страница] ─────────────────────────────────────────────────────────

@router.message(Command("users"))
async def cmd_users(message: Message):
    if not await _check_admin(message):
        return

    parts = message.text.split()
    page = int(parts[1]) - 1 if len(parts) > 1 else 0
    limit = 15
    users = await admin_list_users(limit=limit, offset=page * limit)

    if not users:
        await message.answer("Пользователей не найдено.")
        return

    lines = [f"👥 *Пользователи* (стр. {page + 1})\n"]
    for u in users:
        uname = f"@{u['username']}" if u.get("username") else u.get("first_name", "—")
        lines.append(f"`{u['id']}` {uname} — {u['plan']} ({u['created_at'][:10]})")

    lines.append(f"\nСледующая страница: /users {page + 2}")
    await message.answer("\n".join(lines), parse_mode="Markdown")


# ── /stats ────────────────────────────────────────────────────────────────────

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    if not await _check_admin(message):
        return

    s = await admin_get_stats()
    await message.answer(
        f"📊 *Статистика бота*\n\n"
        f"👥 Всего пользователей: {s['total']}\n"
        f"  🆓 Бесплатных: {s['free']}\n"
        f"  💳 Платных: {s['paid']}\n"
        f"  🚫 Забанено: {s['banned']}\n\n"
        f"🆕 Новых сегодня: {s['new_today']}\n"
        f"💰 Успешных оплат: {s['payments_total']}\n"
        f"📈 Конверсия: {(s['paid'] / s['total'] * 100) if s['total'] else 0:.1f}%",
        parse_mode="Markdown"
    )


# ── /broadcast <текст> ────────────────────────────────────────────────────────

@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message):
    if not await _check_admin(message):
        return

    text = message.text.removeprefix("/broadcast").strip()
    if not text:
        await message.answer("Использование: `/broadcast <текст сообщения>`", parse_mode="Markdown")
        return

    user_ids = await get_all_user_ids()
    await message.answer(f"📢 Рассылка начата. Получателей: {len(user_ids)}...")

    sent = 0
    failed = 0
    for uid in user_ids:
        try:
            await message.bot.send_message(uid, text)
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)   # ~20 сообщений/сек, не превышаем лимит Telegram

    await message.answer(
        f"✅ Рассылка завершена.\n"
        f"Отправлено: {sent}\n"
        f"Ошибок: {failed}"
    )
