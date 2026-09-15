document.addEventListener("DOMContentLoaded", function () {
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

  document.getElementById("forgotPasswordForm").addEventListener("submit", function (e) {
    e.preventDefault();

    const recoverUsername = document.getElementById("recover-username").value;

    fetch("/recover_password", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ username: recoverUsername }),
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.message) {
          toastr.success(data.message);
          const resetPasswordModal = bootstrap.Modal.getInstance(document.getElementById("resetPasswordModal"));
          resetPasswordModal.hide();
          setTimeout(() => window.location.reload(), 1000);
        } else if (data.error) {
          toastr.error(data.error);
        }
      })
      .catch((error) => {
        console.error("Erro:", error);
        toastr.error("Houve um erro ao enviar o e-mail de recuperação.");
      });
  });
});