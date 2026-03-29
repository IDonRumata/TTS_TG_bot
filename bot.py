import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN, WEBHOOK_PORT
from handlers import router as main_router
from payments_stars import router as stars_router
from database import init_db, check_expired_subscriptions
from webhook_server import start_webhook_server, set_bot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


async def expiry_checker(bot: Bot):
    """Каждые 6 часов проверяет истёкшие подписки и уведомляет пользователей."""
    while True:
        await asyncio.sleep(6 * 3600)
        try:
            expired = await check_expired_subscriptions()
            for user_id in expired:
                try:
                    await bot.send_message(
                        user_id,
                        "⚠️ Ваша подписка истекла. Вы переведены на бесплатный тариф.\n"
                        "Продлить: /plans"
                    )
                except Exception:
                    pass
            if expired:
                logger.info("Истёкшие подписки: %s пользователей", len(expired))
        except Exception as e:
            logger.error("Ошибка проверки подписок: %s", e)


async def main():
    logger.info("Инициализация БД...")
    await init_db()

    bot = Bot(token=BOT_TOKEN)
    set_bot(bot)

    dp = Dispatcher()
    dp.include_router(stars_router)
    dp.include_router(main_router)

    logger.info("Запуск бота и webhook-сервера...")
    await asyncio.gather(
        dp.start_polling(bot),
        start_webhook_server(port=WEBHOOK_PORT),
        expiry_checker(bot),
    )


if __name__ == "__main__":
    asyncio.run(main())
