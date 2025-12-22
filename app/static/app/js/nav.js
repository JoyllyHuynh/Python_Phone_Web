// navbar.js
document.addEventListener('DOMContentLoaded', function() {
    // Mobile Navigation
    const mobileToggle = document.getElementById('mobileToggle');
    const mobileNavOverlay = document.getElementById('mobileNavOverlay');
    const mobileNavDrawer = document.getElementById('mobileNavDrawer');
    const mobileNavClose = document.getElementById('mobileNavClose');

    function openMobileNav() {
        mobileToggle.classList.add('active');
        mobileNavOverlay.classList.add('active');
        mobileNavDrawer.classList.add('active');
        document.body.style.overflow = 'hidden';
    }

    function closeMobileNav() {
        mobileToggle.classList.remove('active');
        mobileNavOverlay.classList.remove('active');
        mobileNavDrawer.classList.remove('active');
        document.body.style.overflow = '';
    }

    mobileToggle?.addEventListener('click', openMobileNav);
    mobileNavClose?.addEventListener('click', closeMobileNav);
    mobileNavOverlay?.addEventListener('click', closeMobileNav);

    // Mobile Submenu Toggle
    const submenuTriggers = document.querySelectorAll('.submenu-trigger');
    submenuTriggers.forEach(trigger => {
        trigger.addEventListener('click', function(e) {
            e.preventDefault();
            const parent = this.closest('.mobile-menu-item');
            parent.classList.toggle('active');
        });
    });

    // Search Clear Button
    const searchInput = document.getElementById('searchInput');
    const searchClear = document.getElementById('searchClear');

    searchClear?.addEventListener('click', function() {
        searchInput.value = '';
        searchInput.focus();
    });

    // Mega Menu Category Hover
    const categoryItems = document.querySelectorAll('.category-item');
    const contentPanels = document.querySelectorAll('.category-content-panel');

    categoryItems.forEach(item => {
        item.addEventListener('mouseenter', function() {
            const category = this.dataset.category;

            categoryItems.forEach(i => i.classList.remove('active'));
            contentPanels.forEach(p => p.classList.remove('active'));

            this.classList.add('active');
            document.querySelector(`[data-panel="${category}"]`)?.classList.add('active');
        });
    });

    // Promo Tag Click to Fill
    const promoTags = document.querySelectorAll('.promo-tag');
    const promoInput = document.querySelector('.promo-input');

    promoTags.forEach(tag => {
        tag.addEventListener('click', function() {
            if (promoInput) {
                promoInput.value = this.dataset.code;
            }
        });
    });

    // Sticky Navbar Behavior
    let lastScroll = 0;
    const mainNavbar = document.getElementById('mainNavbar');

    window.addEventListener('scroll', function() {
        const currentScroll = window.pageYOffset;

        if (currentScroll > 100) {
            mainNavbar.classList.add('scrolled');
        } else {
            mainNavbar.classList.remove('scrolled');
        }

        // Optional: Hide on scroll down, show on scroll up
        // if (currentScroll > lastScroll && currentScroll > 200) {
        //     mainNavbar.classList.add('hidden');
        // } else {
        //     mainNavbar.classList.remove('hidden');
        // }

        lastScroll = currentScroll;
    });
});