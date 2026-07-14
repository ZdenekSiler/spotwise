// Forecast view: day+2/+3 directional strip.
(function () {
  "use strict";
  const { apiFetch, escHtml, fmtNum, onView } = window.Spotwise;

  const LABEL = { cheap: "Levno", expensive: "Draho", neutral: "Průměr", unknown: "?" };

  async function render() {
    const strip = document.getElementById("forecastStrip");
    let data;
    try {
      data = await apiFetch("/api/forecast");
    } catch (e) {
      strip.innerHTML = `<p class="notice warn">${escHtml(e.message)}</p>`;
      return;
    }
    if (data.degraded && !data.days.length) {
      strip.innerHTML = `<p class="notice">Předpověď za horizont den-dopředu vyžaduje token ENTSO-E. Zatím zobrazujeme jen zveřejněné ceny.</p>`;
      return;
    }
    strip.innerHTML = data.days.map((d) => `
      <div class="forecast-day">
        <div class="date">${escHtml(d.target_date)}</div>
        <div><span class="chip ${escHtml(d.direction)}">${LABEL[d.direction] || d.direction}</span></div>
        <div class="muted">jistota ${fmtNum(d.confidence * 100, 0)} %</div>
      </div>`).join("");
  }

  onView("forecast", render);
})();
