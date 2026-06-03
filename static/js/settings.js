(function () {
    'use strict';

    window.USER_SETTINGS = window.USER_SETTINGS || {};
    let muteCountdownTimer = null;

    window.isTasksMuted = function () {
        if (!window.IS_WORKER) return false;
        const until = window.TASKS_MUTED_UNTIL;
        if (!until) return false;
        const end = new Date(until);
        if (Number.isNaN(end.getTime())) return false;
        return Date.now() < end.getTime();
    };

    window.isChatSoundEnabled = function () {
        return window.USER_SETTINGS.chat_sound_enabled !== false;
    };

    window.shouldSendMessageOnEnter = function (e) {
        const sendOnEnter = window.USER_SETTINGS.send_by_enter !== false
            && window.USER_SETTINGS.chat_send_on_enter !== false;
        if (sendOnEnter) {
            return e.key === 'Enter' && !e.shiftKey;
        }
        return e.key === 'Enter' && (e.ctrlKey || e.metaKey);
    };

    window.isTaskNotificationEnabled = function (kind) {
        if (window.IS_WORKER && window.isTasksMuted()) {
            return false;
        }
        const s = window.USER_SETTINGS || {};
        if (kind === 'new_task' || kind === 'task_reopened') {
            return s.notify_new_tasks !== false;
        }
        if (kind === 'worker_status' || kind === 'task_updated') {
            return s.notify_status_changes !== false;
        }
        if (kind === 'route_reminder' || kind === 'route_nudge' || kind === 'route_alarm'
            || kind === 'route_removed') {
            return s.notify_system_alerts !== false;
        }
        return true;
    };

    function formatLocalDateTime(iso) {
        const date = new Date(iso);
        if (Number.isNaN(date.getTime())) return '—';
        return date.toLocaleString('ru-RU', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    }

    function formatCountdown(ms) {
        if (ms <= 0) return '00:00:00';
        const totalSec = Math.floor(ms / 1000);
        const h = Math.floor(totalSec / 3600);
        const m = Math.floor((totalSec % 3600) / 60);
        const s = totalSec % 60;
        return [h, m, s].map(function (n) { return String(n).padStart(2, '0'); }).join(':');
    }

    function updateMuteUi() {
        const statusEl = document.getElementById('tasks-mute-status');
        const labelEl = document.getElementById('tasks-mute-until-label');
        const countdownEl = document.getElementById('tasks-mute-countdown');
        const toggle = document.getElementById('tasks-sleep-toggle');
        const active = window.isTasksMuted();

        window.TASKS_MUTED_ACTIVE = active;

        if (toggle) {
            toggle.checked = active;
        }

        if (!statusEl || !labelEl || !countdownEl) {
            return;
        }

        if (!active || !window.TASKS_MUTED_UNTIL) {
            statusEl.hidden = true;
            countdownEl.hidden = true;
            countdownEl.textContent = '';
            if (muteCountdownTimer) {
                clearInterval(muteCountdownTimer);
                muteCountdownTimer = null;
            }
            return;
        }

        statusEl.hidden = false;
        countdownEl.hidden = false;
        labelEl.textContent = formatLocalDateTime(window.TASKS_MUTED_UNTIL);

        function tick() {
            const end = new Date(window.TASKS_MUTED_UNTIL).getTime();
            const left = end - Date.now();
            if (left <= 0) {
                window.TASKS_MUTED_UNTIL = null;
                window.TASKS_MUTED_ACTIVE = false;
                if (toggle) toggle.checked = false;
                statusEl.hidden = true;
                countdownEl.hidden = true;
                clearInterval(muteCountdownTimer);
                muteCountdownTimer = null;
                return;
            }
            countdownEl.textContent = 'Осталось: ' + formatCountdown(left);
        }

        tick();
        if (muteCountdownTimer) clearInterval(muteCountdownTimer);
        muteCountdownTimer = setInterval(tick, 1000);
    }

    function applySaveResponse(data) {
        if (data.settings) {
            window.USER_SETTINGS = data.settings;
        }
        if (typeof data.tasks_muted_until !== 'undefined') {
            window.TASKS_MUTED_UNTIL = data.tasks_muted_until;
        }
        if (typeof data.tasks_muted_active !== 'undefined') {
            window.TASKS_MUTED_ACTIVE = data.tasks_muted_active;
        }
        updateMuteUi();
    }

    async function saveSetting(key, value) {
        const res = await fetch('/api/save-settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ key, value }),
        });
        const data = await res.json();
        if (!res.ok || !data.ok) {
            throw new Error(data.error || 'Ошибка сохранения');
        }
        applySaveResponse(data);
        if (typeof window.showToast === 'function') {
            window.showToast('Настройки сохранены', 'success');
        }
        return data;
    }

    function bindSettingsPage() {
        const root = document.getElementById('settings-page');
        if (!root) return;

        if (window.INITIAL_TASKS_MUTED_UNTIL) {
            window.TASKS_MUTED_UNTIL = window.INITIAL_TASKS_MUTED_UNTIL;
        }
        updateMuteUi();

        root.querySelectorAll('[data-setting-key]').forEach(function (el) {
            if (el.dataset.bound === '1') return;
            el.dataset.bound = '1';

            el.addEventListener('change', async function () {
                let value;
                if (el.type === 'checkbox') {
                    value = el.checked;
                } else if (el.type === 'radio') {
                    if (!el.checked) return;
                    value = el.value === '1' || el.value === 'true';
                } else if (el.dataset.settingKey === 'send_by_enter') {
                    value = el.value === '1' || el.value === 'true';
                } else {
                    value = el.value;
                }

                const prevChecked = el.type === 'checkbox' ? !el.checked : null;
                const b2bWrap = el.closest('.b2b-select-wrapper');
                el.disabled = true;
                if (b2bWrap) b2bWrap.classList.add('is-disabled');
                try {
                    await saveSetting(el.dataset.settingKey, value);
                } catch (err) {
                    if (el.type === 'checkbox' && prevChecked !== null) {
                        el.checked = prevChecked;
                    }
                    updateMuteUi();
                    if (typeof window.showToast === 'function') {
                        window.showToast(err.message || 'Ошибка сохранения', 'error');
                    }
                } finally {
                    el.disabled = false;
                    if (b2bWrap) b2bWrap.classList.remove('is-disabled');
                }
            });
        });
    }

    document.addEventListener('DOMContentLoaded', bindSettingsPage);
    window.saveUserSetting = saveSetting;
    window.updateTasksMuteUi = updateMuteUi;

    document.addEventListener('DOMContentLoaded', function () {
        if (document.getElementById('settings-page') && typeof refreshIcons === 'function') {
            refreshIcons();
        }
    });
})();
