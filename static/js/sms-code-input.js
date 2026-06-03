/**
 * 4-значный SMS-код: автофокус, только цифры, переход по ячейкам (опционально).
 */
(function () {
    'use strict';

    function bindSmsInput(el) {
        if (!el || el.dataset.smsBound) return;
        el.dataset.smsBound = '1';
        el.addEventListener('input', function () {
            this.value = this.value.replace(/\D/g, '').slice(0, 4);
        });
        el.addEventListener('paste', function (e) {
            e.preventDefault();
            const text = (e.clipboardData || window.clipboardData).getData('text') || '';
            this.value = text.replace(/\D/g, '').slice(0, 4);
        });
        if (document.activeElement !== el) {
            setTimeout(function () { el.focus(); }, 80);
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        document.querySelectorAll('.sms-code-input, #smsCodeInput').forEach(bindSmsInput);
    });

    window.bindSmsCodeInput = bindSmsInput;
})();
