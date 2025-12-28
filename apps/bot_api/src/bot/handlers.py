"""
Telegram Bot Handlers

Обрабатывает входящие сообщения от пользователя.
"""

import os
import logging
from aiogram import Router, F, Bot
from aiogram.types import (
    Message, CallbackQuery, ChatMemberUpdated,
    InlineKeyboardButton, InlineKeyboardMarkup
)
from aiogram.filters import Command, ChatMemberUpdatedFilter, IS_MEMBER, IS_NOT_MEMBER

from src.db.database import get_async_session_maker
from src.services import db_service
from src.bot.keyboards import get_settings_keyboard, get_bind_topic_keyboard

logger = logging.getLogger(__name__)

router = Router()


# ============ DEBUG: Логирование всех сообщений ============

@router.message()
async def debug_log_all_messages(message: Message):
    """Отладочный обработчик — логирует ВСЕ входящие сообщения."""
    chat_type = message.chat.type
    chat_id = message.chat.id
    thread_id = message.message_thread_id
    user_id = message.from_user.id if message.from_user else None
    text = (message.text or "")[:50]
    
    logger.info(f"[DEBUG] Сообщение: chat_type={chat_type}, chat_id={chat_id}, thread={thread_id}, user={user_id}, text='{text}'")
    
    # Если это группа — обрабатываем захват тем
    if chat_type in ("group", "supergroup"):
        await _process_group_message(message)


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
            user = await db_service.get_or_create_user(session, owner_id)
            
            # Сохраняем группу
            group = await db_service.get_or_create_group(
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
            group = await db_service.get_user_group(session, message.from_user.id)
            
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
        await db_service.get_or_create_user(session, message.from_user.id)
    
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
    # URL WebApp (относительный путь на том же сервере)
    # В production это будет https://your-app.timeweb.cloud/webapp
    webapp_url = os.getenv("WEBAPP_URL", "https://your-app.timeweb.cloud/webapp")
    
    await message.answer(
        "⚙️ <b>Настройки бота</b>\n\n"
        "Нажмите кнопку ниже, чтобы открыть панель настроек.\n"
        "Там вы можете:\n"
        "• Управлять темами группы\n"
        "• Настроить AI-провайдера\n"
        "• Изменить уровень краткости",
        reply_markup=get_settings_keyboard(webapp_url)
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


# ============ Group Message Handler (для захвата тем) ============

async def _process_group_message(message: Message):
    """
    Внутренняя функция обработки сообщений в группе.
    Автоматически добавляет темы в БД при получении сообщений.
    Также привязывает группу к пользователю если она ещё не привязана.
    """
    logger.info(f"[GROUP] Обрабатываем сообщение: chat_id={message.chat.id}, thread={message.message_thread_id}")
    
    chat = message.chat
    is_forum = getattr(chat, 'is_forum', False)
    
    # Сохраняем группу и тему в БД
    session_maker = get_async_session_maker()
    async with session_maker() as session:
        # Получаем/создаем группу
        # Важно: если user_id есть, это хорошо, но в группе может писать кто угодно
        # Поэтому сначала пробуем найти группу по ID
        # Если message.from_user есть — используем его
        
        user_id = message.from_user.id if message.from_user else 0
        if user_id:
             await db_service.get_or_create_user(session, user_id)

        # Здесь логика немного сложнее: мы не всегда хотим создавать группу, если её нет, 
        # только если мы знаем owner'а (например админа). 
        # Но в оригинале мы создавали группу, если её нет, и привязывали к текущему юзеру.
        # Оставим пока как было:
        
        group = await db_service.get_or_create_group(
             session, 
             user_id=user_id, 
             chat_id=chat.id, 
             title=chat.title or "Без названия", 
             is_forum=is_forum
        )
        
        if not group:
            logger.warning(f"[GROUP] Не удалось создать или найти группу {chat.id}")
            return
        
        # Если это не форум или нет thread_id — просто выходим
        if not is_forum or not message.message_thread_id:
            logger.info(f"[GROUP] is_forum={is_forum}, thread_id={message.message_thread_id}, пропускаем добавление темы")
            return
        
        topic_id = message.message_thread_id
        topic_name = None
        
        # Пробуем получить название темы
        if message.forum_topic_created:
            topic_name = message.forum_topic_created.name
        elif message.forum_topic_edited:
            topic_name = message.forum_topic_edited.name
        else:
            topic_name = f"Тема #{topic_id}"
        
        logger.info(f"[GROUP] topic_id={topic_id}, topic_name={topic_name}")
        
        # Проверяем существует ли тема
        topic = await db_service.get_topic(session, group.id, topic_id)
        
        if not topic:
            # Создаём новую тему
            await db_service.create_topic(session, group.id, topic_id, topic_name)
            logger.info(f"[GROUP] Добавлена тема: {topic_name} (id={topic_id})")
            
            # Предлагаем настроить тему с инлайн кнопкой
            await message.answer(
                "👋 Вижу новую тему!\n\n"
                "Хотите настроить её для бота?",
                reply_markup=get_bind_topic_keyboard(topic_id)
            )


@router.message(Command("sync"))
async def cmd_sync_topics(message: Message, bot: Bot):
    """Команда /sync — синхронизация тем группы."""
    chat = message.chat
    
    if chat.type == "private":
        await message.answer(
            "❌ Эту команду нужно выполнить в группе с темами.\n"
            "Добавьте бота в группу и напишите /sync там."
        )
        return
    
    is_forum = getattr(chat, 'is_forum', False)
    if not is_forum:
        await message.answer(
            "❌ Эта группа не является форумом.\n"
            "Включите темы в настройках группы."
        )
        return
    
    # Получаем список тем через сообщения
    await message.answer(
        "🔄 <b>Синхронизация тем</b>\n\n"
        "Бот автоматически добавляет темы, когда видит сообщения в них.\n\n"
        "Чтобы синхронизировать все темы:\n"
        "1. Отправьте любое сообщение в каждой теме\n"
        "2. Или просто используйте бота — темы добавятся автоматически\n\n"
        "✅ Уже отслеживаю эту группу!"
    )
