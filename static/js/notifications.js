(function () {
    'use strict';

    let alarmInterval = null;

    function getActiveChatId() {
        const match = window.location.pathname.match(/\/chat\/(\d+)/);
        if (match) return match[1];
        return window.currentChatId
            || document.querySelector('.chat-container[data-chat-id]')?.dataset?.chatId
            || null;
    }

    function playTone(freq, duration, volume) {
        try {
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.type = 'sine';
            osc.frequency.value = freq;
            gain.gain.value = volume || 0.08;
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.start();
            osc.stop(ctx.currentTime + duration);
        } catch (e) { /* ignore */ }
    }

    window.playMessageSound = function () {
        playTone(880, 0.06, 0.06);
        setTimeout(() => playTone(1175, 0.05, 0.05), 50);
    };

    window.playAlarmSound = function () {
        if (alarmInterval) return;
        const tick = () => {
            playTone(660, 0.25, 0.15);
            setTimeout(() => playTone(880, 0.25, 0.15), 280);
        };
        tick();
        alarmInterval = setInterval(tick, 1400);
    };

    window.stopAlarmSound = function () {
        if (alarmInterval) {
            clearInterval(alarmInterval);
            alarmInterval = null;
        }
    };

    function ensurePushContainer() {
        let el = document.getElementById('gruzz-push-container');
        if (!el) {
            el = document.createElement('div');
            el.id = 'gruzz-push-container';
            el.className = 'gruzz-push-container';
            document.body.appendChild(el);
        }
        return el;
    }

    window.showMessagePushToast = function (payload) {
        const chatId = payload.chat_id;
        const sender = payload.sender_name || payload.author_name || 'Сообщение';
        const text = (payload.message || payload.text || '').trim() || 'Вложение';
        const container = ensurePushContainer();
        const toast = document.createElement('button');
        toast.type = 'button';
        toast.className = 'gruzz-push-toast';
        toast.innerHTML = `
            <span class="gruzz-push-title">${escapeHtml(sender)}</span>
            <span class="gruzz-push-body">${escapeHtml(text.length > 80 ? text.slice(0, 77) + '…' : text)}</span>
        `;
        toast.addEventListener('click', () => {
            toast.remove();
            if (typeof window.goToChat === 'function') {
                window.goToChat(chatId);
            } else {
                window.location.href = '/chat/' + chatId;
            }
        });
        container.appendChild(toast);
        setTimeout(() => {
            toast.classList.add('is-leaving');
            setTimeout(() => toast.remove(), 300);
        }, 6000);
    };

    window.showLoginAttemptAlert = function (data) {
        const container = ensurePushContainer();
        const wrap = document.createElement('div');
        wrap.className = 'gruzz-push-toast gruzz-push-toast--security';
        wrap.innerHTML = `
            <span class="gruzz-push-title">${escapeHtml(data.title || 'Новый вход')}</span>
            <span class="gruzz-push-body">${escapeHtml(data.body || data.message || '')}</span>
            <button type="button" class="gruzz-push-block-btn">Заблокировать сессию</button>
        `;
        const blockBtn = wrap.querySelector('.gruzz-push-block-btn');
        if (blockBtn) {
            blockBtn.addEventListener('click', async function (e) {
                e.stopPropagation();
                blockBtn.disabled = true;
                try {
                    const res = await fetch('/api/security/block-login-attempt', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                        credentials: 'same-origin',
                        body: JSON.stringify({ attempt_id: data.attempt_id || data.attempt_token }),
                    });
                    const json = await res.json();
                    if (!res.ok || !json.ok) throw new Error(json.error || 'Ошибка');
                    if (typeof window.showToast === 'function') {
                        window.showToast('Попытка входа заблокирована', 'success');
                    }
                    wrap.remove();
                } catch (err) {
                    blockBtn.disabled = false;
                    if (typeof window.showToast === 'function') {
                        window.showToast(err.message || 'Не удалось заблокировать', 'error');
                    }
                }
            });
        }
        container.appendChild(wrap);
        setTimeout(function () {
            wrap.classList.add('is-leaving');
            setTimeout(function () { wrap.remove(); }, 300);
        }, 30000);
        window.playMessageSound();
    };

    window.showUserPushToast = function (data) {
        const container = ensurePushContainer();
        const toast = document.createElement('button');
        toast.type = 'button';
        toast.className = 'gruzz-push-toast gruzz-push-toast--task';
        toast.innerHTML = `
            <span class="gruzz-push-title">${escapeHtml(data.title || 'Уведомление')}</span>
            <span class="gruzz-push-body">${escapeHtml(data.body || '')}</span>
        `;
        if (data.task_id) {
            toast.addEventListener('click', () => {
                toast.remove();
                if (typeof window.openTaskDetail === 'function') {
                    window.openTaskDetail(data.task_id);
                }
            });
        }
        container.appendChild(toast);
        setTimeout(() => {
            toast.classList.add('is-leaving');
            setTimeout(() => toast.remove(), 300);
        }, 8000);
    };

    window.handleIncomingMessageNotification = function (payload) {
        const authorId = payload.author_id ?? payload.sender_id;
        const myId = parseInt(window.currentUserId || document.body.dataset.userId, 10);
        if (authorId != null && myId && String(authorId) === String(myId)) return;

        const activeChatId = getActiveChatId();
        const isActiveChat = activeChatId && String(activeChatId) === String(payload.chat_id);

        if (typeof window.updateSidebarPreview === 'function') {
            window.updateSidebarPreview(payload);
        }

        if (!isActiveChat) {
            if (typeof window.isChatSoundEnabled === 'function' && !window.isChatSoundEnabled()) {
                window.showMessagePushToast(payload);
                return;
            }
            window.playMessageSound();
            window.showMessagePushToast(payload);
        }
    };

    window.handleUserNotification = function (data) {
        window.handleTaskNotification(data);
    };

    window.handleTaskNotification = function (data) {
        if (!data) return;

        if (data.kind === 'login_attempt') {
            window.showLoginAttemptAlert(data);
            return;
        }

        if (data.kind === 'security_alert') {
            window.playMessageSound();
            window.showUserPushToast(data);
            if (typeof window.showToast === 'function') {
                const msg = [data.title, data.body].filter(Boolean).join(': ');
                if (msg) window.showToast(msg, 'error');
            }
            return;
        }

        const myId = parseInt(window.currentUserId || document.body.dataset.userId, 10);
        if (data.actor_id && myId && parseInt(data.actor_id, 10) === myId) {
            return;
        }

        if (typeof window.isTaskNotificationEnabled === 'function'
            && !window.isTaskNotificationEnabled(data.kind)) {
            return;
        }

        const wsId = window.CURRENT_USER_WORKSPACE_ID;
        if (
            data.workspace_id != null && wsId != null
            && parseInt(data.workspace_id, 10) !== parseInt(wsId, 10)
        ) {
            return;
        }

        if (data.alarm || data.kind === 'task_cancelled') {
            window.playAlarmSound();
        } else if (data.kind !== 'task_updated') {
            window.playMessageSound();
        }

        window.showUserPushToast(data);

        const payload = data.payload;
        if (payload) {
            if (data.kind === 'new_task' && typeof window.handleNewTask === 'function') {
                window.handleNewTask(payload);
            }
            if (data.kind === 'task_reopened') {
                const tid = payload && (payload.id || payload.task_id);
                const hasCard = tid && typeof window.findTaskCardById === 'function' && window.findTaskCardById(tid);
                if (hasCard && typeof window.handleTaskUpdate === 'function') {
                    window.handleTaskUpdate(payload);
                } else if (typeof window.handleNewTask === 'function') {
                    window.handleNewTask(payload);
                }
            }
            if ((data.kind === 'task_updated' || data.kind === 'worker_status') && typeof window.handleTaskUpdate === 'function') {
                window.handleTaskUpdate(payload);
            }
            if (data.kind === 'task_cancelled' && typeof window.handleTaskCancelled === 'function') {
                window.handleTaskCancelled(payload);
            }
        }

        if (typeof window.showToast === 'function' && data.kind !== 'task_updated') {
            const msg = [data.title, data.body].filter(Boolean).join(': ');
            if (msg) window.showToast(msg, data.alarm ? 'error' : 'info');
        }
    };

    function escapeHtml(text) {
        if (!text) return '';
        return String(text)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }
})();
