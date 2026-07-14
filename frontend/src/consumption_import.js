// Consumption view: CSV upload with a small client-side preview, then POST to the API.
(function () {
  "use strict";
  const { apiFetch, escHtml, isLoggedIn, promptLogin, onView } = window.Spotwise;

  function render() {
    const card = document.getElementById("consumptionCard");
    if (!isLoggedIn()) {
      card.innerHTML = `<p class="notice">Pro nahrání spotřeby se přihlaste.</p>
        <button class="primary" id="cLogin">Přihlásit</button>`;
      document.getElementById("cLogin").onclick = promptLogin;
      return;
    }
    card.innerHTML = `
      <input type="file" id="csvFile" accept=".csv,text/csv" />
      <button class="primary" id="uploadBtn">Nahrát</button>
      <div id="uploadStatus" class="muted" style="margin-top:0.8rem"></div>`;
    document.getElementById("uploadBtn").onclick = upload;
  }

  async function upload() {
    const input = document.getElementById("csvFile");
    const status = document.getElementById("uploadStatus");
    if (!input.files.length) { status.textContent = "Vyberte soubor."; return; }
    const fd = new FormData();
    fd.append("file", input.files[0]);
    status.textContent = "Nahrávám…";
    try {
      const res = await apiFetch("/api/consumption", { method: "POST", body: fd });
      status.innerHTML = `<span class="chip cheap">Hotovo</span> Importováno ${res.rows_imported} záznamů (celkem ${res.total_rows}).`;
    } catch (e) {
      status.innerHTML = `<span class="chip expensive">Chyba</span> ${escHtml(e.message)}`;
    }
  }

  document.addEventListener("auth-changed", () => {
    if (document.getElementById("view-consumption").classList.contains("open")) render();
  });
  onView("consumption", render);
})();
