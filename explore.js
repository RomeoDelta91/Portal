window.onload = function () {
  // Dynamisch jaartal en titel
  const yearHeading = document.getElementById("year-heading");
  if (yearHeading) {
    yearHeading.textContent = new Date().getFullYear();
  }
  document.title = `Explore ${new Date().getFullYear()}`;

  // Intro fade-in
  const intro = document.getElementById("intro");
  if (intro) {
    intro.style.visibility = "visible";
    intro.style.animationPlayState = "running";
  }

  // Wereld-iconen fade-in
  const worlds = document.querySelectorAll(".world");
  worlds.forEach((world, index) => {
    setTimeout(() => {
      world.style.opacity = "1";
    }, 500 + index * 200);
  });

  // Neon rain injectie met druppelvorm
  const rainContainer = document.querySelector('.neon-rain');
if (rainContainer) {
  for (let i = 0; i < 60; i++) {
    const drop = document.createElement('div');
    drop.classList.add('drop');
    drop.style.left = `${Math.random() * 100}vw`;
    drop.style.animationDuration = `${4 + Math.random() * 2}s`; // trager
    drop.style.animationDelay = `${Math.random() * 4}s`;
    rainContainer.appendChild(drop);
  }
}
};

// Navigatie naar homepage
function goHome() {
  window.location.href = "index.html";
}