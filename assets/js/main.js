// Het Weer Uitgelegd — gedeelde interactiviteit

document.addEventListener('DOMContentLoaded', function () {
  // FAQ / accordion toggles
  document.querySelectorAll('.faq-question').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var item = btn.closest('.faq-item');
      item.classList.toggle('open');
    });
  });

  // Mark active nav link based on current page
  var current = window.location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.main-nav a').forEach(function (link) {
    var href = link.getAttribute('href').split('/').pop();
    if (href === current) {
      link.classList.add('active');
    }
  });

  // Dictionary live search
  var search = document.getElementById('dictionary-search');
  if (search) {
    search.addEventListener('input', function () {
      var q = search.value.trim().toLowerCase();
      document.querySelectorAll('.dictionary-term').forEach(function (term) {
        var text = term.textContent.toLowerCase();
        term.style.display = text.indexOf(q) !== -1 ? '' : 'none';
      });
    });
  }

  // "Vraag het de Meteoroloog" form (front-end only — no backend yet)
  var askForm = document.getElementById('ask-form');
  if (askForm) {
    askForm.addEventListener('submit', function (e) {
      e.preventDefault();
      var msg = document.getElementById('ask-form-message');
      msg.textContent = 'Bedankt! Je vraag is genoteerd. Ons team neemt deze mee in een toekomstig kennisartikel.';
      msg.style.display = 'block';
      askForm.reset();
    });
  }
});
