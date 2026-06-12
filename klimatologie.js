function showInfo(id) {
  const infoBlock = document.getElementById("info-block");
  let html = "";

  if (id === "palet") {
    html = `
      <h2>Tropisch Palet</h2>
      <p>Suriname kent een <strong>tropisch klimaat</strong>, gekenmerkt door hoge temperaturen, veel zonne-uren en aanzienlijke neerslag.
      Volgens de <em>Köppen-Geigerclassificatie</em> zijn er drie hoofdtypes:</p>
      <ul>
        <li><strong>Af</strong> — Tropisch regenwoudklimaat <em>(noorden, inclusief kustregio's)</em></li>
        <li><strong>Am</strong> — Tropisch moessonklimaat <em>(zuidelijke laaglanden)</em></li>
        <li><strong>Aw</strong> — Tropisch savanneklimaat <em>(berggebieden in het zuiden)</em></li>
      </ul>
    `;
  }

  if (id === "seizoenen") {
    html = `
      <h2>Seizoensindeling van Suriname</h2>
      <p>In Suriname onderscheiden we <strong>vier seizoenen</strong> op basis van neerslag en de positie van de ITCZ.</p>
      <ul>
        <li><strong>Kleine regentijd:</strong> Eerste helft december – Eerste helft februari — ITCZ boven Suriname</li>
        <li><strong>Kleine droge tijd:</strong> Eerste helft februari – Tweede helft maart — ITCZ ten zuiden</li>
        <li><strong>Grote regentijd:</strong> Tweede helft maart – Tweede helft juli — ITCZ boven Suriname</li>
        <li><strong>Grote droge tijd:</strong> Tweede helft juli – Eerste helft december — ITCZ boven Atlantische Oceaan</li>
      </ul>
      <p><em>Zelfs in droge tijden valt er gemiddeld nog 100–150 mm regen per maand.</em></p>
    `;
  }

  if (id === "temperatuur") {
    html = `
      <h2>Temperatuur in Suriname</h2>
      <ul>
        <li><strong>Minimum (ochtend):</strong> 21–24 °C</li>
        <li><strong>Maximum (middag):</strong> 31–34 °C</li>
        <li><strong>Jaarlijks gemiddelde:</strong> ± 27 °C</li>
        <li><strong>Berggebieden:</strong> 's nachts net boven de 10 °C</li>
      </ul>
    `;
  }

  if (id === "wind") {
    html = `
      <h2>Wind &amp; Weersinvloeden</h2>
      <ul>
        <li><strong>Invloedssfeer:</strong> Suriname ligt in de invloedssfeer van zowel de noordoostpassaat als de zuidoostpassaat</li>
        <li><strong>Sibibusies:</strong> sterke, lokale windstoten tijdens felle buien</li>
        <li><strong>Grootschalige invloeden:</strong> uitlopers van orkanen, El Niño en La Niña beïnvloeden neerslagpatronen</li>
      </ul>
    `;
  }

  infoBlock.innerHTML = html;
}

const modules = document.querySelectorAll(".module");
const infoBlock = document.getElementById("info-block");

modules.forEach((mod) => {
  mod.addEventListener("click", () => {
    const id = mod.getAttribute("data-info");
    modules.forEach(m => m.classList.remove("active"));
    mod.classList.add("active");
    showInfo(id);
    infoBlock.classList.add("visible");
    infoBlock.setAttribute("data-active", id);
  });

  mod.addEventListener("mouseenter", () => {
    const id = mod.getAttribute("data-info");
    showInfo(id);
    infoBlock.classList.add("visible");
    infoBlock.setAttribute("data-active", id);
  });

  mod.addEventListener("mouseleave", () => {
    const activeModule = document.querySelector(".module.active");
    if (!activeModule) {
      infoBlock.classList.remove("visible");
      infoBlock.removeAttribute("data-active");
      setTimeout(() => { infoBlock.innerHTML = ""; }, 300);
    } else {
      const id = activeModule.getAttribute("data-info");
      showInfo(id);
      infoBlock.setAttribute("data-active", id);
    }
  });
});

document.addEventListener("DOMContentLoaded", () => {
  const backBtn = document.querySelector(".back-button");
  if (backBtn) {
    const year = new Date().getFullYear();
    backBtn.textContent = `Terug naar Dashboard ${year}`;
  }
});
