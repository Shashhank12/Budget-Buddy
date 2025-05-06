function toggle_password() {  
    const passwordInput1 = document.getElementById("password");
    passwordInput1.type = passwordInput1.type === "password" ? "text" : "password";

    const passwordInput2 = document.getElementById("confirm_password");
    passwordInput2.type = passwordInput2.type === "password" ? "text" : "password";

}
