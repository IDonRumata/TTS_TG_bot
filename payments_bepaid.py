"""Оплата через bePaid (Беларусь, СНГ)."""

import hashlib
import hmac
import json
import logging
import httpx
from config import BEPAID_SHOP_ID, BEPAID_SECRET_KEY, BEPAID_WEBHOOK_URL, BOT_URL
from plans import PLANS

logger = logging.getLogger(__name__)

BEPAID_API_URL = "https://checkout.bepaid.by/ctp/api/checkouts"


def _sign(data: dict, secret: str) -> str:
    """Подпись для bePaid (не используется — они используют Basic Auth)."""
    return hmac.new(secret.encode(), json.dumps(data).encode(), hashlib.sha256).hexdigest()


async def create_payment_link(
    user_id: int,
    plan_id: str,
    period: str,
    first_name: str = ""
) -> str | None:
    """Создаёт платёжную ссылку bePaid и возвращает URL."""
    plan = PLANS.get(plan_id)
    if not plan:
        return None

    amount = plan[f"price_{period}_byn"]
    period_label = "месяц" if period == "month" else "год"

    payload = {
        "checkout": {
            "test": False,
            "transaction_type": "payment",
            "order": {
                "amount": amount * 100,      # в копейках
                "currency": "BYR",
                "description": f"{plan['name']} TTS-бот — {period_label}",
                "tracking_id": f"tts_{user_id}_{plan_id}_{period}",
            },
            "settings": {
                "success_url": BOT_URL,
                "decline_url": BOT_URL,
                "notification_url": f"{BEPAID_WEBHOOK_URL}/bepaid/webhook",
                "language": "ru",
            },
            "customer": {
                "first_name": first_name or "User",
            }
        }
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                BEPAID_API_URL,
                json=payload,
                auth=(BEPAID_SHOP_ID, BEPAID_SECRET_KEY),
                headers={"Content-Type": "application/json", "Accept": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()
            url = data["checkout"]["redirect_url"]
            logger.info("bePaid ссылка создана: user=%s plan=%s", user_id, plan_id)
            return url
    except Exception as e:
        logger.error("Ошибка создания bePaid-ссылки: %s", e)
        return None


def parse_webhook(body: bytes, auth_header: str) -> dict | None:
    """
    Разбирает и проверяет webhook от bePaid.
    bePaid шлёт HTTP Basic Auth в заголовке Authorization.
    Возвращает dict с данными платежа или None при ошибке.
    """
    import base64
    try:
        # Проверяем Basic Auth
        encoded = auth_header.replace("Basic ", "")
        decoded = base64.b64decode(encoded).decode()
        shop_id, secret = decoded.split(":", 1)
        if shop_id != BEPAID_SHOP_ID or secret != BEPAID_SECRET_KEY:
            logger.warning("bePaid webhook: неверная аутентификация")
            return None
        return json.loads(body)
    except Exception as e:
        logger.error("Ошибка разбора bePaid webhook: %s", e)
        return None


def extract_tracking(tracking_id: str) -> tuple[int, str, str] | None:
    """Разбирает tracking_id: 'tts_{user_id}_{plan}_{period}'."""
    try:
        parts = tracking_id.split("_")
        # tts, user_id, plan, period
        user_id = int(parts[1])
        plan_id = parts[2]
        period = parts[3]
        return user_id, plan_id, period
    except Exception:
        return None
