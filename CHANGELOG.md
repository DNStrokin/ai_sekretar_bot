# История изменений

Все значимые изменения проекта документируются в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/).
Проект следует [Семантическому версионированию](https://semver.org/lang/ru/).

## [Unreleased]

## [0.1.0] - 2025-12-28

### Добавлено

- Начальная структура проекта на основе технической документации
- **bot-api** — основной сервис (aiogram 3 + FastAPI)
  - Обработчики команд Telegram (`/start`, `/help`, `/settings`)
  - REST API для WebApp (управление темами и настройками)
  - Абстракция AI-провайдеров (OpenAI, Gemini)
  - Интерфейс STT-сервиса
  - Асинхронные модели SQLAlchemy 2.x
  - Настройка миграций Alembic
  - Конфигурация через Pydantic Settings
- **worker** — фоновый сервис (Celery)
  - Задачи транскрипции голосовых сообщений
  - Извлечение метаданных из URL
  - Обработка файлов
- **Инфраструктура**
  - Docker Compose (bot-api, worker, postgres, redis)
  - Конфигурация Nginx reverse proxy
  - Pre-commit хуки (ruff, black, mypy)
- **Документация**
  - README.md с инструкцией по запуску
  - AI_RULES.md — правила для AI-агентов
  - Техническое задание (specification.md)
  - Описание стека (tech_stack.md)
  - Дизайн взаимодействия с LLM (llm_interaction_design.md)

[Unreleased]: https://github.com/username/ai_sekretar_bot/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/username/ai_sekretar_bot/releases/tag/v0.1.0
