/**
 * Кнопки исполнителя: «Взять в работу» (inline-лоадер в кнопке), статусы, отказ, снятие.
 */
(function () {
    'use strict';

    const ACCEPT_LOADER_MS = 5000;
    const ACCEPT_PLAYBACK_RATE = 2.0;
    const ACCEPT_SUCCESS_MS = 500;

    const STEP_TO_API_STATUS = {
        route: 'on_way',
        arrive: 'arrived',
        finish: 'completed',
        submit: 'submit',
        reject: 'reject',
    };

    function taskDetailFooter() {
        return document.getElementById('task-detail-footer');
    }

    function isInsideWorkerActionsPanel(el) {
        return Boolean(el && el.closest('.task-detail-actions-worker'));
    }

    function resolveTaskIdFromClick(target, fallbackId) {
        const footer = target.closest(
            '.task-detail-actions-worker, #task-detail-footer, .worker-actions-footer, #detail-worker-actions'
        );
        if (footer && footer.dataset.taskId) {
            return parseInt(footer.dataset.taskId, 10);
        }
        const card = target.closest('#detail-assignments-card, [data-task-id]');
        if (card && card.dataset.taskId) {
            return parseInt(card.dataset.taskId, 10);
        }
        const btn = target.closest('[data-task-id]');
        if (btn && btn.dataset.taskId) {
            return parseInt(btn.dataset.taskId, 10);
        }
        return fallbackId ? parseInt(fallbackId, 10) : null;
    }

    function getInlineAcceptVideo(btn) {
        if (!btn || !isInsideWorkerActionsPanel(btn)) return null;
        return btn.querySelector('.btn-video');
    }

    function resetInlineVideo(btn) {
        const video = getInlineAcceptVideo(btn);
        if (!video) return;
        video.pause();
        video.loop = false;
        video.removeAttribute('autoplay');
        video.playbackRate = 1;
        video.currentTime = 0;
    }

    function stopInlineAcceptLoader(btn) {
        const video = getInlineAcceptVideo(btn);
        if (video) {
            video.onended = null;
            video.pause();
            video.currentTime = 0;
            video.playbackRate = 1;
        }
        if (btn) {
            btn.classList.remove('is-animating', 'is-previewing');
        }
    }

    /**
     * Лоадер строго внутри кнопки: 2x скорость, макс. 5 с, затем resolve.
     */
    function playInlineAcceptLoader(btn) {
        return new Promise(function (resolve) {
            const video = getInlineAcceptVideo(btn);
            if (!video) {
                setTimeout(resolve, ACCEPT_LOADER_MS);
                return;
            }

            let settled = false;
            function finish() {
                if (settled) return;
                settled = true;
                clearTimeout(fallbackTimer);
                video.removeEventListener('ended', onEnded);
                video.pause();
                resolve();
            }

            function onEnded() {
                finish();
            }

            btn.classList.remove('is-previewing');
            btn.classList.add('is-animating');
            video.pause();
            video.currentTime = 0;
            video.loop = false;
            video.playbackRate = ACCEPT_PLAYBACK_RATE;
            video.addEventListener('ended', onEnded);

            const fallbackTimer = setTimeout(finish, ACCEPT_LOADER_MS);
            video.play().catch(function () {
                finish();
            });
        });
    }

    async function postTaskStatus(taskId, status) {
        const response = await fetch(`/api/tasks/${taskId}/status`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: JSON.stringify({ status }),
        });
        const data = await response.json().catch(() => ({}));
        return { response, data };
    }

    async function postRemoveWorker(taskId, workerId) {
        const response = await fetch(`/api/tasks/${taskId}/remove-worker`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: JSON.stringify({ worker_id: workerId }),
        });
        const data = await response.json().catch(() => ({}));
        return { response, data };
    }

    function applyTaskPayload(data) {
        const payload = data.payload || data;
        if (typeof window.handleTaskUpdate === 'function' && payload) {
            window.handleTaskUpdate(payload);
        }
    }

    function refreshTaskDetail(taskId) {
        if (typeof window.openGlobalTaskSidebar === 'function') {
            window.openGlobalTaskSidebar(taskId);
        } else if (typeof window.openTaskDetail === 'function') {
            window.openTaskDetail(taskId);
        }
    }

    async function handleTaskAccept(btn, taskId) {
        if (!btn || !isInsideWorkerActionsPanel(btn)) return;
        if (!taskId || btn.classList.contains('is-success') || btn.dataset.loading === '1') {
            return;
        }

        btn.dataset.loading = '1';

        try {
            await playInlineAcceptLoader(btn);

            const { response, data } = await postTaskStatus(taskId, 'accept');
            if (!response.ok || !data.ok) {
                alert(data.error || 'Не удалось взять заявку');
                btn.dataset.loading = '';
                stopInlineAcceptLoader(btn);
                return;
            }

            btn.classList.add('is-success');
            btn.classList.remove('is-animating');
            stopInlineAcceptLoader(btn);
            applyTaskPayload(data);

            await new Promise(function (r) {
                setTimeout(r, ACCEPT_SUCCESS_MS);
            });
            refreshTaskDetail(taskId);
        } catch (err) {
            console.error(err);
            alert('Ошибка сети');
            btn.dataset.loading = '';
            stopInlineAcceptLoader(btn);
        }
    }

    async function updateWorkerStatus(taskId, step, btn, options) {
        if (!taskId) return;
        if (btn && (btn.disabled || btn.classList.contains('is-disabled'))) return;

        if (step === 'reject') {
            if (!confirm('Отказаться от этой заявки? Она снова станет доступна другим исполнителям.')) {
                return;
            }
        }

        const apiStatus = STEP_TO_API_STATUS[step] || step;
        if (btn) btn.disabled = true;

        try {
            const { response, data } = await postTaskStatus(taskId, apiStatus);
            if (!response.ok || !data.ok) {
                alert(data.error || 'Не удалось обновить статус');
                if (btn) btn.disabled = false;
                return;
            }
            applyTaskPayload(data);
            if (options && options.fromCard) {
                if (typeof window.refreshTaskCardTracking === 'function') {
                    window.refreshTaskCardTracking(taskId, data.tracking || data);
                }
            } else {
                refreshTaskDetail(taskId);
            }
        } catch (err) {
            console.error(err);
            alert('Ошибка сети');
            if (btn) btn.disabled = false;
        }
    }

    /** Ховер: только подсветка текста/рамки, видео не показываем и не запускаем. */
    function bindGruzzVideoBtnHover(root) {
        const scope = root || document;
        scope.querySelectorAll('.task-detail-actions-worker .gruzz-video-btn').forEach(function (btn) {
            if (btn.dataset.hoverBound === '1') return;
            btn.dataset.hoverBound = '1';
            resetInlineVideo(btn);

            btn.addEventListener('mouseenter', function () {
                if (btn.classList.contains('is-success') || btn.classList.contains('is-animating')) {
                    return;
                }
                btn.classList.add('is-previewing');
                resetInlineVideo(btn);
            });

            btn.addEventListener('mouseleave', function () {
                if (btn.classList.contains('is-animating') || btn.classList.contains('is-success')) {
                    return;
                }
                btn.classList.remove('is-previewing');
                resetInlineVideo(btn);
            });
        });
    }

    function initAcceptTaskButton(root, taskId) {
        const scope = root || document;
        scope.querySelectorAll('.task-detail-actions-worker .gruzz-video-btn').forEach(function (btn) {
            if (btn.dataset.clickBound === '1') return;
            btn.dataset.clickBound = '1';
            const tid = btn.dataset.taskId || taskId;
            if (!tid) return;
            resetInlineVideo(btn);
            btn.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
                handleTaskAccept(btn, tid);
            });
        });
    }

    function bindWorkerActionButtons(taskId, root) {
        const scope = root || document;
        scope.querySelectorAll('[data-worker-action]').forEach(function (btn) {
            if (btn.dataset.bound === '1') return;
            btn.dataset.bound = '1';
            btn.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
                const tid = resolveTaskIdFromClick(btn, taskId) || taskId;
                updateWorkerStatus(tid, btn.dataset.workerAction, btn);
            });
        });
    }

    function bindRemoveWorkerButtons(taskId, root) {
        const scope = root || document;
        scope.querySelectorAll('.detail-remove-worker').forEach(function (btn) {
            if (btn.dataset.bound === '1') return;
            btn.dataset.bound = '1';
            btn.addEventListener('click', async function (e) {
                e.preventDefault();
                e.stopPropagation();
                const userId = btn.dataset.userId;
                const tid = resolveTaskIdFromClick(btn, taskId) || taskId;
                if (!userId || !tid) return;
                if (!confirm('Снять исполнителя с заявки?')) return;

                btn.disabled = true;
                try {
                    const { response, data } = await postRemoveWorker(tid, parseInt(userId, 10));
                    if (!response.ok || !data.ok) {
                        alert(data.error || 'Не удалось снять исполнителя');
                        return;
                    }
                    applyTaskPayload(data);
                    refreshTaskDetail(tid);
                } catch (err) {
                    console.error(err);
                    alert('Ошибка сети');
                } finally {
                    btn.disabled = false;
                }
            });
        });
    }

    function ensureFooterClickDelegation() {
        if (document.body.dataset.taskWorkerDelegation === '1') return;
        document.body.dataset.taskWorkerDelegation = '1';

        document.addEventListener('click', function (e) {
            const removeBtn = e.target.closest('.detail-remove-worker');
            if (removeBtn) {
                const tid = resolveTaskIdFromClick(removeBtn, window.currentTaskId);
                const userId = removeBtn.dataset.userId;
                if (!tid || !userId || removeBtn.dataset.bound === '1') return;
                e.preventDefault();
                e.stopPropagation();
                if (!confirm('Снять исполнителя с заявки?')) return;
                removeBtn.disabled = true;
                postRemoveWorker(tid, parseInt(userId, 10))
                    .then(function ({ response, data }) {
                        if (!response.ok || !data.ok) {
                            alert(data.error || 'Не удалось снять исполнителя');
                            return;
                        }
                        applyTaskPayload(data);
                        refreshTaskDetail(tid);
                    })
                    .catch(function () {
                        alert('Ошибка сети');
                    })
                    .finally(function () {
                        removeBtn.disabled = false;
                    });
                return;
            }

            const acceptBtn = e.target.closest('.task-detail-actions-worker .gruzz-video-btn');
            if (acceptBtn) {
                const tid = resolveTaskIdFromClick(acceptBtn, window.currentTaskId);
                if (!tid || acceptBtn.dataset.clickBound === '1') return;
                e.preventDefault();
                e.stopPropagation();
                handleTaskAccept(acceptBtn, tid);
                return;
            }

            const actionBtn = e.target.closest('[data-worker-action]');
            if (!actionBtn) return;
            const inFooter = actionBtn.closest(
                '#task-detail-footer, .worker-actions-footer, #detail-worker-actions, .task-detail-actions-worker'
            );
            if (!inFooter) return;
            if (actionBtn.dataset.bound === '1') return;

            const tid = resolveTaskIdFromClick(actionBtn, window.currentTaskId);
            if (!tid) return;
            e.preventDefault();
            e.stopPropagation();
            updateWorkerStatus(tid, actionBtn.dataset.workerAction, actionBtn);
        }, true);
    }

    function bindDetailPanelInteractions(taskId, root) {
        const scopes = [];
        if (root) scopes.push(root);
        const footer = taskDetailFooter();
        if (footer && scopes.indexOf(footer) === -1) scopes.push(footer);

        scopes.forEach(function (scope) {
            bindGruzzVideoBtnHover(scope);
            initAcceptTaskButton(scope, taskId);
            bindWorkerActionButtons(taskId, scope);
            bindRemoveWorkerButtons(taskId, scope);
        });
        ensureFooterClickDelegation();
    }

    window.handleTaskAccept = handleTaskAccept;
    window.updateWorkerStatus = updateWorkerStatus;
    window.bindGruzzVideoBtnHover = bindGruzzVideoBtnHover;
    window.initAcceptTaskButton = initAcceptTaskButton;
    window.bindWorkerAction = bindWorkerActionButtons;
    window.bindDetailPanelInteractions = bindDetailPanelInteractions;
    window.bindRemoveWorkerButtons = bindRemoveWorkerButtons;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', ensureFooterClickDelegation);
    } else {
        ensureFooterClickDelegation();
    }
})();
