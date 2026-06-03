(function () {

    'use strict';



    const overlay = () => document.getElementById('profile-panel-overlay');

    const panelBody = () => document.getElementById('profile-panel-body');

    let loading = false;

    let profileUserId = null;

    let profileRelation = { is_contact: false, is_blocked: false, is_self: false };

    let profileContactMenu = null;

    let profileContactMenuDismiss = null;

    let workerDocsOpen = false;

    let workerDocsLoading = false;



    function clearSensitiveImagesOnly() {

        document.querySelectorAll('.js-profile-sensitive-img').forEach(function (img) {

            img.removeAttribute('src');

            img.src = '';

        });

        if (typeof window.closeImageLightbox === 'function') {

            window.closeImageLightbox();

        }

    }

    let workerDocUrls = [];



    function purgeSensitiveWorkerMedia() {

        clearSensitiveImagesOnly();

        var block = document.getElementById('profile-panel-documents');

        if (block) {

            block.hidden = true;

            block.classList.remove('is-open');

        }

        workerDocsOpen = false;

    }



    function clearVerificationMediaSession() {

        purgeSensitiveWorkerMedia();

        if (window._verificationMediaClearSent) return;

        window._verificationMediaClearSent = true;

        fetch('/admin/verification/clear-media', {

            method: 'POST',

            headers: { 'X-Requested-With': 'XMLHttpRequest' },

            keepalive: true,

        }).catch(function () {});

    }



    function escapeHtml(text) {

        if (!text) return '';

        return String(text)

            .replace(/&/g, '&amp;')

            .replace(/</g, '&lt;')

            .replace(/>/g, '&gt;')

            .replace(/"/g, '&quot;');

    }



    function toast(msg, type) {

        if (typeof window.showToast === 'function') {

            window.showToast(msg, type || 'info');

        }

    }



    async function apiPost(url, body) {

        const res = await fetch(url, {

            method: 'POST',

            headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },

            credentials: 'same-origin',

            body: JSON.stringify(body || {}),

        });

        const data = await res.json();

        if (!res.ok || data.ok === false) {

            throw new Error(data.error || data.message || 'Ошибка запроса');

        }

        return data;

    }



    function renderAvatar(data) {

        const name = data.name || data.full_name || '?';

        if (data.avatar_url) {

            return `<img src="${escapeHtml(data.avatar_url)}" alt="${escapeHtml(name)}">`;

        }

        return `<span class="profile-panel-initials">${escapeHtml(name.charAt(0).toUpperCase())}</span>`;

    }



    function renderField(label, value, icon) {

        const display = value || '—';

        return `

            <div class="profile-panel-field">

                <div class="profile-panel-field-label">

                    ${icon ? `<i data-lucide="${icon}"></i>` : ''}

                    <span>${escapeHtml(label)}</span>

                </div>

                <div class="profile-panel-field-value">${escapeHtml(display)}</div>

            </div>

        `;

    }



    function renderWorkerExtras(data) {

        const stats = `

            <div class="profile-panel-stats">

                <div class="profile-panel-stat">

                    <span class="profile-panel-stat-value">${escapeHtml(String(data.rating ?? 0))}</span>

                    <span class="profile-panel-stat-label">Рейтинг</span>

                </div>

                <div class="profile-panel-stat">

                    <span class="profile-panel-stat-value">${escapeHtml(String(data.completed_tasks ?? 0))}</span>

                    <span class="profile-panel-stat-label">Выполнено</span>

                </div>

                <div class="profile-panel-stat">

                    <span class="profile-panel-stat-value">${escapeHtml(String(data.missed_tasks ?? 0))}</span>

                    <span class="profile-panel-stat-label">Пропущено</span>

                </div>

            </div>

        `;



        let bankCardBlock;

        if (data.can_edit_bank_card) {

            bankCardBlock = `

                <div class="profile-panel-field profile-panel-field--editable">

                    <div class="profile-panel-field-label">

                        <i data-lucide="credit-card"></i>

                        <span>Номер банковской карты</span>

                    </div>

                    <div class="profile-panel-bank-row">

                        <input type="text" id="profile-panel-bank-card-input"

                               class="profile-panel-input"

                               value="${escapeHtml(data.bank_card || '')}"

                               placeholder="0000 0000 0000 0000"

                               autocomplete="off">

                        <button type="button" class="btn-primary profile-panel-save-card" id="profile-panel-save-card">

                            Сохранить

                        </button>

                    </div>

                </div>

            `;

        } else if (data.bank_card) {

            bankCardBlock = renderField('Номер банковской карты', data.bank_card, 'credit-card');

        }



        return stats + (bankCardBlock || '');

    }



    function socialActionsMarkup() {

        return `

            <div id="profile-panel-social-actions" class="profile-panel-actions" hidden>

                <button type="button" class="b2b-btn b2b-btn-secondary profile-panel-action-btn" id="profile-btn-contact">

                    Добавить в контакты

                </button>

                <button type="button" class="b2b-btn b2b-btn-secondary profile-panel-action-btn" id="profile-btn-write" hidden>

                    Написать

                </button>

            </div>

        `;

    }



    function updateSocialActions(data) {

        const actions = document.getElementById('profile-panel-social-actions');

        const contactBtn = document.getElementById('profile-btn-contact');

        const writeBtn = document.getElementById('profile-btn-write');

        if (!actions || !contactBtn || !writeBtn) return;



        const isSelf = !!data.is_self;

        const isMessenger = data.context === 'messenger' || data.profile_type === 'messenger';



        if (isSelf || !isMessenger) {

            actions.hidden = true;

            return;

        }



        profileUserId = data.id;

        profileRelation = {

            is_contact: !!data.is_contact,

            is_blocked: !!data.is_blocked,

            is_self: false,

        };



        if (profileRelation.is_contact) {

            contactBtn.textContent = 'Удалить из контактов';

            writeBtn.hidden = false;

        } else {

            contactBtn.textContent = 'Добавить в контакты';

            writeBtn.hidden = true;

        }



        actions.hidden = false;

    }



    function renderMessengerProfile(data) {

        const body = panelBody();

        if (!body) return;



        body.innerHTML = `

            <div class="profile-panel-hero">

                <div class="profile-panel-avatar">${renderAvatar(data)}</div>

                <h2 class="profile-panel-name" id="profile-panel-title">${escapeHtml(data.name || '—')}</h2>

                <div class="profile-panel-role-badge">${escapeHtml(data.role_label || '')}</div>

            </div>

            <div class="profile-panel-fields">

                ${renderField('Телефон', data.phone, 'phone')}

                ${data.tag ? renderField('Тег', data.tag, 'at-sign') : ''}

                ${data.username && data.username !== data.tag ? renderField('Username', data.username, 'user') : ''}

                ${renderField('Дата рождения', data.birth_date, 'cake')}

            </div>

            ${socialActionsMarkup()}

        `;



        updateSocialActions(data);

        refreshPanelIcons();

    }



    function workerStaffActionsMarkup(data) {

        if (!data.can_open_chat && !data.can_view_documents) return '';

        return `

            <div class="profile-panel-actions profile-panel-worker-actions">

                ${data.can_open_chat ? `

                <button type="button" class="b2b-btn b2b-btn-secondary profile-panel-action-btn" id="profile-btn-worker-write">

                    <i data-lucide="message-circle"></i>

                    Написать

                </button>

                ` : ''}

                ${data.can_view_documents ? `

                <button type="button" class="b2b-btn b2b-btn-secondary profile-panel-action-btn" id="profile-btn-worker-documents">

                    <i data-lucide="shield-check"></i>

                    Проверить данные

                </button>

                ` : ''}

            </div>

            <div id="profile-panel-documents" class="profile-panel-documents" hidden>

                <div class="profile-panel-documents-title">Документы анкеты</div>

                <div class="profile-panel-documents-loading" id="profile-panel-documents-loading" hidden>Загрузка…</div>

                <div class="profile-panel-documents-error" id="profile-panel-documents-error" hidden></div>

                <div class="profile-panel-documents-empty" id="profile-panel-documents-empty" hidden>

                    <i data-lucide="file-x"></i>

                    <span>Документы не загружены</span>

                </div>

                <div class="profile-panel-documents-grid" id="profile-panel-documents-grid"></div>

            </div>

        `;

    }



    function renderWorkerDocumentsGrid(documents) {

        const grid = document.getElementById('profile-panel-documents-grid');

        const emptyEl = document.getElementById('profile-panel-documents-empty');

        if (!grid) return;

        workerDocUrls = (documents || []).map(function (d) { return d.url; }).filter(Boolean);

        if (!documents || !documents.length) {

            grid.innerHTML = '';

            grid.classList.add('is-hidden');

            if (emptyEl) emptyEl.hidden = false;

            return;

        }

        if (emptyEl) emptyEl.hidden = true;

        grid.classList.remove('is-hidden');

        grid.innerHTML = documents.map(function (doc) {

            return `

                <div class="profile-panel-doc-item">

                    <span class="profile-panel-doc-label">${escapeHtml(doc.label || doc.type)}</span>

                    <div class="profile-panel-doc-preview is-clickable js-profile-doc-preview" data-doc-url="${escapeHtml(doc.url)}">

                        <img class="js-profile-sensitive-img" src="${escapeHtml(doc.url)}" alt="${escapeHtml(doc.label || '')}">

                    </div>

                </div>

            `;

        }).join('');

        grid.querySelectorAll('.js-profile-doc-preview').forEach(function (preview) {

            preview.addEventListener('click', function () {

                const url = preview.dataset.docUrl;

                if (!url || typeof window.openImageLightbox !== 'function') return;

                window.openImageLightbox(url, workerDocUrls);

            });

        });

        if (typeof refreshIcons === 'function') refreshIcons();

    }



    async function toggleWorkerDocuments(userId) {

        const block = document.getElementById('profile-panel-documents');

        const loadingEl = document.getElementById('profile-panel-documents-loading');

        const errorEl = document.getElementById('profile-panel-documents-error');

        if (!block) return;



        if (workerDocsOpen) {

            purgeSensitiveWorkerMedia();

            clearVerificationMediaSession();

            window._verificationMediaClearSent = false;

            workerDocUrls = [];

            return;

        }



        clearSensitiveImagesOnly();

        block.hidden = false;

        workerDocsOpen = true;

        requestAnimationFrame(function () {

            block.classList.add('is-open');

        });

        if (loadingEl) loadingEl.hidden = false;

        if (errorEl) {

            errorEl.hidden = true;

            errorEl.textContent = '';

        }

        renderWorkerDocumentsGrid([]);



        try {

            const response = await fetch('/admin/workers/' + userId + '/verification-documents', {

                credentials: 'same-origin',

                headers: { 'Accept': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },

            });

            const data = await response.json();

            if (!response.ok || !data.ok) {

                throw new Error(data.error || 'Документы недоступны');

            }

            if (!data.has_documents || !data.documents || !data.documents.length) {

                renderWorkerDocumentsGrid([]);

                return;

            }

            renderWorkerDocumentsGrid(data.documents);

        } catch (err) {

            if (errorEl) {

                errorEl.textContent = err.message || 'Ошибка загрузки';

                errorEl.hidden = false;

            }

            renderWorkerDocumentsGrid([]);

            purgeSensitiveWorkerMedia();

        } finally {

            if (loadingEl) loadingEl.hidden = true;

        }

    }



    function renderWorkerCard(data) {

        const body = panelBody();

        if (!body) return;



        purgeSensitiveWorkerMedia();

        window._verificationMediaClearSent = false;



        const title = data.full_name || data.name || '—';



        body.innerHTML = `

            <div class="profile-panel-hero">

                <div class="profile-panel-avatar">${renderAvatar(data)}</div>

                <h2 class="profile-panel-name" id="profile-panel-title">${escapeHtml(title)}</h2>

                <div class="profile-panel-role-badge">${escapeHtml(data.role_label || '')}</div>

                ${data.is_verified ? '<div class="profile-panel-verified"><i data-lucide="badge-check"></i> Верифицирован</div>' : ''}

            </div>

            <div class="profile-panel-fields">

                ${renderField('Телефон', data.phone, 'phone')}

                ${renderField('Дата рождения', data.birth_date, 'cake')}

                ${data.profile_type === 'worker' ? renderWorkerExtras(data) : ''}

            </div>

            ${workerStaffActionsMarkup(data)}

        `;



        refreshPanelIcons();



        const saveBtn = document.getElementById('profile-panel-save-card');

        if (saveBtn) {

            saveBtn.addEventListener('click', saveBankCard);

        }

    }



    function refreshPanelIcons() {

        if (typeof window.refreshGruzzIcons === 'function') window.refreshGruzzIcons();

        if (typeof lucide !== 'undefined') lucide.createIcons();

    }



    async function saveBankCard() {

        const input = document.getElementById('profile-panel-bank-card-input');

        const btn = document.getElementById('profile-panel-save-card');

        if (!input || !btn) return;



        btn.disabled = true;

        try {

            const response = await fetch('/profile/update-bank-card', {

                method: 'POST',

                headers: {

                    'Content-Type': 'application/json',

                    'X-Requested-With': 'XMLHttpRequest',

                },

                body: JSON.stringify({ bank_card: input.value.trim() }),

            });

            const data = await response.json();

            if (!response.ok) {

                alert(data.error || 'Не удалось сохранить');

                return;

            }

            toast('Номер карты сохранён', 'success');

        } catch (err) {

            alert('Ошибка сети');

        } finally {

            btn.disabled = false;

        }

    }



    async function toggleContact() {

        if (!profileUserId) return;

        try {

            if (profileRelation.is_contact) {

                await apiPost('/api/contacts/remove', { user_id: profileUserId });

                profileRelation.is_contact = false;

                toast('Удалено из контактов', 'success');

            } else {

                await apiPost('/api/contacts/add', { user_id: profileUserId });

                profileRelation.is_contact = true;

                toast('Добавлено в контакты', 'success');

            }

            updateSocialActions({

                id: profileUserId,

                is_contact: profileRelation.is_contact,

                is_blocked: profileRelation.is_blocked,

                is_self: false,

                context: 'messenger',

                profile_type: 'messenger',

            });

        } catch (e) {

            toast(e.message, 'error');

        }

    }



    function unbindProfileContactMenuDismiss() {

        if (!profileContactMenuDismiss) return;

        document.removeEventListener('mousedown', profileContactMenuDismiss.onPointerDown, true);

        document.removeEventListener('keydown', profileContactMenuDismiss.onKey);

        profileContactMenuDismiss = null;

    }



    function closeProfileContactMenu() {

        unbindProfileContactMenuDismiss();

        if (profileContactMenu) {

            profileContactMenu.remove();

            profileContactMenu = null;

        }

        if (window.ChatSocial && typeof window.ChatSocial.closeListContextMenu === 'function') {

            window.ChatSocial.closeListContextMenu();

        }

    }



    function bindProfileContactMenuDismiss() {

        unbindProfileContactMenuDismiss();

        const onPointerDown = function (e) {

            if (profileContactMenu && profileContactMenu.contains(e.target)) return;

            closeProfileContactMenu();

        };

        const onKey = function (e) {

            if (e.key === 'Escape') closeProfileContactMenu();

        };

        profileContactMenuDismiss = { onPointerDown: onPointerDown, onKey: onKey };

        document.addEventListener('mousedown', onPointerDown, true);

        document.addEventListener('keydown', onKey);

    }



    function showProfileContactBlockMenu(x, y) {

        if (!profileUserId || profileRelation.is_blocked || profileRelation.is_self) return;

        closeProfileContactMenu();

        const menu = document.createElement('div');

        menu.className = 'chat-list-context-menu profile-contact-context-menu';

        const btn = document.createElement('button');

        btn.type = 'button';

        btn.className = 'danger';

        btn.textContent = '❌ Заблокировать пользователя';

        btn.addEventListener('click', function (e) {

            e.stopPropagation();

            closeProfileContactMenu();

            toggleBlock();

        });

        menu.appendChild(btn);

        document.body.appendChild(menu);

        profileContactMenu = menu;

        const rect = menu.getBoundingClientRect();

        let left = x;

        let top = y;

        if (left + rect.width > window.innerWidth) left = window.innerWidth - rect.width - 8;

        if (top + rect.height > window.innerHeight) top = window.innerHeight - rect.height - 8;

        menu.style.left = left + 'px';

        menu.style.top = top + 'px';

        bindProfileContactMenuDismiss();

    }



    async function toggleBlock() {

        if (!profileUserId) return;

        const block = !profileRelation.is_blocked;

        if (block && !confirm('Заблокировать пользователя? Диалог и контакт будут недоступны.')) return;

        try {

            await apiPost('/api/blacklist', { user_id: profileUserId, action: block ? 'add' : 'remove' });

            profileRelation.is_blocked = block;

            if (block) profileRelation.is_contact = false;

            toast(block ? 'Пользователь заблокирован' : 'Пользователь разблокирован', 'success');

            updateSocialActions({

                id: profileUserId,

                is_contact: profileRelation.is_contact,

                is_blocked: profileRelation.is_blocked,

                is_self: false,

                context: 'messenger',

                profile_type: 'messenger',

            });

        } catch (e) {

            toast(e.message, 'error');

        }

    }



    function openPrivateChatFromProfile() {

        if (!profileUserId) return;

        window.location.href = `/chat/create/private/${profileUserId}`;

    }



    function showLoading() {

        const body = panelBody();

        if (!body) return;

        body.innerHTML = `

            <div class="profile-panel-loading">

                <div class="profile-panel-spinner"></div>

                <span>Загрузка профиля…</span>

            </div>

        `;

    }



    function openPanel() {

        const el = overlay();

        if (!el) return;

        el.hidden = false;

        requestAnimationFrame(() => el.classList.add('is-open'));

        document.body.classList.add('profile-panel-open');

    }



    function closePanel() {

        closeProfileContactMenu();

        clearVerificationMediaSession();

        window._verificationMediaClearSent = false;

        profileUserId = null;

        const el = overlay();

        if (!el) return;

        el.classList.remove('is-open');

        document.body.classList.remove('profile-panel-open');

        setTimeout(() => {

            if (!el.classList.contains('is-open')) {

                el.hidden = true;

                purgeSensitiveWorkerMedia();

            }

        }, 220);

    }



    function resolveProfileContext(el) {

        const trigger = el.closest('[data-profile-user-id]');

        if (!trigger) return 'messenger';

        const ctx = (trigger.dataset.profileContext || '').trim().toLowerCase();

        if (ctx === 'worker' || ctx === 'messenger') {

            return ctx;

        }

        return 'messenger';

    }



    function resolveUserId(el) {

        const trigger = el.closest('[data-profile-user-id]');

        if (!trigger) return null;

        const id = parseInt(trigger.dataset.profileUserId, 10);

        return id || null;

    }



    function showProfileError(message) {

        const body = panelBody();

        if (!body) return;

        body.innerHTML = `

            <div class="profile-panel-loading">

                <span>${escapeHtml(message || 'Не удалось загрузить профиль')}</span>

            </div>

        `;

    }



    async function openUserProfile(userId, context) {

        const id = parseInt(userId, 10);

        if (!id) return;

        if (loading) return;



        const ctx = context === 'worker' ? 'worker' : 'messenger';



        openPanel();

        showLoading();

        loading = true;



        try {

            const response = await fetch(`/api/users/${id}/profile?context=${ctx}`, {

                credentials: 'same-origin',

                headers: { 'Accept': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },

            });

            const contentType = response.headers.get('content-type') || '';

            let data = null;

            if (contentType.includes('application/json')) {

                data = await response.json();

            } else {

                throw new Error('Сервер вернул некорректный ответ');

            }

            if (!response.ok) {

                showProfileError(data?.error || 'Не удалось загрузить профиль');

                toast(data?.error || 'Не удалось загрузить профиль', 'error');

                return;

            }

            profileUserId = data.id;



            if (data.context === 'worker' || ctx === 'worker') {

                renderWorkerCard(data);

            } else {

                renderMessengerProfile(data);

            }

            refreshPanelIcons();

        } catch (err) {

            console.error('[Profile]', err);

            showProfileError('Ошибка сети');

            toast('Ошибка сети', 'error');

        } finally {

            loading = false;

        }

    }



    function handleTriggerClick(event) {

        const id = resolveUserId(event.target);

        if (!id) return;

        event.preventDefault();

        event.stopPropagation();

        openUserProfile(id, resolveProfileContext(event.target));

    }



    function handleTriggerKeydown(event) {

        if (event.key !== 'Enter' && event.key !== ' ') return;

        const id = resolveUserId(event.target);

        if (!id) return;

        event.preventDefault();

        openUserProfile(id, resolveProfileContext(event.target));

    }



    document.addEventListener('click', handleTriggerClick);

    document.addEventListener('keydown', handleTriggerKeydown);



    document.addEventListener('click', (event) => {

        const el = overlay();

        if (!el || el.hidden) return;

        if (event.target === el) closePanel();

    });



    document.addEventListener('keydown', (event) => {

        if (event.key === 'Escape') closePanel();

    });



    window.addEventListener('pagehide', clearVerificationMediaSession);

    window.addEventListener('beforeunload', clearVerificationMediaSession);



    document.addEventListener('DOMContentLoaded', () => {

        const closeBtn = document.getElementById('profile-panel-close');

        if (closeBtn) closeBtn.addEventListener('click', closePanel);



        const profilePanel = document.getElementById('profile-panel');

        profilePanel?.addEventListener('click', (event) => {

            if (event.target.closest('#profile-btn-contact')) {

                event.preventDefault();

                toggleContact();

                return;

            }

            if (event.target.closest('#profile-btn-write')) {

                event.preventDefault();

                openPrivateChatFromProfile();

            }

            if (event.target.closest('#profile-btn-worker-write')) {

                event.preventDefault();

                if (profileUserId) {

                    window.location.href = '/chat/create/private/' + profileUserId;

                }

                return;

            }

            if (event.target.closest('#profile-btn-worker-documents')) {

                event.preventDefault();

                if (profileUserId && !workerDocsLoading) {

                    workerDocsLoading = true;

                    toggleWorkerDocuments(profileUserId).finally(function () {

                        workerDocsLoading = false;

                    });

                }

            }

        });

        profilePanel?.addEventListener('contextmenu', (event) => {

            event.preventDefault();

            event.stopPropagation();

            const contactBtn = event.target.closest('#profile-btn-contact');

            if (!contactBtn) return;

            if (window.ChatSocial && typeof window.ChatSocial.closeListContextMenu === 'function') {

                window.ChatSocial.closeListContextMenu();

            }

            showProfileContactBlockMenu(event.clientX, event.clientY);

        });

    });



    window.openUserProfile = openUserProfile;

    window.openWorkerProfile = function (userId) {

        return openUserProfile(userId, 'worker');

    };

    window.openMessengerProfile = function (userId) {

        return openUserProfile(userId, 'messenger');

    };

    window.closeUserProfile = closePanel;

})();

