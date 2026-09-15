$(document).ready(function () {
    $(".toggle-password").click(function () {
        const target = $(this).data("target");
        const input = $("#" + target);
        const icon = $(this).find("i");

        if (input.attr("type") === "password") {
            input.attr("type", "text");
            icon.removeClass("fa-eye-slash").addClass("fa-eye");
        } else {
            input.attr("type", "password");
            icon.removeClass("fa-eye").addClass("fa-eye-slash");
        }
    });

    $("#new_password").on("input", function () {
        const password = $(this).val();
        let strength = 0;

        if (password.match(/[a-z]+/)) strength += 33;
        if (password.match(/[A-Z]+/)) strength += 33;
        if (password.match(/[0-9]+/)) strength += 34;

        const bar = $("#password-strength-bar");
        const text = $("#password-strength-text");

        bar.css("width", strength + "%");

        if (strength <= 33) {
            bar.removeClass().addClass("progress-bar bg-danger");
            text.text("Força da senha: Fraca");
        } else if (strength <= 66) {
            bar.removeClass().addClass("progress-bar bg-warning");
            text.text("Força da senha: Média");
        } else {
            bar.removeClass().addClass("progress-bar bg-success");
            text.text("Força da senha: Forte");
        }
    });

    $("#change-password-form").on("submit", function (e) {
        e.preventDefault();

        const currentPassword = $("#current_password");
        const newPassword = $("#new_password");
        const confirmPassword = $("#confirm_password");
        const errorElement = $("#password-error");

        errorElement.addClass("d-none");
        currentPassword.removeClass("is-invalid");
        newPassword.removeClass("is-invalid");
        confirmPassword.removeClass("is-invalid");

        if (newPassword.val() !== confirmPassword.val()) {
            errorElement
                .removeClass("d-none")
                .text("As palavras-passe não coincidem!");
            newPassword.addClass("is-invalid");
            confirmPassword.addClass("is-invalid");
            return;
        }

        if (currentPassword.val() === newPassword.val()) {
            errorElement
                .removeClass("d-none")
                .text("A nova palavra-passe deve ser diferente da atual!");
            currentPassword.addClass("is-invalid");
            newPassword.addClass("is-invalid");
            return;
        }

        const submitBtn = $(this).find('button[type="submit"]');
        const originalBtnText = submitBtn.html();
        submitBtn.html('<i class="fas fa-spinner fa-spin me-2"></i>A guardar...');
        submitBtn.prop("disabled", true);

        const currentPwd = currentPassword.val();
        const newPwd = newPassword.val();

        console.log("Enviando:", { current_password: currentPwd, new_password: newPwd });

        fetch("/change_password", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                current_password: currentPwd,
                new_password: newPwd,
            }),
        })
        .then(response => {
            console.log("Response status:", response.status);
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.message || `Erro ${response.status}`);
                });
            }
            return response.json();
        })
        .then(data => {
            console.log("Response data:", data);
            if (data.success) {
                Swal.fire({
                    toast: true,
                    position: "top-end",
                    icon: "success",
                    title: data.message || "Palavra-passe alterada com sucesso.",
                    showConfirmButton: false,
                    timer: 3500,
                    timerProgressBar: true,
                });

                $("#change-password-form")[0].reset();
                $("#password-strength-bar")
                    .css("width", "0%")
                    .removeClass()
                    .addClass("progress-bar bg-danger");
                $("#password-strength-text").text("Força da senha: Fraca");

                const modalEl = document.getElementById("changePasswordModal");
                const modal = bootstrap.Modal.getInstance(modalEl);
                if (modal) {
                    modal.hide();
                }
            } else {
                Swal.fire({
                    toast: true,
                    position: "top-end",
                    icon: "error",
                    title: data.message || "Não foi possível alterar a palavra-passe.",
                    showConfirmButton: false,
                    timer: 4000,
                    timerProgressBar: true,
                });
            }
        })
        .catch(error => {
            console.error("Erro:", error);
            Swal.fire({
                toast: true,
                position: "top-end",
                icon: "error",
                title: error.message || "Erro ao processar a solicitação. Tente novamente mais tarde.",
                showConfirmButton: false,
                timer: 4000,
                timerProgressBar: true,
            });
        })
        .finally(() => {
            submitBtn.html(originalBtnText);
            submitBtn.prop("disabled", false);
        });
    });

    $("#changePasswordModal").on("hidden.bs.modal", function () {
        $("#change-password-form")[0].reset();
        $("#password-strength-bar")
            .css("width", "0%")
            .removeClass()
            .addClass("progress-bar bg-danger");
        $("#password-strength-text").text("Força da senha: Fraca");
        $("#password-error").addClass("d-none");
        $(this).find(".is-invalid").removeClass("is-invalid");
    });
});