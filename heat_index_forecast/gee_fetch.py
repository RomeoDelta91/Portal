"""Ophalen van NOAA GFS 0.25°-forecastdata uit Google Earth Engine.

Werkwijze:
- De heat index wordt server-side per GFS-beeld berekend (heat_index_ee),
  zodat grid- en stationswaarden exact dezelfde formule gebruiken.
- Onzekerheid wordt geschat met een *lagged ensemble*: de laatste N GFS-runs
  (om de 6 uur) worden per geldigheidstijdstip gestapeld en als percentielen
  (P10/P50/P90) samengevat. GFS zelf is deterministisch; de spreiding tussen
  opeenvolgende runs is een praktische maat voor de forecast-onzekerheid.
"""

from __future__ import annotations

import datetime as dt
import logging

import numpy as np
import pandas as pd
import xarray as xr

import ee

from config import (
    BAND_RH,
    BAND_TEMP,
    EE_PRIVATE_KEY_FILE,
    EE_PROJECT,
    EE_SERVICE_ACCOUNT,
    FORECAST_HOURS,
    GFS_COLLECTION,
    GRID_SCALE_DEG,
    LAGGED_ENSEMBLE_RUNS,
    STATIONS,
    SURINAME_BBOX,
)
from heat_index import heat_index_ee

log = logging.getLogger(__name__)

GFS_NATIVE_SCALE_M = 27830  # ±0.25° op de evenaar


def init_ee() -> None:
    """Initialiseer Earth Engine.

    - Met EE_SERVICE_ACCOUNT + EE_PRIVATE_KEY_FILE in .env: service account
      (productie/cron, stap 8).
    - Anders: lokaal opgeslagen credentials van `ee.Authenticate()`.
    """
    if EE_SERVICE_ACCOUNT and EE_PRIVATE_KEY_FILE:
        creds = ee.ServiceAccountCredentials(EE_SERVICE_ACCOUNT, EE_PRIVATE_KEY_FILE)
        ee.Initialize(creds, project=EE_PROJECT)
        log.info("EE geïnitialiseerd met service account %s", EE_SERVICE_ACCOUNT)
    else:
        ee.Initialize(project=EE_PROJECT)
        log.info("EE geïnitialiseerd met lokale gebruikerscredentials (%s)", EE_PROJECT)


def bbox_geometry() -> ee.Geometry:
    return ee.Geometry.Rectangle(list(SURINAME_BBOX), proj="EPSG:4326", geodesic=False)


def latest_runs(n: int = LAGGED_ENSEMBLE_RUNS) -> list[int]:
    """Creation-times (ms sinds epoch) van de n meest recente GFS-runs."""
    times = (
        ee.ImageCollection(GFS_COLLECTION)
        .filter(ee.Filter.eq("forecast_hours", 0))
        .filterDate(
            (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=3)).isoformat(),
            (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1)).isoformat(),
        )
        .aggregate_array("creation_time")
        .distinct()
        .sort()
        .getInfo()
    )
    if not times:
        raise RuntimeError("Geen recente GFS-runs gevonden in NOAA/GFS0P25.")
    return times[-n:]


def valid_times_for_run(run_ms: int, hours: list[int] | None = None) -> list[int]:
    hours = hours or FORECAST_HOURS
    return [run_ms + h * 3_600_000 for h in hours]


def _hi_collection(runs: list[int], valid_times: list[int]) -> ee.ImageCollection:
    """GFS-beelden van de opgegeven runs op de opgegeven geldigheidstijden,
    met een extra 'heat_index'-band (°C), geknipt op Suriname."""
    bbox = bbox_geometry()
    coll = (
        ee.ImageCollection(GFS_COLLECTION)
        .filter(ee.Filter.inList("creation_time", runs))
        .filter(ee.Filter.inList("forecast_time", valid_times))
        .select([BAND_TEMP, BAND_RH])
        .map(lambda im: heat_index_ee(im, BAND_TEMP, BAND_RH).clip(bbox))
    )
    return coll


# ---------------------------------------------------------------------------
# Stationsreeksen
# ---------------------------------------------------------------------------

def station_forecast(runs: list[int], valid_times: list[int]) -> pd.DataFrame:
    """Puntwaarden op de stationslocaties voor alle runs × geldigheidstijden.

    Retourneert een DataFrame met kolommen:
    station, station_naam, run (UTC), valid_time (UTC), temp_c, rh, hi_c
    """
    points = ee.FeatureCollection(
        [
            ee.Feature(ee.Geometry.Point([s.lon, s.lat]), {"station": s.key})
            for s in STATIONS
        ]
    )
    coll = _hi_collection(runs, valid_times)

    def sample(image):
        return image.reduceRegions(
            collection=points,
            reducer=ee.Reducer.first(),
            scale=GFS_NATIVE_SCALE_M,
        ).map(
            lambda f: f.set(
                {
                    "creation_time": image.get("creation_time"),
                    "forecast_time": image.get("forecast_time"),
                }
            )
        )

    feats = coll.map(sample).flatten().getInfo()["features"]
    naam = {s.key: s.naam for s in STATIONS}
    rows = []
    for f in feats:
        p = f["properties"]
        if p.get(BAND_TEMP) is None:
            continue
        rows.append(
            {
                "station": p["station"],
                "station_naam": naam[p["station"]],
                "run": pd.Timestamp(p["creation_time"], unit="ms", tz="UTC"),
                "valid_time": pd.Timestamp(p["forecast_time"], unit="ms", tz="UTC"),
                "temp_c": p[BAND_TEMP],
                "rh": p[BAND_RH],
                "hi_c": p["heat_index"],
            }
        )
    df = pd.DataFrame(rows).sort_values(["station", "valid_time", "run"])
    if df.empty:
        raise RuntimeError("Stationsextractie leverde geen data op.")
    return df.reset_index(drop=True)


def station_ensemble_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Lagged-ensemblestatistiek per station en geldigheidstijd:
    P10/P50/P90 van de heat index plus temp/RH van de nieuwste run."""
    newest = df["run"].max()

    def agg(g: pd.DataFrame) -> pd.Series:
        newest_rows = g[g["run"] == newest]
        base = newest_rows.iloc[0] if not newest_rows.empty else g.iloc[-1]
        return pd.Series(
            {
                "hi_p10": np.percentile(g["hi_c"], 10),
                "hi_p50": np.percentile(g["hi_c"], 50),
                "hi_p90": np.percentile(g["hi_c"], 90),
                "n_runs": g["run"].nunique(),
                "temp_c": base["temp_c"],
                "rh": base["rh"],
            }
        )

    out = (
        df.groupby(["station", "station_naam", "valid_time"])
        .apply(agg, include_groups=False)
        .reset_index()
    )
    out["run"] = newest
    return out


# ---------------------------------------------------------------------------
# Grid (P50 + spread) naar xarray
# ---------------------------------------------------------------------------

def _grid_definition():
    west, south, east, north = SURINAME_BBOX
    width = int(round((east - west) / GRID_SCALE_DEG))
    height = int(round((north - south) / GRID_SCALE_DEG))
    grid = {
        "dimensions": {"width": width, "height": height},
        "affineTransform": {
            "scaleX": GRID_SCALE_DEG,
            "shearX": 0,
            "translateX": west,
            "shearY": 0,
            "scaleY": -GRID_SCALE_DEG,
            "translateY": north,
        },
        "crsCode": "EPSG:4326",
    }
    lons = west + GRID_SCALE_DEG * (np.arange(width) + 0.5)
    lats = north - GRID_SCALE_DEG * (np.arange(height) + 0.5)
    return grid, lats, lons


def grid_percentile_image(runs: list[int], valid_time: int) -> ee.Image:
    """P10/P50/P90-beeld van de heat index over de lagged ensemble voor één
    geldigheidstijdstip (bandnamen: heat_index_p10/p50/p90)."""
    coll = _hi_collection(runs, [valid_time]).select("heat_index")
    return coll.reduce(ee.Reducer.percentile([10, 50, 90])).rename(
        ["heat_index_p10", "heat_index_p50", "heat_index_p90"]
    )


def grid_forecast(runs: list[int], valid_times: list[int]) -> xr.Dataset:
    """Grid-forecast als xarray Dataset met dims (time, lat, lon) en
    variabelen hi_p50 en hi_spread (= P90 − P10), beide in °C."""
    grid, lats, lons = _grid_definition()
    p50 = np.full((len(valid_times), len(lats), len(lons)), np.nan, dtype=np.float32)
    spread = np.full_like(p50, np.nan)

    for i, vt in enumerate(valid_times):
        image = grid_percentile_image(runs, vt)
        arr = ee.data.computePixels(
            {"expression": image, "fileFormat": "NUMPY_NDARRAY", "grid": grid}
        )
        p10 = arr["heat_index_p10"].astype(np.float32)
        p90 = arr["heat_index_p90"].astype(np.float32)
        p50[i] = arr["heat_index_p50"].astype(np.float32)
        spread[i] = p90 - p10

    times = pd.to_datetime(valid_times, unit="ms", utc=True).tz_convert(None)
    ds = xr.Dataset(
        {
            "hi_p50": (("time", "lat", "lon"), p50),
            "hi_spread": (("time", "lat", "lon"), spread),
        },
        coords={"time": times, "lat": lats, "lon": lons},
    )
    return ds


# ---------------------------------------------------------------------------
# Kaarttegels voor het dashboard
# ---------------------------------------------------------------------------

def map_tile_url(image: ee.Image, band: str, vmin: float, vmax: float,
                 palette: list[str]) -> str:
    """XYZ-tile-URL (getMapId) voor gebruik in folium."""
    mapid = image.select(band).getMapId(
        {"min": vmin, "max": vmax, "palette": palette}
    )
    return mapid["tile_fetcher"].url_format
