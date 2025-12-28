"""
Telegram Bot Handlers

Обрабатывает входящие сообщения от пользователя.
"""

import logging
from aiogram import Router, F, Bot
from aiogram.types import (
    Message, CallbackQuery, ChatMemberUpdated,
    InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
)
from aiogram.filters import Command, ChatMemberUpdatedFilter, IS_MEMBER, IS_NOT_MEMBER
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_async_session_maker
from src.db.models import User, Group

logger = logging.getLogger(__name__)

router = Router()


async def get_or_create_user(session: AsyncSession, telegram_user_id: int) -> User:
    """Получить или создать пользователя в БД."""
    result = await session.execute(
        select(User).where(User.telegram_user_id == telegram_user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        user = User(telegram_user_id=telegram_user_id)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        logger.info(f"Создан новый пользователь: {telegram_user_id}")
    
    return user


async def save_group_to_db(
    session: AsyncSession, 
    user_id: int, 
    telegram_group_id: int, 
    title: str,
    is_forum: bool = False
) -> Group:
    """Сохранить группу в БД."""
    # Проверяем, есть ли уже группа для этого пользователя
    result = await session.execute(
        select(Group).where(Group.user_id == user_id)
    )
    group = result.scalar_one_or_none()
    
    if group:
        # Обновляем существующую группу
        group.telegram_group_id = telegram_group_id
        group.title = title
        group.topics_enabled = is_forum
    else:
        # Создаём новую группу
        group = Group(
            telegram_group_id=telegram_group_id,
            title=title,
            topics_enabled=is_forum,
            user_id=user_id
        )
        session.add(group)
    
    await session.commit()
    await session.refresh(group)
    return group


async def get_user_group(session: AsyncSession, telegram_user_id: int) -> Group | None:
    """Получить группу пользователя из БД."""
    result = await session.execute(
        select(Group)
        .join(User)
        .where(User.telegram_user_id == telegram_user_id)
    )
    return result.scalar_one_or_none()


@router.my_chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER))
async def on_bot_added_to_chat(event: ChatMemberUpdated, bot: Bot):
    """
    Обработчик добавления бота в группу/чат.
    Автоматически сохраняет ID группы в базу данных.
    """
    chat = event.chat
    
    # Проверяем, что это группа или супергруппа
    if chat.type not in ("group", "supergroup"):
        return
    
    is_forum = getattr(chat, 'is_forum', False)
    owner_id = event.from_user.id
    
    logger.info(f"Бот добавлен в группу: {chat.title} (ID: {chat.id}, Форум: {is_forum})")
    
    # Сохраняем в БД
    try:
        session_maker = get_async_session_maker()
        async with session_maker() as session:
            # Получаем или создаём пользователя
            user = await get_or_create_user(session, owner_id)
            
            # Сохраняем группу
            group = await save_group_to_db(
                session, 
                user.id, 
                chat.id, 
                chat.title,
                is_forum
            )
            
            logger.info(f"Группа сохранена в БД: {group.telegram_group_id}")
        
        # Отправляем сообщение пользователю
        await bot.send_message(
            owner_id,
            f"✅ <b>Группа подключена и сохранена!</b>\n\n"
            f"📋 <b>Название:</b> {chat.title}\n"
            f"🆔 <b>ID группы:</b> <code>{chat.id}</code>\n"
            f"📁 <b>Темы (форум):</b> {'Да ✓' if is_forum else 'Нет'}\n\n"
            f"{'⚠️ Рекомендуется включить темы в настройках группы!' if not is_forum else '👍 Всё готово к работе!'}"
        )
    except Exception as e:
        logger.error(f"Ошибка при сохранении группы: {e}")
        try:
            await bot.send_message(
                owner_id,
                f"⚠️ Группа обнаружена, но возникла ошибка при сохранении.\n"
                f"ID группы: <code>{chat.id}</code>"
            )
        except:
            pass


@router.message(Command("group_id"))
async def cmd_group_id(message: Message):
    """Показать ID группы пользователя."""
    chat = message.chat
    
    if chat.type == "private":
        # Получаем группу из БД
        session_maker = get_async_session_maker()
        async with session_maker() as session:
            group = await get_user_group(session, message.from_user.id)
            
            if group:
                await message.answer(
                    f"✅ <b>Ваша группа:</b>\n\n"
                    f"📋 <b>Название:</b> {group.title}\n"
                    f"🆔 <b>ID:</b> <code>{group.telegram_group_id}</code>\n"
                    f"📁 <b>Темы:</b> {'Да ✓' if group.topics_enabled else 'Нет'}"
                )
            else:
                await message.answer(
                    "❌ Группа ещё не подключена.\n\n"
                    "Добавьте бота в группу, и я автоматически её сохраню."
                )
    else:
        is_forum = getattr(chat, 'is_forum', False)
        await message.answer(
            f"📋 <b>Информация о чате:</b>\n\n"
            f"🆔 <b>ID:</b> <code>{chat.id}</code>\n"
            f"📁 <b>Тип:</b> {chat.type}\n"
            f"📁 <b>Темы (форум):</b> {'Да ✓' if is_forum else 'Нет'}"
        )


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработка команды /start."""
    # Создаём пользователя в БД при первом старте
    session_maker = get_async_session_maker()
    async with session_maker() as session:
        await get_or_create_user(session, message.from_user.id)
    
    await message.answer(
        "👋 Привет! Я твой личный AI-секретарь.\n\n"
        "Отправь мне любую информацию (текст, голосовое, ссылку или файл), "
        "и я помогу её структурировать и сохранить в нужную тему.\n\n"
        "📌 <b>Первые шаги:</b>\n"
        "1. Добавь меня в группу с темами\n"
        "2. Используй /group_id чтобы проверить подключение\n"
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
        "/group_id - показать подключённую группу\n"
        "/settings - настройки"
    )


@router.message(Command("settings"))
async def cmd_settings(message: Message):
    """Обработка команды /settings — открытие WebApp."""
    # URL WebApp (GitHub Pages)
    # TODO: Заменить на реальный URL после деплоя
    webapp_url = "https://your-username.github.io/ai_sekretar_bot/"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="⚙️ Открыть настройки",
            web_app=WebAppInfo(url=webapp_url)
        )]
    ])
    
    await message.answer(
        "⚙️ <b>Настройки бота</b>\n\n"
        "Нажмите кнопку ниже, чтобы открыть панель настроек.\n"
        "Там вы можете:\n"
        "• Управлять темами группы\n"
        "• Настроить AI-провайдера\n"
        "• Изменить уровень краткости",
        reply_markup=keyboard
    )


@router.message(F.text)
async def handle_text(message: Message):
    """Обработка текстовых сообщений."""
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
    
    await message.answer(
        "🎤 Получил голосовое сообщение. Распознаю...\n\n"
        "<i>(STT будет реализован позже)</i>"
    )


@router.message(F.document | F.photo)
async def handle_file(message: Message):
    """Обработка файлов и изображений."""
    if message.chat.type != "private":
        return
    
    await message.answer(
        "📎 Получил файл. Обрабатываю...\n\n"
        "<i>(Обработка файлов будет реализована позже)</i>"
    )


@router.callback_query()
async def handle_callback(callback: CallbackQuery):
    """Обработка callback-кнопок."""
    await callback.answer("Обработка...")
