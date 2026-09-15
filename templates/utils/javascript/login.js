document.getElementById("current-year").textContent = new Date().getFullYear();

document.addEventListener("DOMContentLoaded", function () {
    let loginUrl = "";

    const navLinks = document.querySelectorAll('[id="loginToggle"]');

    navLinks.forEach((link) => {
        link.addEventListener("click", function () {
            loginUrl = link.getAttribute("data-url");
            updateModalForLoginType(loginUrl);
        });
    });

    function updateModalForLoginType(url) {
        const modalTitle = document.getElementById("loginModalLabel");
        const forgotPasswordGroup = document.getElementById("forgotPasswordGroup");
        const windowsLoginSection = document.getElementById("windowsLoginSection");
        const windowsLoginButton = document.getElementById("windowsLoginButton");
        const usernameInput = document.getElementById("username");
        const usernameLabel = document.querySelector('label[for="username"]');

        switch (url) {
            case "/login_employee":
                modalTitle.innerHTML = '<i class="fas fa-user me-2"></i>Login - Funcionário';
                usernameLabel.textContent = "Username ou Email";
                usernameInput.placeholder = "Introduza o seu username ou email";
                forgotPasswordGroup.style.display = 'block';
                windowsLoginSection.style.display = 'block';
                windowsLoginButton.style.display = 'block';
                break;
            case "/login_manager":
                modalTitle.innerHTML = '<i class="fas fa-user-tie me-2"></i>Login - Gestor';
                usernameLabel.textContent = "Username ou Email";
                usernameInput.placeholder = "Introduza o seu username ou email";
                forgotPasswordGroup.style.display = 'block';
                windowsLoginSection.style.display = 'block';
                windowsLoginButton.style.display = 'block';
                break;
            case "/login_hr":
                modalTitle.innerHTML = '<i class="fas fa-users me-2"></i>Login - Recursos Humanos';
                usernameLabel.textContent = "Username ou Email";
                usernameInput.placeholder = "Introduza o seu username ou email";
                forgotPasswordGroup.style.display = 'block';
                windowsLoginSection.style.display = 'block';
                windowsLoginButton.style.display = 'block';
                break;
            case "/login_admin":
                modalTitle.innerHTML = '<i class="fas fa-cogs me-2"></i>Login - Administrador';
                usernameLabel.textContent = "Email Administrador";
                usernameInput.placeholder = "Introduza o email de administrador";
                forgotPasswordGroup.style.display = 'none';
                windowsLoginSection.style.display = 'none';
                windowsLoginButton.style.display = 'none';
                break;
            default:
                modalTitle.innerHTML = '<i class="fas fa-sign-in-alt me-2"></i>Login';
                usernameLabel.textContent = "Nome de utilizador";
                usernameInput.placeholder = "Introduza o seu nome de utilizador";
                forgotPasswordGroup.style.display = 'block';
                windowsLoginSection.style.display = 'block';
                windowsLoginButton.style.display = 'block';
        }

        clearLoginError();
        document.getElementById('loginForm').reset();
    }

    function clearLoginError() {
        const loginError = document.getElementById('login-error');
        loginError.classList.add('d-none');
    }

    function showLoginError(message) {
        if (typeof toastr !== 'undefined') {
            toastr.error(message, 'Erro de Login');
        } else {
            const loginError = document.getElementById('login-error');
            const loginErrorMessage = document.getElementById('login-error-message');
            loginErrorMessage.textContent = message;
            loginError.classList.remove('d-none');
        }
    }

    // Prevenir submissão nativa do formulário
    document.getElementById("loginForm").addEventListener("submit", function (e) {
        e.preventDefault();
    });

    document.getElementById("loginButton").addEventListener("click", function (e) {
        e.preventDefault();
        const form = document.getElementById("loginForm");
        const formData = new FormData(form);

        if (!loginUrl) {
            showLoginError("Tipo de login não definido");
            return;
        }

        fetch(loginUrl, {
            method: "POST",
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
            .then((response) => response.json())
            .then((data) => {
                if (data.success) {
                    if (data.status === false) {
                        const loginModal = bootstrap.Modal.getInstance(document.getElementById('modalLogin'));
                        loginModal.hide();

                        setTimeout(function () {
                            const firstLoginModal = new bootstrap.Modal(document.getElementById('modalFirstLogin'), {
                                backdrop: 'static',
                                keyboard: false
                            });
                            firstLoginModal.show();
                        }, 500);
                    } else {
                        const loginModal = bootstrap.Modal.getInstance(document.getElementById('modalLogin'));
                        if (loginModal) {
                            loginModal.hide();
                        }
                        
                        if (typeof toastr !== 'undefined') {
                            toastr.success('Login realizado com sucesso!', 'Sucesso');
                        }
                        
                        setTimeout(function() {
                            redirectAfterLogin(loginUrl, data);
                        }, 1000);
                    }
                } else {
                    if (data.error === 'Acesso não autorizado') {
                        showLoginError("Acesso não autorizado. Verifique as suas permissões.");
                    } else if (data.error === 'Credenciais inválidas') {
                        showLoginError("Credenciais inválidas. Verifique os seus dados.");
                    } else {
                        showLoginError(data.error || data.message || "Erro ao fazer login");
                    }
                }
            })
            .catch((error) => {
                console.error("Erro:", error);
                showLoginError("Erro de conexão");
            });
    });

    document.getElementById("windowsLoginBtn").addEventListener("click", function () {
        if (!loginUrl) {
            showLoginError("Tipo de login não definido");
            return;
        }

        const button = this;
        const originalText = button.innerHTML;
        button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Autenticando...';
        button.disabled = true;

        fetch('/windows_login?login_type=' + encodeURIComponent(loginUrl), {
            method: "GET",
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
            .then((response) => response.json())
            .then((data) => {
                if (data.success) {
                    const loginModal = bootstrap.Modal.getInstance(document.getElementById('modalLogin'));
                    loginModal.hide();

                    setTimeout(function () {
                        if (data.redirect_url) {
                            window.location.href = data.redirect_url;
                        } else {
                            redirectAfterLogin(loginUrl, data);
                        }
                    }, 1000);
                } else {
                    showLoginError(data.message || "Erro na autenticação Windows");
                }
            })
            .catch((error) => {
                console.error("Erro:", error);
                showLoginError("Erro ao conectar com o servidor");
            })
            .finally(() => {
                button.innerHTML = originalText;
                button.disabled = false;
            });
    });

    // Prevenir submissão nativa do formulário de primeiro login
    document.getElementById('firstLoginForm').addEventListener('submit', function (e) {
        e.preventDefault();
    });

    document.getElementById('firstLoginSubmitBtn').addEventListener('click', function (e) {
        e.preventDefault();

        const newPassword = document.getElementById('new_password').value;
        const confirmPassword = document.getElementById('confirm_password').value;
        const errorElement = document.getElementById('password-error');
        const errorMessage = document.getElementById('password-error-message');

        if (!newPassword || newPassword.length < 4) {
            const message = "A palavra-passe deve ter pelo menos 4 caracteres!";
            if (typeof toastr !== 'undefined') {
                toastr.error(message, 'Erro');
            } else {
                errorMessage.textContent = message;
                errorElement.classList.remove('d-none');
            }
            return;
        }

        if (newPassword !== confirmPassword) {
            const message = "As palavras-passe não coincidem!";
            if (typeof toastr !== 'undefined') {
                toastr.error(message, 'Erro');
            } else {
                errorMessage.textContent = message;
                errorElement.classList.remove('d-none');
            }
            return;
        }

        errorElement.classList.add('d-none');

        const formElement = document.getElementById('firstLoginForm');
        fetch('/change_first_password', {
            method: 'POST',
            body: new FormData(formElement),
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const firstLoginModal = bootstrap.Modal.getInstance(document.getElementById('modalFirstLogin'));
                    firstLoginModal.hide();
                    
                    if (typeof toastr !== 'undefined') {
                        toastr.success('Palavra-passe alterada com sucesso!', 'Sucesso');
                    }

                    setTimeout(function () {
                        redirectAfterLogin(loginUrl, data);
                    }, 1000);
                } else {
                    const message = data.error || data.message || "Erro ao alterar a palavra-passe";
                    if (typeof toastr !== 'undefined') {
                        toastr.error(message, 'Erro');
                    } else {
                        errorMessage.textContent = message;
                        errorElement.classList.remove('d-none');
                    }
                }
            })
            .catch(error => {
                console.error('Erro:', error);
                const message = "Erro ao alterar a palavra-passe. Tente novamente.";
                if (typeof toastr !== 'undefined') {
                    toastr.error(message, 'Erro');
                } else {
                    errorMessage.textContent = message;
                    errorElement.classList.remove('d-none');
                }
            });
    });

    function redirectAfterLogin(url, data = null) {
        if (data && data.redirect_url) {
            window.location.href = data.redirect_url;
            return;
        }

        switch (url) {
            case "/login_employee":
                window.location.href = "/dashboard";
                break;
            case "/login_manager":
                window.location.href = "/manager/dashboard";
                break;
            case "/login_hr":
                window.location.href = "/hr/dashboard";
                break;
            case "/login_admin":
                window.location.href = "/settings";
                break;
            default:
                window.location.href = "/";
        }
    }

    document.getElementById("backToLogin").addEventListener("click", function (e) {
        e.preventDefault();
        const registerModal = bootstrap.Modal.getInstance(document.getElementById("modalRegister"));
        if (registerModal) {
            registerModal.hide();
        }
        setTimeout(function () {
            const loginModal = new bootstrap.Modal(document.getElementById("modalLogin"));
            loginModal.show();
        }, 500);
    });

    document.getElementById("forgotPasswordLink").addEventListener("click", function (e) {
        e.preventDefault();
        const loginModal = bootstrap.Modal.getInstance(document.getElementById("modalLogin"));
        if (loginModal) {
            loginModal.hide();
        }
        setTimeout(function () {
            const resetPasswordModal = new bootstrap.Modal(document.getElementById("resetPasswordModal"));
            resetPasswordModal.show();
        }, 500);
    });
});