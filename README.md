# Het Weer Uitgelegd — Meteorologisch Kennisportaal Suriname

Een statische website (HTML/CSS/JS, geen build-stap nodig) die weer en klimaat
in Suriname op een toegankelijke manier uitlegt aan het algemene publiek.

## Structuur

- `index.html` — homepage (hub naar alle onderdelen, infographic-overzicht, "Weer van de Week")
- `pages/` — inhoudspagina's:
  - `weer-uitgelegd.html` — FAQ over dagelijks weer + Mythes &amp; Feiten
  - `klimaat-uitgelegd.html` — klimaatkennis + de 5 infographics (El Niño/La Niña, Kelvin Waves, MJO, Rossby Waves, Tropical Waves)
  - `weersverschijnselen.html` — onweer, bliksem, mist, regenbogen, hitte, droogte, overstromingen
  - `veiligheid.html` — praktische veiligheidsadviezen
  - `leren.html` — lesmateriaal voor scholieren/studenten
  - `klimaatgegevens.html` — neerslag, temperatuur, grafieken, records (in te vullen met officiële cijfers)
  - `woordenboek.html` — doorzoekbaar woordenboek van meteorologische termen
  - `contact.html` — contactgegevens en "Vraag het de Meteoroloog"-formulier
- `assets/css/style.css` — gedeelde opmaak
- `assets/js/main.js` — gedeelde interactie (FAQ-accordion, woordenboek-zoekfunctie, formulier, actieve navigatie)
- `assets/infographics/` — plaats hier de 5 infographic-afbeeldingen (zie README in die map)

## Lokaal bekijken

Open `index.html` direct in een browser, of start een lokale server:

```
python3 -m http.server 8000
```

en ga naar `http://localhost:8000`.

## Contact

Telefoon: 325190 / 325206
