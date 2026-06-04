(function () {
    'use strict';

    const panel = document.getElementById('workspace-admin-panel');
    const overlay = document.getElementById('workspace-admin-overlay');
    const body = document.getElementById('workspace-admin-body');
    const titleEl = document.getElementById('workspace-admin-title');
    const closeBtn = document.getElementById('workspace-admin-close');

    let activeWorkspaceId = null;
    let loading = false;
    let subscriptionPicker = null;

    function escapeHtml(text) {
        if (text == null) return '';
        return String(text)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function openPanel() {
        if (panel) panel.classList.add('open');
        if (overlay) overlay.classList.add('open');
        document.body.style.overflow = 'hidden';
    }

    function closePanel() {
        if (panel) panel.classList.remove('open');
        if (overlay) overlay.classList.remove('open');
        document.body.style.overflow = '';
        activeWorkspaceId = null;
        subscriptionPicker = null;
    }

    function getSubscriptionExpiresValue() {
        const root = document.getElementById('ws-subscription-date-picker');
        if (root && root.__gruzzPicker && typeof root.__gruzzPicker.getValue === 'function') {
            return root.__gruzzPicker.getValue() || '';
        }
        const hidden = root && root.querySelector('input[type="hidden"]');
        return hidden ? (hidden.value || '') : '';
    }

    function initSubscriptionPicker(iso) {
        const root = document.getElementById('ws-subscription-date-picker');
        if (!root || !window.GruzzDatePicker) return null;
        delete root.__gruzzPicker;
        const hidden = root.querySelector('input[type="hidden"]');
        if (hidden) hidden.value = iso || '';
        const display = root.querySelector('.gruzz-date-display');
        if (display) {
            window.GruzzDatePicker.updateDisplay(display, iso || '', 'Без ограничения');
        }
        const nowYear = new Date().getFullYear();
        subscriptionPicker = window.GruzzDatePicker.init(root, {
            placeholder: 'Без ограничения',
            changeMonth: true,
            changeYear: true,
            yearRange: [nowYear, nowYear + 20],
            initialValue: iso || '',
        });
        return subscriptionPicker;
    }

    function renderAdminSessions(admin, allowTerminate) {
        const sessions = admin.sessions || [];
        if (!sessions.length) {
            return '<div class="ws-admin-no-sessions">Нет активных сеансов</div>';
        }
        return sessions.map(function (s) {
            const platform = escapeHtml(s.platform || 'Веб-браузер');
            const device = escapeHtml(s.device_name || 'Устройство');
            const ip = escapeHtml(s.location || s.ip_address || '—');
            const last = escapeHtml(s.last_active || '—');
            const legacy = s.is_legacy_device;
            const terminateBtn = legacy || !allowTerminate
                ? '<span class="ws-session-legacy-hint">История устройства</span>'
                : `<button type="button" class="ws-btn-terminate" data-user-id="${admin.id}" data-session-id="${s.id}">Завершить сеанс</button>`;
            return `
                <div class="ws-session-row">
                    <div class="ws-session-info">
                        <span class="ws-session-platform-badge">${platform}</span>
                        <div class="ws-session-device">${device}</div>
                        <div class="ws-session-meta">IP: ${ip}</div>
                        <div class="ws-session-meta ws-session-time">${last}</div>
                    </div>
                    ${terminateBtn}
                </div>
            `;
        }).join('');
    }

    function panelPermissions(ws) {
        if (ws && ws.permissions) return ws.permissions;
        return window.WORKSPACE_ADMIN_DEFAULT_PERMS || {};
    }

    function renderPanel(ws) {
        if (!body || !ws) return;
        titleEl.textContent = ws.name || 'Пространство';

        const perms = panelPermissions(ws);
        const readonly = !!perms.is_readonly_panel;
        const canExtend = !!perms.can_extend_subscription && !readonly;
        const canTerminate = !!perms.can_terminate_sessions && !readonly;
        const canEditAdminLimit = !!perms.can_edit_admin_limit;
        const isFlagship = !!perms.is_flagship_workspace || !!ws.is_flagship_workspace || !!ws.admin_limit_unlimited;

        const stats = ws.stats || {};
        const adminLimitLabel = isFlagship
            ? '∞'
            : String(stats.admin_limit ?? ws.admin_limit ?? 5);
        const adminsHtml = (ws.admins || []).map(function (admin) {
            const avatar = admin.avatar_url
                ? `<img src="${escapeHtml(admin.avatar_url)}" alt="">`
                : `<span>${escapeHtml((admin.name || '?').charAt(0).toUpperCase())}</span>`;
            const tagLine = admin.tag_display
                ? `<span class="ws-admin-tag">${escapeHtml(admin.tag_display)}</span>`
                : '';
            return `
                <div class="ws-admin-card">
                    <div class="ws-admin-head">
                        <div class="ws-admin-avatar">${avatar}</div>
                        <div class="ws-admin-head-text">
                            <div class="ws-admin-name">${escapeHtml(admin.name)}</div>
                            ${tagLine}
                        </div>
                    </div>
                    <div class="ws-admin-sessions">${renderAdminSessions(admin, canTerminate)}</div>
                </div>
            `;
        }).join('') || '<p class="ws-empty-admins">Админский состав пуст</p>';

        const expiresIso = ws.expires_at || '';
        const expiresPlaceholder = ws.expires_at_display
            ? escapeHtml(ws.expires_at_display)
            : 'Без ограничения';

        const subscriptionBlock = readonly
            ? `
            <div class="ws-panel-section">
                <h4>Подписка</h4>
                <p class="ws-readonly-expires">Срок действия: <strong>${expiresIso ? expiresPlaceholder : 'без ограничения'}</strong></p>
                <p class="ws-hint">Изменение подписки доступно только создателю платформы и директору флагманского пространства.</p>
            </div>`
            : `
            <div class="ws-panel-section">
                <h4>Управление подпиской</h4>
                <form id="workspace-extend-form" class="ws-extend-form">
                    <label class="ws-extend-label">
                        Срок действия подписки
                        <div class="gruzz-date-picker ws-subscription-picker" id="ws-subscription-date-picker" data-gruzz-date-picker data-placeholder="Без ограничения">
                            <input type="hidden" name="expires_at" value="${escapeHtml(expiresIso)}">
                            <button type="button" class="gruzz-date-trigger filter-date-trigger">
                                <i data-lucide="calendar"></i>
                                <span class="gruzz-date-display${expiresIso ? '' : ' is-placeholder'}">${expiresIso ? expiresPlaceholder : 'Без ограничения'}</span>
                            </button>
                            <div class="custom-datepicker gruzz-date-dropdown" style="display: none;"></div>
                        </div>
                    </label>
                    <div class="ws-extend-actions">
                        <button type="button" class="ws-btn-secondary" id="ws-clear-subscription-date">Сбросить дату</button>
                        <button type="submit" class="ws-btn-primary">Сохранить</button>
                    </div>
                    <p class="ws-hint">«Сбросить дату» — подписка без ограничения по сроку</p>
                </form>
            </div>`;

        const adminLimitBlock = isFlagship
            ? `
            <div class="ws-panel-section">
                <h4>Лимит админ-состава</h4>
                <p class="ws-readonly-expires">Флагманское пространство: <strong>без лимита</strong></p>
            </div>`
            : canEditAdminLimit
            ? `
            <div class="ws-panel-section">
                <h4>Лимит админ-состава</h4>
                <form id="workspace-admin-limit-form" class="ws-extend-form">
                    <label class="ws-extend-label">
                        Максимум админов / диспетчеров
                        <input type="number" name="admin_limit" min="1" max="100" value="${escapeHtml(String(ws.admin_limit ?? stats.admin_limit ?? 5))}" required class="ws-admin-limit-input">
                    </label>
                    <div class="ws-extend-actions">
                        <button type="submit" class="ws-btn-primary">Сохранить лимит</button>
                    </div>
                    <p class="ws-hint">Текущий состав: ${stats.admins ?? 0}. После сохранения в БД лимит применится сразу.</p>
                </form>
            </div>`
            : `
            <div class="ws-panel-section">
                <h4>Лимит админ-состава</h4>
                <p class="ws-readonly-expires">Лимит: <strong>${adminLimitLabel}</strong></p>
            </div>`;

        body.innerHTML = `
            ${subscriptionBlock}
            ${adminLimitBlock}
            <div class="ws-panel-stats">
                <div class="ws-panel-stat">Исполнителей: <strong>${stats.workers ?? 0}</strong></div>
                <div class="ws-panel-stat">Клиентов: <strong>${stats.clients ?? 0}</strong></div>
                <div class="ws-panel-stat">Админов: <strong>${stats.admins ?? 0}</strong> / ${adminLimitLabel}</div>
            </div>
            <div class="ws-panel-section ws-panel-section-admins">
                <h4>Админский состав</h4>
                <div class="ws-admins-list">${adminsHtml}</div>
            </div>
        `;

        if (!readonly) {
            const extendForm = document.getElementById('workspace-extend-form');
            if (extendForm) extendForm.addEventListener('submit', onExtendSubmit);
            const limitForm = document.getElementById('workspace-admin-limit-form');
            if (limitForm) limitForm.addEventListener('submit', onAdminLimitSubmit);
            const clearBtn = document.getElementById('ws-clear-subscription-date');
            if (clearBtn) {
                clearBtn.addEventListener('click', function () {
                    if (subscriptionPicker && subscriptionPicker.setValue) {
                        subscriptionPicker.setValue('');
                    } else {
                        initSubscriptionPicker('');
                    }
                });
            }
            initSubscriptionPicker(expiresIso);
        } else {
            subscriptionPicker = null;
        }
        body.querySelectorAll('.ws-btn-terminate').forEach(function (btn) {
            btn.addEventListener('click', onTerminateSession);
        });
        if (typeof refreshIcons === 'function') refreshIcons();
    }

    async function loadWorkspace(wsId) {
        if (loading) return;
        loading = true;
        body.innerHTML = '<div class="ws-panel-loading">Загрузка…</div>';
        openPanel();
        try {
            const res = await fetch(`/api/admin/workspaces/${wsId}`, {
                headers: { Accept: 'application/json; charset=utf-8', 'X-Requested-With': 'XMLHttpRequest' },
            });
            const data = await res.json();
            if (!res.ok || data.status !== 'success') {
                throw new Error((data && data.error) || 'Ошибка загрузки');
            }
            activeWorkspaceId = wsId;
            renderPanel(data.workspace);
        } catch (err) {
            body.innerHTML = `<div class="ws-panel-error">${escapeHtml(err.message || 'Ошибка сети')}</div>`;
        } finally {
            loading = false;
        }
    }

    async function onAdminLimitSubmit(e) {
        e.preventDefault();
        if (!activeWorkspaceId) return;
        const input = document.querySelector('#workspace-admin-limit-form input[name="admin_limit"]');
        const adminLimit = input ? parseInt(input.value, 10) : NaN;
        if (!adminLimit || adminLimit < 1) {
            alert('Укажите лимит не менее 1');
            return;
        }
        try {
            const res = await fetch(`/api/admin/workspaces/${activeWorkspaceId}/admin-limit`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json; charset=utf-8',
                    Accept: 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                },
                body: JSON.stringify({ admin_limit: adminLimit }),
            });
            const data = await res.json();
            if (!res.ok || data.status !== 'success') {
                throw new Error((data && data.error) || 'Не удалось сохранить лимит');
            }
            renderPanel(data.workspace);
            updateCardFromWorkspace(activeWorkspaceId, data.workspace);
            if (typeof window.showToast === 'function') {
                window.showToast('Лимит админ-состава обновлён', 'success');
            }
        } catch (err) {
            alert(err.message || 'Ошибка сохранения');
        }
    }

    async function onExtendSubmit(e) {
        e.preventDefault();
        if (!activeWorkspaceId) return;
        const expiresAt = getSubscriptionExpiresValue();
        try {
            const res = await fetch(`/api/admin/workspaces/${activeWorkspaceId}/extend`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json; charset=utf-8',
                    Accept: 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                },
                body: JSON.stringify({ expires_at: expiresAt || null }),
            });
            const data = await res.json();
            if (!res.ok || data.status !== 'success') {
                throw new Error((data && data.error) || 'Не удалось сохранить');
            }
            renderPanel(data.workspace);
            updateCardFromWorkspace(activeWorkspaceId, data.workspace);
            if (typeof window.showToast === 'function') {
                window.showToast('Подписка обновлена', 'success');
            }
        } catch (err) {
            alert(err.message || 'Ошибка сохранения');
        }
    }

    async function onTerminateSession(e) {
        const btn = e.currentTarget;
        const userId = btn.dataset.userId;
        const sessionId = btn.dataset.sessionId;
        if (!activeWorkspaceId || !userId || !sessionId) return;
        if (!confirm('Завершить этот сеанс? Пользователю потребуется войти снова.')) return;
        btn.disabled = true;
        try {
            const res = await fetch(`/api/admin/workspaces/${activeWorkspaceId}/sessions/terminate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json; charset=utf-8',
                    Accept: 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                },
                body: JSON.stringify({ user_id: parseInt(userId, 10), session_id: parseInt(sessionId, 10) }),
            });
            const data = await res.json();
            if (!res.ok || data.status !== 'success') {
                throw new Error((data && data.error) || 'Не удалось завершить сеанс');
            }
            renderPanel(data.workspace);
            if (typeof window.showToast === 'function') {
                window.showToast('Сеанс завершён', 'info');
            }
        } catch (err) {
            alert(err.message || 'Ошибка');
        } finally {
            btn.disabled = false;
        }
    }

    function updateCardFromWorkspace(wsId, ws) {
        const card = document.querySelector(`.workspace-card[data-workspace-id="${wsId}"]`);
        if (!card) return;
        const title = card.querySelector('.workspace-card-title');
        if (title && ws.name) title.textContent = ws.name;
        if (ws.stats) {
            const workersEl = card.querySelector('[data-stat-workers]');
            const clientsEl = card.querySelector('[data-stat-clients]');
            if (workersEl) workersEl.textContent = String(ws.stats.workers ?? 0);
            if (clientsEl) clientsEl.textContent = String(ws.stats.clients ?? 0);
        }
        const expiresEl = card.querySelector('[data-stat-expires]');
        if (expiresEl) {
            expiresEl.textContent = ws.expires_at_display || 'без ограничения';
        }
    }

    document.querySelectorAll('.workspace-card[data-workspace-id]').forEach(function (card) {
        card.addEventListener('click', function (e) {
            if (e.target.closest('a, button, input, code, .gruzz-date-picker')) return;
            const id = card.dataset.workspaceId;
            if (id) loadWorkspace(id);
        });
    });

    if (closeBtn) closeBtn.addEventListener('click', closePanel);
    if (overlay) overlay.addEventListener('click', closePanel);
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') closePanel();
    });
})();
