(function () {
    'use strict';

    var phonePending = '';
    var tagPending = '';

    function escapeHtml(text) {
        if (!text) return '';
        return String(text)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function showToast(msg, type) {
        if (typeof window.showToast === 'function') {
            window.showToast(msg, type || 'info');
        } else {
            alert(msg);
        }
    }

    async function apiPost(url, body) {
        var res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify(body || {}),
        });
        var data = await res.json();
        if (!res.ok && data.status !== 'success' && data.status !== 'ticket_created' && data.status !== 'codes_sent') {
            throw new Error(data.error || data.message || 'Ошибка запроса');
        }
        return data;
    }

    function openModal(modalId) {
        var modal = document.getElementById(modalId);
        if (!modal) return;
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
        if (typeof refreshIcons === 'function') refreshIcons();
    }

    function closeModal(modalId) {
        var modal = document.getElementById(modalId);
        if (!modal) return;
        modal.classList.remove('active');
        document.body.style.overflow = '';
    }

    function showCodesStep(step1Id, step2Id, devHintId, data) {
        document.getElementById(step1Id).hidden = true;
        document.getElementById(step2Id).hidden = false;
        var hint = document.getElementById(devHintId);
        if (data.mock_codes) {
            hint.innerHTML = '<strong>Режим разработки:</strong> старый SMS <code>' + escapeHtml(data.mock_codes.old_sms) +
                '</code>, новый SMS <code>' + escapeHtml(data.mock_codes.new_sms) +
                '</code>, email <code>' + escapeHtml(data.mock_codes.email) + '</code>';
            hint.hidden = false;
        } else {
            hint.hidden = true;
        }
    }

    function resetSecurityModal(modalId, step1Id, step2Id, devHintId) {
        document.getElementById(step1Id).hidden = false;
        document.getElementById(step2Id).hidden = true;
        document.getElementById(devHintId).hidden = true;
        openModal(modalId);
    }

    window.openPhoneChangeModal = function () {
        phonePending = '';
        resetSecurityModal('phoneChangeModal', 'phoneChangeStep1', 'phoneChangeStep2', 'phoneChangeDevHint');
    };

    window.closePhoneChangeModal = function () {
        closeModal('phoneChangeModal');
    };

    window.openTagChangeModal = function () {
        tagPending = '';
        resetSecurityModal('tagChangeModal', 'tagChangeStep1', 'tagChangeStep2', 'tagChangeDevHint');
    };

    window.closeTagChangeModal = function () {
        closeModal('tagChangeModal');
    };

    async function loadSessions() {
        var list = document.getElementById('active-sessions-list');
        if (!list) return;
        try {
            var res = await fetch('/api/sessions', { credentials: 'same-origin', headers: { 'Accept': 'application/json' } });
            var data = await res.json();
            if (!data.ok || !data.sessions || !data.sessions.length) {
                list.innerHTML = '<div class="settings-row-hint">Нет сохранённых устройств</div>';
                return;
            }
            list.innerHTML = data.sessions.map(function (s) {
                var title = s.device_name || [s.browser, s.os].filter(Boolean).join(' · ') || 'Устройство';
                var ip = s.ip_address || s.ip;
                var meta = ip ? 'IP ' + ip : '';
                var whenRaw = s.last_active || s.last_login;
                var when = whenRaw ? new Date(whenRaw).toLocaleString('ru-RU') : '—';
                return '<div class="session-item' + (s.is_current ? ' is-current' : '') + '">' +
                    '<div class="session-item-main">' +
                    '<div class="session-item-title">' + escapeHtml(title) + '</div>' +
                    '<div class="session-item-meta">' + escapeHtml(meta ? meta + ' · ' : '') +
                    'Последняя активность: ' + escapeHtml(when) + '</div>' +
                    '</div>' +
                    (s.is_current ? '<span class="session-badge">Текущее</span>' : '') +
                    '</div>';
            }).join('');
        } catch (e) {
            list.innerHTML = '<div class="settings-row-hint">Не удалось загрузить сессии</div>';
        }
    }

    function focusSecurityBlockFromHash() {
        var hash = window.location.hash;
        if (!hash) return;
        var el = document.querySelector(hash);
        if (!el || !el.classList.contains('settings-hash-target')) return;
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        el.classList.remove('settings-hash-highlight');
        void el.offsetWidth;
        el.classList.add('settings-hash-highlight');
        window.setTimeout(function () {
            el.classList.remove('settings-hash-highlight');
        }, 2200);
    }

    document.addEventListener('DOMContentLoaded', function () {
        var openPhoneBtn = document.getElementById('btn-open-phone-change');
        if (openPhoneBtn) openPhoneBtn.addEventListener('click', window.openPhoneChangeModal);

        var openTagBtn = document.getElementById('btn-open-tag-change');
        if (openTagBtn) openTagBtn.addEventListener('click', window.openTagChangeModal);

        var getPhoneCodesBtn = document.getElementById('btnPhoneChangeGetCodes');
        if (getPhoneCodesBtn) {
            getPhoneCodesBtn.addEventListener('click', async function () {
                var phone = (document.getElementById('phoneChangeNew').value || '').trim();
                if (!phone) {
                    showToast('Введите новый номер', 'error');
                    return;
                }
                phonePending = phone;
                getPhoneCodesBtn.disabled = true;
                try {
                    var data = await apiPost('/api/request-phone-change', { action: 'init', new_phone: phone });
                    showCodesStep('phoneChangeStep1', 'phoneChangeStep2', 'phoneChangeDevHint', data);
                    showToast('Коды отправлены (режим разработки)', 'success');
                } catch (err) {
                    showToast(err.message, 'error');
                } finally {
                    getPhoneCodesBtn.disabled = false;
                }
            });
        }

        var phoneBackBtn = document.getElementById('btnPhoneChangeBack');
        if (phoneBackBtn) {
            phoneBackBtn.addEventListener('click', function () {
                document.getElementById('phoneChangeStep2').hidden = true;
                document.getElementById('phoneChangeStep1').hidden = false;
            });
        }

        var resendPhoneEmail = document.getElementById('btnResendEmailCode');
        if (resendPhoneEmail) {
            resendPhoneEmail.addEventListener('click', async function () {
                try {
                    var data = await apiPost('/api/request-phone-change', { action: 'send_email' });
                    if (data.mock_codes && data.mock_codes.email) {
                        var hint = document.getElementById('phoneChangeDevHint');
                        hint.innerHTML = '<strong>Email-код (dev):</strong> <code>' + escapeHtml(data.mock_codes.email) + '</code>';
                        hint.hidden = false;
                    }
                    showToast('Код отправлен на почту', 'success');
                } catch (err) {
                    showToast(err.message, 'error');
                }
            });
        }

        var confirmPhoneBtn = document.getElementById('btnPhoneChangeConfirm');
        if (confirmPhoneBtn) {
            confirmPhoneBtn.addEventListener('click', async function () {
                confirmPhoneBtn.disabled = true;
                try {
                    var data = await apiPost('/api/request-phone-change', {
                        action: 'confirm',
                        new_phone: phonePending,
                        old_sms_code: document.getElementById('phoneChangeOldSms').value,
                        new_sms_code: document.getElementById('phoneChangeNewSms').value,
                        email_code: document.getElementById('phoneChangeEmail').value,
                    });
                    if (data.status === 'success') {
                        var phoneEl = document.getElementById('settings-current-phone');
                        if (phoneEl && data.phone) phoneEl.textContent = data.phone;
                        showToast('Номер телефона успешно изменён. Баланс заморожен на 48 ч.', 'success');
                        closePhoneChangeModal();
                        setTimeout(function () { window.location.reload(); }, 800);
                    }
                } catch (err) {
                    showToast(err.message, 'error');
                } finally {
                    confirmPhoneBtn.disabled = false;
                }
            });
        }

        var phoneRecoveryBtn = document.getElementById('btnPhoneRecovery');
        if (phoneRecoveryBtn) {
            phoneRecoveryBtn.addEventListener('click', async function () {
                if (!confirm('Отправить заявку диспетчеру на ручную проверку?')) return;
                try {
                    var data = await apiPost('/api/request-phone-change', {
                        action: 'recovery',
                        new_phone: phonePending || document.getElementById('phoneChangeNew').value,
                    });
                    showToast(data.message || 'Заявка на восстановление отправлена диспетчеру', 'success');
                    closePhoneChangeModal();
                } catch (err) {
                    showToast(err.message, 'error');
                }
            });
        }

        var getTagCodesBtn = document.getElementById('btnTagChangeGetCodes');
        if (getTagCodesBtn) {
            getTagCodesBtn.addEventListener('click', async function () {
                var tag = (document.getElementById('tagChangeNew').value || '').trim();
                if (!tag) {
                    showToast('Введите новый тег', 'error');
                    return;
                }
                tagPending = tag;
                getTagCodesBtn.disabled = true;
                try {
                    var data = await apiPost('/api/request-tag-change', { action: 'init', new_tag: tag });
                    showCodesStep('tagChangeStep1', 'tagChangeStep2', 'tagChangeDevHint', data);
                    showToast('Коды отправлены (режим разработки)', 'success');
                } catch (err) {
                    showToast(err.message, 'error');
                } finally {
                    getTagCodesBtn.disabled = false;
                }
            });
        }

        var tagBackBtn = document.getElementById('btnTagChangeBack');
        if (tagBackBtn) {
            tagBackBtn.addEventListener('click', function () {
                document.getElementById('tagChangeStep2').hidden = true;
                document.getElementById('tagChangeStep1').hidden = false;
            });
        }

        var resendTagEmail = document.getElementById('btnTagResendEmailCode');
        if (resendTagEmail) {
            resendTagEmail.addEventListener('click', async function () {
                try {
                    var data = await apiPost('/api/request-tag-change', { action: 'send_email' });
                    if (data.mock_codes && data.mock_codes.email) {
                        var hint = document.getElementById('tagChangeDevHint');
                        hint.innerHTML = '<strong>Email-код (dev):</strong> <code>' + escapeHtml(data.mock_codes.email) + '</code>';
                        hint.hidden = false;
                    }
                    showToast('Код отправлен на почту', 'success');
                } catch (err) {
                    showToast(err.message, 'error');
                }
            });
        }

        var confirmTagBtn = document.getElementById('btnTagChangeConfirm');
        if (confirmTagBtn) {
            confirmTagBtn.addEventListener('click', async function () {
                confirmTagBtn.disabled = true;
                try {
                    var data = await apiPost('/api/request-tag-change', {
                        action: 'confirm',
                        new_tag: tagPending,
                        old_sms_code: document.getElementById('tagChangeOldSms').value,
                        new_sms_code: document.getElementById('tagChangeNewSms').value,
                        email_code: document.getElementById('tagChangeEmail').value,
                    });
                    if (data.status === 'success') {
                        var tagEl = document.getElementById('settings-current-tag');
                        if (tagEl && data.tag) tagEl.textContent = '@' + data.tag;
                        showToast('Тег успешно изменён. Баланс заморожен на 48 ч.', 'success');
                        closeTagChangeModal();
                        setTimeout(function () { window.location.reload(); }, 800);
                    }
                } catch (err) {
                    showToast(err.message, 'error');
                } finally {
                    confirmTagBtn.disabled = false;
                }
            });
        }

        var tagRecoveryBtn = document.getElementById('btnTagRecovery');
        if (tagRecoveryBtn) {
            tagRecoveryBtn.addEventListener('click', async function () {
                if (!confirm('Отправить заявку диспетчеру на ручную проверку?')) return;
                try {
                    var data = await apiPost('/api/request-tag-change', {
                        action: 'recovery',
                        new_tag: tagPending || document.getElementById('tagChangeNew').value,
                    });
                    showToast(data.message || 'Заявка на восстановление отправлена диспетчеру', 'success');
                    closeTagChangeModal();
                } catch (err) {
                    showToast(err.message, 'error');
                }
            });
        }

        var revokeBtn = document.getElementById('btn-revoke-sessions');
        if (revokeBtn) {
            revokeBtn.addEventListener('click', async function () {
                if (!confirm('Завершить все сессии, кроме текущей?')) return;
                try {
                    await apiPost('/api/sessions/terminate', {});
                    showToast('Остальные сессии завершены', 'success');
                    loadSessions();
                } catch (err) {
                    showToast(err.message, 'error');
                }
            });
        }

        loadSessions();
        focusSecurityBlockFromHash();
        window.addEventListener('hashchange', focusSecurityBlockFromHash);

        if (window.location.hash === '#tag-block') {
            window.setTimeout(window.openTagChangeModal, 400);
        } else if (window.location.hash === '#phone-block') {
            window.setTimeout(window.openPhoneChangeModal, 400);
        }
    });
})();
