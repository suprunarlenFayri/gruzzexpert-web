/**
 * Глобальный лайтбокс (#image-lightbox) — тот же DOM, что в чатах.
 */
(function () {
    'use strict';

    let galleryUrls = [];
    let currentIndex = 0;
    let bound = false;

    function lb() {
        return document.getElementById('image-lightbox');
    }

    function lbImg() {
        return document.getElementById('lightbox-img');
    }

    function renderThumbnails() {
        const container = document.getElementById('lightbox-thumbnails');
        if (!container) return;
        container.innerHTML = '';
        if (galleryUrls.length <= 1) return;

        galleryUrls.forEach(function (url, index) {
            const thumb = document.createElement('img');
            thumb.src = url;
            thumb.alt = '';
            thumb.style.cssText = 'width:50px;height:50px;object-fit:cover;border-radius:4px;cursor:pointer;transition:all 0.2s;opacity:0.6;';
            if (index === currentIndex) {
                thumb.style.opacity = '1';
                thumb.style.border = '2px solid #fff';
                thumb.style.transform = 'scale(1.1)';
            }
            thumb.addEventListener('click', function (e) {
                e.stopPropagation();
                switchTo(index);
            });
            container.appendChild(thumb);
        });
    }

    function switchTo(index) {
        if (!galleryUrls[index]) return;
        currentIndex = index;
        const img = lbImg();
        if (img) img.src = galleryUrls[index];
        renderThumbnails();
    }

    function bindEvents() {
        if (bound) return;
        bound = true;

        document.addEventListener('click', function (e) {
            const lightbox = lb();
            if (!lightbox || lightbox.style.display !== 'flex') return;
            if (e.target.classList.contains('close-lightbox') || e.target === lightbox) {
                window.closeImageLightbox();
            }
            if (e.target.classList.contains('left-arrow')) {
                if (galleryUrls.length > 1) {
                    switchTo((currentIndex - 1 + galleryUrls.length) % galleryUrls.length);
                }
            }
            if (e.target.classList.contains('right-arrow')) {
                if (galleryUrls.length > 1) {
                    switchTo((currentIndex + 1) % galleryUrls.length);
                }
            }
        });

        document.addEventListener('keydown', function (e) {
            const lightbox = lb();
            if (!lightbox || lightbox.style.display !== 'flex') return;
            if (e.key === 'Escape') {
                window.closeImageLightbox();
            }
            if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
                if (galleryUrls.length > 1) {
                    switchTo((currentIndex + 1) % galleryUrls.length);
                }
            }
            if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
                if (galleryUrls.length > 1) {
                    switchTo((currentIndex - 1 + galleryUrls.length) % galleryUrls.length);
                }
            }
        });
    }

    window.openImageLightbox = function (imageUrl, optionalGallery) {
        const lightbox = lb();
        const img = lbImg();
        if (!lightbox || !img || !imageUrl) return;

        bindEvents();

        const list = Array.isArray(optionalGallery)
            ? optionalGallery.filter(Boolean)
            : [];
        galleryUrls = list.length ? list : [imageUrl];
        currentIndex = Math.max(0, galleryUrls.indexOf(imageUrl));
        if (currentIndex < 0) currentIndex = 0;

        img.src = galleryUrls[currentIndex];
        lightbox.style.display = 'flex';

        const showArrows = galleryUrls.length > 1;
        const left = lightbox.querySelector('.left-arrow');
        const right = lightbox.querySelector('.right-arrow');
        if (left) left.style.display = showArrows ? 'block' : 'none';
        if (right) right.style.display = showArrows ? 'block' : 'none';

        renderThumbnails();
    };

    window.closeImageLightbox = function () {
        const lightbox = lb();
        if (lightbox) lightbox.style.display = 'none';
        const img = lbImg();
        if (img) {
            img.removeAttribute('src');
            img.src = '';
        }
        const thumbs = document.getElementById('lightbox-thumbnails');
        if (thumbs) thumbs.innerHTML = '';
        galleryUrls = [];
        currentIndex = 0;
    };

    bindEvents();
})();
