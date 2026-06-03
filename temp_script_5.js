// Global variables
        let dropdownOpen = false;
        
        // Sidebar functions
        function toggleSidebar() {
            const sidebar = document.getElementById('sidebar');
            const overlay = document.getElementById('sidebarOverlay');
            if (sidebar) {
                sidebar.classList.toggle('open');
                if (overlay) overlay.classList.toggle('active');
            }
        }
        
        function closeSidebar() {
            const sidebar = document.getElementById('sidebar');
            const overlay = document.getElementById('sidebarOverlay');
            if (sidebar) sidebar.classList.remove('open');
            if (overlay) overlay.classList.remove('active');
        }
        
        function filterSidebarChats() {
            const search = document.getElementById('chat-list-search');
            if (!search) return;
            if (typeof window.ChatListUI !== 'undefined') {
                window.ChatListUI.filterChatList(search.value);
            }
        }
        
        function goToChat(chatId) {
            if (chatId) {
                if (typeof window.clearChatUnreadBadge === 'function') {
                    window.clearChatUnreadBadge(chatId);
                }
                window.location.href = '/chat/' + chatId;
            }
        }
        
        function toggleDropdown(event) {
            event?.stopPropagation();
            const menu = document.getElementById('dropdownMenu');
            if (menu) {
                const isShow = menu.classList.contains('show');
                // Close all dropdowns first
                document.querySelectorAll('.dropdown-menu.show').forEach(m => m.classList.remove('show'));
                if (!isShow) {
                    menu.classList.add('show');
                    dropdownOpen = true;
                } else {
                    dropdownOpen = false;
                }
            }
        }
        
        // Close dropdown when clicking outside
        document.addEventListener('click', function(e) {
            const menu = document.getElementById('dropdownMenu');
            const userMenu = document.querySelector('.user-menu');
            if (menu && userMenu && !userMenu.contains(e.target) && menu.classList.contains('show')) {
                menu.classList.remove('show');
                dropdownOpen = false;
            }
            
            // Close sidebar on mobile when clicking outside
            if (window.innerWidth <= 768) {
                const sidebar = document.getElementById('sidebar');
                const overlay = document.getElementById('sidebarOverlay');
                if (sidebar?.classList.contains('open') && overlay && !sidebar.contains(e.target) && !overlay.contains(e.target)) {
                    closeSidebar();
                }
            }
        });
        
        // Theme toggle with ripple effect
        function toggleTheme() {
            const isLight = document.body.classList.contains('light');
            const ripple = document.createElement('div');
            ripple.classList.add('theme-ripple');
            ripple.style.backgroundColor = isLight ? '#0e1621' : '#ffffff';
            ripple.style.left = '50%';
            ripple.style.top = '50%';
            document.body.appendChild(ripple);
            
            requestAnimationFrame(() => {
                ripple.classList.add('ripple-animate');
            });
            
            setTimeout(() => {
                if (isLight) {
                    document.body.classList.remove('light');
                    localStorage.setItem('theme', 'dark');
                    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', '#0e1621');
                } else {
                    document.body.classList.add('light');
                    localStorage.setItem('theme', 'light');
                    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', '#ffffff');
                }
                if (typeof lucide !== 'undefined') lucide.createIcons();
            }, 400);
            
            setTimeout(() => {
                ripple.remove();
            }, 800);
        }
        
        // Load saved theme
        if (localStorage.getItem('theme') === 'light') {
            document.body.classList.add('light');
            document.querySelector('meta[name="theme-color"]')?.setAttribute('content', '#ffffff');
        } else {
            document.querySelector('meta[name="theme-color"]')?.setAttribute('content', '#0e1621');
        }
        
        // Auto-resize textarea
        function autoResizeTextarea(textarea) {
            if (typeof window.autoResizeTextarea === 'function' && window.autoResizeTextarea !== autoResizeTextarea) {
                window.autoResizeTextarea(textarea);
                return;
            }
            if (!textarea) return;
            textarea.style.height = 'auto';
            textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px';
        }
        
        // Initialize all textareas with auto-resize
        function initAutoResize() {
            document.querySelectorAll('textarea').forEach(textarea => {
                if (!textarea.hasAttribute('data-autoresize-init')) {
                    textarea.setAttribute('data-autoresize-init', 'true');
                    textarea.addEventListener('input', function() {
                        autoResizeTextarea(this);
                    });
                    autoResizeTextarea(textarea);
                }
            });
        }
        
        // Send message with Enter (Shift+Enter for new line)
        function setupMessageInput(textareaId, sendButtonId) {
            const textarea = document.getElementById(textareaId);
            const sendBtn = document.getElementById(sendButtonId);
            
            if (textarea) {
                textarea.addEventListener('keydown', function(e) {
                    if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        if (sendBtn && !sendBtn.disabled) {
                            sendBtn.click();
                        }
                    }
                });
            }
        }
        
        // Smooth scroll to bottom of messages
        function scrollToBottom(containerId) {
            const container = document.getElementById(containerId);
            if (container) {
                container.scrollTop = container.scrollHeight;
            }
        }
        
        // Initialize Lucide icons when DOM is ready
        function initIcons() {
            if (typeof window.refreshGruzzIcons === 'function') {
                window.refreshGruzzIcons();
            }
            if (typeof lucide !== 'undefined') {
                lucide.createIcons();
            } else {
                setTimeout(initIcons, 100);
            }
        }
        
        // Mobile back button handler (if needed)
        function initMobileBack() {
            const backBtn = document.querySelector('.mobile-back-btn');
            if (backBtn) {
                backBtn.addEventListener('click', () => {
                    if (window.innerWidth <= 768) {
                        // Logic for mobile back
                        history.back();
                    }
                });
            }
        }
        
        // Expose functions to global scope
        window.filterSidebarChats = filterSidebarChats;
        window.toggleSidebar = toggleSidebar;
        window.closeSidebar = closeSidebar;
        window.autoResizeTextarea = autoResizeTextarea;
        window.toggleTheme = toggleTheme;
        window.goToChat = goToChat;
        window.scrollToBottom = scrollToBottom;
        window.setupMessageInput = setupMessageInput;
        
        // Initialize on DOMContentLoaded
        document.addEventListener('DOMContentLoaded', function() {
            initIcons();
            initAutoResize();
            initMobileBack();
            
            // Close dropdown on escape key
            document.addEventListener('keydown', function(e) {
                if (e.key === 'Escape') {
                    const menu = document.getElementById('dropdownMenu');
                    if (menu?.classList.contains('show')) {
                        menu.classList.remove('show');
                    }
                    closeSidebar();
                }
            });
        });
        
        // Re-initialize icons after dynamic content updates (call this function after AJAX)
        window.refreshIcons = function() {
            if (typeof window.refreshGruzzIcons === 'function') {
                window.refreshGruzzIcons();
            }
            if (typeof lucide !== 'undefined') {
                lucide.createIcons();
            }
        };