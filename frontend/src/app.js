// Core app: API helper, shared utils, view switching, auth slot.
// Modules communicate via window-scope globals (apiFetch, escHtml, fmtNum, onView).
(function () {
  "use strict";

  const API = ""; // same origin; nginx proxies /api and /auth to the backend

  // ─── API + utils ───
  async function apiFetch(path, opts = {}) {
    const res = await fetch(API + path, {
      credentials: "same-origin",
      headers: opts.body && !(opts.body instanceof FormData)
        ? { "Content-Type": "application/json", ...(opts.headers || {}) }
        : opts.headers || {},
      ...opts,
    });
    if (!res.ok) {
      let detail = res.statusText;
      try { detail = (await res.json()).detail || detail; } catch (_) {}
      const err = new Error(detail);
      err.status = res.status;
      throw err;
    }
    return res.status === 204 ? null : res.json();
  }

  function escHtml(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
  }

  function fmtNum(n, digits = 2) {
    if (n == null || Number.isNaN(n)) return "—";
    return Number(n).toLocaleString("cs-CZ", {
      minimumFractionDigits: digits, maximumFractionDigits: digits,
    });
  }

  // ─── View switching ───
  const viewHandlers = {};
  function onView(name, fn) { viewHandlers[name] = fn; }

  function showView(name) {
    document.querySelectorAll(".view").forEach((v) => v.classList.remove("open"));
    document.getElementById("view-" + name).classList.add("open");
    document.querySelectorAll("nav.tabs button").forEach((b) =>
      b.classList.toggle("active", b.dataset.view === name));
    if (viewHandlers[name]) viewHandlers[name]();
  }

  document.querySelectorAll("nav.tabs button").forEach((b) =>
    b.addEventListener("click", () => showView(b.dataset.view)));

  // ─── Auth slot ───
  let currentUser = null;
  async function refreshAuth() {
    const slot = document.getElementById("authSlot");
    try {
      currentUser = await apiFetch("/auth/me");
      slot.innerHTML =
        `<span class="muted">${escHtml(currentUser.email)}</span>` +
        `<button class="ghost" id="logoutBtn">Odhlásit</button>`;
      document.getElementById("logoutBtn").onclick = async () => {
        await apiFetch("/auth/logout", { method: "POST" });
        currentUser = null;
        refreshAuth();
      };
    } catch (_) {
      currentUser = null;
      slot.innerHTML = `<button class="primary" id="loginBtn">Přihlásit / Registrovat</button>`;
      document.getElementById("loginBtn").onclick = promptLogin;
    }
    document.dispatchEvent(new CustomEvent("auth-changed"));
  }

  async function promptLogin() {
    const email = prompt("E-mail:");
    if (!email) return;
    const password = prompt("Heslo (min. 8 znaků):");
    if (!password) return;
    const body = JSON.stringify({ email, password });
    try {
      await apiFetch("/auth/login", { method: "POST", body });
    } catch (_) {
      try { await apiFetch("/auth/signup", { method: "POST", body }); }
      catch (e) { alert("Přihlášení selhalo: " + e.message); return; }
    }
    refreshAuth();
  }

  // Expose to other modules.
  window.Spotwise = { apiFetch, escHtml, fmtNum, onView, isLoggedIn: () => !!currentUser, promptLogin };

  // Defer initial render until every view module (loaded after this script) has registered its
  // onView handler — otherwise showView("dashboard") runs before dashboard.js exists.
  document.addEventListener("DOMContentLoaded", () => {
    refreshAuth();
    showView("dashboard");
  });
})();
