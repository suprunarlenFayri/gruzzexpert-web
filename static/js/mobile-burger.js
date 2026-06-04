/**
 * Мобильное бургер-меню сайдбара. Безопасно, если кнопки нет на странице.
 */
(function () {
    'use strict';

    function initMobileBurgerMenu() {
        try {
            const burger = document.getElementById('mobile-burger-btn');
            const sidebar = document.getElementById('sidebar');
            const overlay = document.getElementById('sidebarOverlay');

            if (!burger || !sidebar) {
                return;
            }

            const body = document.body;

            burger.addEventListener('click', function (e) {
                e.stopPropagation();
                sidebar.classList.toggle('open');
                if (overlay) overlay.classList.toggle('active');
                body.classList.toggle('no-scroll');
            });

            if (overlay) {
                overlay.addEventListener('click', function () {
                    sidebar.classList.remove('open');
                    overlay.classList.remove('active');
                    body.classList.remove('no-scroll');
                });
            }
        } catch (err) {
            console.warn('[mobile-burger] init skipped:', err);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initMobileBurgerMenu);
    } else {
        initMobileBurgerMenu();
    }
})();
