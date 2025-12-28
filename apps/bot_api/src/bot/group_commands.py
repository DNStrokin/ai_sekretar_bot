"""
Group Topic Commands

Команды управления темами в группе:
- /init - инициализация темы (сразу спрашивает описание)
- /rules - редактировать описание темы
- /format - формат заметок
- /info - показать настройки темы
"""

import logging
from aiogram import Router, F, Bot
from aiogram.types import (
    Message, CallbackQuery, BotCommand, 
    BotCommandScopeAllPrivateChats, BotCommandScopeAllGroupChats,
    InlineKeyboardButton, InlineKeyboardMarkup
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select

from src.db.database import get_async_session_maker
from src.db.models import User, Group, Topic

logger = logging.getLogger(__name__)

# Роутер для групповых команд
group_router = Router()

# Формат заметок по умолчанию
DEFAULT_FORMAT = "Заголовок, краткое описание, дата"


# ============ FSM States ============

class TopicInitState(StatesGroup):
    """Состояния для инициализации темы."""
    waiting_for_description = State()


class TopicRulesState(StatesGroup):
    """Состояния для редактирования описания."""
    waiting_for_rules = State()


class TopicFormatState(StatesGroup):
    """Состояния для формата заметок."""
    waiting_for_format = State()


# ============ Bot Commands Menu ============

async def setup_bot_commands(bot: Bot):
    """Настройка меню команд бота для разных типов чатов."""
    
    # Команды для личных сообщений
    private_commands = [
        BotCommand(command="start", description="🚀 Начать работу"),
        BotCommand(command="help", description="❓ Справка"),
        BotCommand(command="settings", description="⚙️ Настройки"),
    ]
    
    # Команды для групп
    group_commands = [
        BotCommand(command="info", description="ℹ️ Настройки темы"),
    ]
    
    # Устанавливаем команды
    await bot.set_my_commands(private_commands, scope=BotCommandScopeAllPrivateChats())
    await bot.set_my_commands(group_commands, scope=BotCommandScopeAllGroupChats())
    
    logger.info("Меню команд бота настроено")


# ============ Helper Functions ============

async def get_or_create_user(session, telegram_user_id: int) -> User:
    """Получить или создать пользователя."""
    result = await session.execute(
        select(User).where(User.telegram_user_id == telegram_user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        user = User(telegram_user_id=telegram_user_id)
        session.add(user)
        await session.commit()
        await session.refresh(user)
    
    return user


async def get_or_create_group(session, user_id: int, chat) -> Group:
    """Получить или создать группу."""
    result = await session.execute(
        select(Group).where(Group.telegram_group_id == chat.id)
    )
    group = result.scalar_one_or_none()
    
    if not group:
        is_forum = getattr(chat, 'is_forum', False)
        group = Group(
            telegram_group_id=chat.id,
            title=chat.title or "Без названия",
            topics_enabled=is_forum,
            user_id=user_id
        )
        session.add(group)
        await session.commit()
        await session.refresh(group)
    
    return group


async def get_topic(session, group_id: int, topic_id: int) -> Topic | None:
    """Получить тему по ID."""
    result = await session.execute(
        select(Topic).where(
            Topic.group_id == group_id,
            Topic.telegram_topic_id == topic_id
        )
    )
    return result.scalar_one_or_none()


def is_group_forum(message: Message) -> bool:
    """Проверить что сообщение из форума группы."""
    return (
        message.chat.type in ("group", "supergroup") and
        getattr(message.chat, 'is_forum', False) and
        message.message_thread_id is not None
    )


def get_topic_settings_keyboard(topic_id: int) -> InlineKeyboardMarkup:
    """Создать инлайн клавиатуру для настроек темы."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📝 Описание", callback_data=f"topic_rules:{topic_id}"),
            InlineKeyboardButton(text="📋 Формат", callback_data=f"topic_format:{topic_id}"),
        ],
        [
            InlineKeyboardButton(text="🔄 Обновить", callback_data=f"topic_info:{topic_id}"),
        ]
    ])


@group_router.message(TopicInitState.waiting_for_description, F.chat.type.in_({"group", "supergroup"}))
async def process_init_description(message: Message, state: FSMContext):
    """Обработка ввода описания при инициализации."""
    data = await state.get_data()
    topic_id = data.get("topic_id")
    group_id = data.get("group_id")
    
    if not topic_id or not group_id:
        await state.clear()
        await message.answer("❌ Ошибка. Попробуйте /info снова.")
        return
    
    description = message.text.strip()
    
    session_maker = get_async_session_maker()
    async with session_maker() as session:
        result = await session.execute(
            select(Topic).where(
                Topic.group_id == group_id,
                Topic.telegram_topic_id == topic_id
            )
        )
        topic = result.scalar_one_or_none()
        
        if topic:
            topic.description = description
            # Используем первые слова описания как название
            topic.title = description[:50] + ("..." if len(description) > 50 else "")
            await session.commit()
            
            logger.info(f"[INIT] Тема {topic_id} настроена: {description[:50]}...")
    
    await state.clear()
    
    await message.answer(
        f"✅ <b>Тема настроена!</b>\n\n"
        f"📝 {description}\n\n"
        f"Теперь бот будет понимать, какие заметки сохранять сюда.",
        reply_markup=get_topic_settings_keyboard(topic_id)
    )


# ============ /rules Command ============

@group_router.message(Command("rules"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_set_rules(message: Message, state: FSMContext):
    """Команда /rules — редактировать описание темы."""
    if not is_group_forum(message):
        await message.answer("❌ Выполните эту команду внутри темы форума.")
        return
    
    topic_id = message.message_thread_id
    
    # Проверяем есть ли аргумент сразу
    args = message.text.split(maxsplit=1)
    if len(args) > 1:
        await _save_topic_rules(message, topic_id, args[1].strip())
        return
    
    session_maker = get_async_session_maker()
    async with session_maker() as session:
        user = await get_or_create_user(session, message.from_user.id)
        group = await get_or_create_group(session, user.id, message.chat)
        topic = await get_topic(session, group.id, topic_id)
        
        if not topic:
            await message.answer("❌ Сначала выполните /init")
            return
        
        current = topic.description or "<i>не задано</i>"
        
        await state.update_data(topic_id=topic_id, group_id=group.id)
        await state.set_state(TopicRulesState.waiting_for_rules)
        
        await message.answer(
            f"📝 <b>Описание темы</b>\n\n"
            f"Текущее: {current}\n\n"
            f"Введите новое описание:"
        )


@group_router.message(TopicRulesState.waiting_for_rules, F.chat.type.in_({"group", "supergroup"}))
async def process_rules_input(message: Message, state: FSMContext):
    """Обработка ввода нового описания."""
    data = await state.get_data()
    topic_id = data.get("topic_id")
    
    if topic_id:
        await _save_topic_rules(message, topic_id, message.text.strip())
    
    await state.clear()


async def _save_topic_rules(message: Message, topic_id: int, rules_text: str):
    """Сохранить описание темы."""
    session_maker = get_async_session_maker()
    async with session_maker() as session:
        user = await get_or_create_user(session, message.from_user.id)
        group = await get_or_create_group(session, user.id, message.chat)
        topic = await get_topic(session, group.id, topic_id)
        
        if not topic:
            await message.answer("❌ Сначала выполните /init")
            return
        
        topic.description = rules_text
        topic.title = rules_text[:50] + ("..." if len(rules_text) > 50 else "")
        await session.commit()
        
        logger.info(f"[RULES] Тема {topic_id}: {rules_text[:50]}...")
        
        await message.answer(f"✅ Описание обновлено:\n\n{rules_text}")


# ============ /format Command ============

@group_router.message(Command("format"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_set_format(message: Message, state: FSMContext):
    """Команда /format — задать формат заметок."""
    if not is_group_forum(message):
        await message.answer("❌ Выполните эту команду внутри темы форума.")
        return
    
    topic_id = message.message_thread_id
    
    args = message.text.split(maxsplit=1)
    if len(args) > 1:
        await _save_topic_format(message, topic_id, args[1].strip())
        return
    
    session_maker = get_async_session_maker()
    async with session_maker() as session:
        user = await get_or_create_user(session, message.from_user.id)
        group = await get_or_create_group(session, user.id, message.chat)
        topic = await get_topic(session, group.id, topic_id)
        
        if not topic:
            await message.answer("❌ Сначала выполните /init")
            return
        
        current = topic.format_policy_text or "<i>по умолчанию</i>"
        
        await state.update_data(topic_id=topic_id, group_id=group.id)
        await state.set_state(TopicFormatState.waiting_for_format)
        
        await message.answer(
            f"📋 <b>Формат заметок</b>\n\n"
            f"Текущий: {current}\n\n"
            f"Опишите, как оформлять заметки:\n"
            f"• <i>Заголовок и краткое описание</i>\n"
            f"• <i>Только ключевые слова</i>\n"
            f"• <i>Списком с датами</i>\n\n"
            f"Введите формат:"
        )


@group_router.message(TopicFormatState.waiting_for_format, F.chat.type.in_({"group", "supergroup"}))
async def process_format_input(message: Message, state: FSMContext):
    """Обработка ввода формата."""
    data = await state.get_data()
    topic_id = data.get("topic_id")
    
    if topic_id:
        await _save_topic_format(message, topic_id, message.text.strip())
    
    await state.clear()


async def _save_topic_format(message: Message, topic_id: int, format_text: str):
    """Сохранить формат заметок."""
    session_maker = get_async_session_maker()
    async with session_maker() as session:
        user = await get_or_create_user(session, message.from_user.id)
        group = await get_or_create_group(session, user.id, message.chat)
        topic = await get_topic(session, group.id, topic_id)
        
        if not topic:
            await message.answer("❌ Сначала выполните /init")
            return
        
        topic.format_policy_text = format_text
        await session.commit()
        
        logger.info(f"[FORMAT] Тема {topic_id}: {format_text[:50]}...")
        
        await message.answer(f"✅ Формат заметок задан:\n\n{format_text}")


# ============ /info Command ============

@group_router.message(Command("info"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_topic_info(message: Message, state: FSMContext):
    """
    Команда /info — универсальная команда управления темой.
    Если тема не настроена — запускает настройку.
    Если настроена — показывает статус и кнопки управления.
    """
    if not is_group_forum(message):
        await message.answer("❌ Выполните эту команду внутри темы форума.")
        return
    
    topic_id = message.message_thread_id
    chat = message.chat
    
    session_maker = get_async_session_maker()
    async with session_maker() as session:
        user = await get_or_create_user(session, message.from_user.id)
        group = await get_or_create_group(session, user.id, chat)
        topic = await get_topic(session, group.id, topic_id)
        
        # Если темы нет или она не настроена — запускаем настройку
        if not topic or not topic.description:
            # Создаём тему если её нет
            if not topic:
                topic = Topic(
                    telegram_topic_id=topic_id,
                    title="Тема",
                    group_id=group.id,
                    is_active=True
                )
                session.add(topic)
                await session.commit()
                logger.info(f"[INFO] Создана тема {topic_id}")
            
            # Запускаем настройку
            await state.update_data(topic_id=topic_id, group_id=group.id)
            await state.set_state(TopicInitState.waiting_for_description)
            
            await message.answer(
                "📁 <b>Настройка темы</b>\n\n"
                "Опишите, какую информацию нужно сохранять в эту тему.\n\n"
                "Например:\n"
                "• <i>Идеи для проектов</i>\n"
                "• <i>Книги для чтения</i>\n"
                "• <i>Список покупок</i>\n\n"
                "Введите описание:"
            )
            return
        
        # Тема настроена — показываем статус
        description = topic.description
        format_text = topic.format_policy_text or "<i>по умолчанию</i>"
        status = "✅ Активна" if topic.is_active else "⏸ Неактивна"
        
        await message.answer(
            f"ℹ️ <b>Настройки темы</b>\n\n"
            f"📝 <b>Описание:</b>\n{description}\n\n"
            f"📋 <b>Формат:</b>\n{format_text}\n\n"
            f"Статус: {status}",
            reply_markup=get_topic_settings_keyboard(topic_id)
        )


# ============ Callback Handlers ============

@group_router.callback_query(F.data.startswith("topic_rules:"))
async def callback_topic_rules(callback: CallbackQuery, state: FSMContext):
    """Обработка нажатия кнопки 'Описание'."""
    topic_id = int(callback.data.split(":")[1])
    
    session_maker = get_async_session_maker()
    async with session_maker() as session:
        user = await get_or_create_user(session, callback.from_user.id)
        group = await get_or_create_group(session, user.id, callback.message.chat)
        topic = await get_topic(session, group.id, topic_id)
        
        if not topic:
            await callback.answer("❌ Тема не найдена", show_alert=True)
            return
        
        current = topic.description or "не задано"
        
        await state.update_data(topic_id=topic_id, group_id=group.id)
        await state.set_state(TopicRulesState.waiting_for_rules)
        
        await callback.message.answer(
            f"📝 <b>Описание темы</b>\n\n"
            f"Текущее: {current}\n\n"
            f"Введите новое описание:"
        )
        await callback.answer()


@group_router.callback_query(F.data.startswith("topic_format:"))
async def callback_topic_format(callback: CallbackQuery, state: FSMContext):
    """Обработка нажатия кнопки 'Формат'."""
    topic_id = int(callback.data.split(":")[1])
    
    session_maker = get_async_session_maker()
    async with session_maker() as session:
        user = await get_or_create_user(session, callback.from_user.id)
        group = await get_or_create_group(session, user.id, callback.message.chat)
        topic = await get_topic(session, group.id, topic_id)
        
        if not topic:
            await callback.answer("❌ Тема не найдена", show_alert=True)
            return
        
        current = topic.format_policy_text or "по умолчанию"
        
        await state.update_data(topic_id=topic_id, group_id=group.id)
        await state.set_state(TopicFormatState.waiting_for_format)
        
        await callback.message.answer(
            f"📋 <b>Формат заметок</b>\n\n"
            f"Текущий: {current}\n\n"
            f"Опишите, как оформлять заметки:"
        )
        await callback.answer()


@group_router.callback_query(F.data.startswith("topic_info:"))
async def callback_topic_info(callback: CallbackQuery):
    """Обработка нажатия кнопки 'Обновить' — показывает актуальные настройки."""
    topic_id = int(callback.data.split(":")[1])
    
    session_maker = get_async_session_maker()
    async with session_maker() as session:
        user = await get_or_create_user(session, callback.from_user.id)
        group = await get_or_create_group(session, user.id, callback.message.chat)
        topic = await get_topic(session, group.id, topic_id)
        
        if not topic:
            await callback.answer("❌ Тема не найдена", show_alert=True)
            return
        
        description = topic.description or "<i>не задано</i>"
        format_text = topic.format_policy_text or "<i>по умолчанию</i>"
        status = "✅ Активна" if topic.is_active else "⏸ Неактивна"
        
        await callback.message.edit_text(
            f"ℹ️ <b>Настройки темы</b>\n\n"
            f"📝 <b>Описание:</b>\n{description}\n\n"
            f"📋 <b>Формат:</b>\n{format_text}\n\n"
            f"Статус: {status}",
            reply_markup=get_topic_settings_keyboard(topic_id)
        )
        await callback.answer("✅ Обновлено")


@group_router.callback_query(F.data.startswith("bind_topic:"))
async def callback_bind_topic(callback: CallbackQuery, state: FSMContext):
    """Обработка нажатия кнопки 'Привязать тему'."""
    topic_id = int(callback.data.split(":")[1])
    
    session_maker = get_async_session_maker()
    async with session_maker() as session:
        user = await get_or_create_user(session, callback.from_user.id)
        group = await get_or_create_group(session, user.id, callback.message.chat)
        
        # Сохраняем данные для FSM
        await state.update_data(topic_id=topic_id, group_id=group.id)
        await state.set_state(TopicInitState.waiting_for_description)
        
        await callback.message.edit_text(
            "📁 <b>Настройка темы</b>\n\n"
            "Опишите, какую информацию нужно сохранять в эту тему.\n\n"
            "Например:\n"
            "• <i>Идеи для проектов</i>\n"
            "• <i>Книги для чтения</i>\n"
            "• <i>Список покупок</i>"
        )
        await callback.answer()
