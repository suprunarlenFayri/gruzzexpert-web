window.formatLocalTimeFromServer = function(value) {
            if (!value) {
                return new Date().toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
            }
            const date = new Date(value);
            if (Number.isNaN(date.getTime())) return String(value);
            return date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
        };

        (function wrapRealtimeNotifications() {
            const origShowNotification = window.showNotification;
            window.showNotification = function(title, body, timestamp) {
                let finalBody = body || '';
                if (timestamp) {
                    const localTime = window.formatLocalTimeFromServer(timestamp);
                    finalBody = finalBody ? `${finalBody} (${localTime})` : localTime;
                }
                if (typeof origShowNotification === 'function') {
                    origShowNotification(title, finalBody);
                }
            };

            const origShowToast = window.showToast;
            if (typeof origShowToast === 'function') {
                window.showToast = function(message, type, timestamp) {
                    let finalMessage = message || '';
                    if (timestamp) {
                        const localTime = window.formatLocalTimeFromServer(timestamp);
                        finalMessage = finalMessage ? `${finalMessage} · ${localTime}` : localTime;
                    }
                    origShowToast(finalMessage, type);
                };
            }
        })();

        function initSocket() {
            if (window.socket) return;
            window.socket = io({
                transports: ['websocket', 'polling'],
                reconnection: true,
                maxHttpBufferSize: 1e8
            });

            window.socket.on('connect', function() {
                console.log('✅ Socket connected');
                document.dispatchEvent(new CustomEvent('socketReady'));
            });

            window.socket.on('connect_error', function(error) {
                console.log('❌ Socket error:', error);
            });
        }

        
        window.addEventListener('load', initSocket);