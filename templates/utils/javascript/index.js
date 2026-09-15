document.getElementById("current-year").textContent = new Date().getFullYear();

document.addEventListener("DOMContentLoaded", function () {
    document
        .getElementById("realizarLogin")
        .addEventListener("click", function (e) {
            e.preventDefault();
            var loginModal = new bootstrap.Modal(
                document.getElementById("modalLogin")
            );
            loginModal.show();
        });

    document
        .getElementById("realizarRegisto")
        .addEventListener("click", function (e) {
            e.preventDefault();
            var registerModal = new bootstrap.Modal(
                document.getElementById("modalRegister")
            );
            registerModal.show();
        });

    document
        .querySelectorAll(".nav-link[data-target]")
        .forEach(function (item) {
            item.addEventListener("click", function (e) {
                e.preventDefault();
                var loginModal = new bootstrap.Modal(
                    document.getElementById("modalLogin")
                );
                loginModal.show();
            });
        });
});