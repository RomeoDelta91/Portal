"""Centrale configuratie voor de Heat Index forecast pipeline (MDS Suriname).

Alles wat locatie-, drempel- of projectspecifiek is staat hier, zodat de
overige modules (fetch, berekening, biascorrectie, export, dashboard) geen
hardgecodeerde waarden bevatten.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Earth Engine
# ---------------------------------------------------------------------------
EE_PROJECT = os.getenv("EE_PROJECT", "my-project-brokopondo")
EE_SERVICE_ACCOUNT = os.getenv("EE_SERVICE_ACCOUNT", "")
EE_PRIVATE_KEY_FILE = os.getenv("EE_PRIVATE_KEY_FILE", "")
# Alternatief voor CI (GitHub Actions): de JSON-sleutel als string in een
# secret, zodat er geen bestand op schijf hoeft te staan.
EE_PRIVATE_KEY_DATA = os.getenv("EE_PRIVATE_KEY_DATA", "")

GFS_COLLECTION = "NOAA/GFS0P25"
BAND_TEMP = "temperature_2m_above_ground"        # °C
BAND_RH = "relative_humidity_2m_above_ground"    # %

# Forecasthorizon: 0 t/m 120 uur (5 dagen). GFS0P25 levert 1-uurs stappen
# t/m +120 u; we bemonsteren per 3 uur om volume beheersbaar te houden.
FORECAST_HOURS = list(range(0, 121, 3))

# Aantal recente GFS-runs (om de 6 uur) voor de lagged ensemble waarmee de
# onzekerheidsband (spread) wordt geschat.
LAGGED_ENSEMBLE_RUNS = 4

# ---------------------------------------------------------------------------
# Gebied
# ---------------------------------------------------------------------------
# Suriname bounding box (west, zuid, oost, noord). Iets ruimer dan de
# oorspronkelijke 1.8°N–6.1°N / 58.1°W–53.9°W zodat het grid het volledige
# districten-shapefile dekt (dat tot 1.46°N en 58.43°W reikt).
SURINAME_BBOX = (-58.5, 1.4, -53.9, 6.1)

# Doelresolutie voor gridexport, in graden (GFS-native is 0.25°).
GRID_SCALE_DEG = 0.25

# Tijdzone Suriname (vast, geen zomertijd)
LOCAL_UTC_OFFSET_HOURS = -3
LOCAL_TZ_NAME = "America/Paramaribo"

# ---------------------------------------------------------------------------
# Stations
# ---------------------------------------------------------------------------
# LET OP / TE BEVESTIGEN: onderstaande coördinaten zijn voorlopige waarden op
# basis van publiek bekende locaties (luchthavens/plaatsen). Vervang ze door
# de exacte stationscoördinaten van de MDS zodra die zijn aangeleverd.


@dataclass(frozen=True)
class Station:
    key: str
    naam: str
    lat: float
    lon: float


STATIONS: list[Station] = [
    Station("zanderij", "Zanderij (JAP)", 5.4526, -55.1878),
    Station("zorg_en_hoop", "Zorg en Hoop", 5.8108, -55.1907),
    Station("nickerie", "Nieuw Nickerie", 5.9450, -56.9730),
    Station("afobaka", "Brokopondo / Afobaka", 4.9860, -54.9930),
    Station("paramaribo", "Paramaribo (stad)", 5.8520, -55.2038),
]

# ---------------------------------------------------------------------------
# Hitte-risicocategorieën — Suriname-geadapteerde schaal
# ---------------------------------------------------------------------------
# VOORSTEL, TE BEVESTIGEN DOOR MDS — dit zijn niet de officiële NOAA/VS-
# drempels. Omdat de basisluchtvochtigheid in Suriname structureel boven het
# Amerikaanse kalibratiebereik ligt, zijn de klassegrenzen hier voorlopig
# gekozen rond klimatologische praktijkwaarden voor de kuststrook (dagelijkse
# HI-maxima liggen het grootste deel van het jaar al in de NOAA-klasse
# "extreme caution"). Definitieve grenzen bij voorkeur afleiden als
# percentielen (bv. P75/P90/P98/P99.5) uit de eigen ERA5-Land HI-klimatologie
# 1990–2025; zie bias_correction.thresholds_from_climatology().


@dataclass(frozen=True)
class RiskCategory:
    key: str
    naam_nl: str
    beschrijving_nl: str
    hi_min_c: float          # ondergrens (inclusief), °C heat index
    kleur: str               # hex, voor kaart en grafieken


RISK_CATEGORIES: list[RiskCategory] = [
    RiskCategory(
        "normaal", "Normaal",
        "Gebruikelijke warmte voor Suriname. Geen bijzondere maatregelen nodig.",
        float("-inf"), "#3f9e6e",
    ),
    RiskCategory(
        "let_op", "Let op",
        "Warmer dan gebruikelijk. Drink voldoende water en beperk zware "
        "inspanning rond het middaguur.",
        32.0, "#d8ac18",
    ),
    RiskCategory(
        "verhoogd", "Verhoogd risico",
        "Aanhoudende hittebelasting. Risico op uitputting bij langdurige "
        "inspanning; extra aandacht voor ouderen, kinderen en buitenwerkers.",
        38.0, "#d1590f",
    ),
    RiskCategory(
        "gevaarlijk", "Gevaarlijk",
        "Grote kans op hitte-uitputting; hitteberoerte mogelijk. Vermijd "
        "inspanning overdag, zoek koelte en schaduw.",
        43.0, "#c22b36",
    ),
    RiskCategory(
        "extreem", "Extreem gevaarlijk",
        "Hitteberoerte waarschijnlijk bij blootstelling. Volg waarschuwingen "
        "van de MDS en de autoriteiten op.",
        50.0, "#8e2ba8",
    ),
]


def classify_hi(hi_c: float) -> RiskCategory:
    """Geef de risicocategorie voor een heat-indexwaarde in °C."""
    categorie = RISK_CATEGORIES[0]
    for cat in RISK_CATEGORIES:
        if hi_c >= cat.hi_min_c:
            categorie = cat
    return categorie


# ---------------------------------------------------------------------------
# Paden
# ---------------------------------------------------------------------------
PACKAGE_DIR = Path(__file__).resolve().parent
DATA_DIR = PACKAGE_DIR / "data"
OUTPUT_DIR = DATA_DIR / "output"        # NetCDF/CSV-uitvoer (git-ignored)
RAW_DIR = DATA_DIR / "raw"              # ruwe downloads (git-ignored)

ERA5_CLIMATOLOGY_FILE = os.getenv("ERA5_CLIMATOLOGY_FILE", "")

for _d in (OUTPUT_DIR, RAW_DIR):
    _d.mkdir(parents=True, exist_ok=True)
