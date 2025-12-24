
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('registerForm');
    const passInput = document.getElementById('id_password1');
    const errorSpan = document.querySelector('.error-msg');

    form.addEventListener('submit', function(e) {
        const password = passInput.value;
        let errorMessage = "";

        if (password.length < 8) {
            errorMessage = "Mật khẩu phải có ít nhất 8 ký tự!";
        }
        //chu hoa
        else if (!/[A-Z]/.test(password)) {
            errorMessage = "Mật khẩu phải chứa ít nhất 1 chữ cái in hoa!";
        }
        // so
        else if (!/\d/.test(password)) {
            errorMessage = "Mật khẩu phải chứa ít nhất 1 chữ số!";
        }
        // ky tu dac biet
        else if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
            errorMessage = "Mật khẩu phải chứa ít nhất 1 ký tự đặc biệt!";
        }


        if (errorMessage) {
            e.preventDefault();
            alert(errorMessage);
            passInput.focus();
        }
    });
});