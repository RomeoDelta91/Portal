# Heat Index verwachting Suriname — MDS

5-daagse hitte-indexverwachting voor Suriname op basis van NOAA GFS 0.25°
(via Google Earth Engine), met biascorrectie t.o.v. de eigen ERA5-Land
hittestress-klimatologie (1990–2025), CF-1.8 NetCDF-uitvoer en een
Nederlandstalig Streamlit-dashboard.

## Modules

| Bestand | Functie |
|---|---|
| `config.py` | Bounding box, stations, risicocategorieën, paden, EE-project |
| `gee_fetch.py` | GFS-data uit Earth Engine + lagged ensemble (P10/P50/P90) |
| `heat_index.py` | NOAA Rothfusz-regressie (numpy én server-side ee.Image) |
| `bias_correction.py` | Additieve delta-correctie t.o.v. ERA5-Land-klimatologie |
| `netcdf_export.py` | CF-1.8 NetCDF-export (P50 + spread) |
| `run_pipeline.py` | Orchestrator voor de volledige dagelijkse run |
| `dashboard/app.py` | Streamlit-dashboard (kaart + tijdreeksen, NL) |
| `geo.py` | Districtsgrenzen (GeoJSON) + land-masker voor het grid |
| `scripts/test_gee_auth.py` | Minimale rooktest voor EE-authenticatie (stap 2) |
| `scripts/convert_districts.py` | Eenmalige shapefile → GeoJSON-conversie |
| `tests/test_heat_index.py` | Unit-tests tegen de officiële NOAA-tabel |

De officiële districten-shapefile (UTM 21N) staat in `data/geo/`; het
dashboard gebruikt de daaruit geconverteerde WGS84-GeoJSON voor de
districtsgrenzen op de kaart en om de gridkleuring tot het landoppervlak
te beperken.

## Installatie

```bash
cd heat_index_forecast
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # en vul in (EE_PROJECT staat al goed)
```

## Stap 2 — authenticatie testen (eerst doen!)

```bash
python scripts/test_gee_auth.py
```

Bij de eerste keer opent een browservenster: log in met
`meteozanderijdata@gmail.com`. Het script bevestigt daarna toegang tot het
project `ee-zanderij` en print gemiddelde 2m-temperatuur en RH van de meest
recente GFS-analyse over de Suriname-bbox. Pas als dit werkt heeft het zin de
volledige pipeline te draaien.

## Pipeline draaien

```bash
python run_pipeline.py               # volledige run (stations + grid + NetCDF)
python run_pipeline.py --skip-grid   # sneller: alleen stationsforecast
```

Uitvoer in `data/output/` (git-ignored):
- `station_forecast_<run>.csv` + `station_forecast_latest.csv`
- `heat_index_forecast_<run>.nc` + `heat_index_forecast_latest.nc` (CF-1.8,
  variabelen `hi_p50` en `hi_spread`)

### Onzekerheidsbanden
GFS is deterministisch; de onzekerheid wordt geschat met een **lagged
ensemble**: de laatste 4 runs (24 uur aan runs, om de 6 uur) worden per
geldigheidstijdstip gestapeld en samengevat als P10/P50/P90. `hi_spread`
in de NetCDF is P90−P10.

### Biascorrectie
Additieve delta-methode: `HI_corr = HI_gfs + (ERA5clim(doy,uur) −
GFSref(uur))`, waarbij GFSref het gemiddelde van de GFS-analyses (+0 u) van
de afgelopen 30 dagen per synoptisch uur is. Zet het pad naar het
ERA5-Land-klimatologiebestand in `.env` (`ERA5_CLIMATOLOGY_FILE`). Zolang
dat bestand ontbreekt draait de pipeline **zonder** correctie en markeert de
uitvoer `bias_corrected = false` (het dashboard toont dan een waarschuwing).

## Dashboard

```bash
streamlit run dashboard/app.py
```

Toont: overzichtstegels (piek komende 24 u), kaart met risicokleuren
(grid-overlay + stations, folium), tijdreeks per station met
P10–P90-onzekerheidsband en risicobanden, uitleg van de categorieën en een
tabel met dagelijkse maxima. Alle teksten in het Nederlands.

## Tests

```bash
python -m pytest tests/ -v
```

## ⚠️ Te bevestigen door MDS

1. **Stationscoördinaten** — de waarden in `config.py` zijn voorlopig
   (publiek bekende luchthaven-/plaatslocaties). Vervang door de exacte
   MDS-coördinaten.
2. **Risicoklassegrenzen** — de Suriname-geadapteerde drempels in
   `config.py` (32/38/43/50 °C) zijn een **voorstel**, geen vastgestelde
   schaal. Aanbevolen: definitieve grenzen afleiden als percentielen uit de
   eigen ERA5-Land-klimatologie met
   `bias_correction.thresholds_from_climatology()`.
3. **Schema van het ERA5-klimatologiebestand** — de loader herkent gangbare
   namen (dims `dayofyear`/`hour`/`lat`/`lon`), maar het echte bestand is
   nog niet aangekoppeld.

## Hosten op Streamlit Community Cloud (geen lokale installatie nodig)

De opzet is zo gemaakt dat er **niets op een eigen pc hoeft te draaien**:

1. **Service account aanmaken** (eenmalig, in de browser) — zie stappen
   1–3 onder "Stap 8" hieronder.
2. **GitHub-secrets instellen**: in deze repo → *Settings → Secrets and
   variables → Actions* → twee secrets toevoegen:
   - `EE_SERVICE_ACCOUNT` — het e-mailadres van het service account
   - `EE_PRIVATE_KEY_DATA` — de volledige inhoud van de JSON-sleutel
     (openen in een teksteditor, alles kopiëren en plakken)
3. **GitHub Action** — `.github/workflows/heat_index_daily.yml` draait de
   pipeline elke ochtend (06:15 uur Surinaamse tijd) en commit
   `data/output/station_forecast_latest.csv` en
   `heat_index_forecast_latest.nc` naar de repo. Handmatig starten kan via
   *Actions → Heat index forecast (dagelijks) → Run workflow*.
4. **Streamlit Cloud koppelen**: ga naar https://share.streamlit.io, log in
   met GitHub, kies *New app* en vul in:
   - Repository: `RomeoDelta91/Portal`
   - Branch: de branch waarop dit staat
   - Main file path: `heat_index_forecast/dashboard/app.py`

   Streamlit Cloud installeert de `requirements.txt` in de repo-root en
   herstart de app automatisch bij elke commit — dus ook bij elke
   dagelijkse data-update van de Action.

Het dashboard zelf heeft géén Earth Engine-credentials nodig: het leest
alleen de door de Action gecommitte bestanden.

## Stap 8 — service account & dagelijkse runs

Nodig voor de GitHub Action hierboven:

1. In Google Cloud Console, project `ee-zanderij`: *IAM & Admin → Service
   Accounts → Create*, bv. `heatindex-runner@ee-zanderij.iam.gserviceaccount.com`.
2. Rol **Earth Engine Resource Viewer** (of hoger) toekennen en het account
   registreren voor Earth Engine op
   https://code.earthengine.google.com/register (zelfde Cloud-project).
3. JSON-sleutel aanmaken (*Keys → Add key → JSON*) en de inhoud in de
   GitHub-secrets zetten zoals hierboven beschreven. De sleutel hoort
   **nooit** in de repo zelf.
4. De dagelijkse planning loopt via de GitHub Action; een eigen server met
   cron is niet nodig. Wie tóch lokaal wil draaien zet in `.env`:
   ```
   EE_SERVICE_ACCOUNT=heatindex-runner@ee-zanderij.iam.gserviceaccount.com
   EE_PRIVATE_KEY_FILE=/pad/naar/sleutel.json
   ```
   `gee_fetch.init_ee()` pakt het service account dan automatisch op.

Credentials horen nooit in git: `.env`, sleutels en ruwe data staan in
`.gitignore`.
