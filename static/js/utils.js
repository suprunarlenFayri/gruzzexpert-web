/**
 * UTILS.JS - Общие утилиты для всего приложения
 */

window.initUserTimezone = function() {
    try {
        const userTimeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;
        if (userTimeZone) {
            document.cookie = 'user_timezone=' + encodeURIComponent(userTimeZone) + '; path=/; max-age=31536000; SameSite=Lax';
            console.log('🌍 Локальная таймзона пользователя определена:', userTimeZone);
        }
        return userTimeZone;
    } catch (e) {
        console.warn('Не удалось определить таймзону пользователя', e);
        return null;
    }
};

window.formatUtcToLocalTime = function(isoString, options) {
    if (!isoString) return '';
    const date = new Date(isoString);
    if (Number.isNaN(date.getTime())) return '';
    return date.toLocaleTimeString('ru-RU', Object.assign({ hour: '2-digit', minute: '2-digit' }, options || {}));
};

window.formatUtcToLocalDateTime = function(isoString, options) {
    if (!isoString) return '';
    const date = new Date(isoString);
    if (Number.isNaN(date.getTime())) return '';
    return date.toLocaleString('ru-RU', Object.assign({
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    }, options || {}));
};

// Экранирование HTML
window.escapeHtml = function(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
};

// Уведомления
window.showToast = function(message, type = 'info') {
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.style.cssText = `
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            z-index: 9999;
            display: flex;
            flex-direction: column;
            gap: 10px;
            pointer-events: none;
        `;
        document.body.appendChild(toastContainer);
    }
    
    const toast = document.createElement('div');
    const bgColor = type === 'error' ? 'var(--danger)' : 
                    type === 'success' ? 'var(--success)' : 'var(--accent)';
    toast.style.cssText = `
        background: ${bgColor};
        color: white;
        padding: 10px 20px;
        border-radius: var(--radius-md);
        font-size: 13px;
        font-weight: 500;
        box-shadow: var(--shadow-lg);
        animation: slideUp 0.3s ease;
        pointer-events: auto;
    `;
    toast.textContent = message;
    toastContainer.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(-20px)';
        setTimeout(() => toast.remove(), 300);
    }, 2000);
};

// Скролл вниз
window.scrollToBottom = function(containerId) {
    const container = document.getElementById(containerId);
    if (container) {
        container.scrollTop = container.scrollHeight;
    }
};

window.MESSAGE_INPUT_MAX_HEIGHT = window.MESSAGE_INPUT_MAX_HEIGHT || 150;

/** Сброс высоты поля ввода после отправки */
window.resetMessageInputHeight = function(textarea) {
    if (!textarea) return;
    textarea.style.height = '';
    textarea.style.overflowY = '';
};

/**
 * Авто-высота textarea (1–6 строк, max 150px).
 * Не дёргает скролл ленты, если пользователь не у нижнего края.
 */
window.autoResizeTextarea = function(textarea) {
    if (!textarea) return;

    const messagesContainer = document.getElementById('messages-container');
    const stickToBottom = messagesContainer
        ? messagesContainer.scrollHeight - messagesContainer.scrollTop - messagesContainer.clientHeight < 96
        : false;
    const scrollTopBefore = messagesContainer ? messagesContainer.scrollTop : 0;

    const maxH = window.MESSAGE_INPUT_MAX_HEIGHT || 150;

    if (textarea.value.trim() === '') {
        textarea.style.height = '';
        textarea.style.overflowY = 'hidden';
    } else {
        textarea.style.height = 'auto';
        const newHeight = Math.min(Math.max(textarea.scrollHeight, 40), maxH);
        textarea.style.height = `${newHeight}px`;
        textarea.style.overflowY = textarea.scrollHeight > maxH ? 'auto' : 'hidden';
    }

    if (messagesContainer) {
        if (stickToBottom) {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        } else {
            messagesContainer.scrollTop = scrollTopBefore;
        }
    }
};

// Обновление иконок
window.GruzzIcons = window.GruzzIcons || {
    search: `<svg width="100%" height="100%" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="square"><circle cx="10" cy="10" r="6"/><line x1="14.5" y1="14.5" x2="20" y2="20"/><circle cx="10" cy="10" r="1.2" fill="currentColor"/></svg>`
};

window.refreshGruzzIcons = function() {
    document.querySelectorAll('[data-gruzz-icon]').forEach(el => {
        const iconName = el.getAttribute('data-gruzz-icon');
        if (window.GruzzIcons[iconName]) {
            el.innerHTML = window.GruzzIcons[iconName];
        }
    });
};

window.refreshIcons = function() {
    if (typeof window.refreshGruzzIcons === 'function') {
        window.refreshGruzzIcons();
    }
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
};

// Форматирование времени
window.formatTime = function() {
    const now = new Date();
    return now.getHours().toString().padStart(2, '0') + ':' +
           now.getMinutes().toString().padStart(2, '0');
};

/**
 * GruzzDatePicker — кастомный календарь (из UI поиска в чатах).
 * Работает на любой странице: формы, фильтры, навигация по датам в чате.
 */
window.GruzzDatePicker = {
    monthsRu: ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'],
    monthsRuGenitive: ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'],

    formatIso(year, monthIndex, day) {
        return `${year}-${String(monthIndex + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    },

    formatDisplay(year, monthIndex, day) {
        return `${parseInt(day, 10)} ${this.monthsRuGenitive[monthIndex]} ${year}`;
    },

    formatDisplayShort(year, monthIndex, day) {
        return `${parseInt(day, 10)} ${this.monthsRuGenitive[monthIndex]}`;
    },

    parseIso(iso) {
        if (!iso || typeof iso !== 'string') return null;
        const match = iso.trim().match(/^(\d{4})-(\d{2})-(\d{2})/);
        if (!match) return null;
        return {
            year: parseInt(match[1], 10),
            month: parseInt(match[2], 10) - 1,
            day: parseInt(match[3], 10)
        };
    },

    refreshPickerIcons(dropdown) {
        if (typeof window.refreshGruzzIcons === 'function') {
            window.refreshGruzzIcons();
        }
        if (typeof window.refreshIcons === 'function') {
            window.refreshIcons();
        } else if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    },

    render(dropdown, viewDate, selectedIso, handlers, pickerOptions = {}) {
        const year = viewDate.getFullYear();
        const month = viewDate.getMonth();
        const changeMonth = pickerOptions.changeMonth === true;
        const changeYear = pickerOptions.changeYear === true;
        const yearRange = pickerOptions.yearRange || null;
        const minYear = yearRange ? yearRange[0] : null;
        const maxYear = yearRange ? yearRange[1] : null;
        const firstDayIndex = new Date(year, month, 1).getDay();
        const startOffset = firstDayIndex === 0 ? 6 : firstDayIndex - 1;
        const totalDays = new Date(year, month + 1, 0).getDate();
        const now = new Date();

        let headerCenter = `<span>${this.monthsRu[month]} ${year}</span>`;
        if (changeMonth || changeYear) {
            let monthPart = changeMonth
                ? `<select class="gruzz-cal-month-select" aria-label="Месяц">${this.monthsRu.map((name, idx) =>
                    `<option value="${idx}"${idx === month ? ' selected' : ''}>${name}</option>`
                ).join('')}</select>`
                : `<span>${this.monthsRu[month]}</span>`;
            let yearPart = changeYear && minYear !== null && maxYear !== null
                ? `<select class="gruzz-cal-year-select" aria-label="Год">${Array.from(
                    { length: maxYear - minYear + 1 },
                    (_, i) => maxYear - i
                ).map(y =>
                    `<option value="${y}"${y === year ? ' selected' : ''}>${y}</option>`
                ).join('')}</select>`
                : `<span>${year}</span>`;
            headerCenter = `<div class="gruzz-cal-header-selects">${monthPart}${yearPart}</div>`;
        }

        let html = `
            <div class="custom-datepicker-header">
                <button type="button" class="gruzz-cal-prev" aria-label="Предыдущий месяц">
                    <i data-lucide="chevron-left"></i>
                </button>
                ${headerCenter}
                <button type="button" class="gruzz-cal-next" aria-label="Следующий месяц">
                    <i data-lucide="chevron-right"></i>
                </button>
            </div>
            <div class="custom-datepicker-weekdays">
                <div>Пн</div><div>Вт</div><div>Ср</div><div>Чт</div><div>Пт</div><div>Сб</div><div>Вс</div>
            </div>
            <div class="custom-datepicker-days">
        `;

        for (let i = 0; i < startOffset; i++) {
            html += '<div class="custom-datepicker-day empty"></div>';
        }

        for (let day = 1; day <= totalDays; day++) {
            const isToday = day === now.getDate() && month === now.getMonth() && year === now.getFullYear();
            const iso = this.formatIso(year, month, day);
            const isSelected = selectedIso === iso;
            let classes = 'custom-datepicker-day';
            if (isToday) classes += ' today';
            if (isSelected) classes += ' selected';
            html += `<div class="${classes}" data-day="${day}" data-iso="${iso}">${day}</div>`;
        }

        html += '</div>';
        dropdown.innerHTML = html;
        this.refreshPickerIcons(dropdown);

        dropdown.querySelector('.gruzz-cal-prev')?.addEventListener('click', (e) => {
            e.stopPropagation();
            handlers.onPrevMonth();
        });
        dropdown.querySelector('.gruzz-cal-next')?.addEventListener('click', (e) => {
            e.stopPropagation();
            handlers.onNextMonth();
        });
        dropdown.querySelector('.gruzz-cal-month-select')?.addEventListener('change', (e) => {
            e.stopPropagation();
            handlers.onMonthChange(parseInt(e.target.value, 10));
        });
        dropdown.querySelector('.gruzz-cal-year-select')?.addEventListener('change', (e) => {
            e.stopPropagation();
            handlers.onYearChange(parseInt(e.target.value, 10));
        });

        dropdown.querySelectorAll('.custom-datepicker-day:not(.empty)').forEach(dayEl => {
            dayEl.addEventListener('click', (e) => {
                e.stopPropagation();
                handlers.onDaySelect(dayEl.dataset.iso, parseInt(dayEl.dataset.day, 10));
            });
        });
    },

    updateDisplay(displayEl, iso, placeholder) {
        if (!displayEl) return;
        const parsed = this.parseIso(iso);
        if (parsed) {
            displayEl.textContent = this.formatDisplay(parsed.year, parsed.month, parsed.day);
            displayEl.classList.remove('is-placeholder');
        } else {
            displayEl.textContent = placeholder;
            displayEl.classList.add('is-placeholder');
        }
    },

    init(root, options = {}) {
        if (!root) return null;
        if (root.__gruzzPicker) return root.__gruzzPicker;

        const trigger = options.trigger
            || root.querySelector('[data-gruzz-date-trigger]')
            || root.querySelector('.gruzz-date-trigger')
            || root.querySelector('.gruzz-date-display');
        const dropdown = options.dropdown
            || root.querySelector('.gruzz-date-dropdown')
            || root.querySelector('.custom-datepicker');
        const hiddenInput = options.hiddenInput !== undefined
            ? options.hiddenInput
            : root.querySelector('input[type="hidden"]');
        const displayEl = options.displayEl
            || root.querySelector('.gruzz-date-display')
            || (trigger?.classList?.contains('gruzz-date-display') ? trigger : null)
            || trigger?.querySelector('.gruzz-date-display');
        const nowYear = new Date().getFullYear();
        const placeholder = options.placeholder || root.dataset.placeholder || 'Выберите дату';
        const pickerOptions = {
            changeMonth: options.changeMonth !== false,
            changeYear: options.changeYear !== false,
            yearRange: Array.isArray(options.yearRange)
                ? options.yearRange
                : [nowYear - 50, nowYear + 10],
        };
        const minYear = pickerOptions.yearRange ? pickerOptions.yearRange[0] : null;
        const maxYear = pickerOptions.yearRange ? pickerOptions.yearRange[1] : null;

        if (!trigger || !dropdown) return null;

        let currentViewDate = new Date();
        let selectedIso = hiddenInput?.value?.trim() || options.initialValue || '';

        if (selectedIso) {
            const parsed = this.parseIso(selectedIso);
            if (parsed) {
                currentViewDate = new Date(parsed.year, parsed.month, parsed.day);
            }
        }

        this.updateDisplay(displayEl, selectedIso, placeholder);

        const closeDropdown = () => {
            dropdown.style.display = 'none';
        };

        const clampViewDate = () => {
            if (minYear !== null && currentViewDate.getFullYear() < minYear) {
                currentViewDate.setFullYear(minYear, 0, 1);
            }
            if (maxYear !== null && currentViewDate.getFullYear() > maxYear) {
                currentViewDate.setFullYear(maxYear, 11, 1);
            }
        };

        const renderCurrent = () => {
            clampViewDate();
            this.render(dropdown, currentViewDate, selectedIso, {
                onPrevMonth: () => {
                    currentViewDate.setMonth(currentViewDate.getMonth() - 1);
                    clampViewDate();
                    renderCurrent();
                },
                onNextMonth: () => {
                    currentViewDate.setMonth(currentViewDate.getMonth() + 1);
                    clampViewDate();
                    renderCurrent();
                },
                onMonthChange: (monthIndex) => {
                    currentViewDate.setMonth(monthIndex);
                    clampViewDate();
                    renderCurrent();
                },
                onYearChange: (yearValue) => {
                    currentViewDate.setFullYear(yearValue);
                    clampViewDate();
                    renderCurrent();
                },
                onDaySelect: (iso) => {
                    selectedIso = iso;
                    const parsed = this.parseIso(iso);
                    if (hiddenInput) hiddenInput.value = iso;
                    this.updateDisplay(displayEl, iso, placeholder);

                    if (parsed) {
                        const shortLabel = this.formatDisplayShort(parsed.year, parsed.month, parsed.day);
                        if (typeof options.onSelect === 'function') {
                            options.onSelect(iso, shortLabel, parsed);
                        } else if (!displayEl && trigger && !trigger.querySelector('.gruzz-date-display')) {
                            trigger.textContent = shortLabel;
                        }
                    }

                    hiddenInput?.dispatchEvent(new Event('change', { bubbles: true }));
                    closeDropdown();
                }
            }, pickerOptions);
        };

        trigger.addEventListener('click', (e) => {
            e.stopPropagation();
            if (dropdown.style.display === 'block') {
                closeDropdown();
            } else {
                dropdown.style.display = 'block';
                renderCurrent();
            }
        });

        document.addEventListener('click', (e) => {
            if (!root.contains(e.target)) {
                closeDropdown();
            }
        });

        const api = {
            getValue: () => selectedIso,
            setValue(iso) {
                selectedIso = iso || '';
                if (hiddenInput) hiddenInput.value = selectedIso;
                GruzzDatePicker.updateDisplay(displayEl, selectedIso, placeholder);
                const parsed = GruzzDatePicker.parseIso(selectedIso);
                if (parsed) {
                    currentViewDate = new Date(parsed.year, parsed.month, parsed.day);
                }
                hiddenInput?.dispatchEvent(new Event('change', { bubbles: true }));
            }
        };

        root.__gruzzPicker = api;
        return api;
    },

    initAll(selector = '[data-gruzz-date-picker]') {
        document.querySelectorAll(selector).forEach(el => this.init(el));
    }
};