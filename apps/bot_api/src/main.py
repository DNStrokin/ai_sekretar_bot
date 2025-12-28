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
from bot.handlers import router as bot_router
from webapp.api import router as webapp_router
from db.database import init_db


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
    """Application lifespan: startup and shutdown events."""
    # Startup
    logger.info("Starting application...")
    await init_db()
    
    # Start polling in background (для разработки)
    # В production используется webhook
    if settings.USE_POLLING:
        polling_task = asyncio.create_task(dp.start_polling(bot))
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    if settings.USE_POLLING:
        polling_task.cancel()
    await bot.session.close()


# FastAPI app
app = FastAPI(
    title="Личный секретарь API",
    description="API для Telegram-бота и WebApp",
    version="0.1.0",
    lifespan=lifespan
)

# Include WebApp API routes
app.include_router(webapp_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
