"""
Telegram Bot «Личный секретарь» - Main Entry Point

Объединяет aiogram (Telegram Bot) и FastAPI (WebApp API) в единое приложение.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from src.settings.config import settings
from src.bot.handlers import router as bot_router
from src.webapp.api import router as webapp_router
from src.db.database import init_db, get_async_session_maker


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Bot instance
bot = Bot(
    token=settings.TELEGRAM_BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()
dp.include_router(bot_router)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Жизненный цикл приложения: startup и shutdown."""
    # Startup
    logger.info("Запуск приложения...")
    await init_db()
    
    # Запуск polling в фоне (для разработки)
    # В production используется webhook
    if settings.USE_POLLING:
        polling_task = asyncio.create_task(dp.start_polling(bot))
        logger.info("Бот запущен в режиме polling")
    
    yield
    
    # Shutdown
    logger.info("Остановка приложения...")
    if settings.USE_POLLING:
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass
    await bot.session.close()


# FastAPI app
app = FastAPI(
    title="Личный секретарь API",
    description="API для Telegram-бота и WebApp",
    version="0.1.0",
    lifespan=lifespan
)

# CORS для WebApp (если нужен доступ с других доменов)
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Для MVP разрешаем все
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include WebApp API routes
app.include_router(webapp_router, prefix="/api/v1")

# Статические файлы WebApp
import os
from fastapi.staticfiles import StaticFiles

# Путь к static относительно src/main.py
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Редирект с /webapp на /static/webapp/index.html
from fastapi.responses import RedirectResponse

@app.get("/webapp")
async def redirect_to_webapp():
    """Редирект на WebApp."""
    return RedirectResponse(url="/static/webapp/index.html")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

