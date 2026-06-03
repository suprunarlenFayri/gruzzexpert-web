(function() {
        const userTimeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;
        document.cookie = "user_timezone=" + encodeURIComponent(userTimeZone) + "; path=/; max-age=31536000; SameSite=Lax";
        console.log("🌍 Глобальная таймзона зафиксирована:", userTimeZone);
    })();