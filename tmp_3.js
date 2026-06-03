// Загрузка сохранённого градиента при загрузке любой страницы
        (function() {
            const savedStart = localStorage.getItem('gradient_start');
            const savedEnd = localStorage.getItem('gradient_end');

            function hexToRgb(hex) {
                const match = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex || '');
                if (!match) return null;
                return `${parseInt(match[1], 16)}, ${parseInt(match[2], 16)}, ${parseInt(match[3], 16)}`;
            }
            
            if (savedStart && savedEnd) {
                document.documentElement.style.setProperty('--gradient-start', savedStart);
                document.documentElement.style.setProperty('--gradient-end', savedEnd);
                document.documentElement.style.setProperty('--accent', savedStart);
                document.documentElement.style.setProperty('--accent-hover', savedEnd);
                const accentRgb = hexToRgb(savedStart);
                if (accentRgb) {
                    document.documentElement.style.setProperty('--accent-rgb', accentRgb);
                }
            }
        })();