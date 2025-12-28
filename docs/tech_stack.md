# Стек разработки
## Проект: Telegram-бот «Личный секретарь»

---

## 1. Цели выбора стека

Стек должен обеспечивать:
- модульность (возможность развивать проект по компонентам);
- масштабируемость (переход от MVP к многопользовательскому продукту);
- надёжность (очереди задач, ретраи, наблюдаемость);
- экономичную эксплуатацию;
- простое развёртывание и обновление через **docker-compose**.

---

## 2. Общая архитектура (сервисная, но лёгкая)

Проект строится как набор сервисов, разворачиваемых через docker-compose:

1) **bot-api** — единый backend, который:
   - принимает Telegram updates (webhook)
   - обслуживает WebApp API
   - управляет логикой сценариев
   - формирует запросы к LLM/STT

2) **worker** — фоновые задачи:
   - STT
   - HTTP fetch заголовков/description
   - обработка файлов (в будущем)
   - ретраи при сбоях

3) **postgres** — хранение метаданных (пользователь/группа/темы/настройки/pending)

4) **redis** — брокер задач и кеш:
   - очередь задач (Celery)
   - быстрый кеш тем/настроек
   - rate limit

5) **nginx** (опционально, рекомендовано для webhook/WebApp)
   - TLS termination (в проде)
   - проксирование на bot-api

6) **observability** (опционально)
   - Prometheus + Grafana
   - Loki (логи)

---

## 3. Язык и фреймворки

### 3.1 Backend язык: Python 3.12+
Причины:
- зрелая экосистема для Telegram-ботов;
- сильная поддержка AI-интеграций;
- удобный стек очередей, БД, мониторинга;
- быстрый time-to-market.

### 3.2 Telegram Bot Framework: aiogram 3
- современный async
- хорошая типизация
- поддержка webhook

### 3.3 Web API: FastAPI
- быстрый async REST
- удобная документация OpenAPI
- хорошая совместимость с WebApp

Рекомендация: держать aiogram и FastAPI в одном приложении (один контейнер `bot-api`).

---

## 4. Очереди и фоновые задачи

### Celery + Redis
- стандартный “боевой” вариант
- ретраи, backoff, dead-letter подход (через отдельную очередь)

Функции worker:
- STT-транскрипция
- обработка ссылок
- тяжёлые операции по файлам

---

## 5. База данных

### PostgreSQL 16+
Хранится:
- пользователь
- группа
- темы
- описания
- форматирование
- настройки
- pending confirmations (TTL)

### ORM: SQLAlchemy 2.x + Alembic
- миграции схемы
- строгая типизация

---

## 6. Интеграции AI

### 6.1 LLM провайдеры
- OpenAI API
- Google Gemini API

### 6.2 Абстракция “AI Provider”
Должна быть единая внутренняя прослойка (модуль), например:
- `providers/openai_provider.py`
- `providers/gemini_provider.py`

Единый интерфейс:
- `classify_note(context) -> ClassificationResult`
- `render_note(context) -> RenderedNote`
- `transcribe_voice(audio) -> text` (если STT через провайдера)

---

## 7. STT (распознавание речи)

Варианты (выбирается конфигом):
- OpenAI Speech-to-Text (если используется OpenAI)
- Google Speech / Gemini STT (если используется Google)

Рекомендация:
- иметь независимый модуль `stt_service` с единым интерфейсом

---

## 8. Конфигурация и секреты

### 8.1 Настройки через env
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_GROUP_ID`
- `OPENAI_API_KEY`
- `GEMINI_API_KEY`
- `DATABASE_URL`
- `REDIS_URL`

### 8.2 Управление конфигом
- Pydantic Settings (pydantic-settings)

---

## 9. Наблюдаемость (observability)

### 9.1 Логи
- структурированные JSON-логи (loguru или std logging + structlog)
- корреляция по `request_id`

### 9.2 Метрики
- Prometheus
- экспортер FastAPI

### 9.3 Трейсинг (опционально)
- OpenTelemetry

---

## 10. Тестирование и качество

### 10.1 Unit / integration tests
- pytest
- pytest-asyncio

### 10.2 Linters/formatters
- ruff
- black
- mypy

### 10.3 Pre-commit
- pre-commit hooks

---

## 11. Структура репозитория (рекомендация)

```
repo/
  apps/
    bot_api/
      src/
        main.py
        bot/
        webapp/
        ai/
        stt/
        db/
        settings/
      tests/
      Dockerfile
    worker/
      src/
        worker.py
      Dockerfile
  infra/
    docker-compose.yml
    nginx/
      nginx.conf
  docs/
    ...
  .env.example
  README.md
```

Принцип:
- модульность по доменам (bot/webapp/ai/stt/db)
- явное разделение между runtime (apps) и инфраструктурой (infra)

---

## 12. Docker и docker-compose (обязательное требование)

### 12.1 Сервисы compose
- `bot-api`
- `worker`
- `postgres`
- `redis`
- `nginx` (опционально)
- `prometheus/grafana` (опционально)

### 12.2 Сети и тома
- отдельная сеть `app-net`
- volume для postgres данных
- (опционально) volume для логов

### 12.3 Миграции
- при старте `bot-api` выполнять `alembic upgrade head`

---

## 13. Масштабирование (как стек поддерживает рост)

### 13.1 Горизонтальное масштабирование
- `bot-api` масштабируется по репликам (если webhook и stateless)
- worker масштабируется по количеству процессов/контейнеров

### 13.2 Кеширование
- Redis кеш:
  - список тем
  - настройки
  - промежуточные результаты

### 13.3 Переход к multi-tenant
- таблицы уже проектируются с внешним ключом на пользователя/группу
- добавление биллинга поверх существующей схемы

---

## 14. Почему этот стек “передовой” для данного проекта

- Async Python + FastAPI + aiogram 3 — оптимально под Telegram и webhooks
- Postgres + Alembic — надёжное хранение метаданных
- Redis + Celery — готовая инфраструктура фоновых задач
- docker-compose — простой прод-деплой и переносимость
- Модульная структура — легко добавлять интеграции (Notion/Calendar) и монетизацию

---

## 15. Рекомендуемые версии (фиксировать в проекте)

- Python: 3.12+
- PostgreSQL: 16+
- Redis: 7+
- FastAPI: актуальная стабильная
- aiogram: v3.x
- SQLAlchemy: 2.x
- Celery: 5.x

---

## 16. Минимальный набор для MVP

В MVP обязательно:
- bot-api (aiogram + FastAPI)
- worker (Celery)
- postgres
- redis
- docker-compose

Остальное (nginx/observability) — подключаем в проде или на следующем этапе.

