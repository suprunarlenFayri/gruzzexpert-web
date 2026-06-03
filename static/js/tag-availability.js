/**
 * Проверка занятости тега через GET /api/users/check-tag
 */
(function (global) {
    const DEFAULT_MESSAGE = 'Этот тег уже занят, придумайте другой';

    function debounce(fn, ms) {
        let timer;
        return function (...args) {
            clearTimeout(timer);
            timer = setTimeout(() => fn.apply(this, args), ms);
        };
    }

    function initTagInput(input, form, options) {
        if (!input) return;

        const opts = options || {};
        const noticeId = opts.noticeId || 'tag-availability-notice';
        let notice = document.getElementById(noticeId);
        if (!notice) {
            notice = document.createElement('div');
            notice.id = noticeId;
            notice.className = 'tag-availability-notice';
            notice.setAttribute('role', 'alert');
            notice.hidden = true;
            input.parentNode.appendChild(notice);
        }

        let tagOk = !input.required;
        let checking = false;

        function setSubmitEnabled(enabled) {
            const btn = form && (form.querySelector('[type="submit"]') || form.querySelector('button[type="submit"]'));
            if (btn) btn.disabled = !enabled;
        }

        function setInvalid(message) {
            input.classList.add('tag-invalid');
            notice.textContent = message || DEFAULT_MESSAGE;
            notice.hidden = false;
            tagOk = false;
            setSubmitEnabled(false);
        }

        function setValid() {
            input.classList.remove('tag-invalid');
            notice.hidden = true;
            notice.textContent = '';
            tagOk = true;
            if (!checking) setSubmitEnabled(true);
        }

        async function runCheck() {
            const tag = (input.value || '').trim().replace(/^@+/, '');
            if (!tag) {
                tagOk = !input.required;
                input.classList.remove('tag-invalid');
                notice.hidden = true;
                setSubmitEnabled(tagOk);
                return;
            }

            checking = true;
            setSubmitEnabled(false);
            try {
                const params = new URLSearchParams({ tag });
                if (opts.excludeUserId) params.set('exclude', String(opts.excludeUserId));
                const res = await fetch(`/api/users/check-tag?${params.toString()}`, {
                    headers: { Accept: 'application/json' },
                });
                const data = await res.json();
                if (data.available) {
                    setValid();
                } else {
                    setInvalid(DEFAULT_MESSAGE);
                }
            } catch (err) {
                console.error('tag check failed', err);
                setSubmitEnabled(true);
            } finally {
                checking = false;
            }
        }

        const debouncedCheck = debounce(runCheck, 350);
        input.addEventListener('input', debouncedCheck);
        input.addEventListener('blur', runCheck);

        if (form) {
            form.addEventListener('submit', (e) => {
                const tag = (input.value || '').trim();
                if (tag && !tagOk) {
                    e.preventDefault();
                    setInvalid(DEFAULT_MESSAGE);
                }
            });
        }

        if ((input.value || '').trim()) {
            runCheck();
        }
    }

    global.TagAvailability = { init: initTagInput, DEFAULT_MESSAGE };
})(window);
