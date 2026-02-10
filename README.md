# Lesson Schedule Bot

Телеграм-бот на базе **aiogram** для записи на занятия:

- админ создаёт свободные временные слоты;
- пользователи записываются, смотрят свои занятия и могут отменять их.

## Основное

- Язык: Python
- Фреймворк: aiogram
- База: PostgreSQL (через SQLAlchemy)

## Установка

```bash
git clone <url-репозитория>
cd lesson_shedule_bot_aiogram
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

Создайте файл `.env` в корне проекта:

```env
TOKEN=ваш_telegram_bot_token
ADMIN_ID=123456789
POSTGRES_USER=postgres
POSTGRES_PASSWORD=пароль
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=lesson_schedule
```

## Запуск

```bash
cd app
python main.py
```

После запуска бот начнёт опрос Telegram и будет готов к работе.

## Деплой

Бот успешно поднимался и работал на платформе Railway (PostgreSQL и бот размещены там же).
