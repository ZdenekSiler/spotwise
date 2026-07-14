// Savings view: backtested supplier ranking + negative-price capture.
(function () {
  "use strict";
  const { apiFetch, escHtml, fmtNum, isLoggedIn, promptLogin, onView } = window.Spotwise;

  async function render() {
    const card = document.getElementById("savingsCard");
    if (!isLoggedIn()) {
      card.innerHTML = `<p class="notice">Pro výpočet úspor se přihlaste.</p>
        <button class="primary" id="sLogin">Přihlásit</button>`;
      document.getElementById("sLogin").onclick = promptLogin;
      return;
    }
    card.innerHTML = `<p class="muted">Počítám…</p>`;
    let data;
    try {
      data = await apiFetch("/api/savings");
    } catch (e) {
      card.innerHTML = `<p class="notice warn">${escHtml(e.message)}</p>`;
      return;
    }
    const rows = data.ranking.map((r, i) => `
      <tr>
        <td>${i + 1}. ${escHtml(r.supplier)} ${r.sample ? '<span class="chip sample">vzorek</span>' : ""}</td>
        <td class="num">${fmtNum(r.total_czk, 0)} Kč</td>
        <td class="num">${r.vs_current_czk == null ? "—" : fmtNum(r.vs_current_czk, 0) + " Kč"}</td>
      </tr>`).join("");
    const partial = data.partial_window
      ? `<p class="notice warn">Backtest jen z dostupných dat (${fmtNum(data.window_months, 0)} měs.).</p>` : "";
    card.innerHTML = `
      ${partial}
      <table>
        <thead><tr><th>Dodavatel</th><th class="num">Roční náklad</th><th class="num">vs. stávající</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
      <p class="muted" style="margin-top:0.9rem">Potenciál z „záporných cen": <strong>${fmtNum(data.negative_capture_czk, 0)} Kč</strong></p>`;
  }

  document.addEventListener("auth-changed", () => {
    if (document.getElementById("view-savings").classList.contains("open")) render();
  });
  onView("savings", render);
})();
