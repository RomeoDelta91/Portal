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
| `scripts/test_gee_auth.py` | Minimale rooktest voor EE-authenticatie (stap 2) |
| `tests/test_heat_index.py` | Unit-tests tegen de officiële NOAA-tabel |

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

## Stap 8 — service account & dagelijkse runs (nog niet actief)

Pas uitvoeren nadat de kernpipeline end-to-end werkt:

1. In Google Cloud Console, project `ee-zanderij`: *IAM & Admin → Service
   Accounts → Create*, bv. `heatindex-runner@ee-zanderij.iam.gserviceaccount.com`.
2. Rol **Earth Engine Resource Viewer** (of hoger) toekennen en het account
   registreren voor Earth Engine op
   https://code.earthengine.google.com/register (zelfde Cloud-project).
3. JSON-sleutel aanmaken, opslaan **buiten** de repo, en in `.env`:
   ```
   EE_SERVICE_ACCOUNT=heatindex-runner@ee-zanderij.iam.gserviceaccount.com
   EE_PRIVATE_KEY_FILE=/pad/naar/sleutel.json
   ```
   `gee_fetch.init_ee()` gebruikt het service account dan automatisch.
4. Cron (dagelijks ~05:30 lokale tijd, na binnenkomst van de 06Z-run):
   ```
   30 5 * * * cd /pad/naar/Portal/heat_index_forecast && .venv/bin/python run_pipeline.py >> data/output/pipeline.log 2>&1
   ```

Credentials horen nooit in git: `.env`, sleutels en ruwe data staan in
`.gitignore`.
