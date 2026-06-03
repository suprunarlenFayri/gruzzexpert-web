// Глобальные уведомления (обёртка с локальным временем — в base.html)
window.showNotification = function(title, body) {
    if ("Notification" in window && Notification.permission === "granted") {
        new Notification(title, { body: body });
    }
};

if ("Notification" in window && Notification.permission === "default") {
    Notification.requestPermission();
}

/** Текст превью в сайдбаре: подпись к вложениям, если текста нет */
function sidebarPreviewSnippet(msg) {
    if (!msg) return '';

    const candidates = [msg.text, msg.message, msg.body];
    for (const value of candidates) {
        if (value == null) continue;
        const raw = String(value).trim();
        if (!raw || raw === 'undefined' || raw === 'null') continue;
        return raw.length > 40 ? `${raw.slice(0, 37)}…` : raw;
    }

    const list = msg.attachments;
    if (list && list.length > 0) {
        const hasImage = list.some((a) => {
            const ft = String(a.file_type || '').toLowerCase();
            if (ft === 'image') return true;
            const name = String(a.filename || a.name || a.file_path || '');
            return /\.(jpe?g|png|gif|webp|bmp|svg)$/i.test(name);
        });
        return hasImage ? '🖼 Фото' : '📎 Файл';
    }

    return '';
}

function formatSidebarMessageTime(msg) {
    const rawTime = msg?.created_at || msg?.time;
    if (!rawTime) return '';
    if (typeof window.formatLocalTimeFromServer === 'function') {
        return window.formatLocalTimeFromServer(rawTime);
    }
    if (typeof window.formatUtcToLocalTime === 'function') {
        return window.formatUtcToLocalTime(rawTime);
    }
    const date = new Date(rawTime);
    if (Number.isNaN(date.getTime())) return String(rawTime);
    return date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
}

// Обновление превью в сайдбаре
function updateSidebarPreview(msg) {
    const chatId = msg?.chat_id;
    if (chatId == null) return;

    const chatItem = document.querySelector(`.chat-item[data-chat-id="${chatId}"]`);

    if (chatItem) {
        const preview = chatItem.querySelector('.chat-preview');
        if (preview) {
            const snippet = sidebarPreviewSnippet(msg);
            const sender = msg.sender_name || msg.author_name || 'Гость';
            preview.textContent = snippet ? `${sender}: ${snippet}` : sender;
        }

        const timeSpan = chatItem.querySelector('.chat-item-time');
        if (timeSpan) {
            const localTime = formatSidebarMessageTime(msg);
            if (localTime) timeSpan.textContent = localTime;
        }

        const authorId = msg.author_id ?? msg.sender_id;
        const currentUserId = parseInt(document.body.dataset.userId, 10)
            || parseInt(window.ChatConfig?.currentUserId, 10)
            || parseInt(window.currentUserId, 10);
        const skipUnreadBadge =
            authorId != null &&
            currentUserId &&
            String(authorId) === String(currentUserId);

        const activeChatId = window.currentChatId
            || document.querySelector('.chat-container[data-chat-id]')?.dataset?.chatId;

        if (String(activeChatId) !== String(chatId) && !skipUnreadBadge) {
            let badge = chatItem.querySelector('.chat-unread-badge');
            if (!badge) {
                badge = document.createElement('span');
                badge.className = 'chat-unread-badge';
                chatItem.querySelector('.chat-item-meta')?.appendChild(badge);
            }
            let count = parseInt(badge.textContent, 10) || 0;
            count += 1;
            badge.textContent = count > 99 ? '99+' : String(count);
            badge.style.display = 'flex';
        }

        const parent = chatItem.parentElement;
        if (parent) {
            parent.prepend(chatItem);
        }

        chatItem.style.animation = 'highlightChat 0.5s ease';
        setTimeout(() => {
            chatItem.style.animation = '';
        }, 500);
    }
}

window.updateSidebarPreview = updateSidebarPreview;

window.clearChatUnreadBadge = function(chatId) {
    const chatItem = document.querySelector(`.chat-item[data-chat-id="${chatId}"]`);
    if (!chatItem) return;
    const badge = chatItem.querySelector('.chat-unread-badge');
    if (badge) {
        badge.remove();
    }
};

function bindRealtimeHandlers() {
    const socket = window.socket;
    if (!socket || socket.__realtimeBound) return;
    socket.__realtimeBound = true;

    socket.on('connect', () => {
        console.log('✅ Глобальная связь установлена');
    });

    socket.on('global_update', (data) => {
        console.log('⚡ Получено обновление:', data.type, data.payload);

        switch (data.type) {
            case 'new_task':
                if (typeof window.handleNewTask === 'function') {
                    window.handleNewTask(data.payload);
                }
                window.showNotification('Новая заявка!', data.payload.title, data.payload.created_at);
                break;

            case 'task_updated':
                if (typeof window.handleTaskUpdate === 'function') {
                    window.handleTaskUpdate(data.payload);
                }
                break;

            case 'task_deleted':
                if (typeof window.handleTaskDelete === 'function') {
                    window.handleTaskDelete(data.payload);
                }
                break;

            case 'task_cancelled':
                if (typeof window.handleTaskCancelled === 'function') {
                    window.handleTaskCancelled(data.payload);
                }
                break;

            case 'new_message':
                if (typeof window.handleIncomingMessageNotification === 'function') {
                    window.handleIncomingMessageNotification(data.payload);
                } else {
                    updateSidebarPreview(data.payload);
                }
                break;

            case 'auto_chat_created':
                if (typeof window.handleAutoChatCreated === 'function') {
                    window.handleAutoChatCreated(data.payload);
                }
                break;
        }
    });

    socket.on('chat_typing', function(data) {
        if (!data || data.chat_id == null) return;
        if (window.ChatListUI && typeof window.ChatListUI.setChatTyping === 'function') {
            window.ChatListUI.setChatTyping(data.chat_id, !!data.is_typing, data.user_name);
        }
    });

    socket.on('user_notification', function(data) {
        if (typeof window.handleTaskNotification === 'function') {
            window.handleTaskNotification(data);
        }
    });

    socket.on('task_notification', function(data) {
        if (typeof window.handleTaskNotification === 'function') {
            window.handleTaskNotification(data);
        }
    });

    socket.on('new_profile_moderation', function() {
        if (typeof window.updateModerationBadge === 'function') {
            window.updateModerationBadge();
        }
    });

    socket.on('receive_message', function(payload) {
        const activeChatId = window.currentChatId
            || document.querySelector('.chat-container[data-chat-id]')?.dataset?.chatId;
        if (String(activeChatId) !== String(payload.chat_id || '')) {
            if (typeof window.handleIncomingMessageNotification === 'function') {
                window.handleIncomingMessageNotification(payload);
            }
        }
    });

    socket.on('group_updated', function(data) {
        const activeChatMatch = window.location.pathname.match(/\/chat\/(\d+)/);
        const activeChatId = activeChatMatch
            ? parseInt(activeChatMatch[1], 10)
            : (window.ChatConfig?.chatId ? parseInt(window.ChatConfig.chatId, 10) : null);

        if (activeChatId == null || parseInt(data.chat_id, 10) !== activeChatId) return;

        const modal = document.getElementById('groupSettingsModal');
        if (modal && modal.style.display === 'flex' && typeof window.openGroupSettingsModal === 'function') {
            openGroupSettingsModal(data.chat_id);
        } else if (typeof window.handleGroupUpdated === 'function') {
            handleGroupUpdated(data);
        } else {
            window.location.reload();
        }
    });

    socket.on('force_reload_chats', function(data) {
        const currentUserId = parseInt(document.body.dataset.userId, 10)
            || parseInt(window.ChatConfig?.currentUserId, 10)
            || parseInt(window.currentUserId, 10);

        if (currentUserId && parseInt(data.user_id, 10) === currentUserId) {
            console.log('🔄 Состав ваших групп изменился, обновляем интерфейс...');
            window.location.reload();
        }
    });
}

document.addEventListener('socketReady', bindRealtimeHandlers);
if (window.socket) {
    bindRealtimeHandlers();
}

/** Удаление карточек заявки (список, «Мои заявки», сайдбар). list.html может переопределить. */
if (typeof window.handleTaskDelete !== 'function') {
    window.handleTaskDelete = function(task) {
        const taskId = task && (task.id || task.task_id);
        if (!taskId) return;
        const idStr = String(taskId);
        document.querySelectorAll('.task-card').forEach(function(card) {
            const cid = card.dataset.id || card.dataset.taskId;
            if (cid && String(cid) === idStr) card.remove();
        });
        document.querySelectorAll('.task-mini-card').forEach(function(card) {
            const onclick = card.getAttribute('onclick') || '';
            if (onclick.indexOf('(' + idStr + ')') !== -1 || onclick.indexOf('(' + taskId + ')') !== -1) {
                card.remove();
            }
        });
    };
}

if (typeof window.handleTaskCancelled !== 'function') {
    window.handleTaskCancelled = function(payload) {
        const msg = (payload && payload.message) || 'Внимание! Заявка отменена диспетчером.';
        if (typeof window.showToast === 'function') {
            window.showToast(msg, 'error');
        }
        if (payload && typeof window.handleTaskDelete === 'function') {
            window.handleTaskDelete(payload);
        }
    };
}
