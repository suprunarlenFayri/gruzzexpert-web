(function () {
    'use strict';

    var AUTO_SELECTORS = [
        'select.settings-select',
        'select.filter-select',
        'select.gruzz-native-select',
        'select.detail-add-worker-select',
        'select[data-b2b-select]',
    ].join(',');

    function closeAll(except) {
        document.querySelectorAll('.b2b-select-wrapper.open').forEach(function (wrapper) {
            if (wrapper !== except) {
                wrapper.classList.remove('open');
            }
        });
    }

    function getSelectedOption(select) {
        var idx = select.selectedIndex;
        if (idx < 0) return null;
        return select.options[idx];
    }

    function resolveNativeSelect(wrapper) {
        if (wrapper._b2bNativeSelect) return wrapper._b2bNativeSelect;
        var native = wrapper.querySelector('select[data-b2b-converted="1"]');
        if (!native && wrapper.nextElementSibling && wrapper.nextElementSibling.tagName === 'SELECT') {
            native = wrapper.nextElementSibling;
        }
        if (native) wrapper._b2bNativeSelect = native;
        return native || null;
    }

    function buildOptionEl(value, label, isActive) {
        var el = document.createElement('div');
        el.className = 'b2b-select-option' + (isActive ? ' active' : '');
        el.dataset.value = value;
        el.textContent = label;
        el.setAttribute('role', 'option');
        return el;
    }

    function initWrapper(wrapper) {
        if (wrapper.dataset.b2bInit === '1') return;
        wrapper.dataset.b2bInit = '1';

        var input = wrapper.querySelector('.b2b-select-input');
        var dropdown = wrapper.querySelector('.b2b-select-dropdown');
        var valueEl = wrapper.querySelector('.b2b-selected-value');
        var hidden = wrapper.querySelector('input[type="hidden"]');
        var nativeSelect = resolveNativeSelect(wrapper);

        if (!input || !valueEl || !dropdown) return;

        function refreshOptions() {
            return wrapper.querySelectorAll('.b2b-select-option');
        }

        function setValue(val, label, silent) {
            if (hidden) {
                hidden.value = val;
            }
            if (nativeSelect) {
                nativeSelect.value = val;
            }
            valueEl.textContent = label;
            refreshOptions().forEach(function (opt) {
                opt.classList.toggle('active', opt.dataset.value === val);
            });
            wrapper.classList.remove('open');
            if (!silent && hidden) {
                hidden.dispatchEvent(new Event('change', { bubbles: true }));
            }
        }

        function pickOption(opt, e) {
            if (!opt || wrapper.classList.contains('is-disabled')) return;
            if (e) {
                e.preventDefault();
                e.stopPropagation();
            }
            setValue(opt.dataset.value, opt.textContent.trim());
        }

        input.addEventListener('click', function (e) {
            e.stopPropagation();
            if (wrapper.classList.contains('is-disabled')) return;
            var willOpen = !wrapper.classList.contains('open');
            closeAll(willOpen ? wrapper : null);
            wrapper.classList.toggle('open', willOpen);
        });

        input.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                input.click();
            } else if (e.key === 'Escape') {
                wrapper.classList.remove('open');
            }
        });

        dropdown.addEventListener('mousedown', function (e) {
            pickOption(e.target.closest('.b2b-select-option'), e);
        });

        dropdown.addEventListener('click', function (e) {
            pickOption(e.target.closest('.b2b-select-option'), e);
        });

        wrapper._b2bSetValue = setValue;
    }

    function convertNativeSelect(select) {
        if (!select || select.dataset.b2bConverted === '1') return null;
        if (select.multiple || select.size > 1) return null;
        if (select.classList.contains('tomselected')) return null;

        var selected = getSelectedOption(select);
        var wrapper = document.createElement('div');
        wrapper.className = 'b2b-select-wrapper';
        if (select.classList.contains('filter-control')) {
            wrapper.classList.add('filter-control');
        }
        if (select.classList.contains('detail-add-worker-select')) {
            wrapper.classList.add('detail-add-worker-b2b');
        }

        var input = document.createElement('div');
        input.className = 'b2b-select-input';
        input.tabIndex = 0;
        input.setAttribute('role', 'button');
        input.setAttribute('aria-haspopup', 'listbox');

        var valueSpan = document.createElement('span');
        valueSpan.className = 'b2b-selected-value';
        valueSpan.textContent = selected ? selected.textContent.trim() : '';

        var arrow = document.createElement('span');
        arrow.className = 'b2b-select-arrow';
        arrow.textContent = '↓';

        input.appendChild(valueSpan);
        input.appendChild(arrow);

        var dropdown = document.createElement('div');
        dropdown.className = 'b2b-select-dropdown';
        dropdown.setAttribute('role', 'listbox');

        Array.prototype.forEach.call(select.options, function (opt) {
            dropdown.appendChild(buildOptionEl(opt.value, opt.textContent.trim(), opt.selected));
        });

        var hidden = document.createElement('input');
        hidden.type = 'hidden';
        if (select.name) hidden.name = select.name;
        hidden.value = selected ? selected.value : '';
        if (select.id) {
            hidden.id = select.id;
            select.removeAttribute('id');
        }

        if (select.dataset.settingKey) {
            hidden.dataset.settingKey = select.dataset.settingKey;
        }

        wrapper._b2bNativeSelect = select;
        wrapper.appendChild(input);
        wrapper.appendChild(dropdown);
        wrapper.appendChild(hidden);

        select.parentNode.insertBefore(wrapper, select);
        select.removeAttribute('name');
        select.classList.add('b2b-select-native-hidden');
        select.dataset.b2bConverted = '1';
        select._b2bWrapper = wrapper;
        select.setAttribute('aria-hidden', 'true');
        select.tabIndex = -1;
        wrapper.appendChild(select);

        initWrapper(wrapper);
        return wrapper;
    }

    function initAll(root) {
        var scope = root || document;
        scope.querySelectorAll(AUTO_SELECTORS).forEach(convertNativeSelect);
        scope.querySelectorAll('.b2b-select-wrapper').forEach(initWrapper);
    }

    document.addEventListener('mousedown', function (e) {
        if (e.target.closest('.b2b-select-wrapper')) return;
        closeAll(null);
    });

    document.addEventListener('DOMContentLoaded', function () {
        initAll(document);
    });

    window.B2bSelect = {
        init: initAll,
        initWrapper: initWrapper,
        convertNativeSelect: convertNativeSelect,
        closeAll: closeAll,
    };
})();
