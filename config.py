import os
from dotenv import load_dotenv

load_dotenv()

# ── Telegram ──────────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в .env")

allowed_users_str = os.getenv("ALLOWED_USERS", "")
ALLOWED_USERS = [
    int(uid.strip())
    for uid in allowed_users_str.split(",")
    if uid.strip().isdigit()
]

# ── Лимиты ────────────────────────────────────────────────────────────────────
MAX_TEXT_LENGTH = 5_000
CHUNK_SIZE      = 900
RATE_LIMIT      = 10       # запросов в минуту
RATE_WINDOW     = 60

# ── bePaid ────────────────────────────────────────────────────────────────────
BEPAID_SHOP_ID    = os.getenv("BEPAID_SHOP_ID", "")
BEPAID_SECRET_KEY = os.getenv("BEPAID_SECRET_KEY", "")
BEPAID_WEBHOOK_URL = os.getenv("BEPAID_WEBHOOK_URL", "")   # https://your-domain.com

# ── Webhook сервер ────────────────────────────────────────────────────────────
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "8444"))

# ── Бот (ссылка на себя для кнопки "Вернуться") ───────────────────────────────
BOT_URL = os.getenv("BOT_URL", "https://t.me/text_to_voice_for_me_bot")
