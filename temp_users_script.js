
document.addEventListener('DOMContentLoaded', function() {
    // Пытаемся найти бургер (есть только в list.html и chats/list.html)
    const burger = document.getElementById('mobile-burger-btn');
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    const body = document.body;

    // Проверяем, есть ли кнопка бургера на этой странице
    if (burger && sidebar) {
        console.log('✅ Бургер найден, инициализация');
        
        burger.addEventListener('click', function(e) {
            e.stopPropagation();
            sidebar.classList.toggle('open');
            if (overlay) overlay.classList.toggle('active');
            body.classList.toggle('no-scroll');
            console.log('Клик сработал, класс open переключен');
        });

        if (overlay) {
            overlay.addEventListener('click', function() {
                sidebar.classList.remove('open');
                overlay.classList.remove('active');
                body.classList.remove('no-scroll');
            });
        }
    } else {
        console.log('ℹ️ Бургер не найден (скорее всего, это страница чата)');
    }
});
