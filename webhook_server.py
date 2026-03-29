"""
FastAPI-сервер для приёма webhook-уведомлений от bePaid.
Запускается параллельно с ботом в одном процессе.
"""

import logging
import uvicorn
from fastapi import FastAPI, Request, Response, HTTPException
from database import activate_subscription
from payments_bepaid import parse_webhook, extract_tracking
from plans import PLANS

logger = logging.getLogger(__name__)
app = FastAPI(docs_url=None, redoc_url=None)  # отключаем UI в продакшене

_bot = None  # Устанавливается из bot.py


def set_bot(bot):
    global _bot
    _bot = bot


@app.post("/bepaid/webhook")
async def bepaid_webhook(request: Request):
    body = await request.body()
    auth = request.headers.get("Authorization", "")

    data = parse_webhook(body, auth)
    if data is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        transaction = data.get("transaction", {})
        status = transaction.get("status")
        tracking_id = transaction.get("tracking_id", "")
        uid = transaction.get("uid", "")
        amount = transaction.get("amount", 0) / 100
        currency = transaction.get("currency", "BYR")

        logger.info("bePaid webhook: status=%s tracking=%s", status, tracking_id)

        if status == "successful":
            parsed = extract_tracking(tracking_id)
            if not parsed:
                logger.error("Не удалось разобрать tracking_id: %s", tracking_id)
                return Response(status_code=200)

            user_id, plan_id, period = parsed
            plan = PLANS.get(plan_id)
            if not plan:
                logger.error("Неизвестный план: %s", plan_id)
                return Response(status_code=200)

            await activate_subscription(
                user_id=user_id,
                plan=plan_id,
                period=period,
                provider="bepaid",
                provider_id=uid,
                amount=amount,
                currency=currency
            )

            # Уведомляем пользователя в Telegram
            if _bot:
                period_label = "месяц" if period == "month" else "год"
                try:
                    await _bot.send_message(
                        user_id,
                        f"✅ Оплата через bePaid прошла!\n"
                        f"Тариф **{plan['name']}** активирован на {period_label}.\n"
                        f"Лимит: {plan['chars_per_month']:,} символов/мес.\n\n"
                        f"Проверь командой /status",
                        parse_mode="Markdown"
                    )
                except Exception as e:
                    logger.error("Не удалось отправить уведомление user=%s: %s", user_id, e)

        return Response(status_code=200)

    except Exception as e:
        logger.error("Ошибка обработки bePaid webhook: %s", e)
        return Response(status_code=200)  # всегда возвращаем 200, иначе bePaid будет повторять


@app.get("/health")
async def health():
    return {"status": "ok"}


async def start_webhook_server(host: str = "0.0.0.0", port: int = 8444):
    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    await server.serve()
