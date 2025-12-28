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
    BotCommandScopeAllPrivateChats, BotCommandScopeAllGroupChats
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from src.db.database import get_async_session_maker
from src.db.models import Topic
from src.services import db_service
from src.bot.states import TopicInitState, TopicRulesState, TopicFormatState
from src.bot.keyboards import (
    get_topic_settings_keyboard, 
    get_cancel_keyboard, 
    get_bind_topic_keyboard,
    get_close_keyboard
)

logger = logging.getLogger(__name__)

# Роутер для групповых команд
group_router = Router()

# Формат заметок по умолчанию
from src.bot.constants import DEFAULT_FORMAT


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

def is_group_forum(message: Message) -> bool:
    """Проверить что сообщение из форума группы."""
    return (
        message.chat.type in ("group", "supergroup") and
        getattr(message.chat, 'is_forum', False)
    )


async def delete_message_safe(message: Message):
    """Безопасное удаление сообщения."""
    try:
        await message.delete()
    except Exception:
        pass


# ============ Cancel Handler ============

@group_router.callback_query(F.data == "cancel_dialog")
async def callback_cancel_dialog(callback: CallbackQuery, state: FSMContext):
    """Обработка отмены диалога — очищает state и удаляет сообщение."""
    await state.clear()
    await delete_message_safe(callback.message)
    await callback.answer("Отменено")


@group_router.callback_query(F.data == "close_message")
async def callback_close_message(callback: CallbackQuery):
    """Удалить сообщение при нажатии Закрыть."""
    await delete_message_safe(callback.message)
    await callback.answer()


@group_router.message(TopicInitState.waiting_for_description, F.chat.type.in_({"group", "supergroup"}))
async def process_init_description(message: Message, state: FSMContext):
    """Обработка ввода описания при инициализации."""
    data = await state.get_data()
    topic_id = data.get("topic_id")
    group_id = data.get("group_id")
    bot_message_id = data.get("bot_message_id")
    
    # Сразу удаляем ответ пользователя
    await delete_message_safe(message)
    
    if not topic_id or not group_id:
        await state.clear()
        return
    
    description = message.text.strip()
    
    session_maker = get_async_session_maker()
    async with session_maker() as session:
        topic = await db_service.get_topic(session, group_id, topic_id)
        
        if topic:
            topic.description = description
            topic.title = description[:50] + ("..." if len(description) > 50 else "")
            await session.commit()
            logger.info(f"[INIT] Тема {topic_id} настроена: {description[:50]}...")
    
    await state.clear()
    
    # Редактируем сообщение бота, если есть ID
    if bot_message_id:
        try:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=bot_message_id,
                text=f"✅ <b>Тема настроена!</b>\n\n📝 {description}",
                reply_markup=get_topic_settings_keyboard(topic_id)
            )
            return
        except Exception:
            pass
    
    # Если редактирование не удалось, отправляем новое (но это крайний случай)
    await message.answer(
        f"✅ <b>Тема настроена!</b>\n\n📝 {description}",
        reply_markup=get_topic_settings_keyboard(topic_id)
    )


# ============ /rules Command ============

@group_router.message(Command("rules"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_set_rules(message: Message, state: FSMContext):
    """Команда /rules — редактировать описание темы."""
    await delete_message_safe(message)
    
    if not is_group_forum(message):
        return
    
    topic_id = message.message_thread_id
    
    # Проверяем есть ли аргумент сразу
    args = message.text.split(maxsplit=1)
    if len(args) > 1:
        await _save_topic_rules(message, topic_id, args[1].strip())
        return
    
    session_maker = get_async_session_maker()
    async with session_maker() as session:
        user = await db_service.get_or_create_user(session, message.from_user.id)
        group = await db_service.get_or_create_group(session, user.id, message.chat.id, message.chat.title)
        topic = await db_service.get_topic(session, group.id, topic_id)
        
        if not topic:
            # Темы нет, но так как мы удалили команду, надо как-то сообщить
            # Используем временное сообщение которое удалится
            msg = await message.answer("❌ Сначала выполните /info", reply_markup=get_cancel_keyboard())
            # Можно не удалять, юзер нажмет отмена/закрыть
            return
        
        current = topic.description or "<i>не задано</i>"
        
        msg = await message.answer(
            f"📝 <b>Описание темы</b>\n\n"
            f"Текущее: {current}\n\n"
            f"Введите новое описание:",
            reply_markup=get_cancel_keyboard()
        )
        
        await state.update_data(topic_id=topic_id, group_id=group.id, bot_message_id=msg.message_id)
        await state.set_state(TopicRulesState.waiting_for_rules)


@group_router.message(TopicRulesState.waiting_for_rules, F.chat.type.in_({"group", "supergroup"}))
async def process_rules_input(message: Message, state: FSMContext):
    """Обработка ввода нового описания."""
    data = await state.get_data()
    topic_id = data.get("topic_id")
    bot_message_id = data.get("bot_message_id")
    
    # Удаляем сообщение пользователя
    await delete_message_safe(message)
    
    if topic_id:
        await _save_topic_rules(message, topic_id, message.text.strip(), bot_message_id)
    
    await state.clear()


async def _save_topic_rules(message: Message, topic_id: int, rules_text: str, bot_message_id: int = None):
    """Сохранить описание темы."""
    session_maker = get_async_session_maker()
    async with session_maker() as session:
        user = await db_service.get_or_create_user(session, message.from_user.id)
        group = await db_service.get_or_create_group(session, user.id, message.chat.id, message.chat.title)
        topic = await db_service.get_topic(session, group.id, topic_id)
        
        if not topic:
            return
        
        topic.description = rules_text
        topic.title = rules_text[:50] + ("..." if len(rules_text) > 50 else "")
        await session.commit()
        
        logger.info(f"[RULES] Тема {topic_id}: {rules_text[:50]}...")
        
        text = f"✅ Описание обновлено:\n\n{rules_text}"
        
        if bot_message_id:
            try:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=bot_message_id,
                    text=text,
                    reply_markup=get_topic_settings_keyboard(topic_id) # Возвращаем меню настроек или закрыть
                )
            except Exception:
                await message.answer(text, reply_markup=get_topic_settings_keyboard(topic_id))
        else:
             await message.answer(text, reply_markup=get_topic_settings_keyboard(topic_id))


# ============ /format Command ============

@group_router.message(Command("format"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_set_format(message: Message, state: FSMContext):
    """Команда /format — задать формат заметок."""
    await delete_message_safe(message)
    
    if not is_group_forum(message):
        return
    
    topic_id = message.message_thread_id
    
    args = message.text.split(maxsplit=1)
    if len(args) > 1:
        await _save_topic_format(message, topic_id, args[1].strip())
        return

@group_router.message(TopicFormatState.waiting_for_format, F.chat.type.in_({"group", "supergroup"}))
async def process_format_input(message: Message, state: FSMContext):
    """Обработка ввода формата."""
    data = await state.get_data()
    topic_id = data.get("topic_id")
    bot_message_id = data.get("bot_message_id")
    
    await delete_message_safe(message)
    
    if topic_id:
        await _save_topic_format(message, topic_id, message.text.strip(), bot_message_id)
    
    await state.clear()


async def _save_topic_format(message: Message, topic_id: int, format_text: str, bot_message_id: int = None):
    """Сохранить формат заметок."""
    session_maker = get_async_session_maker()
    async with session_maker() as session:
        user = await db_service.get_or_create_user(session, message.from_user.id)
        group = await db_service.get_or_create_group(session, user.id, message.chat.id, message.chat.title)
        topic = await db_service.get_topic(session, group.id, topic_id)
        
        if not topic:
            return
        
        topic.format_policy_text = format_text
        await session.commit()
        
        logger.info(f"[FORMAT] Тема {topic_id}: {format_text[:50]}...")
        
        text = f"✅ Формат заметок задан:\n\n{format_text}"
        
        if bot_message_id:
            try:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=bot_message_id,
                    text=text,
                    reply_markup=get_topic_settings_keyboard(topic_id)
                )
            except Exception:
                await message.answer(text, reply_markup=get_topic_settings_keyboard(topic_id))
        else:
             await message.answer(text, reply_markup=get_topic_settings_keyboard(topic_id))



# ============ /info Command ============

@group_router.message(Command("info"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_topic_info(message: Message, state: FSMContext):
    """
    Команда /info — универсальная команда управления темой.
    """
    await delete_message_safe(message)
    
    # Сначала проверяем, является ли это General топик (thread_id=None или 1)
    # Если это General — отправляем инфо о буфере
    # Примечание: is_group_forum теперь не требует thread_id, но мы проверим его явно ниже для других команд
    
    if is_group_forum(message) and (message.message_thread_id is None or message.message_thread_id == 1):
        await message.answer(
            "📨 <b>Входящий буфер</b>\n\n"
            "Это основная тема группы. Бот использует её как буфер для сортировки.\n"
            "Отправляйте сюда сообщения, и бот автоматически перенесет их в нужную тему.",
            reply_markup=get_close_keyboard()
        )
        return

    if not is_group_forum(message) or message.message_thread_id is None:
        return
    
    topic_id = message.message_thread_id
    chat = message.chat
    
    session_maker = get_async_session_maker()
    async with session_maker() as session:
        user = await db_service.get_or_create_user(session, message.from_user.id)
        group = await db_service.get_or_create_group(session, user.id, chat.id, chat.title)
        topic = await db_service.get_topic(session, group.id, topic_id)
        
        # Если темы нет или она не настроена — запускаем настройку
        if not topic or not topic.description:
            # Создаём тему если её нет
            if not topic:
                topic = await db_service.create_topic(session, group.id, topic_id)
                logger.info(f"[INFO] Создана тема {topic_id}")
            
            # Запускаем настройку
            bot_msg = await message.answer(
                "📁 <b>Настройка темы</b>\n\n"
                "Опишите, какую информацию нужно сохранять в эту тему.\n\n"
                "Например:\n"
                "• <i>Идеи для проектов</i>\n"
                "• <i>Книги для чтения</i>\n"
                "• <i>Список покупок</i>",
                reply_markup=get_cancel_keyboard()
            )
            
            await state.update_data(
                topic_id=topic_id, 
                group_id=group.id,
                bot_message_id=bot_msg.message_id
            )
            await state.set_state(TopicInitState.waiting_for_description)
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
        user = await db_service.get_or_create_user(session, callback.from_user.id)
        group = await db_service.get_or_create_group(session, user.id, callback.message.chat.id, callback.message.chat.title)
        topic = await db_service.get_topic(session, group.id, topic_id)
        
        if not topic:
            await callback.answer("❌ Тема не найдена", show_alert=True)
            return
        
        current = topic.description or "не задано"
        
        await state.update_data(topic_id=topic_id, group_id=group.id, bot_message_id=callback.message.message_id)
        await state.set_state(TopicRulesState.waiting_for_rules)
        
        # Редактируем сообщение (вместо отправки нового)
        await callback.message.edit_text(
            f"📝 <b>Описание темы</b>\n\n"
            f"Текущее: {current}\n\n"
            f"Введите новое описание:",
            reply_markup=get_cancel_keyboard()
        )
        await callback.answer()


@group_router.callback_query(F.data.startswith("topic_format:"))
async def callback_topic_format(callback: CallbackQuery, state: FSMContext):
    """Обработка нажатия кнопки 'Формат'."""
    topic_id = int(callback.data.split(":")[1])
    
    session_maker = get_async_session_maker()
    async with session_maker() as session:
        user = await db_service.get_or_create_user(session, callback.from_user.id)
        group = await db_service.get_or_create_group(session, user.id, callback.message.chat.id, callback.message.chat.title)
        topic = await db_service.get_topic(session, group.id, topic_id)
        
        if not topic:
            await callback.answer("❌ Тема не найдена", show_alert=True)
            return
        
        current = topic.format_policy_text or DEFAULT_FORMAT
        
        await state.update_data(topic_id=topic_id, group_id=group.id, bot_message_id=callback.message.message_id)
        await state.set_state(TopicFormatState.waiting_for_format)
        
        # Редактируем сообщение
        await callback.message.edit_text(
            f"📋 <b>Формат заметок</b>\n\n"
            f"Текущий шаблон:\n<pre>{current}</pre>\n\n"
            f"<b>Доступные переменные:</b>\n"
            f"• <code>[title]</code> - Заголовок (генерируется AI)\n"
            f"• <code>[caption]</code> - Краткая выжимка (генерируется AI)\n"
            f"• <code>[message]</code> - Оригинальный текст сообщения\n"
            f"• <code>[date]</code> - Дата заметки (ДД.ММ.ГГГГ ЧЧ:ММ)\n"
            f"• <code>[tags]</code> - Теги (генерируются AI)\n\n"
            f"Поддерживается HTML разметка (b, i, u, s, code, pre, a).\n\n"
            f"Введите новый шаблон:",
             reply_markup=get_cancel_keyboard(),
             parse_mode="HTML"
        )
        await callback.answer()


@group_router.callback_query(F.data.startswith("topic_info:"))
async def callback_topic_info(callback: CallbackQuery):
    """Обработка нажатия кнопки 'Обновить' — показывает актуальные настройки."""
    topic_id = int(callback.data.split(":")[1])
    
    session_maker = get_async_session_maker()
    async with session_maker() as session:
        user = await db_service.get_or_create_user(session, callback.from_user.id)
        group = await db_service.get_or_create_group(session, user.id, callback.message.chat.id, callback.message.chat.title)
        topic = await db_service.get_topic(session, group.id, topic_id)
        
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
        user = await db_service.get_or_create_user(session, callback.from_user.id)
        group = await db_service.get_or_create_group(session, user.id, callback.message.chat.id, callback.message.chat.title)
        
        # Сохраняем данные для FSM
        await state.update_data(topic_id=topic_id, group_id=group.id, bot_message_id=callback.message.message_id)
        await state.set_state(TopicInitState.waiting_for_description)
        
        await callback.message.edit_text(
            "📁 <b>Настройка темы</b>\n\n"
            "Опишите, какую информацию нужно сохранять в эту тему.\n\n"
            "Например:\n"
            "• <i>Идеи для проектов</i>\n"
            "• <i>Книги для чтения</i>\n"
            "• <i>Список покупок</i>",
            reply_markup=get_cancel_keyboard()
        )
        await callback.answer()



# ============ /info Command ============

@group_router.message(Command("info"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_topic_info(message: Message, state: FSMContext):
    """
    Команда /info — универсальная команда управления темой.
    """
    await delete_message_safe(message)
    
    # Сначала проверяем, является ли это General топик (thread_id=None или 1)
    # Если это General — отправляем инфо о буфере
    # Примечание: is_group_forum теперь не требует thread_id, но мы проверим его явно ниже для других команд
    
    if is_group_forum(message) and (message.message_thread_id is None or message.message_thread_id == 1):
        await message.answer(
            "📨 <b>Входящий буфер</b>\n\n"
            "Это основная тема группы. Бот использует её как буфер для сортировки.\n"
            "Отправляйте сюда сообщения, и бот автоматически перенесет их в нужную тему.",
            reply_markup=get_close_keyboard()
        )
        return

    if not is_group_forum(message) or message.message_thread_id is None:
        return
    
    topic_id = message.message_thread_id
    chat = message.chat
    
    session_maker = get_async_session_maker()
    async with session_maker() as session:
        user = await db_service.get_or_create_user(session, message.from_user.id)
        group = await db_service.get_or_create_group(session, user.id, chat.id, chat.title)
        topic = await db_service.get_topic(session, group.id, topic_id)
        
        # Если темы нет или она не настроена — запускаем настройку
        if not topic or not topic.description:
            # Создаём тему если её нет
            if not topic:
                topic = await db_service.create_topic(session, group.id, topic_id)
                logger.info(f"[INFO] Создана тема {topic_id}")
            
            # Запускаем настройку
            bot_msg = await message.answer(
                "📁 <b>Настройка темы</b>\n\n"
                "Опишите, какую информацию нужно сохранять в эту тему.\n\n"
                "Например:\n"
                "• <i>Идеи для проектов</i>\n"
                "• <i>Книги для чтения</i>\n"
                "• <i>Список покупок</i>",
                reply_markup=get_cancel_keyboard()
            )
            
            await state.update_data(
                topic_id=topic_id, 
                group_id=group.id,
                bot_message_id=bot_msg.message_id
            )
            await state.set_state(TopicInitState.waiting_for_description)
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
        user = await db_service.get_or_create_user(session, callback.from_user.id)
        group = await db_service.get_or_create_group(session, user.id, callback.message.chat.id, callback.message.chat.title)
        topic = await db_service.get_topic(session, group.id, topic_id)
        
        if not topic:
            await callback.answer("❌ Тема не найдена", show_alert=True)
            return
        
        current = topic.description or "не задано"
        
        await state.update_data(topic_id=topic_id, group_id=group.id, bot_message_id=callback.message.message_id)
        await state.set_state(TopicRulesState.waiting_for_rules)
        
        # Редактируем сообщение (вместо отправки нового)
        await callback.message.edit_text(
            f"📝 <b>Описание темы</b>\n\n"
            f"Текущее: {current}\n\n"
            f"Введите новое описание:",
            reply_markup=get_cancel_keyboard()
        )
        await callback.answer()


@group_router.callback_query(F.data.startswith("topic_format:"))
async def callback_topic_format(callback: CallbackQuery, state: FSMContext):
    """Обработка нажатия кнопки 'Формат'."""
    topic_id = int(callback.data.split(":")[1])
    
    session_maker = get_async_session_maker()
    async with session_maker() as session:
        user = await db_service.get_or_create_user(session, callback.from_user.id)
        group = await db_service.get_or_create_group(session, user.id, callback.message.chat.id, callback.message.chat.title)
        topic = await db_service.get_or_create_topic(session, group.id, topic_id) # Changed to get_or_create_topic
        
        if not topic: # This check might be redundant if get_or_create_topic always returns a topic
            await callback.answer("❌ Тема не найдена", show_alert=True)
            return
        
        current = topic.format_policy_text or DEFAULT_FORMAT
        
        await state.update_data(topic_id=topic_id, group_id=group.id, bot_message_id=callback.message.message_id)
        await state.set_state(TopicFormatState.waiting_for_format)
        
        # Редактируем сообщение
        await callback.message.edit_text(
            f"📋 <b>Формат заметок</b>\n\n"
            f"Текущий шаблон:\n<pre>{current}</pre>\n\n"
            f"<b>Доступные переменные:</b>\n"
            f"• <code>[title]</code> - Заголовок (генерируется AI)\n"
            f"• <code>[caption]</code> - Краткая выжимка (генерируется AI)\n"
            f"• <code>[message]</code> - Оригинальный текст сообщения\n"
            f"• <code>[date]</code> - Дата заметки (ДД.ММ.ГГГГ ЧЧ:ММ)\n"
            f"• <code>[tags]</code> - Теги (генерируются AI)\n"
            f"• <code>[url]</code> - Ссылка на сообщение\n" # New variable
            f"• <code>[username]</code> - Имя пользователя\n" # New variable
            f"• <code>[first_name]</code> - Имя пользователя (first_name)\n" # New variable
            f"• <code>[last_name]</code> - Фамилия пользователя (last_name)\n" # New variable
            f"• <code>[full_name]</code> - Полное имя пользователя\n" # New variable
            f"• <code>[user_id]</code> - ID пользователя\n" # New variable
            f"• <code>[chat_title]</code> - Название группы\n" # New variable
            f"• <code>[topic_name]</code> - Название темы\n" # New variable
            f"• <code>[message_id]</code> - ID сообщения\n" # New variable
            f"• <code>[thread_id]</code> - ID темы\n" # New variable
            f"• <code>[group_id]</code> - ID группы\n\n" # New variable
            f"Поддерживается HTML разметка (b, i, u, s, code, pre, a).\n\n"
            f"Введите новый шаблон:",
             reply_markup=get_cancel_keyboard(),
             parse_mode="HTML"
        )
        await callback.answer()


@group_router.callback_query(F.data.startswith("topic_info:"))
async def callback_topic_info(callback: CallbackQuery):
    """Обработка нажатия кнопки 'Обновить' — показывает актуальные настройки."""
    topic_id = int(callback.data.split(":")[1])
    
    session_maker = get_async_session_maker()
    async with session_maker() as session:
        user = await db_service.get_or_create_user(session, callback.from_user.id)
        group = await db_service.get_or_create_group(session, user.id, callback.message.chat.id, callback.message.chat.title)
        topic = await db_service.get_topic(session, group.id, topic_id)
        
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
        user = await db_service.get_or_create_user(session, callback.from_user.id)
        group = await db_service.get_or_create_group(session, user.id, callback.message.chat.id, callback.message.chat.title)
        
        # Сохраняем данные для FSM
        await state.update_data(topic_id=topic_id, group_id=group.id, bot_message_id=callback.message.message_id) # Важно сохранить ID
        await state.set_state(TopicInitState.waiting_for_description)
        
        await callback.message.edit_text(
            "📁 <b>Настройка темы</b>\n\n"
            "Опишите, какую информацию нужно сохранять в эту тему.\n\n"
            "Например:\n"
            "• <i>Идеи для проектов</i>\n"
            "• <i>Книги для чтения</i>\n"
            "• <i>Список покупок</i>",
            reply_markup=get_cancel_keyboard()
        )
        await callback.answer()
