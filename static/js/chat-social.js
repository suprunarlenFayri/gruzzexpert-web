(function () {
    'use strict';

    let listContextMenu = null;
    let listContextMenuDismiss = null;
    let pinnedMessageId = null;

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

    async function apiJson(url, body) {
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

    function refreshIcons(root) {
        if (typeof window.refreshIcons === 'function') window.refreshIcons(root);
        if (typeof lucide !== 'undefined') lucide.createIcons({ root: root || document });
    }

    function unbindListContextMenuDismiss() {
        if (!listContextMenuDismiss) return;
        document.removeEventListener('mousedown', listContextMenuDismiss.onPointerDown, true);
        document.removeEventListener('scroll', listContextMenuDismiss.onScroll, true);
        document.removeEventListener('keydown', listContextMenuDismiss.onKey);
        listContextMenuDismiss = null;
    }

    function closeListContextMenu() {
        unbindListContextMenuDismiss();
        const stale = document.getElementById('chat-list-context-menu');
        if (stale) stale.remove();
        if (listContextMenu) {
            listContextMenu.remove();
            listContextMenu = null;
        }
    }

    function bindListContextMenuDismiss() {
        unbindListContextMenuDismiss();
        const onPointerDown = function (e) {
            if (listContextMenu && listContextMenu.contains(e.target)) return;
            closeListContextMenu();
        };
        const onScroll = function () {
            closeListContextMenu();
        };
        const onKey = function (e) {
            if (e.key === 'Escape') closeListContextMenu();
        };
        listContextMenuDismiss = { onPointerDown: onPointerDown, onScroll: onScroll, onKey: onKey };
        document.addEventListener('mousedown', onPointerDown, true);
        document.addEventListener('scroll', onScroll, true);
        document.addEventListener('keydown', onKey);
    }

    function showListContextMenu(x, y, items) {
        closeListContextMenu();
        const menu = document.createElement('div');
        menu.className = 'chat-list-context-menu';
        menu.id = 'chat-list-context-menu';
        menu.setAttribute('role', 'menu');

        items.forEach(function (item) {
            const btn = document.createElement('button');
            btn.type = 'button';
            if (item.danger) btn.classList.add('danger');
            btn.innerHTML = `<i data-lucide="${item.icon}"></i><span>${escapeHtml(item.label)}</span>`;
            btn.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
                closeListContextMenu();
                try {
                    item.onClick();
                } catch (err) {
                    console.error('[ContextMenu]', err);
                }
            });
            menu.appendChild(btn);
        });

        document.body.appendChild(menu);
        listContextMenu = menu;

        const rect = menu.getBoundingClientRect();
        let left = x;
        let top = y;
        if (left + rect.width > window.innerWidth) left = window.innerWidth - rect.width - 8;
        if (top + rect.height > window.innerHeight) top = window.innerHeight - rect.height - 8;
        menu.style.left = left + 'px';
        menu.style.top = top + 'px';

        try {
            refreshIcons(menu);
        } catch (err) {
            console.warn('[ContextMenu] icons', err);
        }

        bindListContextMenuDismiss();
    }

    function initListContextMenuGlobalClose() {
        if (window.__listContextMenuGlobalClose) return;
        window.__listContextMenuGlobalClose = true;
        document.addEventListener('contextmenu', function () {
            closeListContextMenu();
        }, true);
    }

    function removeChatItemFromDom(chatId) {
        const el = document.querySelector(`.chat-item[data-chat-id="${chatId}"]`);
        if (!el) return;
        el.style.transition = 'opacity 0.25s ease, transform 0.25s ease';
        el.style.opacity = '0';
        el.style.transform = 'translateX(-8px)';
        setTimeout(function () { el.remove(); }, 260);
    }

    function updateChatPinBadge(chatId, pinned) {
        const el = document.querySelector(`.chat-item[data-chat-id="${chatId}"]`);
        if (!el) return;
        el.classList.toggle('is-pinned', !!pinned);
        el.dataset.chatPinned = pinned ? '1' : '0';
        const nameEl = el.querySelector('.chat-name');
        if (!nameEl) return;
        let badge = nameEl.querySelector('.chat-pin-badge');
        if (pinned && !badge) {
            badge = document.createElement('span');
            badge.className = 'chat-pin-badge';
            badge.title = 'Закреплён';
            badge.innerHTML = '<i data-lucide="pin"></i>';
            nameEl.appendChild(badge);
            refreshIcons(badge);
        } else if (!pinned && badge) {
            badge.remove();
        }
        resortChatItems();
    }

    function resortChatItems() {
        document.querySelectorAll('.chat-group-items').forEach(function (container) {
            const items = Array.from(container.querySelectorAll('.chat-item'));
            if (items.length < 2) return;
            items.sort(function (a, b) {
                const ap = a.dataset.chatPinned === '1' ? 0 : 1;
                const bp = b.dataset.chatPinned === '1' ? 0 : 1;
                return ap - bp;
            });
            items.forEach(function (node) { container.appendChild(node); });
        });
    }

    window.pinChat = async function (chatId) {
        try {
            const res = await fetch(`/pin/chat/${chatId}`, {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Accept': 'application/json' },
            });
            const data = await res.json();
            updateChatPinBadge(chatId, !!data.pinned);
            toast(data.pinned ? 'Чат закреплён' : 'Чат откреплён', 'success');
        } catch (e) {
            toast(e.message || 'Не удалось закрепить чат', 'error');
        }
    };

    window.clearChatHistory = async function (chatId) {
        if (!confirm('Очистить историю этого чата?')) return;
        try {
            await fetch(`/chat/clear/${chatId}`, { method: 'POST', credentials: 'same-origin' });
            toast('История очищена', 'success');
            window.location.reload();
        } catch (e) {
            toast('Ошибка очистки', 'error');
        }
    };

    async function hideChat(chatId) {
        try {
            await apiJson(`/api/chats/${chatId}/hide`, {});
            removeChatItemFromDom(chatId);
            toast('Чат удалён из списка', 'success');
            const activeId = window.ChatConfig?.chatId || document.querySelector('.chat-container')?.dataset?.chatId;
            if (String(activeId) === String(chatId)) {
                window.location.href = '/chats';
            }
        } catch (e) {
            toast(e.message, 'error');
        }
    }

    function bindContactsModalContextMenu() {
        const root = document.getElementById('contacts-modal-list');
        if (!root || root.dataset.ctxBound === '1') return;
        root.dataset.ctxBound = '1';
        root.addEventListener('contextmenu', function (e) {
            e.preventDefault();
            e.stopPropagation();
            const item = e.target.closest('.contacts-modal-item');
            if (!item) return;
            const userId = parseInt(item.dataset.userId, 10);
            if (!userId) return;
            showListContextMenu(e.clientX, e.clientY, [
                {
                    icon: 'user',
                    label: 'Открыть профиль',
                    onClick: function () {
                        if (typeof window.openUserProfile === 'function') {
                            window.openUserProfile(userId, 'messenger');
                        }
                    },
                },
                {
                    icon: 'user-minus',
                    label: 'Удалить из контактов',
                    onClick: async function () {
                        try {
                            await apiJson('/api/contacts/remove', { user_id: userId });
                            toast('Удалено из контактов', 'success');
                            loadContactsModalList();
                        } catch (err) {
                            toast(err.message, 'error');
                        }
                    },
                },
                {
                    icon: 'ban',
                    label: 'Заблокировать',
                    danger: true,
                    onClick: async function () {
                        if (!confirm('Заблокировать пользователя?')) return;
                        try {
                            await apiJson('/api/blacklist', { user_id: userId, action: 'add' });
                            toast('Пользователь заблокирован', 'success');
                            loadContactsModalList();
                        } catch (err) {
                            toast(err.message, 'error');
                        }
                    },
                },
            ]);
        });
    }

    function bindChatListContextMenu() {
        if (window.__chatListContextMenuBound) return;
        window.__chatListContextMenuBound = true;
        document.addEventListener('contextmenu', function (e) {
            const item = e.target.closest('.chat-item');
            if (!item) return;
            e.preventDefault();
            e.stopPropagation();
            const chatId = item.dataset.chatId;
            const isPinned = item.dataset.chatPinned === '1';
            showListContextMenu(e.clientX, e.clientY, [
                {
                    icon: 'pin',
                    label: isPinned ? 'Открепить чат' : 'Закрепить чат',
                    onClick: function () { window.pinChat(chatId); },
                },
                {
                    icon: 'trash-2',
                    label: 'Удалить чат',
                    danger: true,
                    onClick: function () {
                        if (confirm('Удалить чат из списка?')) hideChat(chatId);
                    },
                },
            ]);
        });
    }

    async function loadContactsModalList() {
        const root = document.getElementById('contacts-modal-list');
        if (!root) return;
        root.innerHTML = '<div class="contacts-modal-loading">Загрузка…</div>';
        try {
            const res = await fetch('/api/contacts', { credentials: 'same-origin', headers: { 'Accept': 'application/json' } });
            const data = await res.json();
            if (!data.ok || !data.contacts || !data.contacts.length) {
                root.innerHTML = '<div class="contacts-modal-empty">Нет контактов</div>';
                return;
            }
            root.innerHTML = data.contacts.map(function (c) {
                const letter = escapeHtml((c.name || '?').charAt(0).toUpperCase());
                const avatar = c.avatar_url
                    ? `<img src="${escapeHtml(c.avatar_url)}" alt="">`
                    : letter;
                const tag = c.tag ? `<div class="contacts-modal-item-tag">${escapeHtml(c.tag)}</div>` : '';
                return `<a href="${escapeHtml(c.chat_url)}" class="contacts-modal-item" data-user-id="${c.id}">
                    <div class="contacts-modal-avatar">${avatar}</div>
                    <div class="contacts-modal-item-info">
                        <div class="contacts-modal-item-name">${escapeHtml(c.name)}</div>
                        ${tag}
                    </div>
                </a>`;
            }).join('');
            refreshIcons(root);
            bindContactsModalContextMenu();
        } catch (e) {
            root.innerHTML = '<div class="contacts-modal-empty">Не удалось загрузить контакты</div>';
        }
    }

    window.openContactsModal = function () {
        const modal = document.getElementById('contacts-modal');
        if (!modal) return;
        modal.hidden = false;
        document.body.classList.add('contacts-modal-open');
        loadContactsModalList();
        const menu = document.getElementById('dropdownMenu');
        if (menu) menu.classList.remove('show');
    };

    window.closeContactsModal = function () {
        const modal = document.getElementById('contacts-modal');
        if (!modal) return;
        modal.hidden = true;
        document.body.classList.remove('contacts-modal-open');
    };

    function showDeleteMessageModal(messageId, isOwn) {
        const overlay = document.createElement('div');
        overlay.className = 'chat-delete-modal-overlay';
        overlay.innerHTML = `
            <div class="chat-delete-modal" role="dialog">
                <h4>Удалить сообщение?</h4>
                <div class="chat-delete-modal-actions">
                    <button type="button" class="b2b-btn b2b-btn-secondary" data-scope="me">Удалить для меня</button>
                    ${isOwn ? '<button type="button" class="b2b-btn b2b-btn-danger" data-scope="all">Удалить для всех</button>' : ''}
                    <button type="button" class="b2b-btn b2b-btn-ghost" data-scope="cancel">Отмена</button>
                </div>
            </div>
        `;
        document.body.appendChild(overlay);
        overlay.addEventListener('click', function (e) {
            if (e.target === overlay) overlay.remove();
        });
        overlay.querySelectorAll('[data-scope]').forEach(function (btn) {
            btn.addEventListener('click', async function () {
                const scope = btn.dataset.scope;
                if (scope === 'cancel') {
                    overlay.remove();
                    return;
                }
                try {
                    await apiJson(`/chat/message/${messageId}/delete`, { scope: scope });
                    applyMessageDeleted(messageId, scope === 'all');
                    overlay.remove();
                    toast('Сообщение удалено', 'success');
                } catch (err) {
                    toast(err.message, 'error');
                }
            });
        });
    }

    function applyMessageDeleted(messageId, forAll) {
        const el = document.querySelector(`[data-message-id="${messageId}"], #msg-${messageId}`);
        if (!el) {
            if (String(pinnedMessageId) === String(messageId)) updatePinnedBar(null);
            return;
        }
        if (!forAll) {
            el.style.transition = 'opacity 0.25s ease';
            el.style.opacity = '0';
            setTimeout(function () { el.remove(); }, 250);
        } else {
            const textEl = el.querySelector('.message-text');
            if (textEl) {
                textEl.textContent = 'Сообщение удалено';
                textEl.classList.add('message-text--deleted');
            }
            el.querySelectorAll('.chat-attachments, .attachments').forEach(function (a) { a.remove(); });
        }
        if (String(pinnedMessageId) === String(messageId)) updatePinnedBar(null);
    }

    async function pinMessage(messageId) {
        try {
            const data = await apiJson(`/chat/message/${messageId}/pin`, {});
            if (data.pinned && data.message) {
                pinnedMessageId = data.message.id;
                updatePinnedBar(data.message);
            } else {
                pinnedMessageId = null;
                updatePinnedBar(null);
            }
            toast(data.pinned ? 'Сообщение закреплено' : 'Сообщение откреплено', 'success');
        } catch (e) {
            toast(e.message, 'error');
        }
    }

    function updatePinnedBar(msg) {
        const bar = document.getElementById('chat-pinned-bar');
        const preview = document.getElementById('chat-pinned-preview');
        if (!bar || !preview) return;
        if (!msg) {
            bar.hidden = true;
            bar.style.display = 'none';
            bar.dataset.pinnedId = '';
            pinnedMessageId = null;
            preview.textContent = '';
            return;
        }
        pinnedMessageId = msg.id;
        bar.dataset.pinnedId = String(msg.id);
        const text = (msg.text || msg.message || '').trim() || 'Вложение';
        preview.textContent = (msg.author_name || msg.sender_name || '') + ': ' + text;
        bar.hidden = false;
        bar.style.display = 'flex';
        refreshIcons(bar);
    }

    function scrollToPinnedMessage() {
        const bar = document.getElementById('chat-pinned-bar');
        const msgId = bar?.dataset?.pinnedId || pinnedMessageId;
        if (!msgId) return;
        if (typeof window.scrollToMessage === 'function') {
            window.scrollToMessage(msgId);
        }
    }

    async function unpinCurrentMessage() {
        const bar = document.getElementById('chat-pinned-bar');
        const msgId = bar?.dataset?.pinnedId || pinnedMessageId;
        if (!msgId) return;
        await pinMessage(msgId);
    }

    async function loadPinnedMessage() {
        const chatId = window.ChatConfig?.chatId;
        if (!chatId) return;
        try {
            const res = await fetch(`/chat/${chatId}/pinned-message`, { credentials: 'same-origin', headers: { 'Accept': 'application/json' } });
            const data = await res.json();
            if (data.ok && data.pinned) updatePinnedBar(data.pinned);
            else updatePinnedBar(null);
        } catch (e) { /* ignore */ }
    }

    window.ChatSocial = {
        pinMessage: pinMessage,
        showDeleteMessageModal: showDeleteMessageModal,
        applyMessageDeleted: applyMessageDeleted,
        updatePinnedBar: updatePinnedBar,
        unpinCurrentMessage: unpinCurrentMessage,
        hideChat: hideChat,
        updateChatPinBadge: updateChatPinBadge,
        closeListContextMenu: closeListContextMenu,
    };

    document.addEventListener('DOMContentLoaded', function () {
        if (window.__chatSocialUiBound) return;
        window.__chatSocialUiBound = true;

        initListContextMenuGlobalClose();
        bindChatListContextMenu();
        bindContactsModalContextMenu();
        resortChatItems();

        const pinnedMain = document.getElementById('chat-pinned-bar-main');
        const pinnedClose = document.getElementById('chat-pinned-bar-close');
        if (pinnedMain && !pinnedMain.dataset.bound) {
            pinnedMain.dataset.bound = '1';
            pinnedMain.addEventListener('click', scrollToPinnedMessage);
            pinnedMain.addEventListener('keydown', function (e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    scrollToPinnedMessage();
                }
            });
        }
        if (pinnedClose && !pinnedClose.dataset.bound) {
            pinnedClose.dataset.bound = '1';
            pinnedClose.addEventListener('click', function (e) {
                e.stopPropagation();
                unpinCurrentMessage();
            });
        }
        if (document.getElementById('chat-pinned-bar')) {
            loadPinnedMessage();
        }

        const contactsModal = document.getElementById('contacts-modal');
        if (contactsModal) {
            contactsModal.addEventListener('click', function (e) {
                if (e.target === contactsModal) window.closeContactsModal();
            });
        }
        document.getElementById('contacts-modal-close')?.addEventListener('click', window.closeContactsModal);
    });
})();
