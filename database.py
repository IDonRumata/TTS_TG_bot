"""Асинхронная БД (SQLite через aiosqlite)."""

import aiosqlite
import logging
from datetime import date, datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)
DB_PATH = Path("data/tts_bot.db")


async def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id              INTEGER PRIMARY KEY,
                username        TEXT,
                first_name      TEXT,
                plan            TEXT    DEFAULT 'free',
                language        TEXT    DEFAULT 'ru',
                voice           TEXT    DEFAULT 'ru-RU-SvetlanaNeural',
                chars_today     INTEGER DEFAULT 0,
                chars_month     INTEGER DEFAULT 0,
                reset_date      TEXT    DEFAULT '',
                reset_month     TEXT    DEFAULT '',
                created_at      TEXT    DEFAULT (datetime('now')),
                updated_at      TEXT    DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS subscriptions (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL,
                plan            TEXT    NOT NULL,
                status          TEXT    DEFAULT 'active',
                provider        TEXT,
                started_at      TEXT    DEFAULT (datetime('now')),
                expires_at      TEXT,
                amount          REAL,
                currency        TEXT
            );

            CREATE TABLE IF NOT EXISTS payments (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL,
                provider        TEXT,
                provider_id     TEXT,
                amount          REAL,
                currency        TEXT,
                plan            TEXT,
                period          TEXT,
                status          TEXT    DEFAULT 'pending',
                created_at      TEXT    DEFAULT (datetime('now'))
            );
        """)
        await db.commit()
    logger.info("БД инициализирована: %s", DB_PATH)


# ── Пользователи ─────────────────────────────────────────────────────────────

async def get_or_create_user(user_id: int, username: str = "", first_name: str = "") -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = await cur.fetchone()
        if row:
            return dict(row)
        today = str(date.today())
        await db.execute(
            """INSERT INTO users (id, username, first_name, reset_date, reset_month)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, username, first_name, today, today[:7])
        )
        await db.commit()
        cur = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        return dict(await cur.fetchone())


async def update_user_settings(user_id: int, language: str, voice: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET language=?, voice=?, updated_at=datetime('now') WHERE id=?",
            (language, voice, user_id)
        )
        await db.commit()


async def get_user_plan(user_id: int) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT plan FROM users WHERE id=?", (user_id,))
        row = await cur.fetchone()
        return row[0] if row else "free"


# ── Лимиты символов ───────────────────────────────────────────────────────────

async def check_and_add_chars(user_id: int, chars: int) -> tuple[bool, str]:
    """
    Проверяет и добавляет символы пользователю.
    Возвращает (разрешено: bool, сообщение об ошибке: str).
    """
    from plans import PLANS
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE id=?", (user_id,))
        user = dict(await cur.fetchone())

        today = str(date.today())
        this_month = today[:7]
        plan = PLANS.get(user["plan"], PLANS["free"])

        # Сброс дневного счётчика
        chars_today = user["chars_today"] if user["reset_date"] == today else 0
        # Сброс месячного счётчика
        chars_month = user["chars_month"] if user["reset_month"] == this_month else 0

        # Проверка дневного лимита
        if plan["chars_per_day"] and chars_today + chars > plan["chars_per_day"]:
            remaining = plan["chars_per_day"] - chars_today
            return False, (
                f"⛔ Дневной лимит: {plan['chars_per_day']:,} символов.\n"
                f"Осталось сегодня: {max(0, remaining):,} симв.\n"
                f"💡 Обновите тариф командой /plans"
            )

        # Проверка месячного лимита
        if plan["chars_per_month"] and chars_month + chars > plan["chars_per_month"]:
            remaining = plan["chars_per_month"] - chars_month
            return False, (
                f"⛔ Месячный лимит: {plan['chars_per_month']:,} символов.\n"
                f"Осталось в этом месяце: {max(0, remaining):,} симв.\n"
                f"💡 Обновите тариф командой /plans"
            )

        # Записываем
        await db.execute(
            """UPDATE users SET
               chars_today=?, chars_month=?,
               reset_date=?, reset_month=?,
               updated_at=datetime('now')
               WHERE id=?""",
            (chars_today + chars, chars_month + chars, today, this_month, user_id)
        )
        await db.commit()
        return True, ""


async def get_user_stats(user_id: int) -> dict:
    """Возвращает статистику использования."""
    from plans import PLANS
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE id=?", (user_id,))
        user = dict(await cur.fetchone())

    today = str(date.today())
    this_month = today[:7]
    plan = PLANS.get(user["plan"], PLANS["free"])

    chars_today = user["chars_today"] if user["reset_date"] == today else 0
    chars_month = user["chars_month"] if user["reset_month"] == this_month else 0

    return {
        "plan": user["plan"],
        "plan_name": plan["name"],
        "chars_today": chars_today,
        "chars_month": chars_month,
        "limit_day": plan["chars_per_day"],
        "limit_month": plan["chars_per_month"],
    }


# ── Подписки ──────────────────────────────────────────────────────────────────

async def activate_subscription(
    user_id: int, plan: str, period: str,
    provider: str, provider_id: str,
    amount: float, currency: str
) -> None:
    """Активирует подписку пользователя."""
    if period == "year":
        expires = datetime.utcnow() + timedelta(days=365)
    else:
        expires = datetime.utcnow() + timedelta(days=31)

    async with aiosqlite.connect(DB_PATH) as db:
        # Деактивируем старую подписку
        await db.execute(
            "UPDATE subscriptions SET status='expired' WHERE user_id=? AND status='active'",
            (user_id,)
        )
        # Добавляем новую
        await db.execute(
            """INSERT INTO subscriptions
               (user_id, plan, status, provider, expires_at, amount, currency)
               VALUES (?, ?, 'active', ?, ?, ?, ?)""",
            (user_id, plan, provider, expires.isoformat(), amount, currency)
        )
        # Записываем платёж
        await db.execute(
            """INSERT INTO payments
               (user_id, provider, provider_id, amount, currency, plan, period, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'successful')""",
            (user_id, provider, provider_id, amount, currency, plan, period)
        )
        # Обновляем план пользователя
        await db.execute(
            "UPDATE users SET plan=?, updated_at=datetime('now') WHERE id=?",
            (plan, user_id)
        )
        await db.commit()
    logger.info("Подписка активирована: user=%s plan=%s период=%s", user_id, plan, period)


async def check_expired_subscriptions() -> list[int]:
    """Ищет истёкшие подписки, возвращает список user_id."""
    now = datetime.utcnow().isoformat()
    expired_users = []
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT user_id FROM subscriptions WHERE status='active' AND expires_at < ?",
            (now,)
        )
        rows = await cur.fetchall()
        for row in rows:
            expired_users.append(row[0])
            await db.execute(
                "UPDATE subscriptions SET status='expired' WHERE user_id=? AND status='active'",
                (row[0],)
            )
            await db.execute(
                "UPDATE users SET plan='free', updated_at=datetime('now') WHERE id=?",
                (row[0],)
            )
        await db.commit()
    return expired_users
