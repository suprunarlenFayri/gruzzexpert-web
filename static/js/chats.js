(function () {
    'use strict';

    let selectedGroupUserIds = [];

    function escapeHtml(text) {
        if (!text) return '';
        return String(text)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function setGroupSubmitEnabled() {
        const btn = document.getElementById('create-group-submit-btn');
        if (btn) btn.disabled = selectedGroupUserIds.length === 0;
    }

    function filterGroupUsers() {
        const searchInput = document.getElementById('groupUserSearch');
        const query = (searchInput ? searchInput.value : '').trim().toLowerCase();
        document.querySelectorAll('#group-users-list .group-user-item').forEach(function (item) {
            const name = (item.dataset.searchName || item.querySelector('.user-name')?.textContent || '').toLowerCase();
            item.style.display = !query || name.includes(query) ? '' : 'none';
        });
    }

    function toggleGroupUser(userId, itemEl) {
        const id = parseInt(userId, 10);
        if (!id) return;
        const idx = selectedGroupUserIds.indexOf(id);
        if (idx >= 0) {
            selectedGroupUserIds.splice(idx, 1);
        } else {
            selectedGroupUserIds.push(id);
        }
        const btn = itemEl || document.querySelector(`#group-users-list .group-user-item[data-user-id="${id}"]`);
        if (btn) {
            const active = selectedGroupUserIds.includes(id);
            btn.classList.toggle('active', active);
            btn.setAttribute('aria-selected', active ? 'true' : 'false');
        }
        setGroupSubmitEnabled();
    }

    function bindCreateGroupModal() {
        const list = document.getElementById('group-users-list');
        const search = document.getElementById('groupUserSearch');
        if (list && !list.dataset.bound) {
            list.dataset.bound = '1';
            list.addEventListener('click', function (e) {
                const item = e.target.closest('.group-user-item');
                if (!item || !item.dataset.userId) return;
                toggleGroupUser(item.dataset.userId, item);
            });
        }
        if (search && !search.dataset.bound) {
            search.dataset.bound = '1';
            search.addEventListener('input', filterGroupUsers);
        }
    }

    window.openCreateGroupModal = function () {
        const modal = document.getElementById('createGroupModal');
        if (!modal) return;
        selectedGroupUserIds = [];
        document.querySelectorAll('#group-users-list .group-user-item').forEach(function (item) {
            item.classList.remove('active');
            item.setAttribute('aria-selected', 'false');
            item.style.display = '';
        });
        const nameInput = document.getElementById('groupNameInput');
        const searchInput = document.getElementById('groupUserSearch');
        if (nameInput) nameInput.value = '';
        if (searchInput) searchInput.value = '';
        setGroupSubmitEnabled();
        modal.hidden = false;
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
        bindCreateGroupModal();
        if (typeof window.refreshIcons === 'function') window.refreshIcons(modal);
    };

    window.filterGroupUsers = filterGroupUsers;

    window.closeCreateGroupModal = function () {
        const modal = document.getElementById('createGroupModal');
        if (!modal) return;
        modal.classList.remove('active');
        document.body.style.overflow = '';
        selectedGroupUserIds = [];
        setTimeout(function () {
            if (!modal.classList.contains('active')) modal.hidden = true;
        }, 220);
    };

    window.submitCreateGroup = function () {
        const name = document.getElementById('groupNameInput')?.value.trim();
        if (!name) {
            alert('Введите название группы');
            return;
        }
        if (!selectedGroupUserIds.length) {
            alert('Выберите хотя бы одного участника');
            return;
        }

        const submitBtn = document.getElementById('create-group-submit-btn');
        if (submitBtn) submitBtn.disabled = true;

        fetch('/chats/create_group', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
            body: JSON.stringify({ name: name, user_ids: selectedGroupUserIds }),
        })
            .then(function (res) { return res.json().then(function (data) { return { res: res, data: data }; }); })
            .then(function (_ref) {
                const res = _ref.res;
                const data = _ref.data;
                if (res.ok && data.success && data.chat_id) {
                    closeCreateGroupModal();
                    window.location.replace('/chat/' + data.chat_id);
                    return;
                }
                alert(data.error || 'Ошибка при создании группы');
                setGroupSubmitEnabled();
            })
            .catch(function (err) {
                console.error(err);
                alert('Ошибка сети');
                setGroupSubmitEnabled();
            });
    };

    document.addEventListener('DOMContentLoaded', bindCreateGroupModal);

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
            if (typeof window.closeVideoPlayer === 'function') window.closeVideoPlayer();
            if (typeof window.closeCreateGroupModal === 'function') window.closeCreateGroupModal();
        }
    });
})();

window.playChatVideo = function (videoUrl) {
    const modal = document.getElementById('videoPlayerModal');
    const videoSource = document.getElementById('modalVideoSource');
    if (!modal || !videoSource || !videoUrl) return;
    videoSource.src = videoUrl;
    videoSource.load();
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
    videoSource.play().catch(function () { /* autoplay policy */ });
};

window.closeVideoPlayer = function () {
    const modal = document.getElementById('videoPlayerModal');
    const videoSource = document.getElementById('modalVideoSource');
    if (modal && videoSource) {
        videoSource.pause();
        videoSource.removeAttribute('src');
        videoSource.load();
        modal.style.display = 'none';
        document.body.style.overflow = '';
    }
};

window.openNewChatModal = function () {
    const fab = document.querySelector('.chat-fab-container');
    const url = fab && fab.dataset.newChatUrl;
    if (url) window.location.href = url;
};