from aiogram.fsm.state import State, StatesGroup

class TopicInitState(StatesGroup):
    """Состояния для инициализации темы."""
    waiting_for_description = State()


class TopicRulesState(StatesGroup):
    """Состояния для редактирования описания."""
    waiting_for_rules = State()


class TopicFormatState(StatesGroup):
    """Состояния для формата заметок."""
    waiting_for_format = State()
