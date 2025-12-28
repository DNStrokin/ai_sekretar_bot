import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InputMediaPhoto
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from src.db.database import get_async_session_maker
from src.db.models import Group, Topic
from src.services import db_service
from src.bot.keyboards import get_settings_keyboard, get_bind_topic_keyboard
from src.settings.config import settings
from src.ai.openai_provider import OpenAIProvider, TopicContext
from src.ai.gemini_provider import GeminiProvider

logger = logging.getLogger(__name__)

router = Router()
# ai_provider = OpenAIProvider()
ai_provider = GeminiProvider()


# ============ Private Chat Handlers ============

@router.message(Command("start"), F.chat.type == "private")
async def cmd_start_private(message: Message):
    """Command /start in private chat."""
    user_name = message.from_user.first_name
    await message.answer(
        f"Привет, {user_name}! 👋\n\n"
        "Я AI Секретарь — помогаю организовывать заметки в ваших группах.\n"
        "Добавьте меня в группу и я помогу навести порядок!"
    )


@router.message(Command("settings"), F.chat.type == "private")
async def cmd_settings(message: Message):
    """Open settings Mini App."""
    if not settings.TELEGRAM_WEBHOOK_URL:
         await message.answer("⚠️ Настройки временно недоступны (не задан URL)")
         return
         
    webapp_url = f"{settings.TELEGRAM_WEBHOOK_URL}/webapp"
    await message.answer(
        "Настройки бота:",
        reply_markup=get_settings_keyboard(webapp_url)
    )


# ============ Group Chat Handlers ============

def is_group_forum(message: Message) -> bool:
    """
    Проверяет, является ли чат супергруппой (форумом).
    
    Для обработки General топика, message_thread_id может быть None.
    Но сам чат должен быть форумом.
    """
    return (
        message.chat.type in ("group", "supergroup") and
        getattr(message.chat, 'is_forum', False)
    )


async def _process_group_message(message: Message):
    """
    Обработка сообщения в группе (форуме).
    
    Логика:
    1. Если это General (thread_id=None) -> AI Маршрутизация
    2. Если это Топик (thread_id != None) -> Просто сохраняем/обрабатываем как заметку в этот топик
    """
    if not is_group_forum(message):
        return

    user_id = message.from_user.id
    chat_id = message.chat.id
    topic_id = message.message_thread_id
    text = message.text or message.caption

    if not text:
        return

    # Игнорируем команды (они обрабатываются в group_commands.py)
    if text.startswith("/"):
        return

    session_maker = get_async_session_maker()
    async with session_maker() as session:
        # Получаем/создаем пользователя и группу
        user = await db_service.get_or_create_user(session, user_id)
        group = await db_service.get_or_create_group(session, user.id, chat_id, message.chat.title, is_forum=True)

        # Сценарий 1: Сообщение в General (Буфер) => Маршрутизация
        # Тема 1 - это General в некоторых клиентах/API версиях, либо None
        if topic_id is None or topic_id == 1:
            # Получаем список активных тем
            topics = await db_service.get_group_topics(session, group.id)
            
            if not topics:
                # Нет тем для сортировки — ничего не делаем или просим создать
                logger.info("No active topics found for sorting. Ignoring message in General.")
                return

            # Подготавливаем контекст для AI
            ai_topics = [
                TopicContext(
                    topic_id=t.telegram_topic_id,
                    title=t.title,
                    description=t.description
                ) for t in topics
            ]
            
            # Классификация
            try:
                classification = await ai_provider.classify_note(text, ai_topics)
            except Exception as e:
                logger.error(f"Classification failed: {e}")
                await message.answer(f"⚠️ <b>Ошибка AI (классификация):</b>\n{str(e)}")
                return

            target_topic_id = classification.suggested_topic_id
            
            logger.info(f"Target topic ID: {target_topic_id}")
            
            if target_topic_id == 0:
                await message.answer(
                    f"⚠️ <b>Не удалось определить тему</b>\n\n"
                    f"AI не нашел подходящей темы для: <i>{text[:50]}...</i>\n"
                    f"Активные темы: {', '.join([t.title for t in topics])}"
                )
                return

            # Нашли тему! Форматируем заметку
            target_topic = next((t for t in topics if t.telegram_topic_id == target_topic_id), None)
            
            await message.answer(f"✅ Тема определена: <b>{target_topic.title}</b>. Форматирую...")
            
            try:
                rendered_note = await ai_provider.render_note(
                    text, 
                    TopicContext(
                        topic_id=target_topic.telegram_topic_id,
                        title=target_topic.title,
                        description=target_topic.description,
                        format_policy_text=target_topic.format_policy_text
                    )
                )
            except Exception as e:
                logger.error(f"Rendering failed: {e}")
                await message.answer(f"⚠️ <b>Ошибка AI (форматирование):</b>\n{str(e)}")
                return
            
            # Формируем сообщение
            note_content = (
                f"{rendered_note.title}\n\n"
                f"{rendered_note.content}\n\n"
                f"{' '.join(rendered_note.tags)}\n"
                f"👤 <a href='tg://user?id={user_id}'>{message.from_user.first_name}</a>"
            )
            
            logger.info(f"Target topic ID determined: {target_topic_id}")
            
            # Отправляем в целевую тему
            try:
                await message.bot.send_message(
                    chat_id=chat_id,
                    message_thread_id=target_topic_id,
                    text=note_content,
                    parse_mode="HTML"
                )
                logger.info(f"Сообщение перемещено из General в тему {target_topic_id}")
                
                await message.answer(f"🚀 Заметка отправлена в тему <b>{target_topic.title}</b>")
                
                # Удаляем из General
                try:
                    await message.delete()
                except Exception:
                    pass
                    
            except Exception as e:
                logger.error(f"Ошибка при перемещении заметки: {e}")
                await message.answer(f"⚠️ <b>Ошибка отправки:</b>\n{str(e)}")
            
            return


        # Сценарий 2: Сообщение уже внутри темы => Обработка заметки (если нужно)
        # Здесь логика старая — либо просто "окей", либо авто-форматирование
        topic = await db_service.get_topic(session, group.id, topic_id)

        if not topic:
            # Новая тема, которой нет в БД
            # Создадим её, но пометим как не настроенную
            topic = await db_service.create_topic(session, group.id, topic_id)
            
            # Предлагаем настроить тему с инлайн кнопкой (с опцией скрыть)
            await message.answer(
                "👋 Вижу новую тему!\n\n"
                "Хотите настроить её для бота?",
                reply_markup=get_bind_topic_keyboard(topic_id)
            )
            return

        # Если тема есть и активна — тут можно было бы тоже форматировать,
        # но пока оставим как есть (просто логирование или сохранение)
        logger.info(f"Сообщение в теме {topic_id}: {text[:20]}...")


@router.message(F.chat.type.in_({"group", "supergroup"}))
async def group_message_handler(message: Message):
    """Handler for all group messages."""
    await _process_group_message(message)
