(function () {
    var STORAGE_KEY = "theme";
    var root = document.documentElement;

    function getStoredTheme() {
        try {
            return localStorage.getItem(STORAGE_KEY);
        } catch (e) {
            return null;
        }
    }

    function systemPrefersDark() {
        return window.matchMedia("(prefers-color-scheme: dark)").matches;
    }

    function applyTheme(theme) {
        root.setAttribute("data-theme", theme);
        var btn = document.getElementById("theme-toggle-btn");
        if (btn) {
            btn.setAttribute("aria-pressed", theme === "dark");
        }
    }

    var stored = getStoredTheme();
    var initial = stored || (systemPrefersDark() ? "dark" : "light");
    applyTheme(initial);

    document.addEventListener("DOMContentLoaded", function () {
        var btn = document.getElementById("theme-toggle-btn");
        if (!btn) return;
        applyTheme(root.getAttribute("data-theme"));
        btn.addEventListener("click", function () {
            var current = root.getAttribute("data-theme");
            var next = current === "dark" ? "light" : "dark";
            applyTheme(next);
            try {
                localStorage.setItem(STORAGE_KEY, next);
            } catch (e) {}
        });
    });

    window
        .matchMedia("(prefers-color-scheme: dark)")
        .addEventListener("change", function (e) {
            if (getStoredTheme()) return;
            applyTheme(e.matches ? "dark" : "light");
        });
})();
