from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

def get_topic_settings_keyboard(topic_id: int) -> InlineKeyboardMarkup:
    """Создать инлайн клавиатуру для настроек темы."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📝 Описание", callback_data=f"topic_rules:{topic_id}"),
            InlineKeyboardButton(text="📋 Формат", callback_data=f"topic_format:{topic_id}"),
        ],
        [
            InlineKeyboardButton(text="❌ Закрыть", callback_data="close_message"),
        ]
    ])


def get_close_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура только с кнопкой закрытия."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="close_message")]
    ])


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой отмены для диалогов."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Завершить", callback_data="cancel_dialog")]
    ])


def get_bind_topic_keyboard(topic_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для привязки темы."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📌 Привязать тему", callback_data=f"bind_topic:{topic_id}")],
        [InlineKeyboardButton(text="🙈 Скрыть", callback_data="close_message")]
    ])

def get_settings_keyboard(webapp_url: str) -> InlineKeyboardMarkup:
    """Клавиатура для настроек с WebApp."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="⚙️ Открыть настройки",
            web_app=WebAppInfo(url=webapp_url)
        )]
    ])
