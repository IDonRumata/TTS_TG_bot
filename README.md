# TTS Telegram Bot

Telegram-бот для озвучивания текста голосовыми сообщениями.

- Принимает текст → озвучивает через gTTS
- Английский текст автоматически переводится на русский
- Длинные тексты разбиваются на части
- Доступ только по whitelist (ID пользователей)
- Rate limiting (5 запросов/мин)

## Установка

```bash
git clone <repo_url>
cd TTS_TG_bot
python -m venv .venv
source .venv/bin/activate   # Linux
pip install -r requirements.txt
cp .env.example .env        # заполнить токен и ID
python bot.py
```

## Деплой на VPS (systemd)

```bash
sudo cp tts_bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable tts_bot
sudo systemctl start tts_bot
```

## Структура

| Файл | Назначение |
|------|-----------|
| `bot.py` | Точка входа, запуск polling |
| `handlers.py` | Обработка команд и сообщений |
| `tts.py` | Озвучивание текста (gTTS → .ogg) |
| `translate.py` | Определение языка и перевод |
| `utils.py` | Разбиение текста, rate limiter |
| `config.py` | Загрузка настроек из .env |
