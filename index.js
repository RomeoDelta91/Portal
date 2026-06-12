document.addEventListener("DOMContentLoaded", function () {
  const yearSpan = document.getElementById("year");
  if (yearSpan) {
    yearSpan.textContent = new Date().getFullYear();
  }

  const intro = document.getElementById("intro");
  if (intro) {
    intro.style.visibility = "visible";
    intro.style.animationPlayState = "running";
  }
});

// Explore-knop
function explore() {
  window.location.href = "explore.html";
}

// ------------------------------
// 🔵 POPUP FUNCTIES TOEGEVOEGD
// ------------------------------

// Popup automatisch openen bij paginalaad
window.addEventListener("load", function () {
  const popup = document.getElementById("kaartPopup");
  if (popup) {
    popup.style.display = "flex";
  }
});

// Popup sluiten
function closeKaartPopup() {
  const popup = document.getElementById("kaartPopup");
  if (popup) {
    popup.style.display = "none";
  }
}