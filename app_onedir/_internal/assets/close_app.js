// Shutdown the server if the user exits
window.addEventListener("beforeunload", function () {
    navigator.sendBeacon('/shutdown');
});