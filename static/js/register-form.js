/**
 * Регистрация: нативный POST, без блокировок. Тег — опциональная проверка (tag-availability.js).
 */
(function () {
    'use strict';

    function ensureSubmitEnabled() {
        var btn = document.getElementById('registerSubmitBtn');
        if (!btn) return;
        btn.disabled = false;
        btn.removeAttribute('disabled');
        btn.type = 'submit';
    }

    function initRegisterForm() {
        var form = document.getElementById('registerForm');
        if (!form) return;

        ensureSubmitEnabled();

        var tagInput = document.getElementById('registerTagInput');
        if (tagInput && window.TagAvailability && !form.dataset.tagCheckReady) {
            form.dataset.tagCheckReady = '1';
            try {
                window.TagAvailability.init(tagInput, form);
            } catch (err) {
                console.warn('[register-form] tag check init skipped', err);
            }
        }

        form.addEventListener('submit', function (e) {
            ensureSubmitEnabled();
            if (typeof form.checkValidity === 'function' && !form.checkValidity()) {
                e.preventDefault();
                if (typeof form.reportValidity === 'function') {
                    form.reportValidity();
                }
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initRegisterForm);
    } else {
        initRegisterForm();
    }
    window.addEventListener('load', ensureSubmitEnabled);
})();
