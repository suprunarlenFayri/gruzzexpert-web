/**
 * Проверка занятости тега через GET /api/users/check-tag.
 * Не блокирует отправку формы, кроме случая когда тег уже подтверждённо занят.
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
        if (!input || !form) return;

        const opts = options || {};
        const noticeId = opts.noticeId || 'tag-availability-notice';
        let notice = document.getElementById(noticeId);
        if (!notice && input.parentNode) {
            notice = document.createElement('div');
            notice.id = noticeId;
            notice.className = 'tag-availability-notice';
            notice.setAttribute('role', 'alert');
            notice.hidden = true;
            input.parentNode.appendChild(notice);
        }

        /** @type {'unknown'|'ok'|'bad'} */
        let tagState = 'unknown';

        function setInvalid(message) {
            input.classList.add('tag-invalid');
            if (notice) {
                notice.textContent = message || DEFAULT_MESSAGE;
                notice.hidden = false;
            }
            tagState = 'bad';
        }

        function setValid() {
            input.classList.remove('tag-invalid');
            if (notice) {
                notice.hidden = true;
                notice.textContent = '';
            }
            tagState = 'ok';
        }

        function resetUnknown() {
            if (tagState !== 'bad') {
                input.classList.remove('tag-invalid');
                if (notice) {
                    notice.hidden = true;
                    notice.textContent = '';
                }
            }
            tagState = 'unknown';
        }

        async function checkTagNow() {
            const tag = (input.value || '').trim().replace(/^@+/, '');
            if (!tag) {
                resetUnknown();
                return true;
            }

            try {
                const params = new URLSearchParams({ tag });
                if (opts.excludeUserId) params.set('exclude', String(opts.excludeUserId));
                const res = await fetch(`/api/users/check-tag?${params.toString()}`, {
                    headers: { Accept: 'application/json' },
                });
                if (!res.ok) {
                    return true;
                }
                const data = await res.json();
                if (data.available) {
                    setValid();
                    return true;
                }
                setInvalid(DEFAULT_MESSAGE);
                return false;
            } catch (err) {
                console.warn('[TagAvailability] check failed, allow submit', err);
                return true;
            }
        }

        const debouncedCheck = debounce(checkTagNow, 350);
        input.addEventListener('input', debouncedCheck);
        input.addEventListener('blur', checkTagNow);

        form.addEventListener('submit', function (e) {
            const tag = (input.value || '').trim().replace(/^@+/, '');
            if (!tag) {
                return;
            }
            if (tagState === 'bad') {
                e.preventDefault();
                setInvalid(DEFAULT_MESSAGE);
            }
        });

        const submitBtn = form.querySelector('[type="submit"]');
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.removeAttribute('disabled');
        }

        if ((input.value || '').trim()) {
            checkTagNow();
        }
    }

    global.TagAvailability = { init: initTagInput, DEFAULT_MESSAGE };
})(window);
