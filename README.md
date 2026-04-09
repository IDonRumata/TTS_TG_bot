# 🔊 AI Voice Assistant: TTS & Translation Bot
### Профессиональное решение для озвучки контента и монетизации в Telegram

![Python](https://img.shields.io/badge/python-3.11-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![aiogram](https://img.shields.io/badge/aiogram-3.x-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)
![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)
![Payments](https://img.shields.io/badge/Payments-bePaid%20%7C%20Stars-gold?style=for-the-badge)

Это не просто скрипт, а **готовый микро-бизнес**. Бот позволяет автоматизировать создание аудиоконтента, переводить иностранные тексты «на лету» и принимать платежи от пользователей по всему миру.

---

## 🎯 Бизнес-ценность: Зачем это вашему проекту?

| Параметр | Без бота (вручную) | С моим AI-ботом |
| :--- | :--- | :--- |
| **Процесс** | Поиск сервиса -> Копирование -> Скачивание -> Отправка | Отправил текст в TG -> Получил аудио за 3 сек. |
| **Скорость** | ~5-10 минут на один пост | **~5 секунд** в режиме реального времени |
| **Перевод** | Отдельный переводчик -> TTS сервис | **Авто-определение** и перевод внутри бота |
| **Масштаб** | Ограничен вашим временем | Работает **24/7** на неограниченное кол-во юзеров |

**Кому подойдет:** Авторы каналов, онлайн-школы, создатели подкастов и компании с большим объемом текстовых коммуникаций.

---

## 🔥 Ключевые возможности

* **Умная озвучка:** Конвертация текста в высококачественные голосовые сообщения (.ogg).
* **Интеллектуальный перевод:** Автоматическое определение языка (английский -> русский).
* **Готовая монетизация:** * Интеграция с **bePaid** (банковские карты РФ/РБ/Мир).
    * Интеграция с **Telegram Stars** (оплата внутри приложения).
* **Система тарифов:** Гибкая настройка планов (Free / Basic / Pro) с лимитами по количеству запросов.
* **Надежность:** Rate limiting (защита от спама) и логирование всех операций.

---

## 🛠 Технический стек

* **Core:** Python 3.11, aiogram 3.x (Asynchronous)
* **AI & Logic:** gTTS, deep-translator
* **Database:** SQLite (быстрая и надежная)
* **Infrastructure:** Docker, Docker-compose, systemd
* **Billing:** bePaid API, Telegram Stars API

---

## 🚀 Быстрый запуск (Deployment)

Проект полностью контейнеризирован и готов к запуску на любом VPS за 2 минуты:

```bash
git clone [https://github.com/IDonRumata/TTS_TG_bot](https://github.com/IDonRumata/TTS_TG_bot)
cd TTS_TG_bot
cp .env.example .env    # Укажите ваши токены и ключи
docker-compose up -d    # Готово!
