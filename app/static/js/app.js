/* ==========================================================================
   app.js — the ENTIRE client-side footprint of the app.

   Deliberately tiny and framework-free. It handles five things:
     1. Dark mode toggle (persisted to localStorage)
     2. Mobile sidebar open/close
     3. Modal close (clears the #modal container)
     4. Toast notifications (driven by HTMX `HX-Trigger: {"toast": ...}`)
     5. Copy-to-clipboard buttons ([data-copy="#selector"])
   ...plus registering the service worker for PWA support.

   Everything dynamic on the server side is done with HTMX attributes in the
   templates — there's no app logic here beyond glue.
   ========================================================================== */
(function () {
  "use strict";

  const root = document.documentElement;

  /* --- 1. Dark mode ------------------------------------------------------ */
  function toggleTheme() {
    const isDark = root.classList.toggle("dark");
    try {
      localStorage.setItem("theme", isDark ? "dark" : "light");
    } catch (e) {}
  }

  /* --- 2. Mobile sidebar ------------------------------------------------- */
  function setSidebar(open) {
    const sidebar = document.getElementById("sidebar");
    const backdrop = document.getElementById("sidebar-backdrop");
    if (!sidebar) return;
    sidebar.classList.toggle("-translate-x-full", !open);
    if (backdrop) backdrop.classList.toggle("hidden", !open);
  }

  /* --- 3. Modal ---------------------------------------------------------- */
  function closeModal() {
    const modal = document.getElementById("modal");
    if (modal) modal.innerHTML = "";
  }

  /* --- 4. Toasts (HX-Trigger -> custom "toast" event) -------------------- */
  function showToast(detail) {
    const region = document.getElementById("toast-region");
    if (!region) return;
    const { message = "", category = "info" } = detail || {};

    const colors = {
      success: "border-success/40 bg-success/15 text-success",
      danger: "border-danger/40 bg-danger/15 text-danger",
      info: "border-border bg-surface text-content",
    };

    const toast = document.createElement("div");
    toast.className =
      "pointer-events-auto w-full max-w-sm rounded-lg border px-4 py-3 text-sm shadow-lg " +
      "transition-all duration-300 translate-y-2 opacity-0 " +
      (colors[category] || colors.info);
    toast.setAttribute("role", "status");
    toast.textContent = message;
    region.appendChild(toast);

    // Animate in, then auto-dismiss.
    requestAnimationFrame(() => toast.classList.remove("translate-y-2", "opacity-0"));
    setTimeout(() => {
      toast.classList.add("opacity-0");
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  }

  /* --- 5. Copy to clipboard --------------------------------------------- */
  // <button data-copy="#script-body" data-copied="Copied!">Copy</button>
  // Copies the value/textContent of the element matched by data-copy.
  function copyFrom(trigger) {
    const sel = trigger.getAttribute("data-copy");
    const source = sel ? document.querySelector(sel) : null;
    if (!source) return;
    const text = "value" in source ? source.value : source.textContent;
    const done = () =>
      showToast({ message: trigger.getAttribute("data-copied") || "Copied to clipboard.", category: "success" });
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done).catch(function () {});
    }
  }

  /* --- Event wiring (delegated, so it survives HTMX swaps) --------------- */
  document.addEventListener("click", function (e) {
    if (e.target.closest("[data-theme-toggle]")) {
      e.preventDefault();
      toggleTheme();
    } else if (e.target.closest("[data-copy]")) {
      copyFrom(e.target.closest("[data-copy]"));
    } else if (e.target.closest("[data-sidebar-open]")) {
      setSidebar(true);
    } else if (e.target.closest("[data-sidebar-close]")) {
      setSidebar(false);
    } else if (e.target.closest("[data-modal-close]")) {
      closeModal();
    }
  });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      closeModal();
      setSidebar(false);
    }
  });

  // HTMX dispatches a "toast" event on <body> when the server sends
  // `HX-Trigger: {"toast": {"message": "...", "category": "..."}}`.
  document.body.addEventListener("toast", function (e) {
    showToast(e.detail);
  });

  /* --- Service worker (PWA) ---------------------------------------------- */
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker
        .register("/service-worker.js", { scope: "/" })
        .catch(function (err) {
          console.warn("Service worker registration failed:", err);
        });
    });
  }
})();
