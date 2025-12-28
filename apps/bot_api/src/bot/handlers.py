"""
Telegram Bot Handlers

Обрабатывает входящие сообщения от пользователя.
"""

import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ChatMemberUpdated
from aiogram.filters import Command, ChatMemberUpdatedFilter, IS_MEMBER, IS_NOT_MEMBER

logger = logging.getLogger(__name__)

router = Router()

# Временное хранилище ID группы (позже перенесём в БД)
_detected_group_id: int | None = None


def get_detected_group_id() -> int | None:
    """Получить автоопределённый ID группы."""
    return _detected_group_id


@router.my_chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER))
async def on_bot_added_to_chat(event: ChatMemberUpdated, bot: Bot):
    """
    Обработчик добавления бота в группу/чат.
    Автоматически сохраняет ID группы.
    """
    global _detected_group_id
    
    chat = event.chat
    
    # Проверяем, что это группа или супергруппа
    if chat.type in ("group", "supergroup"):
        _detected_group_id = chat.id
        
        # Проверяем, включены ли темы (форумы)
        is_forum = getattr(chat, 'is_forum', False)
        
        logger.info(f"Бот добавлен в группу: {chat.title} (ID: {chat.id}, Форум: {is_forum})")
        
        # Отправляем сообщение владельцу бота
        owner_id = event.from_user.id
        try:
            await bot.send_message(
                owner_id,
                f"✅ <b>Группа подключена!</b>\n\n"
                f"📋 <b>Название:</b> {chat.title}\n"
                f"🆔 <b>ID группы:</b> <code>{chat.id}</code>\n"
                f"📁 <b>Темы (форум):</b> {'Да ✓' if is_forum else 'Нет'}\n\n"
                f"{'⚠️ Рекомендуется включить темы в настройках группы!' if not is_forum else '👍 Всё готово к работе!'}\n\n"
                f"💡 <i>Добавьте этот ID в .env:</i>\n"
                f"<code>TELEGRAM_GROUP_ID={chat.id}</code>"
            )
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение пользователю: {e}")


@router.message(Command("group_id"))
async def cmd_group_id(message: Message):
    """Показать ID текущего чата."""
    chat = message.chat
    
    if chat.type == "private":
        if _detected_group_id:
            await message.answer(
                f"🆔 <b>Сохранённый ID группы:</b>\n"
                f"<code>{_detected_group_id}</code>\n\n"
                f"Добавьте его в .env:\n"
                f"<code>TELEGRAM_GROUP_ID={_detected_group_id}</code>"
            )
        else:
            await message.answer(
                "❌ Группа ещё не подключена.\n\n"
                "Добавьте бота в группу, и я автоматически определю её ID."
            )
    else:
        is_forum = getattr(chat, 'is_forum', False)
        await message.answer(
            f"📋 <b>Информация о чате:</b>\n\n"
            f"🆔 <b>ID:</b> <code>{chat.id}</code>\n"
            f"📁 <b>Тип:</b> {chat.type}\n"
            f"📁 <b>Темы (форум):</b> {'Да ✓' if is_forum else 'Нет'}\n\n"
            f"Добавьте в .env:\n"
            f"<code>TELEGRAM_GROUP_ID={chat.id}</code>"
        )


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработка команды /start."""
    await message.answer(
        "👋 Привет! Я твой личный AI-секретарь.\n\n"
        "Отправь мне любую информацию (текст, голосовое, ссылку или файл), "
        "и я помогу её структурировать и сохранить в нужную тему.\n\n"
        "📌 <b>Первые шаги:</b>\n"
        "1. Добавь меня в группу с темами\n"
        "2. Используй /group_id чтобы узнать ID группы\n"
        "3. Отправляй мне информацию для сохранения"
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработка команды /help."""
    await message.answer(
        "📚 <b>Как пользоваться ботом:</b>\n\n"
        "1. Отправь мне информацию в любом формате\n"
        "2. Я предложу тему для сохранения\n"
        "3. Подтверди или выбери другую тему\n"
        "4. Я сохраню структурированную заметку в группу\n\n"
        "<b>Команды:</b>\n"
        "/start - начать работу\n"
        "/help - справка\n"
        "/group_id - показать ID группы\n"
        "/settings - настройки"
    )


@router.message(Command("settings"))
async def cmd_settings(message: Message):
    """Обработка команды /settings."""
    await message.answer(
        "⚙️ Настройки доступны через WebApp.\n"
        "Нажми на кнопку меню бота."
    )


@router.message(F.text)
async def handle_text(message: Message):
    """Обработка текстовых сообщений."""
    # Игнорируем сообщения в группах (бот работает в ЛС)
    if message.chat.type != "private":
        return
    
    # TODO: Implement text processing pipeline
    await message.answer(
        "📝 Получил твоё сообщение. Обрабатываю...\n\n"
        "<i>(Полная логика будет реализована позже)</i>"
    )


@router.message(F.voice)
async def handle_voice(message: Message):
    """Обработка голосовых сообщений."""
    if message.chat.type != "private":
        return
    
    # TODO: Implement STT and processing
    await message.answer(
        "🎤 Получил голосовое сообщение. Распознаю...\n\n"
        "<i>(STT будет реализован позже)</i>"
    )


@router.message(F.document | F.photo)
async def handle_file(message: Message):
    """Обработка файлов и изображений."""
    if message.chat.type != "private":
        return
    
    # TODO: Implement file processing
    await message.answer(
        "📎 Получил файл. Обрабатываю...\n\n"
        "<i>(Обработка файлов будет реализована позже)</i>"
    )


@router.callback_query()
async def handle_callback(callback: CallbackQuery):
    """Обработка callback-кнопок."""
    # TODO: Implement callback handling for topic confirmation
    await callback.answer("Обработка...")
