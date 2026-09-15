// Change Password Modal Functionality
document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('changePasswordModal');
    const form = document.getElementById('change-password-form');

    if (!modal || !form) return;

    // Vai buscar o token CSRF à meta tag do <head>.
    // Garante que a página onde este modal aparece (ex: home.html) tem:
    // <meta name="csrf-token" content="{{ csrf_token() }}">
    const csrfMeta = document.querySelector('meta[name="csrf-token"]');
    const CSRF_TOKEN = csrfMeta ? csrfMeta.getAttribute('content') : null;

    if (!CSRF_TOKEN) {
        console.error('CSRF token não encontrado. Adiciona <meta name="csrf-token" content="{{ csrf_token() }}"> ao <head> desta página.');
    }

    const MIN_PASSWORD_LENGTH = 10;

    // Toggle password visibility
    document.querySelectorAll('.toggle-password').forEach(function(toggle) {
        toggle.addEventListener('click', function() {
            const target = this.getAttribute('data-target');
            const input = document.getElementById(target);
            const icon = this.querySelector('i');

            if (input.getAttribute('type') === 'password') {
                input.setAttribute('type', 'text');
                icon.classList.remove('fa-eye-slash');
                icon.classList.add('fa-eye');
            } else {
                input.setAttribute('type', 'password');
                icon.classList.remove('fa-eye');
                icon.classList.add('fa-eye-slash');
            }
        });
    });

    // Password strength checker
    const newPasswordInput = document.getElementById('new_password');
    if (newPasswordInput) {
        newPasswordInput.addEventListener('input', function() {
            const password = this.value;
            let strength = 0;

            if (password.length >= MIN_PASSWORD_LENGTH) strength += 25;
            if (password.match(/[a-z]+/)) strength += 25;
            if (password.match(/[A-Z]+/)) strength += 25;
            if (password.match(/[0-9]+/)) strength += 25;

            const bar = document.getElementById('password-strength-bar');
            const text = document.getElementById('password-strength-text');

            if (bar && text) {
                bar.style.width = strength + '%';

                if (strength <= 25) {
                    bar.className = 'progress-bar bg-danger';
                    text.textContent = 'Força da senha: Fraca';
                } else if (strength <= 75) {
                    bar.className = 'progress-bar bg-warning';
                    text.textContent = 'Força da senha: Média';
                } else {
                    bar.className = 'progress-bar bg-success';
                    text.textContent = 'Força da senha: Forte';
                }
            }
        });
    }

    // Form submission
    form.addEventListener('submit', function(e) {
        e.preventDefault();

        const currentPassword = document.getElementById('current_password');
        const newPassword = document.getElementById('new_password');
        const confirmPassword = document.getElementById('confirm_password');
        const errorElement = document.getElementById('password-error');

        // Reset previous errors
        errorElement.classList.add('d-none');
        [currentPassword, newPassword, confirmPassword].forEach(input => {
            input.classList.remove('is-invalid');
        });

        // Client-side validation
        if (newPassword.value.length < MIN_PASSWORD_LENGTH) {
            errorElement.classList.remove('d-none');
            errorElement.textContent = `A nova palavra-passe deve ter pelo menos ${MIN_PASSWORD_LENGTH} caracteres!`;
            newPassword.classList.add('is-invalid');
            return;
        }

        if (newPassword.value !== confirmPassword.value) {
            errorElement.classList.remove('d-none');
            errorElement.textContent = 'As palavras-passe não coincidem!';
            newPassword.classList.add('is-invalid');
            confirmPassword.classList.add('is-invalid');
            return;
        }

        if (currentPassword.value === newPassword.value) {
            errorElement.classList.remove('d-none');
            errorElement.textContent = 'A nova palavra-passe deve ser diferente da atual!';
            currentPassword.classList.add('is-invalid');
            newPassword.classList.add('is-invalid');
            return;
        }

        if (!CSRF_TOKEN) {
            errorElement.classList.remove('d-none');
            errorElement.textContent = 'Erro de segurança (CSRF token em falta). Recarrega a página.';
            return;
        }

        // Submit button loading state
        const submitBtn = document.querySelector('#changePasswordModal button[type="submit"]');
        let originalBtnText = '';
        if (submitBtn) {
            originalBtnText = submitBtn.innerHTML;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>A guardar...';
            submitBtn.disabled = true;
        }

        const jsonData = {
            current_password: currentPassword.value,
            new_password: newPassword.value
        };

        fetch('/change_password', {
            method: 'POST',
            body: JSON.stringify(jsonData),
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': CSRF_TOKEN
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                try {
                    if (typeof toastr !== 'undefined' && toastr.success) {
                        toastr.success(data.message);
                    } else {
                        alert('Sucesso: ' + data.message);
                    }
                } catch (toastrError) {
                    alert('Sucesso: ' + data.message);
                }

                // Reset form and close modal (usa 'form', não 'this')
                form.reset();
                const strengthBar = document.getElementById('password-strength-bar');
                const strengthText = document.getElementById('password-strength-text');
                strengthBar.style.width = '0%';
                strengthBar.className = 'progress-bar bg-danger';
                strengthText.textContent = 'Força da senha: Fraca';

                const modalInstance = bootstrap.Modal.getInstance(document.getElementById('changePasswordModal'));
                if (modalInstance) {
                    modalInstance.hide();
                }
            } else {
                try {
                    if (typeof toastr !== 'undefined' && toastr.error) {
                        toastr.error(data.message);
                    } else {
                        alert('Erro: ' + data.message);
                    }
                } catch (toastrError) {
                    alert('Erro: ' + data.message);
                }
            }
        })
        .catch(error => {
            try {
                if (typeof toastr !== 'undefined' && toastr.error) {
                    toastr.error('Erro ao processar a solicitação. Tente novamente mais tarde.');
                } else {
                    alert('Erro ao processar a solicitação. Tente novamente mais tarde.');
                }
            } catch (toastrError) {
                alert('Erro ao processar a solicitação. Tente novamente mais tarde.');
            }
        })
        .finally(() => {
            if (submitBtn) {
                submitBtn.innerHTML = originalBtnText;
                submitBtn.disabled = false;
            }
        });
    });

    // Reset form when modal is closed
    modal.addEventListener('hidden.bs.modal', function() {
        form.reset();

        const strengthBar = document.getElementById('password-strength-bar');
        const strengthText = document.getElementById('password-strength-text');
        strengthBar.style.width = '0%';
        strengthBar.className = 'progress-bar bg-danger';
        strengthText.textContent = 'Força da senha: Fraca';

        const errorElement = document.getElementById('password-error');
        errorElement.classList.add('d-none');

        form.querySelectorAll('.is-invalid').forEach(input => {
            input.classList.remove('is-invalid');
        });
    });
});