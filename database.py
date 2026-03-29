"""Асинхронная БД — PostgreSQL через asyncpg."""

import asyncpg
import logging
import os
from datetime import date, datetime, timedelta

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "")
_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    return _pool


async def init_db() -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id              BIGINT PRIMARY KEY,
                username        TEXT,
                first_name      TEXT,
                plan            TEXT        DEFAULT 'free',
                language        TEXT        DEFAULT 'ru',
                voice           TEXT        DEFAULT 'ru-RU-SvetlanaNeural',
                chars_today     INTEGER     DEFAULT 0,
                chars_month     INTEGER     DEFAULT 0,
                reset_date      DATE        DEFAULT CURRENT_DATE,
                reset_month     TEXT        DEFAULT to_char(CURRENT_DATE,'YYYY-MM'),
                created_at      TIMESTAMPTZ DEFAULT NOW(),
                updated_at      TIMESTAMPTZ DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS subscriptions (
                id              SERIAL PRIMARY KEY,
                user_id         BIGINT      NOT NULL REFERENCES users(id),
                plan            TEXT        NOT NULL,
                status          TEXT        DEFAULT 'active',
                provider        TEXT,
                started_at      TIMESTAMPTZ DEFAULT NOW(),
                expires_at      TIMESTAMPTZ,
                amount          NUMERIC(10,2),
                currency        TEXT
            );

            CREATE TABLE IF NOT EXISTS payments (
                id              SERIAL PRIMARY KEY,
                user_id         BIGINT      NOT NULL,
                provider        TEXT,
                provider_id     TEXT,
                amount          NUMERIC(10,2),
                currency        TEXT,
                plan            TEXT,
                period          TEXT,
                status          TEXT        DEFAULT 'pending',
                created_at      TIMESTAMPTZ DEFAULT NOW()
            );
        """)
    logger.info("БД инициализирована (PostgreSQL)")


# ── Пользователи ──────────────────────────────────────────────────────────────

async def get_or_create_user(user_id: int, username: str = "", first_name: str = "") -> dict:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE id=$1", user_id)
        if row:
            return dict(row)
        row = await conn.fetchrow(
            """INSERT INTO users (id, username, first_name)
               VALUES ($1, $2, $3)
               ON CONFLICT (id) DO UPDATE SET
                 username=EXCLUDED.username,
                 first_name=EXCLUDED.first_name,
                 updated_at=NOW()
               RETURNING *""",
            user_id, username, first_name
        )
        return dict(row)


async def update_user_settings(user_id: int, language: str, voice: str) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET language=$1, voice=$2, updated_at=NOW() WHERE id=$3",
            language, voice, user_id
        )


async def get_user_plan(user_id: int) -> str:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT plan FROM users WHERE id=$1", user_id)
        return row["plan"] if row else "free"


# ── Лимиты символов ───────────────────────────────────────────────────────────

async def check_and_add_chars(user_id: int, chars: int) -> tuple[bool, str]:
    from plans import PLANS
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE id=$1", user_id)
        if not row:
            return False, "Пользователь не найден."

        today = date.today()
        this_month = today.strftime("%Y-%m")
        plan = PLANS.get(row["plan"], PLANS["free"])

        chars_today = row["chars_today"] if row["reset_date"] == today else 0
        chars_month = row["chars_month"] if row["reset_month"] == this_month else 0

        if plan["chars_per_day"] and chars_today + chars > plan["chars_per_day"]:
            remaining = max(0, plan["chars_per_day"] - chars_today)
            return False, (
                f"⛔ Дневной лимит: {plan['chars_per_day']:,} символов.\n"
                f"Осталось сегодня: {remaining:,} симв.\n"
                f"💡 Обновите тариф: /plans"
            )

        if plan["chars_per_month"] and chars_month + chars > plan["chars_per_month"]:
            remaining = max(0, plan["chars_per_month"] - chars_month)
            return False, (
                f"⛔ Месячный лимит: {plan['chars_per_month']:,} символов.\n"
                f"Осталось в месяце: {remaining:,} симв.\n"
                f"💡 Обновите тариф: /plans"
            )

        await conn.execute(
            """UPDATE users SET
               chars_today=$1, chars_month=$2,
               reset_date=$3, reset_month=$4,
               updated_at=NOW()
               WHERE id=$5""",
            chars_today + chars, chars_month + chars, today, this_month, user_id
        )
        return True, ""


async def get_user_stats(user_id: int) -> dict:
    from plans import PLANS
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE id=$1", user_id)

    today = date.today()
    this_month = today.strftime("%Y-%m")
    plan = PLANS.get(row["plan"], PLANS["free"])

    chars_today = row["chars_today"] if row["reset_date"] == today else 0
    chars_month = row["chars_month"] if row["reset_month"] == this_month else 0

    return {
        "plan": row["plan"],
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
    expires = datetime.utcnow() + (timedelta(days=365) if period == "year" else timedelta(days=31))
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "UPDATE subscriptions SET status='expired' WHERE user_id=$1 AND status='active'",
                user_id
            )
            await conn.execute(
                """INSERT INTO subscriptions (user_id, plan, status, provider, expires_at, amount, currency)
                   VALUES ($1,$2,'active',$3,$4,$5,$6)""",
                user_id, plan, provider, expires, amount, currency
            )
            await conn.execute(
                """INSERT INTO payments (user_id, provider, provider_id, amount, currency, plan, period, status)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,'successful')""",
                user_id, provider, provider_id, amount, currency, plan, period
            )
            await conn.execute(
                "UPDATE users SET plan=$1, updated_at=NOW() WHERE id=$2",
                plan, user_id
            )
    logger.info("Подписка активирована: user=%s plan=%s период=%s", user_id, plan, period)


async def check_expired_subscriptions() -> list[int]:
    pool = await get_pool()
    expired = []
    async with pool.acquire() as conn:
        async with conn.transaction():
            rows = await conn.fetch(
                "SELECT user_id FROM subscriptions WHERE status='active' AND expires_at < NOW()"
            )
            for row in rows:
                expired.append(row["user_id"])
                await conn.execute(
                    "UPDATE subscriptions SET status='expired' WHERE user_id=$1 AND status='active'",
                    row["user_id"]
                )
                await conn.execute(
                    "UPDATE users SET plan='free', updated_at=NOW() WHERE id=$1",
                    row["user_id"]
                )
    return expired


# ── Админ-функции ─────────────────────────────────────────────────────────────

async def admin_grant_plan(user_id: int, plan: str, days: int) -> None:
    expires = datetime.utcnow() + timedelta(days=days)
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "UPDATE subscriptions SET status='expired' WHERE user_id=$1 AND status='active'",
                user_id
            )
            await conn.execute(
                """INSERT INTO subscriptions (user_id, plan, status, provider, expires_at, amount, currency)
                   VALUES ($1,$2,'active','admin',$3,0,'FREE')""",
                user_id, plan, expires
            )
            await conn.execute(
                "UPDATE users SET plan=$1, updated_at=NOW() WHERE id=$2",
                plan, user_id
            )
    logger.info("Админ выдал план: user=%s plan=%s дней=%s", user_id, plan, days)


async def admin_revoke_plan(user_id: int) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "UPDATE subscriptions SET status='revoked' WHERE user_id=$1 AND status='active'",
                user_id
            )
            await conn.execute(
                "UPDATE users SET plan='free', updated_at=NOW() WHERE id=$1",
                user_id
            )


async def admin_ban_user(user_id: int) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET plan='banned', updated_at=NOW() WHERE id=$1", user_id
        )


async def admin_unban_user(user_id: int) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET plan='free', updated_at=NOW() WHERE id=$1", user_id
        )


async def admin_get_stats() -> dict:
    pool = await get_pool()
    async with pool.acquire() as conn:
        total    = await conn.fetchval("SELECT COUNT(*) FROM users")
        paid     = await conn.fetchval("SELECT COUNT(*) FROM users WHERE plan IN ('basic','pro')")
        banned   = await conn.fetchval("SELECT COUNT(*) FROM users WHERE plan='banned'")
        new_today = await conn.fetchval(
            "SELECT COUNT(*) FROM users WHERE reset_date=CURRENT_DATE"
        )
        payments_total = await conn.fetchval(
            "SELECT COUNT(*) FROM payments WHERE status='successful'"
        )
    return {
        "total": total, "paid": paid,
        "free": total - paid - banned,
        "banned": banned, "new_today": new_today,
        "payments_total": payments_total,
    }


async def admin_get_user_info(user_id: int) -> dict | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE id=$1", user_id)
        if not row:
            return None
        user = dict(row)
        subs = await conn.fetch(
            "SELECT * FROM subscriptions WHERE user_id=$1 ORDER BY started_at DESC LIMIT 3",
            user_id
        )
        user["subscriptions"] = [dict(s) for s in subs]
        return user


async def admin_list_users(limit: int = 20, offset: int = 0) -> list[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, username, first_name, plan, created_at FROM users "
            "ORDER BY created_at DESC LIMIT $1 OFFSET $2",
            limit, offset
        )
        return [dict(r) for r in rows]


async def get_all_user_ids() -> list[int]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT id FROM users WHERE plan != 'banned'")
        return [r["id"] for r in rows]
