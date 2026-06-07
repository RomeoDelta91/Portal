# Infographics

Plaats hier de 5 infographic-bestanden met exact deze namen, zodat ze automatisch
gekoppeld kunnen worden aan de placeholders op de homepage en de pagina
"Klimaat uitgelegd":

- el-nino-la-nina.png
- kelvin-waves.png
- mjo.png
- rossby-waves.png
- tropical-waves.png

Vervang vervolgens elk `<div class="infographic-placeholder" data-infographic="...">`
blok door:

```html
<img src="../assets/infographics/<bestandsnaam>" alt="<beschrijving>">
```

(gebruik `assets/infographics/...` zonder `../` op de homepage `index.html`)
