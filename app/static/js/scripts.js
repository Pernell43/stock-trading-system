document.addEventListener("DOMContentLoaded", function () {
    // Select the button
    let button = document.querySelector(".testButton");

    // Add event listener to redirect to /login when clicked
    if (button) {
        button.addEventListener("click", function () {
            window.location.href = "/login";
        });
    }
});
