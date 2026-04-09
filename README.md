# 🔊 AI Voice Assistant: TTS & Stars Monetization
### Профессиональное решение для озвучки контента и продажи доступа в Telegram

![Python](https://img.shields.io/badge/python-3.11-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![aiogram](https://img.shields.io/badge/aiogram-3.x-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)
![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)
![Payments](https://img.shields.io/badge/Payments-Telegram%20Stars-blue?style=for-the-badge&logo=telegram)

Это готовое решение для автоматизации создания аудиоконтента. Бот позволяет переводить текст в голосовые сообщения, управлять лимитами пользователей и принимать оплату через внутреннюю валюту Telegram Stars.

---

## 🎯 Бизнес-ценность: Зачем это вашему проекту?

Инструмент идеально подходит для авторов каналов, онлайн-школ и блогеров, которым нужно быстро и бюджетно переводить текстовый контент в аудио-формат.

| Параметр | Без бота (вручную) | С моим ассистентом |
| :--- | :--- | :--- |
| **Процесс** | Поиск сервиса -> Скачивание -> Отправка | Отправил текст -> Получил аудио за 3 сек. |
| **Экономия времени** | ~5-10 минут на один пост | **~5 секунд** на весь процесс |
| **Монетизация** | Прием оплат вручную в ЛС | **Автоматическая** продажа планов через Stars |
| **Масштаб** | Ограничен вашим временем | Работает **24/7** на любом потоке юзеров |

---

## 🔥 Ключевые возможности

* **Умная озвучка:** Конвертация текста в качественные голосовые сообщения (.ogg). Поддержка RU/EN с удобным переключением в меню.
* **Монетизация (Stars):** Встроенная система оплаты через **Telegram Stars**. Пользователи могут мгновенно покупать тарифы внутри приложения.
* **Гибкие тарифы:** Настройка планов (Free / Basic / Pro) с лимитами по количеству запросов и символов.
* **Безопасность и контроль:** Система Rate limiting (защита от спама) и детальное логирование всех транзакций в SQLite.
* **Production-ready:** Готовый Docker-образ для развертывания на VPS за считанные минуты.

---

## 🛠 Технический стек

* **Core:** Python 3.11, aiogram 3.x (Asynchronous)
* **Audio Engine:** gTTS (Google Text-to-Speech)
* **Database:** SQLite
* **Infrastructure:** Docker, Docker-compose, systemd
* **Billing:** Telegram Stars API

---

## 🚀 Быстрый запуск (Deployment)

```bash
git clone [https://github.com/IDonRumata/TTS_TG_bot](https://github.com/IDonRumata/TTS_TG_bot)
cd TTS_TG_bot
cp .env.example .env    # Заполните токен бота и лимиты
docker-compose up -d    # Запуск в фоновом режиме
