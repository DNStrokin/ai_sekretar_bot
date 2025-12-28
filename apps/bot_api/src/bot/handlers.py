"""
Telegram Bot Handlers

Обрабатывает входящие сообщения от пользователя.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Handle /start command."""
    await message.answer(
        "👋 Привет! Я твой личный AI-секретарь.\n\n"
        "Отправь мне любую информацию (текст, голосовое, ссылку или файл), "
        "и я помогу её структурировать и сохранить в нужную тему."
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command."""
    await message.answer(
        "📚 <b>Как пользоваться ботом:</b>\n\n"
        "1. Отправь мне информацию в любом формате\n"
        "2. Я предложу тему для сохранения\n"
        "3. Подтверди или выбери другую тему\n"
        "4. Я сохраню структурированную заметку в группу\n\n"
        "<b>Команды:</b>\n"
        "/start - начать работу\n"
        "/help - справка\n"
        "/settings - настройки"
    )


@router.message(Command("settings"))
async def cmd_settings(message: Message):
    """Handle /settings command."""
    await message.answer(
        "⚙️ Настройки доступны через WebApp.\n"
        "Нажми на кнопку меню бота."
    )


@router.message(F.text)
async def handle_text(message: Message):
    """Handle text messages."""
    # TODO: Implement text processing pipeline
    await message.answer(
        "📝 Получил твоё сообщение. Обрабатываю...\n\n"
        "<i>(Полная логика будет реализована позже)</i>"
    )


@router.message(F.voice)
async def handle_voice(message: Message):
    """Handle voice messages."""
    # TODO: Implement STT and processing
    await message.answer(
        "🎤 Получил голосовое сообщение. Распознаю...\n\n"
        "<i>(STT будет реализован позже)</i>"
    )


@router.message(F.document | F.photo)
async def handle_file(message: Message):
    """Handle files and photos."""
    # TODO: Implement file processing
    await message.answer(
        "📎 Получил файл. Обрабатываю...\n\n"
        "<i>(Обработка файлов будет реализована позже)</i>"
    )


@router.callback_query()
async def handle_callback(callback: CallbackQuery):
    """Handle callback queries from inline keyboards."""
    # TODO: Implement callback handling for topic confirmation
    await callback.answer("Обработка...")
