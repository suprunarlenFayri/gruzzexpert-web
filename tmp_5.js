(function() {
    'use strict';

    var ADMIN_CITIES_DATA = [{"id": 1, "name": "\u041c\u043e\u0441\u043a\u0432\u0430"}, {"id": 2, "name": "\u0421\u0430\u043d\u043a\u0442-\u041f\u0435\u0442\u0435\u0440\u0431\u0443\u0440\u0433"}, {"id": 3, "name": "\u0421\u0435\u0432\u0430\u0441\u0442\u043e\u043f\u043e\u043b\u044c"}, {"id": 4, "name": "\u0411\u0435\u043b\u0433\u043e\u0440\u043e\u0434"}, {"id": 5, "name": "\u0411\u0440\u044f\u043d\u0441\u043a"}, {"id": 6, "name": "\u0412\u043b\u0430\u0434\u0438\u043c\u0438\u0440"}, {"id": 7, "name": "\u0412\u043e\u0440\u043e\u043d\u0435\u0436"}, {"id": 8, "name": "\u0418\u0432\u0430\u043d\u043e\u0432\u043e"}, {"id": 9, "name": "\u041a\u0430\u043b\u0443\u0433\u0430"}, {"id": 10, "name": "\u041a\u043e\u0441\u0442\u0440\u043e\u043c\u0430"}, {"id": 11, "name": "\u041a\u0443\u0440\u0441\u043a"}, {"id": 12, "name": "\u041b\u0438\u043f\u0435\u0446\u043a"}, {"id": 13, "name": "\u041e\u0440\u0451\u043b"}, {"id": 14, "name": "\u0420\u044f\u0437\u0430\u043d\u044c"}, {"id": 15, "name": "\u0421\u043c\u043e\u043b\u0435\u043d\u0441\u043a"}, {"id": 16, "name": "\u0422\u0430\u043c\u0431\u043e\u0432"}, {"id": 17, "name": "\u0422\u0432\u0435\u0440\u044c"}, {"id": 18, "name": "\u0422\u0443\u043b\u0430"}, {"id": 19, "name": "\u042f\u0440\u043e\u0441\u043b\u0430\u0432\u043b\u044c"}, {"id": 20, "name": "\u0410\u0440\u0445\u0430\u043d\u0433\u0435\u043b\u044c\u0441\u043a"}, {"id": 21, "name": "\u0412\u043e\u043b\u043e\u0433\u0434\u0430"}, {"id": 22, "name": "\u041a\u0430\u043b\u0438\u043d\u0438\u043d\u0433\u0440\u0430\u0434"}, {"id": 23, "name": "\u041f\u0435\u0442\u0440\u043e\u0437\u0430\u0432\u043e\u0434\u0441\u043a"}, {"id": 24, "name": "\u0421\u044b\u043a\u0442\u044b\u0432\u043a\u0430\u0440"}, {"id": 25, "name": "\u0412\u0435\u043b\u0438\u043a\u0438\u0439 \u041d\u043e\u0432\u0433\u043e\u0440\u043e\u0434"}, {"id": 26, "name": "\u041f\u0441\u043a\u043e\u0432"}, {"id": 27, "name": "\u041c\u0443\u0440\u043c\u0430\u043d\u0441\u043a"}, {"id": 28, "name": "\u0421\u0435\u0432\u0435\u0440\u043e\u0434\u0432\u0438\u043d\u0441\u043a"}, {"id": 29, "name": "\u0427\u0435\u0440\u0435\u043f\u043e\u0432\u0435\u0446"}, {"id": 30, "name": "\u0410\u0441\u0442\u0440\u0430\u0445\u0430\u043d\u044c"}, {"id": 31, "name": "\u0412\u043e\u043b\u0433\u043e\u0433\u0440\u0430\u0434"}, {"id": 32, "name": "\u041a\u0440\u0430\u0441\u043d\u043e\u0434\u0430\u0440"}, {"id": 33, "name": "\u0420\u043e\u0441\u0442\u043e\u0432-\u043d\u0430-\u0414\u043e\u043d\u0443"}, {"id": 34, "name": "\u042d\u043b\u0438\u0441\u0442\u0430"}, {"id": 35, "name": "\u041c\u0430\u0439\u043a\u043e\u043f"}, {"id": 36, "name": "\u041d\u0430\u043b\u044c\u0447\u0438\u043a"}, {"id": 37, "name": "\u0412\u043b\u0430\u0434\u0438\u043a\u0430\u0432\u043a\u0430\u0437"}, {"id": 38, "name": "\u0413\u0440\u043e\u0437\u043d\u044b\u0439"}, {"id": 39, "name": "\u041c\u0430\u0445\u0430\u0447\u043a\u0430\u043b\u0430"}, {"id": 40, "name": "\u041d\u0430\u0437\u0440\u0430\u043d\u044c"}, {"id": 41, "name": "\u0427\u0435\u0440\u043a\u0435\u0441\u0441\u043a"}, {"id": 42, "name": "\u0421\u0442\u0430\u0432\u0440\u043e\u043f\u043e\u043b\u044c"}, {"id": 43, "name": "\u0421\u043e\u0447\u0438"}, {"id": 44, "name": "\u041d\u043e\u0432\u043e\u0440\u043e\u0441\u0441\u0438\u0439\u0441\u043a"}, {"id": 45, "name": "\u0422\u0430\u0433\u0430\u043d\u0440\u043e\u0433"}, {"id": 46, "name": "\u0428\u0430\u0445\u0442\u044b"}, {"id": 47, "name": "\u0412\u043e\u043b\u0436\u0441\u043a\u0438\u0439"}, {"id": 48, "name": "\u0411\u0430\u0442\u0430\u0439\u0441\u043a"}, {"id": 49, "name": "\u0423\u0444\u0430"}, {"id": 50, "name": "\u041a\u0438\u0440\u043e\u0432"}, {"id": 51, "name": "\u0419\u043e\u0448\u043a\u0430\u0440-\u041e\u043b\u0430"}, {"id": 52, "name": "\u0421\u0430\u0440\u0430\u043d\u0441\u043a"}, {"id": 53, "name": "\u041d\u0438\u0436\u043d\u0438\u0439 \u041d\u043e\u0432\u0433\u043e\u0440\u043e\u0434"}, {"id": 54, "name": "\u041e\u0440\u0435\u043d\u0431\u0443\u0440\u0433"}, {"id": 55, "name": "\u041f\u0435\u043d\u0437\u0430"}, {"id": 56, "name": "\u041f\u0435\u0440\u043c\u044c"}, {"id": 57, "name": "\u0421\u0430\u043c\u0430\u0440\u0430"}, {"id": 58, "name": "\u0421\u0430\u0440\u0430\u0442\u043e\u0432"}, {"id": 59, "name": "\u041a\u0430\u0437\u0430\u043d\u044c"}, {"id": 60, "name": "\u0418\u0436\u0435\u0432\u0441\u043a"}, {"id": 61, "name": "\u0423\u043b\u044c\u044f\u043d\u043e\u0432\u0441\u043a"}, {"id": 62, "name": "\u0427\u0435\u0431\u043e\u043a\u0441\u0430\u0440\u044b"}, {"id": 63, "name": "\u0422\u043e\u043b\u044c\u044f\u0442\u0442\u0438"}, {"id": 64, "name": "\u041d\u0430\u0431\u0435\u0440\u0435\u0436\u043d\u044b\u0435 \u0427\u0435\u043b\u043d\u044b"}, {"id": 65, "name": "\u0421\u044b\u0437\u0440\u0430\u043d\u044c"}, {"id": 66, "name": "\u042d\u043d\u0433\u0435\u043b\u044c\u0441"}, {"id": 67, "name": "\u0414\u0437\u0435\u0440\u0436\u0438\u043d\u0441\u043a"}, {"id": 68, "name": "\u041e\u0440\u0441\u043a"}, {"id": 69, "name": "\u0421\u0442\u0435\u0440\u043b\u0438\u0442\u0430\u043c\u0430\u043a"}, {"id": 70, "name": "\u041a\u0443\u0440\u0433\u0430\u043d"}, {"id": 71, "name": "\u0415\u043a\u0430\u0442\u0435\u0440\u0438\u043d\u0431\u0443\u0440\u0433"}, {"id": 72, "name": "\u0422\u044e\u043c\u0435\u043d\u044c"}, {"id": 73, "name": "\u0425\u0430\u043d\u0442\u044b-\u041c\u0430\u043d\u0441\u0438\u0439\u0441\u043a"}, {"id": 74, "name": "\u0427\u0435\u043b\u044f\u0431\u0438\u043d\u0441\u043a"}, {"id": 75, "name": "\u041c\u0430\u0433\u043d\u0438\u0442\u043e\u0433\u043e\u0440\u0441\u043a"}, {"id": 76, "name": "\u041d\u0438\u0436\u043d\u0438\u0439 \u0422\u0430\u0433\u0438\u043b"}, {"id": 77, "name": "\u041a\u0430\u043c\u0435\u043d\u0441\u043a-\u0423\u0440\u0430\u043b\u044c\u0441\u043a\u0438\u0439"}, {"id": 78, "name": "\u0417\u043b\u0430\u0442\u043e\u0443\u0441\u0442"}, {"id": 79, "name": "\u041c\u0438\u0430\u0441\u0441"}, {"id": 80, "name": "\u041a\u043e\u043f\u0435\u0439\u0441\u043a"}, {"id": 81, "name": "\u0421\u0443\u0440\u0433\u0443\u0442"}, {"id": 82, "name": "\u041d\u0438\u0436\u043d\u0435\u0432\u0430\u0440\u0442\u043e\u0432\u0441\u043a"}, {"id": 83, "name": "\u041d\u0435\u0444\u0442\u0435\u044e\u0433\u0430\u043d\u0441\u043a"}, {"id": 84, "name": "\u041d\u043e\u0432\u044b\u0439 \u0423\u0440\u0435\u043d\u0433\u043e\u0439"}, {"id": 85, "name": "\u041d\u043e\u044f\u0431\u0440\u044c\u0441\u043a"}, {"id": 86, "name": "\u0413\u043e\u0440\u043d\u043e-\u0410\u043b\u0442\u0430\u0439\u0441\u043a"}, {"id": 87, "name": "\u0411\u0430\u0440\u043d\u0430\u0443\u043b"}, {"id": 88, "name": "\u0423\u043b\u0430\u043d-\u0423\u0434\u044d"}, {"id": 89, "name": "\u0427\u0438\u0442\u0430"}, {"id": 90, "name": "\u0418\u0440\u043a\u0443\u0442\u0441\u043a"}, {"id": 91, "name": "\u041a\u0435\u043c\u0435\u0440\u043e\u0432\u043e"}, {"id": 92, "name": "\u041d\u043e\u0432\u043e\u043a\u0443\u0437\u043d\u0435\u0446\u043a"}, {"id": 93, "name": "\u041a\u0440\u0430\u0441\u043d\u043e\u044f\u0440\u0441\u043a"}, {"id": 94, "name": "\u041d\u043e\u0432\u043e\u0441\u0438\u0431\u0438\u0440\u0441\u043a"}, {"id": 95, "name": "\u041e\u043c\u0441\u043a"}, {"id": 96, "name": "\u0422\u043e\u043c\u0441\u043a"}, {"id": 97, "name": "\u041a\u044b\u0437\u044b\u043b"}, {"id": 98, "name": "\u0410\u0431\u0430\u043a\u0430\u043d"}, {"id": 99, "name": "\u041f\u0440\u043e\u043a\u043e\u043f\u044c\u0435\u0432\u0441\u043a"}, {"id": 100, "name": "\u0411\u0438\u0439\u0441\u043a"}, {"id": 101, "name": "\u0410\u043d\u0433\u0430\u0440\u0441\u043a"}, {"id": 102, "name": "\u0411\u0440\u0430\u0442\u0441\u043a"}, {"id": 103, "name": "\u041d\u043e\u0440\u0438\u043b\u044c\u0441\u043a"}, {"id": 104, "name": "\u041a\u0430\u043d\u0441\u043a"}, {"id": 105, "name": "\u0411\u0435\u0440\u0434\u0441\u043a"}, {"id": 106, "name": "\u0418\u0441\u043a\u0438\u0442\u0438\u043c"}, {"id": 107, "name": "\u041b\u0435\u043d\u0438\u043d\u0441\u043a-\u041a\u0443\u0437\u043d\u0435\u0446\u043a\u0438\u0439"}, {"id": 108, "name": "\u041c\u0435\u0436\u0434\u0443\u0440\u0435\u0447\u0435\u043d\u0441\u043a"}, {"id": 109, "name": "\u041a\u0438\u0441\u0435\u043b\u0451\u0432\u0441\u043a"}, {"id": 110, "name": "\u042e\u0440\u0433\u0430"}, {"id": 111, "name": "\u0410\u0447\u0438\u043d\u0441\u043a"}, {"id": 112, "name": "\u0420\u0443\u0431\u0446\u043e\u0432\u0441\u043a"}, {"id": 113, "name": "\u0411\u0438\u0440\u043e\u0431\u0438\u0434\u0436\u0430\u043d"}, {"id": 114, "name": "\u0411\u043b\u0430\u0433\u043e\u0432\u0435\u0449\u0435\u043d\u0441\u043a"}, {"id": 115, "name": "\u0412\u043b\u0430\u0434\u0438\u0432\u043e\u0441\u0442\u043e\u043a"}, {"id": 116, "name": "\u041c\u0430\u0433\u0430\u0434\u0430\u043d"}, {"id": 117, "name": "\u0425\u0430\u0431\u0430\u0440\u043e\u0432\u0441\u043a"}, {"id": 118, "name": "\u042e\u0436\u043d\u043e-\u0421\u0430\u0445\u0430\u043b\u0438\u043d\u0441\u043a"}, {"id": 119, "name": "\u041f\u0435\u0442\u0440\u043e\u043f\u0430\u0432\u043b\u043e\u0432\u0441\u043a-\u041a\u0430\u043c\u0447\u0430\u0442\u0441\u043a\u0438\u0439"}, {"id": 120, "name": "\u042f\u043a\u0443\u0442\u0441\u043a"}, {"id": 121, "name": "\u0423\u0441\u0441\u0443\u0440\u0438\u0439\u0441\u043a"}, {"id": 122, "name": "\u041d\u0430\u0445\u043e\u0434\u043a\u0430"}, {"id": 123, "name": "\u041a\u043e\u043c\u0441\u043e\u043c\u043e\u043b\u044c\u0441\u043a-\u043d\u0430-\u0410\u043c\u0443\u0440\u0435"}, {"id": 124, "name": "\u0410\u0440\u0442\u0451\u043c"}, {"id": 125, "name": "\u0410\u0440\u0441\u0435\u043d\u044c\u0435\u0432"}, {"id": 126, "name": "\u0421\u0432\u043e\u0431\u043e\u0434\u043d\u044b\u0439"}, {"id": 127, "name": "\u0414\u0430\u043b\u044c\u043d\u0435\u0433\u043e\u0440\u0441\u043a"}, {"id": 128, "name": "\u0411\u043e\u043b\u044c\u0448\u043e\u0439 \u041a\u0430\u043c\u0435\u043d\u044c"}];

    var tomSelectInstance = null;
    var currentUserId = null;

    function toggleBranch(element) {
        var branch = element.closest('.hierarchy-branch');
        if (branch) {
            branch.classList.toggle('active');
        }
    }

    function toggleRoleRatingField() {
        var select = document.getElementById('roleSelect');
        var group = document.getElementById('roleRatingGroup');
        if (!select || !group) return;
        var show = select.value === 'worker' || select.value === 'brigadir';
        group.style.display = show ? 'flex' : 'none';
    }

    function openRoleModal(userId, userName, currentRole, currentRating) {
        var modal = document.getElementById('roleModal');
        var form = document.getElementById('roleForm');
        var title = document.getElementById('roleModalUserName');
        var select = document.getElementById('roleSelect');
        var ratingInput = document.getElementById('roleRating');

        if (title) title.textContent = 'Роль: ' + userName;
        if (form) form.action = '/admin/user/' + userId + '/assign-role';
        if (select && currentRole) select.value = currentRole;
        if (ratingInput) {
            ratingInput.value = currentRating != null ? Number(currentRating).toFixed(1) : '';
        }
        toggleRoleRatingField();
        if (modal) modal.classList.add('active');
        document.body.style.overflow = 'hidden';
        if (typeof refreshIcons === 'function') refreshIcons();
    }

    function closeRoleModal() {
        var modal = document.getElementById('roleModal');
        if (modal) modal.classList.remove('active');
        document.body.style.overflow = '';
    }

    function openLocationsModal(userId, userName) {
        if (typeof TomSelect === 'undefined') {
            setTimeout(function() { openLocationsModal(userId, userName); }, 200);
            return;
        }

        currentUserId = userId;
        var modal = document.getElementById('locationsModal');
        var userNameSpan = document.getElementById('modalUserName');

        if (userNameSpan) userNameSpan.textContent = 'Города для ' + userName;
        if (modal) {
            modal.classList.add('active');
            document.body.style.overflow = 'hidden';
        }

        if (tomSelectInstance) {
            tomSelectInstance.destroy();
            tomSelectInstance = null;
        }

        fetch('/admin/user/' + userId + '/locations')
            .then(function(r) { return r.json(); })
            .then(function(data) {
                var select = document.getElementById('citySelect');
                if (!select) return;

                select.innerHTML = '';
                ADMIN_CITIES_DATA.forEach(function(city) {
                    var cityOpt = document.createElement('option');
                    cityOpt.value = city.id;
                    cityOpt.textContent = city.name;
                    select.appendChild(cityOpt);
                });

                tomSelectInstance = new TomSelect(select, {
                    maxItems: null,
                    placeholder: 'Выберите города...',
                    create: false,
                    sortField: { field: 'text', direction: 'asc' },
                    plugins: ['remove_button'],
                    dropdownParent: 'body'
                });

                if (data.locations && data.locations.length > 0) {
                    tomSelectInstance.setValue(data.locations.map(String));
                }
            })
            .catch(function(error) {
                console.error('Ошибка загрузки городов:', error);
            });
    }

    function closeModal() {
        var modal = document.getElementById('locationsModal');
        if (modal) modal.classList.remove('active');
        document.body.style.overflow = '';
        currentUserId = null;
        if (tomSelectInstance) {
            tomSelectInstance.destroy();
            tomSelectInstance = null;
        }
    }

    function showToast(message, type) {
        type = type || 'info';
        var toastContainer = document.getElementById('toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.style.cssText = 'position:fixed;bottom:20px;left:50%;transform:translateX(-50%);z-index:99999;display:flex;flex-direction:column;gap:10px;pointer-events:none;';
            document.body.appendChild(toastContainer);
        }

        var toast = document.createElement('div');
        var bgColor = type === 'error' ? 'var(--danger)' : 'var(--success)';
        toast.style.cssText = 'background:' + bgColor + ';color:#fff;padding:10px 20px;border-radius:8px;font-size:13px;font-weight:500;box-shadow:0 8px 24px rgba(0,0,0,0.25);pointer-events:auto;';
        toast.textContent = message;
        toastContainer.appendChild(toast);

        setTimeout(function() {
            toast.remove();
        }, 2000);
    }

    function saveUserLocations() {
        if (!tomSelectInstance || !currentUserId) return;

        var selected = tomSelectInstance.getValue();

        fetch('/admin/user/' + currentUserId + '/update-locations', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ locations: selected.map(Number) })
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.status === 'success') {
                showToast('Города сохранены', 'success');
                closeModal();
                window.location.reload();
            } else {
                showToast(data.message || 'Ошибка', 'error');
            }
        })
        .catch(function() {
            showToast('Ошибка при сохранении', 'error');
        });
    }

    window.toggleBranch = toggleBranch;
    window.openRoleModal = openRoleModal;
    window.closeRoleModal = closeRoleModal;
    window.openLocationsModal = openLocationsModal;
    window.closeModal = closeModal;
    window.saveUserLocations = saveUserLocations;
    window.toggleRoleRatingField = toggleRoleRatingField;

    document.addEventListener('DOMContentLoaded', function() {
        var searchInput = document.getElementById('adminSearch');
        if (searchInput) {
            searchInput.addEventListener('input', function(e) {
                var searchTerm = e.target.value.toLowerCase().trim();
                document.querySelectorAll('.user-card').forEach(function(row) {
                    var searchData = (row.dataset.search || '').toLowerCase();
                    var matches = searchTerm === '' || searchData.indexOf(searchTerm) !== -1;
                    row.style.display = matches ? '' : 'none';
                    if (matches && searchTerm !== '') {
                        var branch = row.closest('.hierarchy-branch');
                        if (branch) branch.classList.add('active');
                    }
                });
            });
        }

        if (typeof refreshIcons === 'function') refreshIcons();
    });
})();