document.addEventListener("DOMContentLoaded", function () {
    const sidebar = document.getElementById("sidebar");
    const topbar = document.getElementById("topbar");
    const content = document.getElementById("content");
    const footer = document.querySelector(".sticky-footer");
    const sidebarToggle = document.getElementById("sidebarToggle");
    const sidebarToggleTop = document.getElementById("sidebarToggleTop");
    const navLinks = document.querySelectorAll(".sidebar .nav-link");
    const collapseItems = document.querySelectorAll(
        ".sidebar .collapse-item"
    );
    const title = document.querySelector(".topbar .title");

    const currentYear = document.getElementById("currentYear");
    if (currentYear) {
        currentYear.textContent = new Date().getFullYear();
    }

    function toggleSidebar() {
        if (!sidebar || !topbar || !content || !footer) return;
        sidebar.classList.toggle("toggled");
        topbar.classList.toggle("toggled");
        content.classList.toggle("toggled");
        footer.classList.toggle("toggled");
    }

    if (sidebarToggle) sidebarToggle.addEventListener("click", toggleSidebar);
    if (sidebarToggleTop) sidebarToggleTop.addEventListener("click", toggleSidebar);

    document.addEventListener("click", function (e) {
        if (window.innerWidth <= 768) {
            if (
                !e.target.closest("#sidebar, #sidebarToggleTop") &&
                sidebar && sidebar.classList.contains("toggled")
            ) {
                toggleSidebar();
                document
                    .querySelectorAll(".sidebar .collapse")
                    .forEach((collapse) => {
                        collapse.classList.remove("show");
                        collapse.previousElementSibling.classList.add("collapsed");
                    });
            }
        }
    });

    collapseItems.forEach((item) => {
        item.addEventListener("click", function (e) {
            e.preventDefault();
            navLinks.forEach((link) => {
                link.classList.remove("active");
                link.classList.add("collapsed");
            });
            const parentNavLink =
                this.closest(".nav-item").querySelector(".nav-link");
            parentNavLink.classList.add("active");
            parentNavLink.classList.remove("collapsed");
            title.textContent = this.textContent.trim();
            if (window.innerWidth <= 768) {
                this.closest(".collapse").classList.remove("show");
            }
        });
    });

    const currentUrl = window.location.pathname + window.location.search;
    navLinks.forEach((link) => {
        const href = link.getAttribute("href");
        link.classList.remove("active");
        if (href === currentUrl) {
            link.classList.remove("collapsed");
            link.classList.add("active");
        }
    });

    const activeItem = document.querySelector(".sidebar a.active span");
    if (activeItem) {
        title.textContent = activeItem.textContent;
    }

    navLinks.forEach((link) => {
        if (!link.hasAttribute("data-bs-toggle")) {
            link.addEventListener("click", function (e) {
                navLinks.forEach((l) => {
                    l.classList.remove("active");
                    l.classList.add("collapsed");
                });
                this.classList.add("active");
                this.classList.remove("collapsed");
                title.textContent = this.querySelector("span").textContent;
            });
        }
    });

    document.querySelectorAll(".collapse").forEach((collapse) => {
        collapse.addEventListener("show.bs.collapse", function () {
            localStorage.setItem("collapse_" + this.id, "true");
        });
        collapse.addEventListener("hide.bs.collapse", function () {
            localStorage.setItem("collapse_" + this.id, "false");
        });
        if (localStorage.getItem("collapse_" + this.id) === "true") {
            collapse.classList.add("show");
            collapse.previousElementSibling.classList.remove("collapsed");
        }
    });

    window.addEventListener("resize", function () {
        if (window.innerWidth > 768) {
            if (sidebar) sidebar.classList.remove("toggled");
            if (topbar) topbar.classList.remove("toggled");
            if (content) content.classList.remove("toggled");
            if (footer) footer.classList.remove("toggled");
        }
    });
});