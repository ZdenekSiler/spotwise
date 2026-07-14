// Dashboard: spot price chart + landed-cost tiles per supplier.
(function () {
  "use strict";
  const { apiFetch, escHtml, fmtNum, onView } = window.Spotwise;
  let chart = null;

  async function render() {
    let data;
    try {
      data = await apiFetch("/api/prices");
    } catch (e) {
      document.getElementById("chartFallback").innerHTML =
        `<p class="notice warn">Ceny se nepodařilo načíst: ${escHtml(e.message)}</p>`;
      return;
    }
    renderChart(data.series);
    renderTiles(data.tiles, data.fx_stale);
  }

  function renderChart(series) {
    const fb = document.getElementById("chartFallback");
    const labels = series.map((p) => p.ts.slice(11, 16));
    const values = series.map((p) => p.landed_czk_kwh ?? p.price_eur_mwh);

    if (!series.length) { fb.innerHTML = `<p class="muted">Pro dnešek zatím nejsou data.</p>`; return; }
    if (typeof window.Chart === "undefined") {
      // Graceful fallback when Chart.js is not vendored.
      fb.innerHTML = `<p class="muted">Graf není dostupný (chybí Chart.js). Hodnoty Kč/kWh:</p>` +
        `<p>${series.map((p) => fmtNum(p.landed_czk_kwh, 2)).join(" · ")}</p>`;
      return;
    }
    fb.innerHTML = "";
    const ctx = document.getElementById("priceChart");
    if (chart) chart.destroy();
    chart = new window.Chart(ctx, {
      type: "line",
      data: { labels, datasets: [{ label: "Kč/kWh", data: values, borderColor: "#1f6feb",
        backgroundColor: "rgba(31,111,235,0.08)", fill: true, tension: 0.3, pointRadius: 0 }] },
      options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: false } } },
    });
  }

  function renderTiles(tiles, fxStale) {
    const el = document.getElementById("supplierTiles");
    if (!tiles.length) {
      el.innerHTML = `<p class="muted">Zadejte ceny a kurz pro výpočet.</p>`;
      return;
    }
    const warn = fxStale ? `<p class="notice warn">Použit poslední známý kurz ČNB.</p>` : "";
    el.innerHTML = warn + tiles.map((t) => `
      <div class="tile">
        <div class="name">${escHtml(t.supplier)} ${t.sample ? '<span class="chip sample">vzorek</span>' : ""}</div>
        <div class="price">${fmtNum(t.avg_landed_czk_kwh)}</div>
        <div class="unit">Kč/kWh · min ${fmtNum(t.min_landed_czk_kwh)} / max ${fmtNum(t.max_landed_czk_kwh)}</div>
      </div>`).join("");
  }

  onView("dashboard", render);
})();
