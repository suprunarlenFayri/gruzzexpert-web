/**
 * CHAT.JS - Refactored logic for the open chat.
 * Uses the GLOBAL socket from realtime.js.
 */

// === Global Reply State & Window Helpers ===
window.currentReplyParentId = null;

function setReplyState(parentId, authorName, text) {
    window.currentReplyParentId = parentId;
    const previewBar = document.getElementById('chat-reply-preview');
    const messageForm = document.getElementById('message-form');
    const userEl = document.getElementById('reply-preview-user');
    const textEl = document.getElementById('reply-preview-text');
    
    if (userEl) userEl.textContent = authorName || 'Пользователь';
    if (textEl) textEl.textContent = text ? text.substring(0, 60) + (text.length > 60 ? '...' : '') : '...';
    
    if (previewBar) {
        previewBar.style.display = 'flex';
        if (messageForm) {
            messageForm.classList.add('has-reply');
        }
        if (typeof window.refreshGruzzIcons === 'function') window.refreshGruzzIcons();
    }

    focusChatInput();
}

/** Фокус в поле ввода после «Ответить» (ПКМ / dblclick). */
function focusChatInput() {
    const chatInput = document.getElementById('chat-message-input')
        || document.getElementById('message-input')
        || document.querySelector('.chat-input textarea.message-input')
        || document.querySelector('.chat-input-field');
    if (!chatInput) return;
    requestAnimationFrame(() => {
        chatInput.focus();
        if (typeof chatInput.selectionStart === 'number') {
            const len = chatInput.value.length;
            chatInput.selectionStart = chatInput.selectionEnd = len;
        }
    });
}

window.focusChatInput = focusChatInput;

function cancelReply() {
    window.currentReplyParentId = null;
    const previewBar = document.getElementById('chat-reply-preview');
    const messageForm = document.getElementById('message-form');
    
    if (previewBar) previewBar.style.display = 'none';
    if (messageForm) {
        messageForm.classList.remove('has-reply');
    }
}

window.scrollToMessage = function(messageId, event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }

    if (!messageId) return;

    const id = String(messageId).trim();
    const targetMessage = document.getElementById(`msg-${id}`) || 
                          document.querySelector(`[data-message-id="${id}"]`);

    if (targetMessage) {
        // Нативный встроенный скролл — работает всегда безотказно
        targetMessage.scrollIntoView({ behavior: 'smooth', block: 'center' });

        // Ищем баббл для вспышки
        const bubble = targetMessage.querySelector('.message-bubble') || targetMessage;

        if (bubble && bubble.classList) {
            // Сбрасываем старую анимацию
            bubble.classList.remove('message-highlight-flash');
            
            // Магия для перезапуска CSS
            void bubble.offsetWidth; 
            
            // Запускаем золотую вспышку
            bubble.classList.add('message-highlight-flash');

            // Убираем класс после завершения
            setTimeout(() => {
                if (bubble && bubble.classList) {
                    bubble.classList.remove('message-highlight-flash');
                }
            }, 1200);
        }
    } else {
        console.warn(`[ScrollToMessage] Сообщение ${id} не найдено.`);
    }
};

function scrollToMessage(messageId, event) {
    window.scrollToMessage(messageId, event);
}

function getMessageData(target) {
    const messageRow = target.closest('.message, .message-bubble, [id^="msg-"], [data-message-id]');
    if (!messageRow) return null;

    let msgId = null;
    const idAttr = messageRow.getAttribute('id');
    if (idAttr && idAttr.startsWith('msg-')) {
        msgId = idAttr.replace('msg-', '');
    }
    if (!msgId) {
        msgId = messageRow.dataset.messageId || messageRow.dataset.id;
    }
    if (!msgId) return null;

    const userSender = messageRow.querySelector('.message-sender, .sender-name, .author-name')?.textContent || 'Пользователь';
    const msgText = messageRow.querySelector('.message-text, .text-content')?.textContent || 'Сообщение';

    return { id: msgId, author: userSender.trim(), text: msgText.trim() };
}

// Навешиваем слушатели на уровне документа (работают всегда, даже после перезагрузки)
document.addEventListener('dblclick', function(e) {
    const msgData = getMessageData(e.target);
    if (!msgData) return;
    e.preventDefault();
    e.stopPropagation();
    setReplyState(msgData.id, msgData.author, msgData.text);
});

document.addEventListener('click', function(e) {
    if (e.target.closest('#cancel-reply-btn')) {
        e.preventDefault();
        cancelReply();
    }
});


document.addEventListener('DOMContentLoaded', () => {
    if (!window.ChatConfig) {
        console.error('ChatConfig not found');
        return;
    }

    const UI_ELEMENTS = {
        messageForm: document.getElementById('message-form'),
        messageInput: document.getElementById('message-input'),
        messagesContainer: document.getElementById('messages-container'),
        messagesArea: document.querySelector('.messages-area'),
        sendBtn: document.getElementById('send-btn'),
        filesPreview: document.getElementById('files-preview'),
        fileInput: document.getElementById('file-input'),
        attachBtn: document.getElementById('attach-btn'),
        typingIndicator: document.getElementById('typing-indicator'),
        lightbox: document.getElementById('image-lightbox'),
        lightboxImg: document.querySelector('#image-lightbox img'),
        lightboxCloseBtn: document.querySelector('#image-lightbox .close-lightbox'),
        searchBtn: document.getElementById('chat-search-btn'),
        searchBar: document.getElementById('chat-search-bar'),
        searchInput: document.getElementById('chat-search-input'),
        searchCount: document.getElementById('chat-search-count'),
        searchPrev: document.getElementById('chat-search-prev'),
        searchNext: document.getElementById('chat-search-next'),
        searchClose: document.getElementById('chat-search-close'),
        currentDateLabel: document.getElementById('chat-current-date-label'),
        datePrev: document.getElementById('chat-date-prev'),
        dateNext: document.getElementById('chat-date-next')
    };

    let selectedFiles = [];

    const CHAT_ALLOWED_MIME_PREFIXES = ['image/', 'video/'];
    const CHAT_ALLOWED_MIMES = new Set([
        'video/mp4', 'video/quicktime', 'video/webm', 'video/x-msvideo',
        'video/x-m4v', 'application/pdf',
    ]);
    const CHAT_ALLOWED_EXTENSIONS = new Set([
        'png', 'jpg', 'jpeg', 'jfif', 'gif', 'webp',
        'mp4', 'mov', 'avi', 'webm', 'm4v', 'mkv', 'mpeg', 'mpg', '3gp',
        'pdf', 'doc', 'docx', 'xls', 'xlsx',
    ]);

    function isAllowedChatFile(file) {
        if (!file) return false;
        const mime = (file.type || '').toLowerCase();
        if (mime && CHAT_ALLOWED_MIME_PREFIXES.some((p) => mime.startsWith(p))) return true;
        if (mime && CHAT_ALLOWED_MIMES.has(mime)) return true;
        const ext = (file.name || '').split('.').pop().toLowerCase();
        return CHAT_ALLOWED_EXTENSIONS.has(ext);
    }
    let lastDateLabel = null;
    const loadedImages = new Set();
    const missingImageVariants = new Set();
    const attachmentsRenderCache = new Map();
    const attachmentHtmlCache = new Map();
    const renderedMessageKeys = new Set();

    // === Search State ===
    let searchMatches = [];
    let currentSearchIndex = -1;
    const originalTexts = new Map();

    // === Date Navigation State ===
    let dateElements = [];
    let currentDayIndex = -1;

    // === GruzzIcons Pack (Search Only) ===
    const GruzzIcons = {
        search: `<svg width="100%" height="100%" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="square"><circle cx="10" cy="10" r="6"/><line x1="14.5" y1="14.5" x2="20" y2="20"/><circle cx="10" cy="10" r="1.2" fill="currentColor"/></svg>`,
        'arrow-up': `<svg width="100%" height="100%" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="square" stroke-linejoin="miter"><path d="M18 14l-6-6-6 6"/></svg>`,
        'arrow-down': `<svg width="100%" height="100%" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="square" stroke-linejoin="miter"><path d="M6 10l6 6 6-6"/></svg>`,
        close: `<svg width="100%" height="100%" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="square"><line x1="6" y1="6" x2="18" y2="18"/><line x1="18" y1="6" x2="6" y2="18"/></svg>`
    };

    window.refreshGruzzIcons = function() {
        document.querySelectorAll('[data-gruzz-icon]').forEach(el => {
            const iconName = el.getAttribute('data-gruzz-icon');
            if (GruzzIcons[iconName]) {
                el.innerHTML = GruzzIcons[iconName];
            }
        });
    };

    // === Инициализация поиска ===
    function clearSearchHighlights() {
        originalTexts.forEach((originalHtml, element) => {
            if (element && element.parentNode) {
                element.innerHTML = originalHtml;
            }
        });
        originalTexts.clear();
        searchMatches = [];
        currentSearchIndex = -1;
        if (UI_ELEMENTS.searchCount) UI_ELEMENTS.searchCount.textContent = '0 / 0';
    }

    function updateDayNavigation() {
        if (!UI_ELEMENTS.searchBar || !dateElements.length) return;
        if (currentDayIndex < 0) currentDayIndex = 0;
        if (currentDayIndex >= dateElements.length) currentDayIndex = dateElements.length - 1;

        const currentEl = dateElements[currentDayIndex];
        if (!currentEl) return;

        const labelText = currentEl.textContent.trim();
        if (UI_ELEMENTS.currentDateLabel) UI_ELEMENTS.currentDateLabel.textContent = labelText;

        currentEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
        currentEl.classList.add('flash-highlight');
        setTimeout(() => {
            currentEl.classList.remove('flash-highlight');
        }, 1200);
    }

    function highlightMatches() {
        clearSearchHighlights();
        const query = UI_ELEMENTS.searchInput.value.trim();
        if (query.length < 2) {
            if (UI_ELEMENTS.searchCount) UI_ELEMENTS.searchCount.textContent = '0 / 0';
            return;
        }

        const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
        const textNodes = document.querySelectorAll('.message-text');

        textNodes.forEach(node => {
            if (!originalTexts.has(node)) {
                originalTexts.set(node, node.innerHTML);
            }
            const originalHtml = originalTexts.get(node);
            const newHtml = originalHtml.replace(regex, '<mark class="search-highlight">$1</mark>');
            if (newHtml !== originalHtml) {
                node.innerHTML = newHtml;
                const marks = node.querySelectorAll('mark.search-highlight');
                marks.forEach(mark => searchMatches.push(mark));
            }
        });

        if (searchMatches.length > 0) {
            currentSearchIndex = 0;
            highlightActiveMatch();
        }
        updateSearchCounter();
    }

    function updateSearchCounter() {
        if (!UI_ELEMENTS.searchCount) return;
        if (searchMatches.length === 0) {
            UI_ELEMENTS.searchCount.textContent = '0 / 0';
        } else {
            UI_ELEMENTS.searchCount.textContent = `${currentSearchIndex + 1} / ${searchMatches.length}`;
        }
    }

    function highlightActiveMatch() {
        document.querySelectorAll('mark.search-highlight.active-highlight').forEach(el => el.classList.remove('active-highlight'));
        if (currentSearchIndex < 0 || !searchMatches[currentSearchIndex]) return;

        const activeMark = searchMatches[currentSearchIndex];
        activeMark.classList.add('active-highlight');

        const messageEl = activeMark.closest('.message');
        if (messageEl) {
            messageEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
            messageEl.classList.add('flash-highlight');
            setTimeout(() => {
                messageEl.classList.remove('flash-highlight');
            }, 1200);
        }
    }

    function navigateSearch(direction) {
        if (searchMatches.length === 0) return;
        currentSearchIndex += direction;
        if (currentSearchIndex >= searchMatches.length) currentSearchIndex = 0;
        if (currentSearchIndex < 0) currentSearchIndex = searchMatches.length - 1;
        highlightActiveMatch();
        updateSearchCounter();
    }

    if (UI_ELEMENTS.searchBtn) {
        UI_ELEMENTS.searchBtn.onclick = () => {
            const isVisible = UI_ELEMENTS.searchBar.style.display === 'flex';
            UI_ELEMENTS.searchBar.style.display = isVisible ? 'none' : 'flex';
            if (!isVisible) {
                UI_ELEMENTS.searchInput.focus();
                dateElements = Array.from(document.querySelectorAll('.chat-date-separator, .date-divider'));
                currentDayIndex = dateElements.length - 1;
                updateDayNavigation();
            } else {
                clearSearchHighlights();
            }
        };
    }

    if (UI_ELEMENTS.searchInput) {
        UI_ELEMENTS.searchInput.oninput = () => highlightMatches();
        UI_ELEMENTS.searchInput.onkeydown = (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                navigateSearch(1);
            }
        };
    }

    if (UI_ELEMENTS.searchPrev) UI_ELEMENTS.searchPrev.onclick = () => navigateSearch(-1);
    if (UI_ELEMENTS.searchNext) UI_ELEMENTS.searchNext.onclick = () => navigateSearch(1);

    // === Навигация по датам (стрелки календаря) ===
    if (UI_ELEMENTS.datePrev) {
        UI_ELEMENTS.datePrev.onclick = (e) => {
            e.preventDefault();
            if (dateElements.length === 0) {
                dateElements = Array.from(document.querySelectorAll('.chat-date-separator, .date-divider'));
            }
            if (dateElements.length === 0) return;

            currentDayIndex--;
            updateDayNavigation();
        };
    }

    if (UI_ELEMENTS.dateNext) {
        UI_ELEMENTS.dateNext.onclick = (e) => {
            e.preventDefault();
            if (dateElements.length === 0) {
                dateElements = Array.from(document.querySelectorAll('.chat-date-separator, .date-divider'));
            }
            if (dateElements.length === 0) return;

            currentDayIndex++;
            updateDayNavigation();
        };
    }

    if (UI_ELEMENTS.searchClose) {
        UI_ELEMENTS.searchClose.onclick = () => {
            UI_ELEMENTS.searchBar.style.display = 'none';
            clearSearchHighlights();
            if (UI_ELEMENTS.searchInput) UI_ELEMENTS.searchInput.value = '';
        };
    }

    // Экспортируем функцию кастомного контекстного меню во внешнюю область видимости window
    function showContextMenu(e, msgId, userSender, msgText) {
        const oldMenu = document.getElementById('custom-context-menu');
        if (oldMenu) oldMenu.remove();

        const menu = document.createElement('div');
        menu.id = 'custom-context-menu';
        menu.style.cssText = `position: absolute; left: ${e.pageX}px; top: ${e.pageY}px; background: var(--bg-secondary, #1e1e1e); border: 1px solid var(--border, #3a3a3a); border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); z-index: 10000; padding: 6px 0; min-width: 180px; font-size: 14px;`;
        
        const menuItems = [
            { label: 'Ответить', action: () => setReplyState(msgId, userSender, msgText) },
            { label: 'Закрепить', action: () => console.log('Закрепить:', msgId) },
            { label: 'Переслать', action: () => ChatUI.openForwardModal(msgId) }
        ];

        menuItems.forEach(item => {
            const div = document.createElement('div');
            div.style.cssText = `padding: 8px 16px; cursor: pointer; color: var(--text-primary, #fff);`;
            div.innerHTML = item.label;
            div.onmouseover = () => div.style.background = 'var(--bg-tertiary, #2a2a2a)';
            div.onmouseout = () => div.style.background = 'transparent';
            div.onclick = () => {
                item.action();
                menu.remove();
            };
            menu.appendChild(div);
        });

        document.body.appendChild(menu);

        setTimeout(() => {
            document.addEventListener('click', function handler(ev) {
                if (!menu.contains(ev.target)) {
                    menu.remove();
                    document.removeEventListener('click', handler);
                }
            }, { once: true });
        }, 0);
    }
    window.showContextMenuGlobal = showContextMenu;

    // === Reply Jump Logic ===
    document.addEventListener('click', function(e) {
        const replyLink = e.target.closest('.message-reply-link');
        if (!replyLink) return;

        const targetId = replyLink.dataset.targetId;
        if (!targetId) return;

        const originalMessage = document.querySelector(`[data-message-key*="${targetId}"], [data-message-id="${targetId}"], [id="msg-${targetId}"]`);
        if (originalMessage) {
            originalMessage.scrollIntoView({ behavior: 'smooth', block: 'center' });
            originalMessage.style.transition = 'all 0.3s ease';
            originalMessage.style.backgroundColor = 'rgba(255, 255, 255, 0.15)';
            setTimeout(() => {
                originalMessage.style.backgroundColor = 'transparent';
            }, 1200);
        }
    });

    // === Date Navigation Bindings ===
    document.querySelectorAll('.chat-date-separator, .date-divider').forEach((el, index) => {
        el.style.cursor = 'pointer';
        el.onclick = () => {
            if (UI_ELEMENTS.searchBar.style.display !== 'flex') {
                UI_ELEMENTS.searchBar.style.display = 'flex';
            }
            if (dateElements.length === 0) {
                dateElements = Array.from(document.querySelectorAll('.chat-date-separator, .date-divider'));
            }
            currentDayIndex = index;
            updateDayNavigation();
            UI_ELEMENTS.searchInput.focus();
        };
    });

    // === Custom Date Picker Logic (GruzzDatePicker) ===
    const dateLabel = document.getElementById('chat-current-date-label');
    const dropdown = document.getElementById('custom-datepicker-dropdown');
    const dateWrapper = document.querySelector('.chat-date-wrapper');

    if (dateLabel && dropdown && dateWrapper && window.GruzzDatePicker) {
        window.GruzzDatePicker.init(dateWrapper, {
            changeMonth: true,
            changeYear: true,
            trigger: dateLabel,
            dropdown: dropdown,
            hiddenInput: null,
            placeholder: 'Дата',
            onSelect: (iso, shortLabel) => {
                const allDivs = Array.from(document.querySelectorAll('div, span, p'));
                const foundSeparator = allDivs.find(el => {
                    const hasClass = el.className && (
                        el.className.includes('date') ||
                        el.className.includes('separator') ||
                        el.className.includes('divider')
                    );
                    return hasClass && el.textContent.toLowerCase().includes(shortLabel.toLowerCase());
                });

                if (foundSeparator) {
                    foundSeparator.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    foundSeparator.style.transition = 'all 0.3s ease';
                    foundSeparator.style.backgroundColor = 'rgba(255, 255, 255, 0.15)';
                    setTimeout(() => {
                        foundSeparator.style.backgroundColor = 'transparent';
                    }, 1500);

                    dateLabel.textContent = shortLabel;
                }
            }
        });
    }

    // === ChatUI Module ===
    const ChatUI = {
        scrollToBottom: () => {
            if (UI_ELEMENTS.messagesContainer) {
                UI_ELEMENTS.messagesContainer.scrollTop = UI_ELEMENTS.messagesContainer.scrollHeight;
                ChatUI.updateScrollBottomBtn();
            }
        },

        updateScrollBottomBtn: () => {
            const el = UI_ELEMENTS.messagesContainer;
            const btn = document.getElementById('chat-scroll-bottom-btn');
            if (!el || !btn) return;
            const dist = el.scrollHeight - el.scrollTop - el.clientHeight;
            btn.classList.toggle('is-visible', dist > 120);
        },

        updateSendState: () => {
            const hasText = UI_ELEMENTS.messageInput && UI_ELEMENTS.messageInput.value.trim().length > 0;
            const hasFiles = selectedFiles.length > 0;
            if (UI_ELEMENTS.sendBtn) {
                UI_ELEMENTS.sendBtn.disabled = !(hasText || hasFiles);
            }
        },

        resetMessageInput: () => {
            if (UI_ELEMENTS.messageInput) {
                UI_ELEMENTS.messageInput.value = '';
                if (window.resetMessageInputHeight) {
                    window.resetMessageInputHeight(UI_ELEMENTS.messageInput);
                }
            }
            if (UI_ELEMENTS.filesPreview) {
                UI_ELEMENTS.filesPreview.innerHTML = '';
                UI_ELEMENTS.filesPreview.style.display = 'none';
            }
            selectedFiles = [];
            ChatUI.updateSendState();
        },

        autoResizeTextarea: () => {
            if (UI_ELEMENTS.messageInput && window.autoResizeTextarea) {
                window.autoResizeTextarea(UI_ELEMENTS.messageInput);
            }
        },

        displayTypingIndicator: (userName, isTyping) => {
            const headerTyping = document.getElementById('chat-header-typing');
            const headerStatus = document.getElementById('chat-header-status');
            const legacyBox = UI_ELEMENTS.typingIndicator;
            if (legacyBox) legacyBox.style.display = 'none';

            if (isTyping) {
                if (headerTyping) {
                    headerTyping.innerHTML = `${userName || 'Собеседник'} печатает<span class="typing-dots-anim">...</span>`;
                    headerTyping.classList.add('is-visible');
                }
                if (headerStatus) headerStatus.style.display = 'none';
            } else {
                if (headerTyping) {
                    headerTyping.classList.remove('is-visible');
                    headerTyping.textContent = '';
                }
                if (headerStatus) headerStatus.style.display = '';
            }

            if (window.ChatListUI && window.ChatConfig?.chatId) {
                window.ChatListUI.setChatTyping(window.ChatConfig.chatId, isTyping, userName);
            }
        },

        renderFilesPreview: () => {
            const preview = UI_ELEMENTS.filesPreview;
            if (!preview) return;
            
            if (selectedFiles.length === 0) {
                preview.style.display = 'none';
                preview.innerHTML = '';
                return;
            }
            
            preview.style.display = 'flex';
            preview.innerHTML = '';
            
            selectedFiles.forEach((file, index) => {
                const isImage = (file.type || '').startsWith('image/');
                const isVideo = (file.type || '').startsWith('video/') || /\.(mp4|mov|webm|avi|m4v|mkv)$/i.test(file.name || '');
                const wrapper = document.createElement('div');
                wrapper.className = 'file-chip file-preview-card';

                const removeBtn = document.createElement('button');
                removeBtn.type = 'button';
                removeBtn.className = 'file-preview-remove';
                removeBtn.setAttribute('aria-label', 'Удалить файл');
                removeBtn.innerHTML = '✕';
                removeBtn.onclick = (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    selectedFiles.splice(index, 1);
                    ChatUI.renderFilesPreview();
                    ChatUI.updateSendState();
                };

                if (isImage || isVideo) {
                    const thumb = document.createElement('div');
                    thumb.className = 'file-preview-thumb';
                    if (isImage) {
                        const img = document.createElement('img');
                        img.src = URL.createObjectURL(file);
                        img.alt = '';
                        thumb.appendChild(img);
                    } else {
                        const vid = document.createElement('video');
                        vid.className = 'file-chip-video';
                        vid.src = URL.createObjectURL(file);
                        vid.muted = true;
                        vid.playsInline = true;
                        vid.preload = 'metadata';
                        vid.setAttribute('playsinline', '');
                        thumb.appendChild(vid);
                    }
                    thumb.appendChild(removeBtn);
                    wrapper.appendChild(thumb);
                } else {
                    const thumb = document.createElement('div');
                    thumb.className = 'file-preview-thumb file-preview-thumb--doc';
                    const icon = document.createElement('span');
                    icon.className = 'file-preview-doc-icon';
                    icon.textContent = '📄';
                    thumb.appendChild(icon);
                    thumb.appendChild(removeBtn);
                    wrapper.appendChild(thumb);
                    const nameSpan = document.createElement('span');
                    nameSpan.className = 'file-preview-name';
                    nameSpan.textContent = file.name.length > 18 ? file.name.substring(0, 15) + '...' : file.name;
                    wrapper.appendChild(nameSpan);
                }

                preview.appendChild(wrapper);
            });
        },

        addSelectedFiles: (files) => {
            const incoming = Array.from(files || []);
            const valid = incoming.filter(isAllowedChatFile);
            const rejected = incoming.length - valid.length;
            if (rejected > 0) {
                alert('Некоторые файлы не поддерживаются. Допустимы изображения и видео (MP4, MOV, WebM), а также документы до 200 МБ.');
            }
            if (valid.length) {
                selectedFiles = valid;
                ChatUI.renderFilesPreview();
                ChatUI.updateSendState();
            }
        },

        parseAccentRgb: (accent) => {
            const hex = accent.match(/^#?([0-9a-f]{6})$/i);
            if (hex) {
                const n = parseInt(hex[1], 16);
                return { r: (n >> 16) & 255, g: (n >> 8) & 255, b: n & 255 };
            }
            const rgb = accent.match(/rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/i);
            if (rgb) return { r: +rgb[1], g: +rgb[2], b: +rgb[3] };
            return null;
        },

        syncMyBubbleContrast: (messageEl) => {
            if (!messageEl || !messageEl.classList.contains('my')) return;
            if (window.CSS && CSS.supports && CSS.supports('color', 'color-contrast(white vs black, white)')) {
                return;
            }
            const accent = getComputedStyle(document.documentElement).getPropertyValue('--accent').trim();
            const rgb = ChatUI.parseAccentRgb(accent);
            if (!rgb) return;
            const luminance = (0.299 * rgb.r + 0.587 * rgb.g + 0.114 * rgb.b) / 255;
            messageEl.classList.toggle('message-bubble-light', luminance > 0.58);
        },

        syncAllMyBubblesContrast: () => {
            document.querySelectorAll('.chat-container .message.my').forEach(ChatUI.syncMyBubbleContrast);
        },

        currentGalleryLinks: [],
        currentImageIndex: 0,

        openLightbox(clickedLink) {
            const href = clickedLink.getAttribute('href');
            if (!href) return;

            const msgItem = clickedLink.closest('.message-item') || clickedLink.closest('.message');
            let gallery = [href];
            if (msgItem) {
                ChatUI.currentGalleryLinks = Array.from(msgItem.querySelectorAll('.chat-image-link'));
                gallery = ChatUI.currentGalleryLinks
                    .map(function (l) { return l.getAttribute('href'); })
                    .filter(Boolean);
            } else {
                ChatUI.currentGalleryLinks = [clickedLink];
            }

            if (typeof window.openImageLightbox === 'function') {
                window.openImageLightbox(href, gallery);
                return;
            }

            const lb = document.getElementById('image-lightbox');
            if (!lb) return;
            const imgEl = document.getElementById('lightbox-img');
            ChatUI.currentImageIndex = ChatUI.currentGalleryLinks.indexOf(clickedLink);
            if (imgEl) imgEl.src = href;
            lb.style.display = 'flex';
            const leftArrow = lb.querySelector('.left-arrow');
            const rightArrow = lb.querySelector('.right-arrow');
            const showArrows = ChatUI.currentGalleryLinks.length > 1;
            if (leftArrow) leftArrow.style.display = showArrows ? 'block' : 'none';
            if (rightArrow) rightArrow.style.display = showArrows ? 'block' : 'none';
            ChatUI.renderLightboxThumbnails();
        },

        nextImage() {
            if (ChatUI.currentGalleryLinks.length <= 1) return;
            const newIndex = (ChatUI.currentImageIndex + 1) % ChatUI.currentGalleryLinks.length;
            ChatUI.switchImage(newIndex);
        },

        prevImage() {
            if (ChatUI.currentGalleryLinks.length <= 1) return;
            const newIndex = (ChatUI.currentImageIndex - 1 + ChatUI.currentGalleryLinks.length) % ChatUI.currentGalleryLinks.length;
            ChatUI.switchImage(newIndex);
        },

        switchImage(index) {
            if (!ChatUI.currentGalleryLinks[index]) return;
            ChatUI.currentImageIndex = index;
            const link = ChatUI.currentGalleryLinks[index];
            const imgEl = document.getElementById('lightbox-img');
            if (imgEl) imgEl.src = link.getAttribute('href');
            ChatUI.renderLightboxThumbnails();
        },

        renderLightboxThumbnails() {
            const container = document.getElementById('lightbox-thumbnails');
            if (!container) return;
            container.innerHTML = '';

            ChatUI.currentGalleryLinks.forEach((link, index) => {
                const thumbImg = document.createElement('img');
                const originalImg = link.querySelector('img');
                thumbImg.src = originalImg ? originalImg.src : link.getAttribute('href');
                thumbImg.style.cssText = 'width:50px;height:50px;object-fit:cover;border-radius:4px;cursor:pointer;transition:all 0.2s;opacity:0.6;';

                if (index === ChatUI.currentImageIndex) {
                    thumbImg.style.opacity = '1';
                    thumbImg.style.border = '2px solid #fff';
                    thumbImg.style.transform = 'scale(1.1)';
                }

                thumbImg.onclick = () => ChatUI.switchImage(index);
                container.appendChild(thumbImg);
            });
        },

        closeLightbox() {
            if (typeof window.closeImageLightbox === 'function') {
                window.closeImageLightbox();
            }
            ChatUI.currentGalleryLinks = [];
            ChatUI.currentImageIndex = 0;
        }
    };

    // === ChatRenderer Module ===
    const ChatRenderer = {
        CHAT_RU_MONTHS_GENITIVE: [
            'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
            'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря',
        ],

        messageDateSeparatorLabel: (raw) => {
            const labelFromParts = (y, monthOneBased, d) => {
                return `${d} ${ChatRenderer.CHAT_RU_MONTHS_GENITIVE[monthOneBased - 1]} ${y} г.`;
            };
            const fromDate = (d) => {
                if (!d || Number.isNaN(d.getTime())) return null;
                return labelFromParts(d.getFullYear(), d.getMonth() + 1, d.getDate());
            };
            if (raw instanceof Date) {
                return fromDate(raw) || '';
            }
            if (raw != null && String(raw).trim() !== '') {
                const s = String(raw).trim();
                if (s.includes('T')) {
                    const parsed = fromDate(new Date(s));
                    if (parsed) return parsed;
                }
                const iso = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
                if (iso) {
                    return labelFromParts(parseInt(iso[1], 10), parseInt(iso[2], 10), parseInt(iso[3], 10));
                }
                return s;
            }
            return fromDate(new Date()) || '';
        },

        formatTime: (date) => {
            const d = date instanceof Date ? date : new Date(date);
            if (!date || Number.isNaN(d.getTime())) {
                return new Date().toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
            }
            return d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
        },
        todayDateKey: () => {
            const d = new Date();
            return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
        },

        formatAttachmentSize: (bytes) => {
            if (bytes == null || bytes === '' || Number.isNaN(Number(bytes))) return '';
            const n = Number(bytes);
            if (n < 1024) return `${Math.round(n)} Б`;
            if (n < 1048576) {
                const kb = n / 1024;
                return `${(kb >= 100 ? kb.toFixed(0) : kb.toFixed(1)).replace(/\.0$/, '')} КБ`;
            }
            const mb = n / (1024 * 1024);
            return `${(mb >= 100 ? mb.toFixed(0) : mb.toFixed(1)).replace(/\.0$/, '')} МБ`;
        },

        escapeHtml: (text) => {
            if (!text) return '';
            if (window.escapeHtml) return window.escapeHtml(text);
            return String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        },

        /** Расшифрованный текст с бэкенда; enc:… — сырой шифротекст (не показываем). */
        resolvePlaintextField: (value, fallback = '') => {
            const s = String(value ?? '').trim();
            if (!s) return fallback;
            if (s.startsWith('enc:')) return fallback;
            return s;
        },

        resolveParentQuote: (data) => {
            if (!data || (!data.parent_id && !data.parent)) return null;
            const parent = data.parent || {};
            const raw =
                data.parent_text ??
                parent.plaintext_text ??
                parent.text ??
                '';
            return ChatRenderer.resolvePlaintextField(raw, 'Вложение...');
        },

        resolveAvatarUrl: (avatar) => {
            if (!avatar) return null;
            const s = String(avatar).trim();
            if (!s) return null;
            if (s.startsWith('http://') || s.startsWith('https://') || s.startsWith('/')) return s;
            let p = s.replace(/^\/+/, '').replace(/^uploads\/+/, '');
            if (!p.includes('/')) p = `avatars/${p}`;
            return `/uploads/${p}`;
        },

        normalizeFilePath: (path, fallbackPath = '') => {
            const toNormalized = (input) => {
                if (!input || input === '') return '';
                let p = String(input).trim().replace(/^\/+/, '').replace(/^uploads\/+/, '').replace(/^uploads/, '').replace(/^(uploads\/)+/, '').replace(/^\/+/, '');
                return p ? '/uploads/' + p : '';
            };
            const normalized = toNormalized(path);
            if (!normalized) return toNormalized(fallbackPath);
            if (/(?:_thumb|_opt)(?:\.[^./?#]+)?(?:[?#].*)?$/i.test(normalized) && missingImageVariants.has(normalized)) {
                return toNormalized(fallbackPath);
            }
            return normalized;
        },

        markMissingVariantPath: (path) => {
            const normalized = ChatRenderer.normalizeFilePath(path);
            if (normalized) missingImageVariants.add(normalized);
        },

        renderAttachmentSafe: (att) => att ? ChatRenderer.renderAttachments([att]) : '',

        attachmentExtension(att) {
            const src = att.file_path || att.path || att.filename || att.name || '';
            return (String(src).split('.').pop() || '').toLowerCase();
        },

        isVideoAttachment(att) {
            const ext = ChatRenderer.attachmentExtension(att);
            return att.file_type === 'video' || ['mp4', 'webm', 'mov'].includes(ext);
        },

        renderVideoPreview(att) {
            const videoUrl = ChatRenderer.escapeHtml(
                ChatRenderer.normalizeFilePath(att.file_path || att.path || '')
            );
            const fileName = ChatRenderer.escapeHtml(att.filename || att.name || 'Видео');
            return `
                <div class="chat-video-preview message-video" data-video-url="${videoUrl}" onclick="playChatVideo(this.dataset.videoUrl)">
                    <video class="message-video-player" src="${videoUrl}" preload="metadata" muted playsinline></video>
                    <div class="video-play-overlay">
                        <i data-lucide="play"></i>
                    </div>
                    <div class="video-meta-info">
                        <span class="video-name">${fileName}</span>
                    </div>
                </div>`;
        },

        renderFileCard(att) {
            const fileName = ChatRenderer.escapeHtml(att.filename || att.name || 'Файл');
            const fileSize = ChatRenderer.formatAttachmentSize(att.file_size);
            const href = att.id
                ? `/attachment/download/${att.id}`
                : ChatRenderer.escapeHtml(ChatRenderer.normalizeFilePath(att.file_path || att.path || ''));
            const downloadAttr = att.id ? ' download' : ' target="_blank"';
            const metaHtml = fileSize
                ? `<div class="file-meta">${ChatRenderer.escapeHtml(fileSize)}</div>`
                : '<div class="file-meta">Скачать файл</div>';
            return `
                <a href="${href}" class="att-item-file"${downloadAttr}>
                    <div class="att-file-icon-wrap"><i data-lucide="file-text"></i></div>
                    <div class="file-info">
                        <div class="file-name">${fileName}</div>
                        ${metaHtml}
                    </div>
                </a>`;
        },

        renderAttachments(attachments) {
            if (!attachments || attachments.length === 0) return '';
            const images = attachments.filter(att => {
                const ext = ChatRenderer.attachmentExtension(att);
                return att.file_type === 'image' || ['jpg', 'jpeg', 'png', 'gif', 'webp', 'jfif'].includes(ext);
            });
            const videos = attachments.filter(att => ChatRenderer.isVideoAttachment(att));
            const files = attachments.filter(att => !images.includes(att) && !videos.includes(att));
            
            let html = '<div class="chat-attachments">';
            if (images.length > 0) {
                html += '<div class="image-gallery-grid" style="display:flex!important; flex-wrap:wrap!important; gap:6px!important; max-width:300px!important; width:100%!important; margin-top:8px!important; border-radius:12px!important; overflow:hidden!important;">';
                images.forEach((att, index) => {
                    const rawFilePath = att.file_path || att.path || '';
                    const originalSrc = ChatRenderer.normalizeFilePath(rawFilePath);
                    const optimizedSrc = ChatRenderer.normalizeFilePath(att.optimized_path || rawFilePath, rawFilePath);
                    const thumbSrc = ChatRenderer.normalizeFilePath(att.thumbnail_path || att.optimized_path || rawFilePath, rawFilePath);
                    
                    const fullSrc = ChatRenderer.escapeHtml(optimizedSrc || originalSrc);
                    const mainSrc = ChatRenderer.escapeHtml(thumbSrc || optimizedSrc || originalSrc);
                    const isHidden = index >= 4;
                    
                    html += `
                        <div class="attachment-item image-item" style="${isHidden ? 'display: none !important;' : 'display: block !important;'} position:relative!important; flex:1 1 calc(50% - 6px)!important; min-width:130px!important; max-width:145px!important; height:110px!important; margin:0!important; padding:0!important; overflow:hidden!important; border-radius:6px!important;">
                            <a href="${fullSrc}" class="chat-image-link" style="display:block!important; width:100%!important; height:100%!important;">
                                <img src="${mainSrc}" alt="Изображение" onerror="this.src='${fullSrc}'" style="width:100%!important; height:100%!important; object-fit:cover!important; display:block!important;">
                                ${index === 3 && images.length > 4 ? `
                                    <div class="more-images-overlay" style="position:absolute!important; top:0!important; left:0!important; width:100%!important; height:100%!important; background:rgba(0,0,0,0.6)!important; backdrop-filter:blur(4px)!important; display:flex!important; justify-content:center!important; align-items:center!important; border-radius:6px!important; pointer-events:none!important;">
                                        <span style="color:#ffffff!important; font-size:22px!important; font-weight:700!important;">+${images.length - 4}</span>
                                    </div>
                                ` : ''}
                            </a>
                        </div>`;
                });
                html += '</div>';
            }
            if (videos.length > 0) {
                html += '<div class="chat-videos-list">';
                videos.forEach(att => {
                    html += ChatRenderer.renderVideoPreview(att);
                });
                html += '</div>';
            }
            if (files.length > 0) {
                files.forEach(att => {
                    html += ChatRenderer.renderFileCard(att);
                });
            }
            html += '</div>';
            return html;
        },

        renderMessage: (data, messageId = '') => {
            const isMyMessage = !!data.isMyMessage;
            const authorName = data.sender_name || data.author_name || data.author || 'Пользователь';
            const senderId = data.sender_id || data.author_id || '';
            const messageText = ChatRenderer.resolvePlaintextField(data.message || data.text, '');
            const messageTime = ChatRenderer.formatTime(data.created_at || data.time);

            let avatarHtml = '';
            const profileAttrs = senderId
                ? `class="message-avatar profile-trigger" data-profile-user-id="${ChatRenderer.escapeHtml(String(senderId))}" data-profile-context="messenger" role="button" tabindex="0" title="Профиль"`
                : 'class="message-avatar"';
            const senderProfileAttrs = senderId
                ? `class="sender-name message-sender profile-trigger" data-profile-user-id="${ChatRenderer.escapeHtml(String(senderId))}" data-profile-context="messenger" role="button" tabindex="0" title="Профиль"`
                : 'class="sender-name message-sender"';

            if (!isMyMessage) {
                const avatarUrl = ChatRenderer.resolveAvatarUrl(data.sender_avatar || data.avatar);
                const inner = avatarUrl
                    ? `<img src="${ChatRenderer.escapeHtml(avatarUrl)}" alt="${ChatRenderer.escapeHtml(authorName)}" style="width:100%; height:100%; object-fit:cover;">`
                    : `<span>${ChatRenderer.escapeHtml(authorName.charAt(0).toUpperCase())}</span>`;
                avatarHtml = `<div ${profileAttrs}>${inner}</div>`;
            }

            const finalMessageId = messageId || data.id || data.message_id || '';
            const attachmentsHtml = ChatRenderer.renderAttachments(data.attachments, finalMessageId);
            const readMark = isMyMessage ? (data.is_read === true ? '<i class="check-icon check-icon-read">✓✓</i>' : '<i class="check-icon">✓</i>') : '';
            const messageKey = ChatRenderer.escapeHtml(String(data.id ?? `${authorName}|${messageText}|${data.created_at || data.time || ''}|${(data.attachments || []).map((a) => a.id ?? a.file_path ?? a.path ?? '').join(',')}`));

            let replyHtml = '';
            if (data.parent_id || data.parent) {
                const parentId = data.parent_id || (data.parent && data.parent.id);
                const parentAuthor = data.parent_author_name || (data.parent && data.parent.author_name) || 'Сообщение';
                const parentText = ChatRenderer.resolveParentQuote(data);
                replyHtml = `
                    <div class="message-reply-quote" onclick="window.scrollToMessage('${parentId}', event)">
                        <div class="reply-quote-author">${ChatRenderer.escapeHtml(parentAuthor)}</div>
                        <div class="reply-quote-text">${ChatRenderer.escapeHtml(parentText)}</div>
                    </div>
                `;
            }

            return `
                <div class="message ${isMyMessage ? 'my' : 'other'}" id="msg-${finalMessageId}" data-message-key="${messageKey}">
                    ${avatarHtml}
                    <div class="message-bubble">
                        ${!isMyMessage ? `<span ${senderProfileAttrs}>${ChatRenderer.escapeHtml(authorName)}</span>` : ''}
                        ${replyHtml}
                        ${attachmentsHtml}
                        ${messageText ? `<div class="message-text">${ChatRenderer.escapeHtml(messageText)}</div>` : ''}
                        <div class="message-meta">${messageTime} ${readMark}</div>
                    </div>
                </div>
            `;
        },

        addMessageToChat: (data) => {
            if (!UI_ELEMENTS.messagesArea) return;

            const msgDate = data.date_label || ChatRenderer.messageDateSeparatorLabel(data.created_at || data.full_date);
            if (msgDate !== lastDateLabel) {
                UI_ELEMENTS.messagesArea.insertAdjacentHTML('beforeend', `<div class="chat-date-separator"><span>${ChatRenderer.escapeHtml(String(msgDate))}</span></div>`);
                lastDateLabel = msgDate;
            }

            const messageId = data.id || data.message_id || '';
            const incomingMessageKey = String(messageId || `${data.author_name || data.author || 'Пользователь'}|${data.message || ''}|${data.created_at || data.time || ''}|${(data.attachments || []).map((a) => a.id ?? a.file_path ?? a.path ?? '').join(',')}`);
            if (renderedMessageKeys.has(incomingMessageKey)) return;
            renderedMessageKeys.add(incomingMessageKey);

            UI_ELEMENTS.messagesArea.insertAdjacentHTML('beforeend', ChatRenderer.renderMessage(data, messageId));
            const inserted = UI_ELEMENTS.messagesArea.lastElementChild;
            if (inserted && inserted.classList.contains('message') && data.isMyMessage) {
                ChatUI.syncMyBubbleContrast(inserted);
            }
            if (window.refreshIcons) window.refreshIcons();
            ChatUI.scrollToBottom();
            if (typeof window.stabilizeExistingImages === 'function') window.stabilizeExistingImages();
        },

        initLastDateLabelFromDom: () => {
            const area = UI_ELEMENTS.messagesContainer?.querySelector('.messages-area') || UI_ELEMENTS.messagesArea;
            if (!area) return;
            const spans = area.querySelectorAll('.date-divider > span, .chat-date-separator > span');
            const last = spans[spans.length - 1];
            if (last) lastDateLabel = last.textContent.trim() || null;
        },

        prependMessages: (messagesList, currentUserId) => {
            if (!messagesList?.length || !UI_ELEMENTS.messagesArea) return;

            const area = UI_ELEMENTS.messagesArea;
            const firstSep = area.querySelector('.chat-date-separator span');
            const firstDomDateLabel = firstSep ? firstSep.textContent.trim() : null;
            let prevBatchDate = null;

            const fragment = document.createDocumentFragment();
            const temp = document.createElement('div');

            messagesList.forEach((data, index) => {
                data.isMyMessage = data.sender_id === currentUserId || data.isMyMessage === true;
                const msgDate = data.date_label || ChatRenderer.messageDateSeparatorLabel(data.created_at || data.full_date);

                if (msgDate) {
                    const needSep = index === 0
                        ? (msgDate !== firstDomDateLabel)
                        : (msgDate !== prevBatchDate);
                    if (needSep) {
                        const sep = document.createElement('div');
                        sep.className = 'chat-date-separator';
                        sep.innerHTML = `<span>${ChatRenderer.escapeHtml(String(msgDate))}</span>`;
                        fragment.appendChild(sep);
                    }
                    prevBatchDate = msgDate;
                }

                const messageId = data.id || data.message_id || '';
                const incomingMessageKey = String(messageId || `${data.author_name || data.sender_name || ''}|${data.message || data.text || ''}|${data.created_at || ''}`);
                if (renderedMessageKeys.has(incomingMessageKey)) return;
                renderedMessageKeys.add(incomingMessageKey);

                temp.innerHTML = ChatRenderer.renderMessage(data, messageId);
                const row = temp.firstElementChild;
                if (row) {
                    if (row.classList.contains('message') && data.isMyMessage && typeof ChatUI !== 'undefined') {
                        ChatUI.syncMyBubbleContrast(row);
                    }
                    fragment.appendChild(row);
                }
            });

            const anchor = area.querySelector('.message, .chat-date-separator');
            const end = document.getElementById('message-end');
            if (anchor) {
                area.insertBefore(fragment, anchor);
            } else {
                area.insertBefore(fragment, end || null);
            }

            if (window.refreshIcons) window.refreshIcons();
            if (typeof window.stabilizeExistingImages === 'function') window.stabilizeExistingImages();
        }
    };

    // === SocketManager Module ===
    const SocketManager = {
        readStatusTimer: null,
        typingTimeout: null,
        typingSendTimeout: null,

        sendReadStatus: () => {
            if (!window.socket || !window.ChatConfig) return;
            window.socket.emit('mark_as_read', { chat_id: window.ChatConfig.chatId });
        },

        scheduleSendReadStatus: () => {
            clearTimeout(SocketManager.readStatusTimer);
            SocketManager.readStatusTimer = setTimeout(SocketManager.sendReadStatus, 280);
        },

        onMessagesScrollForRead: () => {
            const el = UI_ELEMENTS.messagesContainer;
            if (!el) return;
            if (el.scrollHeight - el.scrollTop - el.clientHeight < 100) SocketManager.scheduleSendReadStatus();
        },

        initChatSocket: (socket) => {
            if (!window.ChatConfig?.chatId) return;
            console.log('✅ [chat.js] Глобальный сокет найден, подключаемся к комнате чата');
            socket.emit('join_chat', { chat_id: window.ChatConfig.chatId });
            if (socket.__gruzzChatHandlersBound) return;
            socket.__gruzzChatHandlersBound = true;

            socket.on('messages_marked_read', (payload) => {
                if (!payload || String(payload.chat_id) !== String(window.ChatConfig.chatId)) return;
                if (String(payload.reader_id) === String(window.ChatConfig.currentUserId)) return;
                document.querySelectorAll('.messages-area .message.my .check-icon').forEach((el) => {
                    el.classList.add('check-icon-read');
                    el.textContent = '✓✓';
                });
                if (window.refreshIcons) window.refreshIcons();
            });
            
            socket.on('global_update', (update) => {
                if (update.type === 'new_message' && update.payload.chat_id == window.ChatConfig.chatId) {
                    const payload = update.payload;
                    if (payload.author_id != window.ChatConfig.currentUserId) {
                        ChatRenderer.addMessageToChat({
                            id: payload.id,
                            sender_id: payload.sender_id || payload.author_id,
                            author_name: payload.sender_name || payload.author_name,
                            sender_name: payload.sender_name || payload.author_name,
                            message: payload.message,
                            avatar: payload.sender_avatar || payload.avatar,
                            sender_avatar: payload.sender_avatar || payload.avatar,
                            attachments: payload.attachments,
                            isMyMessage: false,
                            is_read: false,
                            created_at: payload.created_at,
                            parent_id: payload.parent_id,
                            parent_author_name: payload.parent_author_name,
                            parent_text: payload.parent_text,
                        });
                    }
                }
            });

            setTimeout(SocketManager.sendReadStatus, 400);
            
            socket.on('user_typing', (data) => {
                if (data.is_typing && (data.user_id == null || String(data.user_id) !== String(window.ChatConfig.currentUserId))) {
                    ChatUI.displayTypingIndicator(data.user_name || data.user || 'Собеседник', true);
                    clearTimeout(SocketManager.typingSendTimeout);
                    SocketManager.typingSendTimeout = setTimeout(() => ChatUI.displayTypingIndicator('', false), 3000);
                } else {
                    ChatUI.displayTypingIndicator('', false);
                    clearTimeout(SocketManager.typingSendTimeout);
                }
                if (window.ChatListUI && data.chat_id) {
                    window.ChatListUI.setChatTyping(
                        data.chat_id,
                        !!data.is_typing && String(data.user_id) !== String(window.ChatConfig.currentUserId),
                        data.user_name
                    );
                }
            });

            socket.on('message_deleted', (data) => {
                if (!data || String(data.chat_id) !== String(window.ChatConfig.chatId)) return;
                const msgId = data.message_id;
                const msgElement = document.getElementById(`msg-${msgId}`)
                    || document.querySelector(`[data-message-id="${msgId}"]`);
                if (!msgElement) return;

                if (data.deleted_for_all || data.scope === 'all') {
                    if (window.ChatSocial && typeof window.ChatSocial.applyMessageDeleted === 'function') {
                        window.ChatSocial.applyMessageDeleted(msgId, true);
                    } else {
                        const textEl = msgElement.querySelector('.message-text');
                        if (textEl) {
                            textEl.textContent = 'Сообщение удалено';
                            textEl.classList.add('message-text--deleted');
                        }
                        msgElement.querySelectorAll('.chat-attachments, .attachments').forEach((a) => a.remove());
                    }
                    return;
                }

                if (String(data.user_id) === String(window.ChatConfig.currentUserId)) {
                    msgElement.remove();
                }
            });

            socket.on('message_unpinned', (data) => {
                if (!data || String(data.chat_id) !== String(window.ChatConfig.chatId)) return;
                if (window.ChatSocial && typeof window.ChatSocial.updatePinnedBar === 'function') {
                    window.ChatSocial.updatePinnedBar(null);
                } else {
                    const bar = document.getElementById('chat-pinned-bar');
                    if (bar) bar.hidden = true;
                }
            });

            socket.on('chat_pinned_message', (data) => {
                if (!data || String(data.chat_id) !== String(window.ChatConfig.chatId)) return;
                if (window.ChatSocial && typeof window.ChatSocial.updatePinnedBar === 'function') {
                    window.ChatSocial.updatePinnedBar(data.pinned || null);
                }
            });
        },

        waitForSocket: () => {
            if (window.socket) {
                SocketManager.initChatSocket(window.socket);
            } else {
                const checkSocket = setInterval(() => {
                    if (window.socket) {
                        clearInterval(checkSocket);
                        SocketManager.initChatSocket(window.socket);
                    }
                }, 100);
                setTimeout(() => { if (!window.socket) console.error('❌ [chat.js] Глобальный сокет не найден!'); }, 5000);
            }
        }
    };

    // === Боевой метод отправки сообщений (С интеграцией parent_id в FormData перед fetch) ===
    async function sendMessage() {
        if (!UI_ELEMENTS.messageInput) return;
        const text = UI_ELEMENTS.messageInput.value.trim();
        const files = [...selectedFiles];
        if (!text && files.length === 0) return;
        if (UI_ELEMENTS.sendBtn) UI_ELEMENTS.sendBtn.disabled = true;
        
        const formData = new FormData();
        if (window.currentReplyParentId) {
            formData.append('parent_id', window.currentReplyParentId);
        }
        formData.append('text', text);
        for (const file of files) {
            formData.append('files', file);
        }
        
        try {
            const response = await fetch(`/chat/send/${window.ChatConfig.chatId}`, {
                method: 'POST',
                body: formData,
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });
            if (response.status === 413) {
                alert('Файл слишком большой. Максимальный размер вложения — 200 МБ.');
                return;
            }
            const data = await response.json();
            if (data.success && data.message) {
                ChatRenderer.addMessageToChat({
                    id: data.message.id,
                    author_name: window.ChatConfig.currentUserName,
                    message: data.message.text || text,
                    attachments: data.message.attachments || [],
                    isMyMessage: true,
                    is_read: data.message.is_read === true,
                    created_at: data.message.created_at,
                    parent_id: data.message.parent_id,
                    parent_author_name: data.message.parent_author_name,
                    parent_text: data.message.parent_text,
                });
                ChatUI.resetMessageInput();
                cancelReply(); // Сбрасываем плашку ответа после отправки
            } else if (data.error) {
                alert(data.error);
            }
        } catch (error) {
            console.error('Send error:', error);
            alert('Ошибка при отправке. Возможно, файл слишком большой.');
        } finally {
            if (UI_ELEMENTS.sendBtn) UI_ELEMENTS.sendBtn.disabled = false;
        }
    }

    // === Event Listeners Bindings ===
    if (UI_ELEMENTS.attachBtn && UI_ELEMENTS.fileInput) {
        const newAttachBtn = UI_ELEMENTS.attachBtn.cloneNode(true);
        UI_ELEMENTS.attachBtn.parentNode.replaceChild(newAttachBtn, UI_ELEMENTS.attachBtn);
        UI_ELEMENTS.attachBtn = newAttachBtn;
        UI_ELEMENTS.attachBtn.addEventListener('click', () => UI_ELEMENTS.fileInput.click());
        UI_ELEMENTS.fileInput.addEventListener('change', function() {
            if (this.files.length > 0) ChatUI.addSelectedFiles(this.files);
        });
    }

    if (UI_ELEMENTS.messagesContainer) {
        UI_ELEMENTS.messagesContainer.addEventListener('scroll', function() {
            SocketManager.onMessagesScrollForRead();
            ChatUI.updateScrollBottomBtn();
            ChatHistory.onScroll();
        }, { passive: true });
    }

    const ChatHistory = {
        loading: false,
        hasMore: false,
        oldestId: null,

        initFromDom() {
            const area = UI_ELEMENTS.messagesArea;
            if (!area) return;
            this.hasMore = area.dataset.hasMoreOlder === 'true';
            this.oldestId = area.dataset.oldestMessageId || null;
        },

        onScroll() {
            const container = UI_ELEMENTS.messagesContainer;
            if (!container || this.loading || !this.hasMore || !this.oldestId) return;
            if (container.scrollTop > 80) return;
            this.loadOlder();
        },

        async loadOlder() {
            if (this.loading || !this.hasMore || !this.oldestId || !window.ChatConfig?.chatId) return;
            this.loading = true;
            const container = UI_ELEMENTS.messagesContainer;
            const loader = document.getElementById('chat-history-loader');
            if (loader) loader.classList.add('is-visible');

            const prevScrollHeight = container.scrollHeight;
            const prevScrollTop = container.scrollTop;

            try {
                const url = `/chat/${window.ChatConfig.chatId}/messages?before_id=${encodeURIComponent(this.oldestId)}&limit=40`;
                const res = await fetch(url, {
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                });
                const data = await res.json();
                if (!res.ok || !data.success) return;

                if (data.messages?.length) {
                    ChatRenderer.prependMessages(data.messages, window.ChatConfig.currentUserId);
                }

                this.hasMore = !!data.has_more;
                this.oldestId = data.oldest_id ? String(data.oldest_id) : null;

                const area = UI_ELEMENTS.messagesArea;
                if (area) {
                    area.dataset.hasMoreOlder = this.hasMore ? 'true' : 'false';
                    area.dataset.oldestMessageId = this.oldestId || '';
                }

                requestAnimationFrame(() => {
                    const delta = container.scrollHeight - prevScrollHeight;
                    container.scrollTop = prevScrollTop + delta;
                });
            } catch (err) {
                console.error('[ChatHistory] load older failed', err);
            } finally {
                this.loading = false;
                if (loader) loader.classList.remove('is-visible');
            }
        },
    };

    ChatHistory.initFromDom();
    window.ChatHistory = ChatHistory;

    const scrollBottomBtn = document.getElementById('chat-scroll-bottom-btn');
    if (scrollBottomBtn && UI_ELEMENTS.messagesContainer) {
        scrollBottomBtn.addEventListener('click', function() {
            UI_ELEMENTS.messagesContainer.scrollTo({
                top: UI_ELEMENTS.messagesContainer.scrollHeight,
                behavior: 'smooth'
            });
        });
    }
    window.addEventListener('focus', () => SocketManager.scheduleSendReadStatus());

    document.addEventListener('click', (e) => {
        const link = e.target.closest('.chat-image-link');
        if (link) {
            e.preventDefault();
            if (window.ChatUI?.openLightbox) window.ChatUI.openLightbox(link);
        }
    });

    document.addEventListener('click', function(e) {
        const lightbox = document.getElementById('image-lightbox');
        if (!lightbox || lightbox.style.display !== 'flex') return;
        if (e.target.classList.contains('close-lightbox') || e.target === lightbox) {
            if (window.ChatUI && window.ChatUI.closeLightbox) window.ChatUI.closeLightbox();
        }
        if (e.target.classList.contains('left-arrow') && window.ChatUI?.prevImage) window.ChatUI.prevImage();
        if (e.target.classList.contains('right-arrow') && window.ChatUI?.nextImage) window.ChatUI.nextImage();
    });

    document.addEventListener('keydown', function(e) {
        const lightbox = document.getElementById('image-lightbox');
        if (!lightbox || lightbox.style.display !== 'flex') return;
        if (e.key === 'Escape' && window.ChatUI?.closeLightbox) window.ChatUI.closeLightbox();
        if ((e.key === 'ArrowRight' || e.key === 'ArrowDown') && window.ChatUI?.nextImage) window.ChatUI.nextImage();
        if ((e.key === 'ArrowLeft' || e.key === 'ArrowUp') && window.ChatUI?.prevImage) window.ChatUI.prevImage();
    });

    if (UI_ELEMENTS.messageForm) {
        UI_ELEMENTS.messageForm.addEventListener('submit', (e) => {
            e.preventDefault();
            sendMessage();
        });
    }
    
    if (UI_ELEMENTS.messageInput) {
        UI_ELEMENTS.messageInput.addEventListener('keydown', (e) => {
            const shouldSend = typeof window.shouldSendMessageOnEnter === 'function'
                ? window.shouldSendMessageOnEnter(e)
                : (e.key === 'Enter' && !e.shiftKey);
            if (shouldSend) {
                e.preventDefault();
                sendMessage();
            }
        });
        
        UI_ELEMENTS.messageInput.addEventListener('input', () => {
            ChatUI.autoResizeTextarea();
            ChatUI.updateSendState();
            if (window.socket) {
                window.socket.emit('typing', { chat_id: window.ChatConfig.chatId, is_typing: true });
                clearTimeout(SocketManager.typingSendTimeout);
                SocketManager.typingSendTimeout = setTimeout(() => {
                    if (window.socket) window.socket.emit('typing', { chat_id: window.ChatConfig.chatId, is_typing: false });
                }, 2000);
            }
        });
    }
    
    let stabilizeTimeout = null;
    function stabilizeExistingImages() {
        clearTimeout(stabilizeTimeout);
        stabilizeTimeout = setTimeout(() => {
            const container = UI_ELEMENTS.messagesArea || document;
            container.querySelectorAll('.message img, .att-item-img img, img[data-fullsrc]').forEach(img => {
                if (img.dataset.stabilized || img.closest('.image-gallery-grid')) return;
                img.loading = 'lazy';
                img.decoding = 'async';
                img.dataset.stabilized = 'true';

                if (!img.closest('a.chat-image-link')) {
                    const link = document.createElement('a');
                    link.className = 'chat-image-link';
                    link.href = img.dataset.fullsrc || img.src;
                    link.onclick = (e) => { e.preventDefault(); ChatUI.openLightbox(link); };
                    img.parentNode.insertBefore(link, img);
                    link.appendChild(img);
                }

                img.onerror = function() {
                    if (img.dataset.triedFallback) return;
                    img.dataset.triedFallback = 'true';
                    const fallback = img.dataset.fullsrc || img.src.replace(/_thumb\./, '_opt.').replace(/_thumb\.jpg/i, '.jpg').replace(/_thumb\.jpeg/i, '.jpeg');
                    if (fallback && fallback !== img.src) img.src = fallback;
                };
            });
        }, 250);
    }
    window.stabilizeExistingImages = stabilizeExistingImages;

    // === Initialization ===
    ChatUI.syncAllMyBubblesContrast();
    ChatUI.autoResizeTextarea();

    // Железный принудительный скролл вниз при загрузке
    const container = document.getElementById('messages-container');
    if (container) {
        container.style.scrollBehavior = 'auto'; // Отключаем плавность для мгновенного прыжка
        container.scrollTop = container.scrollHeight;

        // Через небольшую задержку возвращаем плавный скролл для новых сообщений
        setTimeout(() => {
            container.style.scrollBehavior = 'smooth';
            container.scrollTop = container.scrollHeight;
            container.classList.add('ready');
            if (typeof ChatUI.updateScrollBottomBtn === 'function') ChatUI.updateScrollBottomBtn();
        }, 50);
    }

    ChatRenderer.initLastDateLabelFromDom();
    document.querySelectorAll('.messages-area .message[data-message-id]').forEach((el) => {
        const id = el.dataset.messageId;
        if (id) renderedMessageKeys.add(String(id));
    });
    if (typeof stabilizeExistingImages === 'function') stabilizeExistingImages();
    if (typeof window.refreshGruzzIcons === 'function') window.refreshGruzzIcons();
    if (typeof SocketManager !== 'undefined') {
        SocketManager.waitForSocket();
        SocketManager.scheduleSendReadStatus();
    }

    // === ЛОГИКА ПЕРЕСЫЛКИ СООБЩЕНИЙ ===
    let selectedUserIds = [];

    Object.assign(ChatUI, {
        currentForwardMessageId: null,
        forwardSearchQuery: '',

        setForwardSubmitEnabled: () => {
            const btn = document.getElementById('forward-submit-btn');
            if (btn) btn.disabled = selectedUserIds.length === 0;
        },

        renderForwardTargetsList: () => {
            const listEl = document.getElementById('forward-users-list');
            const list = window.ForwardTargetsList || window.UserChatsList || [];
            if (!listEl) return;

            const query = (ChatUI.forwardSearchQuery || '').trim().toLowerCase();

            if (!list.length) {
                listEl.innerHTML = '<div class="forward-users-empty">Нет доступных получателей</div>';
                ChatUI.setForwardSubmitEnabled();
                return;
            }

            const filtered = list.filter((item) => {
                if (!query) return true;
                return String(item.name || '').toLowerCase().includes(query);
            });

            if (!filtered.length) {
                listEl.innerHTML = '<div class="forward-users-empty">Никого не найдено</div>';
                ChatUI.setForwardSubmitEnabled();
                return;
            }

            listEl.innerHTML = filtered.map((item) => {
                const userId = item.user_id != null ? item.user_id : item.id;
                const uid = String(userId);
                const isActive = selectedUserIds.includes(Number(userId));
                const name = ChatRenderer.escapeHtml(item.name || 'Пользователь');
                const searchName = ChatRenderer.escapeHtml(String(item.name || '').toLowerCase());
                const initials = ChatRenderer.escapeHtml(
                    item.initials || (item.name && item.name.charAt(0)) || '?'
                );
                const avatar = item.avatar
                    ? `<img src="${ChatRenderer.escapeHtml(item.avatar)}" alt="" class="forward-user-avatar-img">`
                    : `<span class="forward-user-avatar-initials">${initials}</span>`;
                return `<button type="button" class="forward-user-item${isActive ? ' active' : ''}" data-user-id="${uid}" data-search-name="${searchName}" role="option" aria-selected="${isActive}">
                    <span class="forward-user-avatar">${avatar}</span>
                    <span class="forward-user-name">${name}</span>
                </button>`;
            }).join('');
            ChatUI.setForwardSubmitEnabled();
        },

        toggleForwardTarget: (userId, itemEl) => {
            const id = parseInt(userId, 10);
            if (!id) return;
            const idx = selectedUserIds.indexOf(id);
            if (idx >= 0) {
                selectedUserIds.splice(idx, 1);
            } else {
                selectedUserIds.push(id);
            }
            const btn = itemEl || document.querySelector(`.forward-user-item[data-user-id="${id}"]`);
            if (btn) {
                const active = selectedUserIds.includes(id);
                btn.classList.toggle('active', active);
                btn.setAttribute('aria-selected', active ? 'true' : 'false');
            }
            ChatUI.setForwardSubmitEnabled();
        },

        filterForwardTargetsList: (query) => {
            ChatUI.forwardSearchQuery = query || '';
            ChatUI.renderForwardTargetsList();
        },

        loadForwardTargets: async () => {
            try {
                const res = await fetch('/chat/forward-targets', {
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                });
                const data = await res.json();
                if (res.ok && data.success && Array.isArray(data.targets)) {
                    window.ForwardTargetsList = data.targets;
                    window.UserChatsList = data.targets;
                }
            } catch (e) {
                console.warn('[Forward] targets fetch failed', e);
            }
        },

        openForwardModal: async (msgId) => {
            ChatUI.currentForwardMessageId = msgId;
            selectedUserIds = [];
            ChatUI.forwardSearchQuery = '';
            const searchInput = document.getElementById('forward-search-input');
            if (searchInput) searchInput.value = '';
            if (!window.ForwardTargetsList?.length) {
                await ChatUI.loadForwardTargets();
            }
            const modal = document.getElementById('forward-modal');
            if (modal) {
                ChatUI.renderForwardTargetsList();
                modal.hidden = false;
                modal.classList.add('active');
                document.body.style.overflow = 'hidden';
            }
        },

        closeForwardModal: () => {
            ChatUI.currentForwardMessageId = null;
            selectedUserIds = [];
            ChatUI.forwardSearchQuery = '';
            const searchInput = document.getElementById('forward-search-input');
            if (searchInput) searchInput.value = '';
            const modal = document.getElementById('forward-modal');
            if (modal) {
                modal.classList.remove('active');
                document.body.style.overflow = '';
                setTimeout(() => {
                    if (!modal.classList.contains('active')) modal.hidden = true;
                }, 220);
            }
            ChatUI.setForwardSubmitEnabled();
        },

        submitForward: async () => {
            if (!ChatUI.currentForwardMessageId || !selectedUserIds.length) {
                if (window.showToast) window.showToast('Выберите получателей для пересылки', 'error');
                return;
            }

            const submitBtn = document.getElementById('forward-submit-btn');
            if (submitBtn) submitBtn.disabled = true;

            try {
                const res = await fetch(`/chat/forward/${ChatUI.currentForwardMessageId}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                    body: JSON.stringify({ user_ids: selectedUserIds })
                });
                let data = {};
                try {
                    data = await res.json();
                } catch (parseErr) {
                    console.error(parseErr);
                    if (window.showToast) window.showToast('Ошибка ответа сервера', 'error');
                    ChatUI.setForwardSubmitEnabled();
                    return;
                }
                if (res.ok && data.status === 'success') {
                    ChatUI.closeForwardModal();
                    const n = data.processed || selectedUserIds.length;
                    if (window.showToast) {
                        window.showToast(
                            n === 1 ? 'Сообщение переслано' : `Сообщение переслано (${n})`,
                            'success'
                        );
                    }
                } else {
                    if (window.showToast) window.showToast('Ошибка: ' + (data.error || 'Не удалось переслать'), 'error');
                    ChatUI.setForwardSubmitEnabled();
                }
            } catch (err) {
                console.error(err);
                if (window.showToast) window.showToast('Ошибка сети при пересылке', 'error');
                ChatUI.setForwardSubmitEnabled();
            }
        }
    });

    const forwardSubmitBtn = document.getElementById('forward-submit-btn');
    if (forwardSubmitBtn && !forwardSubmitBtn.dataset.bound) {
        forwardSubmitBtn.dataset.bound = '1';
        forwardSubmitBtn.addEventListener('click', () => ChatUI.submitForward());
    }

    const forwardUsersList = document.getElementById('forward-users-list');
    if (forwardUsersList && !forwardUsersList.dataset.bound) {
        forwardUsersList.dataset.bound = '1';
        forwardUsersList.addEventListener('click', (e) => {
            const item = e.target.closest('.forward-user-item');
            if (!item || !item.dataset.userId) return;
            ChatUI.toggleForwardTarget(item.dataset.userId, item);
        });
    }

    const forwardSearchInput = document.getElementById('forward-search-input');
    if (forwardSearchInput && !forwardSearchInput.dataset.bound) {
        forwardSearchInput.dataset.bound = '1';
        forwardSearchInput.addEventListener('input', (e) => {
            ChatUI.filterForwardTargetsList(e.target.value);
        });
    }

    const forwardModal = document.getElementById('forward-modal');
    if (forwardModal && !forwardModal.dataset.bound) {
        forwardModal.dataset.bound = '1';
        forwardModal.addEventListener('click', (e) => {
            if (e.target === forwardModal) ChatUI.closeForwardModal();
        });
    }

    window.ChatUI = ChatUI;
    if (typeof ChatRenderer !== 'undefined') {
        window.ChatRenderer = ChatRenderer;
        window.normalizeFilePath = ChatRenderer.normalizeFilePath;
    }
    console.log('Chat Module Initialized');
});

// === ГЛОБАЛЬНЫЙ ПЕРЕХВАТЧИК ПКМ (КОНТЕКСТНОЕ МЕНЮ СООБЩЕНИЙ) ===
(function () {
    let messageContextMenu = null;
    let messageContextMenuDismiss = null;

    function unbindMessageContextMenuDismiss() {
        if (!messageContextMenuDismiss) return;
        document.removeEventListener('mousedown', messageContextMenuDismiss.onPointerDown, true);
        document.removeEventListener('keydown', messageContextMenuDismiss.onKey);
        messageContextMenuDismiss = null;
    }

    function closeMessageContextMenu() {
        unbindMessageContextMenuDismiss();
        const stale = document.getElementById('custom-context-menu');
        if (stale) stale.remove();
        if (messageContextMenu) {
            messageContextMenu.remove();
            messageContextMenu = null;
        }
        if (window.ChatSocial && typeof window.ChatSocial.closeListContextMenu === 'function') {
            window.ChatSocial.closeListContextMenu();
        }
    }

    function bindMessageContextMenuDismiss() {
        unbindMessageContextMenuDismiss();
        const onPointerDown = function (ev) {
            if (messageContextMenu && messageContextMenu.contains(ev.target)) return;
            closeMessageContextMenu();
        };
        const onKey = function (ev) {
            if (ev.key === 'Escape') closeMessageContextMenu();
        };
        messageContextMenuDismiss = { onPointerDown, onKey };
        document.addEventListener('mousedown', onPointerDown, true);
        document.addEventListener('keydown', onKey);
    }

    document.addEventListener('contextmenu', function (e) {
        closeMessageContextMenu();
    }, true);

    document.addEventListener('contextmenu', function(e) {
    const messageBubble = e.target.closest('.message-bubble') || e.target.closest('.msg-bubble');
    const messageEl = e.target.closest('.message');

    if (!messageBubble || !messageEl) return;

    e.preventDefault();
    e.stopPropagation();

    const msgId = messageEl.dataset.messageId || messageEl.id.replace('msg-', '');
    if (!msgId) return;

    closeMessageContextMenu();

    // Создаем новое красивое меню
    const menu = document.createElement('div');
    menu.id = 'custom-context-menu';
    menu.style.cssText = `
        position: absolute;
        top: ${e.pageY}px;
        left: ${e.pageX}px;
        background: var(--bg-secondary, #2a2a2a);
        border: 1px solid var(--border, rgba(255,255,255,0.1));
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.15);
        padding: 6px;
        z-index: 10000;
        min-width: 160px;
        display: flex;
        flex-direction: column;
        gap: 2px;
    `;

    // Адаптация под светлую тему
    if (document.body.classList.contains('light')) {
        menu.style.background = '#ffffff';
        menu.style.borderColor = 'rgba(0,0,0,0.08)';
        menu.style.boxShadow = '0 4px 20px rgba(0,0,0,0.08)';
    }

    // Функция создания кнопок меню
    const createItem = (icon, text, onClick) => {
        const item = document.createElement('div');
        item.style.cssText = `
            padding: 8px 12px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 10px;
            color: ${document.body.classList.contains('light') ? '#1c1e21' : '#ffffff'};
            border-radius: 6px;
            transition: background 0.2s;
            font-size: 14px;
        `;
        item.onmouseover = () => item.style.background = document.body.classList.contains('light') ? '#f4f5f7' : 'rgba(255,255,255,0.1)';
        item.onmouseout = () => item.style.background = 'transparent';
        item.innerHTML = `<i data-lucide="${icon}" style="width: 16px; height: 16px;"></i> <span>${text}</span>`;
        item.onclick = (event) => {
            event.preventDefault();
            event.stopPropagation();
            closeMessageContextMenu();
            onClick();
        };
        return item;
    };

    // 1. Кнопка "Ответить"
    menu.appendChild(createItem('corner-up-left', 'Ответить', () => {
        const textEl = messageEl.querySelector('.message-text');
        const authorEl = messageEl.querySelector('.message-author, .message-sender, .sender-name');
        const text = textEl ? textEl.textContent.trim() : 'Вложение';
        const author = authorEl ? authorEl.textContent.trim() : 'Собеседник';
        if (typeof setReplyState === 'function') setReplyState(msgId, author, text);
    }));

    // 2. Кнопка "Переслать"
    menu.appendChild(createItem('forward', 'Переслать', () => {
        if (window.ChatUI && window.ChatUI.openForwardModal) {
            window.ChatUI.openForwardModal(msgId);
        } else {
            console.error('Функция пересылки не найдена!');
        }
    }));

    menu.appendChild(createItem('pin', 'Закрепить', () => {
        if (window.ChatSocial && window.ChatSocial.pinMessage) {
            window.ChatSocial.pinMessage(msgId);
        }
    }));

    const isOwn = messageEl.classList.contains('my');
    menu.appendChild(createItem('trash-2', 'Удалить', () => {
        if (window.ChatSocial && window.ChatSocial.showDeleteMessageModal) {
            window.ChatSocial.showDeleteMessageModal(msgId, isOwn);
        }
    }));

    // 3. Кнопка "Копировать"
    const textEl = messageEl.querySelector('.message-text');
    if (textEl && textEl.textContent.trim()) {
        menu.appendChild(createItem('copy', 'Копировать', () => {
            navigator.clipboard.writeText(textEl.textContent.trim());
            if (window.showToast) window.showToast('Текст скопирован', 'success');
        }));
    }

    document.body.appendChild(menu);
    messageContextMenu = menu;
    if (typeof lucide !== 'undefined') lucide.createIcons({ root: menu });

    const rect = menu.getBoundingClientRect();
    if (rect.right > window.innerWidth) menu.style.left = `${window.innerWidth - rect.width - 10}px`;
    if (rect.bottom > window.innerHeight) menu.style.top = `${window.innerHeight - rect.height - 10}px`;

    bindMessageContextMenuDismiss();
    });
})();

window.openGroupSettingsModal = function(chatId) {
    const modal = document.getElementById('groupSettingsModal');
    if (!modal) return;

    fetch(`/chats/${chatId}/info`)
        .then(res => res.json())
        .then(data => {
            if (!data.success) {
                alert(data.error || 'Не удалось загрузить информацию о группе');
                return;
            }

            modal.dataset.chatId = String(chatId);

            const nameEl = document.getElementById('groupSettingsName');
            if (nameEl) nameEl.textContent = data.name || 'Группа';
            updateGroupMembersCount((data.members || []).length);

            const addBtn = document.getElementById('btnAddMembers');
            if (addBtn) addBtn.style.display = data.is_admin ? 'inline-flex' : 'none';

            const panel = document.getElementById('groupAddMembersPanel');
            if (panel) panel.style.display = 'none';

            renderGroupSettingsMembers(chatId, data);
            renderGroupAddMembersList(data.available_users || []);

            const leaveBtn = document.getElementById('groupLeaveBtn');
            if (leaveBtn) {
                leaveBtn.onclick = () => leaveGroup(chatId);
            }

            modal.style.display = 'flex';
            document.body.style.overflow = 'hidden';
            if (typeof window.refreshIcons === 'function') window.refreshIcons();
        })
        .catch(err => console.error(err));
};

window.updateGroupMembersCount = function(count) {
    const text = `${count} участников`;
    const headerCount = document.querySelector('.chat-header-info .members-count');
    if (headerCount) headerCount.innerText = text;
    const countEl = document.getElementById('groupSettingsCount');
    if (countEl) countEl.textContent = text;
};

window.renderGroupMemberAvatar = function(name, avatarUrl) {
    const letter = escapeHtml((name || '?').charAt(0).toUpperCase());
    if (avatarUrl) {
        return `<img src="${escapeHtml(avatarUrl)}" alt="${escapeHtml(name || '')}" style="width: 36px; height: 36px; border-radius: 50%; object-fit: cover;">`;
    }
    return `<div style="width: 36px; height: 36px; border-radius: 50%; background: var(--bg-tertiary); display: flex; align-items: center; justify-content: center; font-weight: bold; color: var(--text-primary); border: 1px solid var(--border);">${letter}</div>`;
};

window.renderGroupSettingsMembers = function(chatId, data) {
    const modalBody = document.querySelector('#groupSettingsModal .members-list');
    if (!modalBody) return;

    const currentUserId = parseInt(
        document.body.dataset.userId || window.ChatConfig?.currentUserId || window.currentUserId,
        10
    );
    modalBody.innerHTML = '';

    (data.members || []).forEach(member => {
        const canKick = data.is_admin
            && member.role !== 'creator'
            && parseInt(member.id, 10) !== currentUserId
            && !(data.current_user_role === 'admin' && member.role === 'admin');

        const actionHtml = canKick
            ? `<button type="button" onclick="kickUser(${chatId}, ${member.id})" style="color: red; border: none; background: none; cursor: pointer; padding: 5px;"><i data-lucide="user-minus"></i></button>`
            : '';

        const avatarHtml = renderGroupMemberAvatar(member.name, member.avatar);
        const roleLabel = member.role === 'creator' ? 'владелец' : member.role;

        modalBody.insertAdjacentHTML('beforeend', `
            <div class="member-item" style="display: flex; justify-content: space-between; align-items: center; padding: 10px; border-bottom: 1px solid var(--border);">
                <div class="profile-trigger" data-profile-user-id="${member.id}" data-profile-context="messenger" role="button" tabindex="0" title="Профиль" style="display: flex; align-items: center; gap: 12px; flex: 1; min-width: 0;">
                    ${avatarHtml}
                    <span style="color: var(--text-primary); font-weight: 500;">
                        ${escapeHtml(member.name || 'Пользователь')}
                        <small style="color: var(--accent); font-weight: normal;">(${escapeHtml(roleLabel)})</small>
                    </span>
                </div>
                ${actionHtml}
            </div>
        `);
    });
};

window.renderGroupAddMembersList = function(users) {
    const list = document.getElementById('groupAddMembersList');
    if (!list) return;

    if (!users.length) {
        list.innerHTML = '<div class="group-users-empty">Все пользователи уже в группе</div>';
        return;
    }

    list.innerHTML = users.map(user => `
        <label class="group-add-member-item">
            <div class="group-user-info">
                <div class="group-user-avatar">
                    ${renderGroupMemberAvatar(user.name, user.avatar)}
                </div>
                <span class="user-name">${escapeHtml(user.name || 'Пользователь')}</span>
            </div>
            <span class="group-user-check">
                <input type="checkbox" class="group-user-checkbox" value="${user.id}">
            </span>
        </label>
    `).join('');
};

window.escapeHtml = window.escapeHtml || function(text) {
    if (!text) return '';
    return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
};

window.handleGroupUpdated = function(data) {
    const chatId = data?.chat_id;
    if (!chatId) return;

    const activeChatMatch = window.location.pathname.match(/\/chat\/(\d+)/);
    const activeChatId = activeChatMatch
        ? parseInt(activeChatMatch[1], 10)
        : (window.ChatConfig?.chatId ? parseInt(window.ChatConfig.chatId, 10) : null);

    if (activeChatId !== parseInt(chatId, 10)) return;

    const modal = document.getElementById('groupSettingsModal');
    if (modal && modal.style.display === 'flex' && typeof window.openGroupSettingsModal === 'function') {
        openGroupSettingsModal(chatId);
        return;
    }

    updateGroupMembersCountFromInfo(chatId);
};

window.updateGroupMembersCountFromInfo = function(chatId) {
    fetch(`/chats/${chatId}/info`)
        .then(res => res.json())
        .then(info => {
            if (!info.success) return;
            updateGroupMembersCount((info.members || []).length);
        })
        .catch(err => console.error(err));
};

window.closeGroupSettingsModal = function() {
    const modal = document.getElementById('groupSettingsModal');
    if (!modal) return;
    modal.style.display = 'none';
    document.body.style.overflow = '';
};

window.toggleGroupAddMembersPanel = function() {
    const panel = document.getElementById('groupAddMembersPanel');
    if (!panel) return;
    panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
    if (panel.style.display === 'block' && typeof window.refreshIcons === 'function') {
        window.refreshIcons();
    }
};

window.filterGroupAddMembers = function() {
    const searchInput = document.getElementById('groupAddMemberSearch');
    const query = (searchInput ? searchInput.value : '').toLowerCase();
    document.querySelectorAll('.group-add-member-item').forEach(item => {
        const nameEl = item.querySelector('.user-name');
        const name = nameEl ? nameEl.innerText.toLowerCase() : '';
        item.style.display = name.includes(query) ? 'flex' : 'none';
    });
};

window.leaveGroup = function(chatId) {
    if (!confirm('Выйти из группы?')) return;

    fetch(`/chats/${chatId}/leave`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
    })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                closeGroupSettingsModal();
                window.location.replace('/chats');
                return;
            }
            alert(data.error || 'Не удалось выйти из группы');
        })
        .catch(err => console.error(err));
};

window.kickUser = function(chatId, userId) {
    if (!confirm('Исключить участника из группы?')) return;

    fetch(`/chats/${chatId}/kick/${userId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
    })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                openGroupSettingsModal(chatId);
                return;
            }
            alert(data.error || 'Не удалось исключить участника');
        })
        .catch(err => console.error(err));
};

window.addGroupMembers = function(chatId, userIds) {
    fetch(`/chats/${chatId}/add_members`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_ids: userIds }),
    })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                const panel = document.getElementById('groupAddMembersPanel');
                if (panel) panel.style.display = 'none';
                openGroupSettingsModal(chatId);
                return;
            }
            alert(data.error || 'Не удалось добавить участников');
        })
        .catch(err => console.error(err));
};

window.confirmAddGroupMembers = function(chatId) {
    const resolvedChatId = chatId || document.getElementById('groupSettingsModal')?.dataset.chatId;
    const userIds = Array.from(document.querySelectorAll('#groupAddMembersList .group-user-checkbox:checked'))
        .map(cb => parseInt(cb.value, 10))
        .filter(id => !Number.isNaN(id));

    if (userIds.length === 0) {
        alert('Выберите хотя бы одного участника');
        return;
    }

    addGroupMembers(resolvedChatId, userIds);
};

document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeGroupSettingsModal();
    }
});