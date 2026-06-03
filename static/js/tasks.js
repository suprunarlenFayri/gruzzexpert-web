/**
 * TASKS.JS - Единый модуль управления заявками
 */
const TaskUI = {
    initTomSelects: function() {
        if (document.querySelector('.create-container, .edit-container')) {
            return;
        }

        // Функция рендера для селектов с избранными городами
        const favRenderConfig = {
            option: function(data, escape) {
                return `<div>
                    <span class="fav-star-btn ${data.isFav ? 'active' : ''}" data-id="${data.value}" style="cursor:pointer; margin-right:8px; color: ${data.isFav ? '#ffca28' : '#999'}; font-size: 16px;">
                        ${data.isFav ? '★' : '☆'}
                    </span>
                    <span>${escape(data.text)}</span>
                </div>`;
            },
            item: function(data, escape) {
                return `<div>${escape(data.text)}</div>`;
            }
        };

        // Обработчик клика по звездочке
        const onFavClick = function() {
            this.dropdown.addEventListener('click', (e) => {
                const btn = e.target.closest('.fav-star-btn');
                if (!btn) return;

                e.preventDefault();
                e.stopPropagation();
                const cityId = btn.dataset.id;

                fetch(`/api/favorite-city/${cityId}`, { method: 'POST' })
                    .then(r => r.json())
                    .then(res => {
                        if (this.options[cityId]) {
                            this.options[cityId].isFav = (res.status === 'added');
                        }
                        this.clearCache();
                        this.refreshOptions(false);
                    });
            });
        };

        // Города на странице создания/редактирования (не список заявок)
        const citySelect = document.getElementById('city_id');
        if (citySelect && !citySelect.tomselect) {
            new window.TomSelect(citySelect, {
                render: favRenderConfig,
                sortField: { field: 'text', direction: 'asc' },
                onInitialize: onFavClick,
            });
        }

        // Инициализация обычных селектов (клиенты и т.д.)
        const clientSelect = document.getElementById('client_id');
        if (clientSelect) {
            new window.TomSelect(clientSelect, {
                sortField: { field: "text", direction: "asc" }
            });
        }
    },

    toggleClientInput: function() {
        const select = document.getElementById('client_id');
        const newClientDiv = document.getElementById('new_client_group');
        if (select && newClientDiv) {
            const isNew = select.value === 'new';
            newClientDiv.style.display = isNew ? 'block' : 'none';

            // Железобетонный фикс валидации: отключаем скрытые поля через disabled
            const hiddenInputs = newClientDiv.querySelectorAll('input, textarea, select');
            hiddenInputs.forEach(input => {
                if (isNew) {
                    input.removeAttribute('disabled');
                    input.setAttribute('required', 'required');
                } else {
                    input.removeAttribute('required');
                    input.setAttribute('disabled', 'disabled'); // Браузер полностью проигнорирует поле
                }
            });
        }
    },

    calculatePrice: function() {
        const priceInput = document.getElementById('price_input');
        const workerInput = document.getElementById('required_workers');
        const resultDiv = document.getElementById('price_result');

        if (!priceInput || !resultDiv) return;

        // Вырезаем ВСЕ пробелы из строки и меняем запятую на точку
        const priceStr = priceInput.value.replace(/\s+/g, '').replace(',', '.');
        const workers = workerInput ? (parseInt(workerInput.value) || 1) : 1;

        if (!priceStr) {
            resultDiv.innerHTML = 'Итого: 0 ₽';
            return;
        }

        // Строгая регулярка без учета пробелов
        const hourlyMatch = priceStr.match(/^(\d+(?:\.\d+)?)\/(\d+(?:\.\d+)?)$/);
        if (hourlyMatch) {
            const rate = parseFloat(hourlyMatch[1]);
            const hours = parseFloat(hourlyMatch[2]);
            const total = rate * hours * workers;
            resultDiv.innerHTML = `Почасовая: ${rate}₽ × ${hours}ч × ${workers} чел = <strong>${total.toFixed(0)} ₽</strong>`;
        } else {
            const total = parseFloat(priceStr) * workers;
            if (!isNaN(total)) {
                resultDiv.innerHTML = `Фиксированная: ${parseFloat(priceStr)}₽ × ${workers} чел = <strong>${total.toFixed(0)} ₽</strong>`;
            } else {
                resultDiv.innerHTML = '<span style="color: var(--danger);">Неверный формат оплаты</span>';
            }
        }
    },

    validateTaskForm: function(e) {
        // Ищем поля по атрибуту name, так как макросы не задают id
        const title = document.querySelector('input[name="title"]')?.value.trim();
        const desc = document.querySelector('textarea[name="description"]')?.value.trim();
        const priceInput = document.getElementById('price_input');
        // Вырезаем ВСЕ пробелы перед проверкой
        const price = priceInput ? priceInput.value.replace(/\s+/g, '').replace(',', '.') : '';

        if (!title || !desc || !price) {
            e.preventDefault();
            if (window.showToast) window.showToast('Заполните все обязательные поля (Название, Описание, Оплата)', 'error');
            else alert('Заполните все обязательные поля (Название, Описание, Оплата)');
            return false;
        }

        // Строгая регулярка без учета пробелов
        const hourlyMatch = price.match(/^(\d+(?:\.\d+)?)\/(\d+(?:\.\d+)?)$/);
        const isNumber = !isNaN(parseFloat(price)) && isFinite(price);

        if (!hourlyMatch && !isNumber) {
            e.preventDefault();
            if (window.showToast) window.showToast('Формат оплаты: 1000 или 450/2', 'error');
            else alert('Укажите оплату в формате: 1000 (фиксированная) или 450/2 (часовая)');
            return false;
        }
        return true;
    },

    initDatePickers: function() {
        if (typeof window.GruzzDatePicker !== 'undefined') {
            window.GruzzDatePicker.initAll('[data-gruzz-date-picker]');
        }
    },

    initFilterCityCombobox: function() {
        const wrap = document.getElementById('filter-city-combobox');
        const input = document.getElementById('filter_city_input');
        const hidden = document.getElementById('filter_city_id');
        const dropdown = document.getElementById('filter_city_dropdown');
        const dataEl = document.getElementById('tasks-filter-cities-data');
        if (!wrap || !input || !hidden || !dropdown) return;
        if (wrap.dataset.comboboxReady === '1') return;
        wrap.dataset.comboboxReady = '1';

        let cities = [];
        if (dataEl && dataEl.textContent) {
            try {
                cities = JSON.parse(dataEl.textContent);
            } catch (e) {
                console.warn('[FilterCity] parse failed', e);
            }
        }

        function escapeHtml(text) {
            if (!text) return '';
            return String(text)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;');
        }

        function sortCities(list) {
            return list.slice().sort(function (a, b) {
                if (a.isFav && !b.isFav) return -1;
                if (!a.isFav && b.isFav) return 1;
                return String(a.name).localeCompare(String(b.name), 'ru');
            });
        }

        function renderDropdown(query) {
            const q = (query || '').trim().toLowerCase();
            let filtered = cities;
            if (q) {
                filtered = cities.filter(function (c) {
                    return String(c.name).toLowerCase().includes(q);
                });
            }
            filtered = sortCities(filtered);

            let html = '';
            if (!q) {
                html += '<button type="button" class="filter-city-option" data-id="" data-name=""><span>Все города</span></button>';
            }
            if (!filtered.length) {
                html += '<div class="filter-city-empty">Ничего не найдено</div>';
            } else {
                html += filtered.map(function (c) {
                    const fav = c.isFav ? '<span class="filter-city-fav" title="В избранном">★</span>' : '';
                    return `<button type="button" class="filter-city-option" data-id="${c.id}">${fav}<span>${escapeHtml(c.name)}</span></button>`;
                }).join('');
            }
            dropdown.innerHTML = html;
            dropdown.hidden = false;
        }

        function selectCity(id, name) {
            hidden.value = id ? String(id) : '';
            input.value = name || '';
            dropdown.hidden = true;
        }

        input.addEventListener('focus', function () {
            renderDropdown(input.value);
        });

        input.addEventListener('input', function () {
            hidden.value = '';
            renderDropdown(input.value);
        });

        input.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') {
                dropdown.hidden = true;
            }
        });

        dropdown.addEventListener('click', function (e) {
            const opt = e.target.closest('.filter-city-option');
            if (!opt) return;
            selectCity(opt.dataset.id || '');
        });

        dropdown.addEventListener('mousedown', function (e) {
            const star = e.target.closest('.filter-city-fav');
            if (!star) return;
            e.preventDefault();
            e.stopPropagation();
            const row = e.target.closest('.filter-city-option');
            if (!row || !row.dataset.id) return;
            const cityId = row.dataset.id;
            fetch('/api/favorite-city/' + cityId, { method: 'POST', headers: { Accept: 'application/json' } })
                .then(function (r) { return r.json(); })
                .then(function (res) {
                    const city = cities.find(function (c) { return String(c.id) === String(cityId); });
                    if (city) city.isFav = res.status === 'added';
                    renderDropdown(input.value);
                })
                .catch(function () { /* ignore */ });
        });

        document.addEventListener('click', function (e) {
            if (!wrap.contains(e.target)) {
                dropdown.hidden = true;
            }
        });

        if (hidden.value) {
            const found = cities.find(function (c) { return String(c.id) === String(hidden.value); });
            if (found) input.value = found.name;
        }
    },

    initListFilters: function() {
        const filterForm = document.getElementById('tasks-filter-form');
        if (!filterForm) return;

        this.initFilterCityCombobox();
        this.initDatePickers();

        if (typeof refreshIcons === 'function') {
            refreshIcons();
        }
    },

    setDeadlineDate: function(deadlineGroup, date) {
        if (!deadlineGroup || typeof window.GruzzDatePicker === 'undefined') return;

        const datePickerRoot = deadlineGroup.querySelector('[data-gruzz-date-picker]');
        if (!datePickerRoot) return;

        const iso = window.GruzzDatePicker.formatIso(
            date.getFullYear(),
            date.getMonth(),
            date.getDate()
        );

        if (datePickerRoot.__gruzzPicker?.setValue) {
            datePickerRoot.__gruzzPicker.setValue(iso);
        } else {
            const hiddenInput = datePickerRoot.querySelector('input[name="execution_date"]');
            const displayEl = datePickerRoot.querySelector('.gruzz-date-display');
            if (hiddenInput) hiddenInput.value = iso;
            window.GruzzDatePicker.updateDisplay(displayEl, iso, 'Выберите дату');
        }
    },

    setQuickDateActive: function(deadlineGroup, mode) {
        deadlineGroup?.querySelectorAll('[data-deadline-today], [data-deadline-tomorrow]').forEach(btn => {
            btn.classList.remove('is-active');
        });
        const selector = mode === 'tomorrow' ? '[data-deadline-tomorrow]' : '[data-deadline-today]';
        deadlineGroup?.querySelector(selector)?.classList.add('is-active');
    },

    selectHourChip: function(deadlineGroup, hour) {
        const timeInput = deadlineGroup?.querySelector('#execution_time');
        if (!timeInput || Number.isNaN(hour)) return;

        const timeValue = `${String(hour).padStart(2, '0')}:00`;
        timeInput.value = timeValue;
        timeInput.dispatchEvent(new Event('input', { bubbles: true }));
        timeInput.dispatchEvent(new Event('change', { bubbles: true }));

        deadlineGroup.querySelectorAll('.time-chip').forEach(chip => {
            chip.classList.toggle('active', parseInt(chip.dataset.hour, 10) === hour);
        });
    },

    normalizeTimeInput: function(input) {
        if (!input) return;
        const val = input.value.trim();
        if (!val) return;

        const match = val.match(/^(\d{1,2})(?::(\d{1,2}))?$/);
        if (!match) return;

        const hours = parseInt(match[1], 10);
        const minutes = match[2] !== undefined ? parseInt(match[2], 10) : 0;
        if (hours < 0 || hours > 23 || minutes < 0 || minutes > 59) return;

        input.value = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`;
    },

    syncHourButtons: function(deadlineGroup) {
        const timeInput = deadlineGroup?.querySelector('#execution_time');
        if (!timeInput) return;

        const match = timeInput.value.trim().match(/^(\d{1,2})/);
        const activeHour = match ? parseInt(match[1], 10) : null;

        deadlineGroup.querySelectorAll('.time-chip').forEach(chip => {
            const hour = parseInt(chip.dataset.hour, 10);
            chip.classList.toggle('active', activeHour === hour);
        });
    },

    initDeadlineControls: function() {
        const deadlineGroup = document.querySelector('[data-deadline-group]');
        if (!deadlineGroup) return;

        const timeInput = deadlineGroup.querySelector('#execution_time');

        deadlineGroup.querySelector('[data-deadline-today]')?.addEventListener('click', (e) => {
            e.preventDefault();
            this.setDeadlineDate(deadlineGroup, new Date());
            this.setQuickDateActive(deadlineGroup, 'today');
        });

        deadlineGroup.querySelector('[data-deadline-tomorrow]')?.addEventListener('click', (e) => {
            e.preventDefault();
            const tomorrow = new Date();
            tomorrow.setDate(tomorrow.getDate() + 1);
            this.setDeadlineDate(deadlineGroup, tomorrow);
            this.setQuickDateActive(deadlineGroup, 'tomorrow');
        });

        deadlineGroup.querySelectorAll('.time-chip').forEach(chip => {
            chip.addEventListener('click', (e) => {
                e.preventDefault();
                const hour = parseInt(chip.dataset.hour, 10);
                this.selectHourChip(deadlineGroup, hour);
            });
        });

        if (timeInput) {
            timeInput.addEventListener('input', () => this.syncHourButtons(deadlineGroup));
            timeInput.addEventListener('blur', () => {
                this.normalizeTimeInput(timeInput);
                this.syncHourButtons(deadlineGroup);
            });
            this.syncHourButtons(deadlineGroup);
        }
    },

    init: function() {
        if (document.querySelector('.create-container, .edit-container')) {
            this.initTomSelects();
            this.initDatePickers();
            this.initDeadlineControls();
        }

        // Привязка событий для форм
        const taskForm = document.querySelector('form');
        if (taskForm && document.getElementById('price_input')) {
            taskForm.addEventListener('submit', (e) => this.validateTaskForm(e));

            const priceInput = document.getElementById('price_input');
            const workerInput = document.getElementById('required_workers');
            const clientSelect = document.getElementById('client_id');
            const calcBtn = document.querySelector('.calc-btn');

            if (priceInput) {
                priceInput.addEventListener('input', () => this.calculatePrice());
                priceInput.addEventListener('blur', () => this.calculatePrice());
            }
            if (workerInput) {
                workerInput.addEventListener('input', () => this.calculatePrice());
                workerInput.addEventListener('change', () => this.calculatePrice());
            }
            if (calcBtn) {
                calcBtn.addEventListener('click', () => this.calculatePrice());
            }
            if (clientSelect) {
                clientSelect.addEventListener('change', () => this.toggleClientInput());
            }

            // Инициализация UI при загрузке
            this.calculatePrice();
            this.toggleClientInput();
        }
        console.log('Tasks Module Initialized');
    }
};

document.addEventListener('DOMContentLoaded', () => {
    TaskUI.init();
});

// Делаем глобально доступным
window.TaskUI = TaskUI;
