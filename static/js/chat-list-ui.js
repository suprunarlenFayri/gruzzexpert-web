/**
 * Список чатов в сайдбаре: поиск, фильтрация, индикатор «печатает…»
 */
(function () {
    'use strict';

    function collectChatSearchText(item) {
        const parts = [];
        const name = item.querySelector('.chat-name');
        const preview = item.querySelector('.chat-preview');
        if (name) parts.push(name.textContent);
        if (preview && !preview.classList.contains('is-typing')) parts.push(preview.textContent);
        return parts.join(' ').trim().toLowerCase();
    }

    window.ChatListUI = {
        filterChatList(query) {
            const q = (query || '').trim().toLowerCase();
            document.querySelectorAll('.chat-item[data-chat-id]').forEach((item) => {
                if (!q) {
                    item.style.display = '';
                    return;
                }
                const haystack = item.dataset.searchText || collectChatSearchText(item);
                if (!item.dataset.searchText) {
                    item.dataset.searchText = haystack;
                }
                item.style.display = haystack.includes(q) ? '' : 'none';
            });

            document.querySelectorAll('.chat-group-section').forEach((section) => {
                const visible = section.querySelectorAll('.chat-item[data-chat-id]');
                const anyVisible = Array.from(visible).some((el) => el.style.display !== 'none');
                section.style.display = anyVisible ? '' : 'none';
            });
        },

        setChatTyping(chatId, isTyping, userName) {
            const item = document.querySelector(`.chat-item[data-chat-id="${chatId}"]`);
            if (!item) return;
            const preview = item.querySelector('.chat-preview');
            if (!preview) return;

            if (isTyping) {
                if (!preview.dataset.prevText) {
                    preview.dataset.prevText = preview.textContent;
                }
                preview.textContent = `${userName || 'Собеседник'} печатает…`;
                preview.classList.add('is-typing');
            } else if (preview.dataset.prevText) {
                preview.textContent = preview.dataset.prevText;
                preview.classList.remove('is-typing');
            }
        },
    };

    function toggleSidebarChatSearch() {
        const expandable = document.getElementById('chatSearchExpandable');
        const searchInput = document.getElementById('chat-list-search');
        if (!expandable) return false;

        const willOpen = !expandable.classList.contains('is-open');
        expandable.classList.toggle('is-open', willOpen);

        if (willOpen && searchInput) {
            searchInput.focus();
        }
        if (!willOpen && searchInput) {
            searchInput.value = '';
            window.ChatListUI.filterChatList('');
        }
        return true;
    }

    function initSidebarChatSearch() {
        const searchBtn = document.getElementById('search-chats-btn');
        const searchInput = document.getElementById('chat-list-search');

        if (searchBtn && !searchBtn.dataset.bound) {
            searchBtn.dataset.bound = '1';
            searchBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                toggleSidebarChatSearch();
            });
        }

        if (searchInput && !searchInput.dataset.bound) {
            searchInput.dataset.bound = '1';
            searchInput.addEventListener('input', () => {
                window.ChatListUI.filterChatList(searchInput.value);
            });
        }
    }

    function initInChatSearchFallback() {
        const searchBtn = document.getElementById('chat-search-btn');
        const searchBar = document.getElementById('chat-search-bar');
        const searchInput = document.getElementById('chat-search-input');
        if (!searchBtn || !searchBar || searchBtn.dataset.fallbackBound) return;
        if (searchBtn.onclick) return;

        searchBtn.dataset.fallbackBound = '1';
        searchBtn.addEventListener('click', (e) => {
            e.preventDefault();
            const visible = searchBar.style.display === 'flex';
            searchBar.style.display = visible ? 'none' : 'flex';
            if (!visible && searchInput) searchInput.focus();
        });
    }

    document.addEventListener('DOMContentLoaded', () => {
        initSidebarChatSearch();
        initInChatSearchFallback();
        if (typeof window.refreshGruzzIcons === 'function') {
            window.refreshGruzzIcons();
        }
    });

    window.toggleSidebarChatSearch = toggleSidebarChatSearch;
})();
