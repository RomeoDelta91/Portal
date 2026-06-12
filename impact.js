function showInfo(type) {
  const infoBlock = document.getElementById("info-block");

  if (type === "impact") {
    infoBlock.innerHTML = `
      <h2>🌍 Klimaatimpact</h2>
      <p>Er wordt nog gewerkt aan dit onderdeel. Binnenkort beschikbaar met kaarten, indicatoren en impactzones.</p>
    `;
  }

  if (type === "scenario") {
    infoBlock.innerHTML = `
      <h2>🔮 Toekomstscenario’s</h2>
      <p>Er wordt nog gewerkt aan dit onderdeel. Binnenkort beschikbaar met modellen, projecties en scenario-kaarten.</p>
    `;
  }
}