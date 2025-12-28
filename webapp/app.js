/**
 * Telegram WebApp — Личный секретарь
 * JavaScript логика для управления темами и настройками
 */

// Конфигурация
const CONFIG = {
    // URL бэкенда (изменить на production URL после деплоя)
    API_URL: 'http://localhost:8000/api/v1',
    // Для разработки используем mock-данные
    USE_MOCK: true
};

// Telegram WebApp
const tg = window.Telegram?.WebApp;

// Состояние приложения
const state = {
    user: null,
    group: null,
    topics: [],
    aiSettings: {
        provider: 'gemini',
        model: 'gemini-pro',
        brevity_level: 3
    },
    editingTopic: null
};

// Mock данные для разработки
const MOCK_DATA = {
    group: {
        id: 1,
        title: '📝 Мои заметки',
        telegram_group_id: -1001234567890
    },
    topics: [
        { id: 1, title: '💡 Идеи', description: 'Мысли, идеи, гипотезы для проектов', format_policy_text: '', is_active: true },
        { id: 2, title: '🛒 Покупки', description: 'Товары и услуги для покупки', format_policy_text: '', is_active: true },
        { id: 3, title: '📚 Книги', description: 'Книги для чтения и заметки', format_policy_text: '', is_active: true },
        { id: 4, title: '🎯 Цели', description: 'Цели и планы на будущее', format_policy_text: '', is_active: true }
    ],
    aiSettings: {
        provider: 'gemini',
        model: 'gemini-pro',
        brevity_level: 3
    }
};

// ============ Инициализация ============

document.addEventListener('DOMContentLoaded', () => {
    initTelegramWebApp();
    initTabs();
    initModal();
    loadData();
});

function initTelegramWebApp() {
    if (tg) {
        // Расширяем WebApp на весь экран
        tg.expand();

        // Получаем данные пользователя
        state.user = tg.initDataUnsafe?.user;

        // Настраиваем главную кнопку (пока скрыта)
        tg.MainButton.hide();

        // Готовы к работе
        tg.ready();

        console.log('Telegram WebApp initialized', state.user);
    } else {
        console.log('Running outside Telegram');
    }
}

function initTabs() {
    const tabs = document.querySelectorAll('.tab');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // Убираем active у всех табов
            tabs.forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

            // Активируем выбранный таб
            tab.classList.add('active');
            const tabId = tab.dataset.tab + '-tab';
            document.getElementById(tabId).classList.add('active');

            // Haptic feedback
            if (tg?.HapticFeedback) {
                tg.HapticFeedback.selectionChanged();
            }
        });
    });
}

function initModal() {
    const modal = document.getElementById('topic-modal');
    const closeBtn = document.getElementById('close-modal');
    const cancelBtn = document.getElementById('cancel-edit');
    const saveBtn = document.getElementById('save-topic');

    closeBtn.addEventListener('click', closeModal);
    cancelBtn.addEventListener('click', closeModal);
    saveBtn.addEventListener('click', saveTopic);

    // Закрытие по клику на фон
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeModal();
    });
}

// ============ Загрузка данных ============

async function loadData() {
    try {
        if (CONFIG.USE_MOCK) {
            // Используем mock-данные
            state.group = MOCK_DATA.group;
            state.topics = MOCK_DATA.topics;
            state.aiSettings = MOCK_DATA.aiSettings;
        } else {
            // Загружаем с сервера
            await Promise.all([
                loadTopics(),
                loadAISettings()
            ]);
        }

        renderGroupName();
        renderTopics();
        renderAISettings();
    } catch (error) {
        console.error('Error loading data:', error);
        showToast('Ошибка загрузки данных');
    }
}

async function loadTopics() {
    const response = await fetch(`${CONFIG.API_URL}/topics`, {
        headers: getAuthHeaders()
    });
    if (response.ok) {
        state.topics = await response.json();
    }
}

async function loadAISettings() {
    const response = await fetch(`${CONFIG.API_URL}/settings/ai`, {
        headers: getAuthHeaders()
    });
    if (response.ok) {
        state.aiSettings = await response.json();
    }
}

function getAuthHeaders() {
    const headers = {
        'Content-Type': 'application/json'
    };

    if (tg?.initData) {
        headers['X-Telegram-Init-Data'] = tg.initData;
    }

    return headers;
}

// ============ Рендеринг ============

function renderGroupName() {
    const groupNameEl = document.getElementById('group-name');
    if (state.group) {
        groupNameEl.textContent = state.group.title;
    } else {
        groupNameEl.textContent = 'Группа не подключена';
    }
}

function renderTopics() {
    const container = document.getElementById('topics-list');

    if (!state.topics.length) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📁</div>
                <p>Нет тем для отображения</p>
                <p>Создайте темы в группе и нажмите 🔄</p>
            </div>
        `;
        return;
    }

    container.innerHTML = state.topics.map(topic => `
        <div class="topic-card" data-topic-id="${topic.id}">
            <div class="topic-title">
                ${topic.title}
                ${topic.is_active ? '' : '<span class="topic-badge">Неактивна</span>'}
            </div>
            <div class="topic-description">
                ${topic.description || 'Нажмите для добавления описания...'}
            </div>
        </div>
    `).join('');

    // Добавляем обработчики кликов
    container.querySelectorAll('.topic-card').forEach(card => {
        card.addEventListener('click', () => {
            const topicId = parseInt(card.dataset.topicId);
            openTopicEditor(topicId);
        });
    });
}

function renderAISettings() {
    document.getElementById('ai-provider').value = state.aiSettings.provider;
    updateModelOptions(state.aiSettings.provider);
    document.getElementById('ai-model').value = state.aiSettings.model;
    document.getElementById('brevity-level').value = state.aiSettings.brevity_level;

    // Обработчик смены провайдера
    document.getElementById('ai-provider').addEventListener('change', (e) => {
        updateModelOptions(e.target.value);
    });

    // Обработчик сохранения
    document.getElementById('save-ai-settings').addEventListener('click', saveAISettings);
}

function updateModelOptions(provider) {
    const modelSelect = document.getElementById('ai-model');

    const models = {
        gemini: [
            { value: 'gemini-pro', label: 'Gemini Pro' },
            { value: 'gemini-flash', label: 'Gemini Flash' }
        ],
        openai: [
            { value: 'gpt-4', label: 'GPT-4' },
            { value: 'gpt-4-turbo', label: 'GPT-4 Turbo' },
            { value: 'gpt-3.5-turbo', label: 'GPT-3.5 Turbo' }
        ]
    };

    modelSelect.innerHTML = models[provider].map(m =>
        `<option value="${m.value}">${m.label}</option>`
    ).join('');
}

// ============ Модальное окно ============

function openTopicEditor(topicId) {
    const topic = state.topics.find(t => t.id === topicId);
    if (!topic) return;

    state.editingTopic = topic;

    document.getElementById('modal-title').textContent = topic.title;
    document.getElementById('topic-description').value = topic.description || '';
    document.getElementById('topic-format').value = topic.format_policy_text || '';

    document.getElementById('topic-modal').classList.remove('hidden');

    if (tg?.HapticFeedback) {
        tg.HapticFeedback.impactOccurred('light');
    }
}

function closeModal() {
    document.getElementById('topic-modal').classList.add('hidden');
    state.editingTopic = null;
}

// ============ Сохранение ============

async function saveTopic() {
    if (!state.editingTopic) return;

    const description = document.getElementById('topic-description').value;
    const formatPolicy = document.getElementById('topic-format').value;

    try {
        if (!CONFIG.USE_MOCK) {
            const response = await fetch(`${CONFIG.API_URL}/topics/${state.editingTopic.id}`, {
                method: 'PATCH',
                headers: getAuthHeaders(),
                body: JSON.stringify({
                    description,
                    format_policy_text: formatPolicy
                })
            });

            if (!response.ok) throw new Error('Failed to save');
        }

        // Обновляем локальное состояние
        const topic = state.topics.find(t => t.id === state.editingTopic.id);
        if (topic) {
            topic.description = description;
            topic.format_policy_text = formatPolicy;
        }

        renderTopics();
        closeModal();
        showToast('✓ Сохранено');

        if (tg?.HapticFeedback) {
            tg.HapticFeedback.notificationOccurred('success');
        }
    } catch (error) {
        console.error('Error saving topic:', error);
        showToast('Ошибка сохранения');

        if (tg?.HapticFeedback) {
            tg.HapticFeedback.notificationOccurred('error');
        }
    }
}

async function saveAISettings() {
    const settings = {
        provider: document.getElementById('ai-provider').value,
        model: document.getElementById('ai-model').value,
        brevity_level: parseInt(document.getElementById('brevity-level').value)
    };

    try {
        if (!CONFIG.USE_MOCK) {
            const response = await fetch(`${CONFIG.API_URL}/settings/ai`, {
                method: 'PATCH',
                headers: getAuthHeaders(),
                body: JSON.stringify(settings)
            });

            if (!response.ok) throw new Error('Failed to save');
        }

        state.aiSettings = settings;
        showToast('✓ Настройки сохранены');

        if (tg?.HapticFeedback) {
            tg.HapticFeedback.notificationOccurred('success');
        }
    } catch (error) {
        console.error('Error saving AI settings:', error);
        showToast('Ошибка сохранения');

        if (tg?.HapticFeedback) {
            tg.HapticFeedback.notificationOccurred('error');
        }
    }
}

// ============ Синхронизация тем ============

document.getElementById('sync-topics').addEventListener('click', async () => {
    const button = document.getElementById('sync-topics');
    button.style.animation = 'spin 1s linear infinite';

    try {
        if (!CONFIG.USE_MOCK) {
            await fetch(`${CONFIG.API_URL}/topics/sync`, {
                method: 'POST',
                headers: getAuthHeaders()
            });
            await loadTopics();
        }

        renderTopics();
        showToast('✓ Темы синхронизированы');
    } catch (error) {
        showToast('Ошибка синхронизации');
    } finally {
        button.style.animation = '';
    }
});

// ============ Утилиты ============

function showToast(message) {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.classList.remove('hidden');

    setTimeout(() => {
        toast.classList.add('hidden');
    }, 2000);
}

// Добавляем анимацию вращения
const style = document.createElement('style');
style.textContent = `
    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
`;
document.head.appendChild(style);
