# 🤖 Личный секретарь — Telegram Bot

AI-помощник для структурированного хранения заметок в Telegram.

## 📋 Описание

«Личный секретарь» — это Telegram-бот, который выступает в роли персонального AI‑секретаря. Бот понимает смысл полученной информации, классифицирует её по темам и сохраняет в виде структурированных заметок в Telegram-группу.

## 🏗 Архитектура

```
┌─────────────────┐     ┌─────────────────┐
│    bot-api      │────▶│     worker      │
│  (aiogram +     │     │    (Celery)     │
│   FastAPI)      │     │                 │
└────────┬────────┘     └────────┬────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│   PostgreSQL    │     │     Redis       │
│   (метаданные)  │     │ (очереди/кеш)   │
└─────────────────┘     └─────────────────┘
```

## 🚀 Быстрый старт

### 1. Клонирование и настройка

```bash
# Скопировать конфигурацию
cp .env.example .env

# Отредактировать .env - добавить токены
```

### 2. Запуск через Docker Compose

```bash
cd infra
docker-compose up -d
```

### 3. Проверка работы

```bash
# Логи бота
docker-compose logs -f bot-api

# Логи воркера
docker-compose logs -f worker

# Health check
curl http://localhost:8000/health
```

## 📁 Структура проекта

```
ai_sekretar_bot/
├── apps/
│   ├── bot_api/              # Основной сервис
│   │   ├── src/
│   │   │   ├── bot/          # Telegram bot handlers
│   │   │   ├── webapp/       # WebApp API
│   │   │   ├── ai/           # AI провайдеры (OpenAI, Gemini)
│   │   │   ├── stt/          # Speech-to-Text
│   │   │   ├── db/           # База данных
│   │   │   └── settings/     # Конфигурация
│   │   ├── tests/
│   │   └── Dockerfile
│   └── worker/               # Celery worker
│       ├── src/
│       └── Dockerfile
├── infra/
│   └── docker-compose.yml
├── docs/
│   ├── specification.md      # ТЗ
│   ├── tech_stack.md         # Стек технологий
│   └── llm_interaction_design.md
├── .env.example
└── README.md
```

## 💬 Команды бота

### В личных сообщениях
| Команда | Описание |
|---------|----------|
| `/start` | Начать работу с ботом |
| `/help` | Справка |
| `/settings` | Открыть настройки (WebApp) |

### В группе с темами
| Команда | Описание |
|---------|----------|
| `/info` | Настроить тему или показать её статус |

При первом сообщении в новой теме бот автоматически предложит её настроить.

## 🛠 Разработка

### Локальный запуск (без Docker)

```bash
# Создать виртуальное окружение
python -m venv venv
source venv/bin/activate  # или venv\Scripts\activate на Windows

# Установить зависимости
pip install -r apps/bot_api/requirements.txt

# Запустить PostgreSQL и Redis локально

# Запустить бота
cd apps/bot_api
python -m src.main
```

### Запуск тестов

```bash
cd apps/bot_api
pytest tests/ -v
```

### Линтеры

```bash
ruff check .
black --check .
mypy src/
```

## 📖 Документация

- [Техническое задание](docs/specification.md)
- [Стек технологий](docs/tech_stack.md)
- [Взаимодействие с LLM](docs/llm_interaction_design.md)

## 🔧 Конфигурация

| Переменная | Описание | Обязательно |
|------------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Токен бота от @BotFather | ✅ |
| `TELEGRAM_GROUP_ID` | ID группы для заметок | ✅ |
| `OPENAI_API_KEY` | Ключ OpenAI API | ⚡ |
| `GEMINI_API_KEY` | Ключ Google Gemini API | ⚡ |
| `POSTGRES_PASSWORD` | Пароль PostgreSQL | ✅ |

⚡ — требуется хотя бы один AI провайдер

## 📝 Лицензия

MIT
