function goBack() {
  window.location.href = "kaarten.html";
}

function openPopup(imgElement) {
  const popup = document.getElementById("popup");
  const popupImg = document.getElementById("popup-img");
  const popupDownload = document.getElementById("popup-download");

  const src = imgElement.src;
  popupImg.src = src;
  popupDownload.href = src;
  popup.style.display = "flex";
}

function closePopup() {
  document.getElementById("popup").style.display = "none";
}

function clickOutside(e) {
  const popupImg = document.getElementById("popup-img");
  if (!popupImg.contains(e.target)) {
    closePopup();
  }
}

document.addEventListener("keydown", function (e) {
  if (e.key === "Escape") {
    closePopup();
  }
});