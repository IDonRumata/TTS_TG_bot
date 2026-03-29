import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Токен бота не найден! Проверьте файл .env")

# Whitelist пользователей
allowed_users_str = os.getenv("ALLOWED_USERS", "")
ALLOWED_USERS = [
    int(uid.strip())
    for uid in allowed_users_str.split(",")
    if uid.strip().isdigit()
]

# Лимиты
MAX_TEXT_LENGTH = 5000          # макс символов на сообщение
CHUNK_SIZE = 900                # символов на один аудио-фрагмент
RATE_LIMIT = 5                  # запросов в минуту на пользователя
RATE_WINDOW = 60                # окно rate-limit в секундах
