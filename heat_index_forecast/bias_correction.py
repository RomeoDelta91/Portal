"""Biascorrectie van de GFS heat-indexforecast met de ERA5-Land-klimatologie.

Methode (additieve delta/anomalie-correctie):

    HI_gecorrigeerd(t, x) = HI_gfs(t, x) + delta(uur, x)
    delta(uur, x)         = HI_era5_clim(doy, uur, x) − HI_gfs_ref(uur, x)

waarbij HI_gfs_ref de gemiddelde GFS-analyse (forecast hour 0) van de
afgelopen N dagen is, per synoptisch uur (00/06/12/18 UTC). De correctie
verschuift dus het GFS-niveau naar het ERA5-Land-klimaatniveau per uur van
de dag, terwijl het forecastsignaal (de anomalie t.o.v. het recente
GFS-niveau) behouden blijft. Dit is bewust een niveau-correctie en geen
kwantielmapping: robuust, uitlegbaar en geschikt voor operationeel gebruik
op 25 km-resolutie in een vochtig-tropische omgeving.

BELANGRIJK: het ERA5-Land-klimatologiebestand wordt door de MDS aangeleverd
(bestaande hittestress-klimatologie 1990–2025). `load_era5_climatology`
accepteert daarom meerdere gangbare variabele-/dimensienamen; als het
bestand ontbreekt draait de pipeline door ZONDER correctie, met een
duidelijke waarschuwing en `bias_corrected = False` in de metadata.
"""

from __future__ import annotations

import datetime as dt
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from config import ERA5_CLIMATOLOGY_FILE, STATIONS

log = logging.getLogger(__name__)

# Kandidaat-namen voor de HI-variabele en dimensies in het klimatologiebestand
_HI_VAR_CANDIDATES = ["heat_index", "hi", "HI", "heat_index_c", "heatindex"]
_DOY_CANDIDATES = ["dayofyear", "doy", "day_of_year"]
_HOUR_CANDIDATES = ["hour", "hour_utc", "hod"]


class ClimatologyUnavailable(Exception):
    """Het ERA5-Land-klimatologiebestand is niet beschikbaar of onleesbaar."""


def load_era5_climatology(path: str | Path | None = None) -> xr.DataArray:
    """Laad de ERA5-Land HI-klimatologie als DataArray.

    Verwachte structuur: dims (dayofyear, hour, lat, lon) — afwijkende maar
    gangbare namen worden herkend en hernoemd. Eenheid: °C.
    """
    raw = str(path or ERA5_CLIMATOLOGY_FILE or "").strip()
    path = Path(raw) if raw else None
    if path is None or not path.is_file():
        raise ClimatologyUnavailable(
            "ERA5-klimatologiebestand niet gevonden"
            + (f": '{path}'" if path else " (ERA5_CLIMATOLOGY_FILE is leeg)")
            + ". Zet ERA5_CLIMATOLOGY_FILE in .env zodra het bestand beschikbaar is."
        )

    ds = xr.open_dataset(path)
    var = next((v for v in _HI_VAR_CANDIDATES if v in ds), None)
    if var is None:
        raise ClimatologyUnavailable(
            f"Geen heat-indexvariabele gevonden in {path.name}; "
            f"verwacht één van {_HI_VAR_CANDIDATES}, gevonden: {list(ds.data_vars)}"
        )
    da = ds[var]

    rename = {}
    for cands, target in [
        (_DOY_CANDIDATES, "dayofyear"),
        (_HOUR_CANDIDATES, "hour"),
        (["latitude"], "lat"),
        (["longitude"], "lon"),
    ]:
        found = next((d for d in cands if d in da.dims), None)
        if found and found != target:
            rename[found] = target
    if rename:
        da = da.rename(rename)

    missing = {"dayofyear", "lat", "lon"} - set(da.dims)
    if missing:
        raise ClimatologyUnavailable(
            f"Klimatologie mist dimensie(s) {missing}; gevonden dims: {da.dims}"
        )
    return da


def gfs_reference_by_hour(days_back: int = 30) -> xr.DataArray:
    """Gemiddelde GFS-analyse-HI (forecast hour 0) per synoptisch uur
    (00/06/12/18 UTC) over de afgelopen `days_back` dagen, op het
    Suriname-grid. Dims: (hour, lat, lon)."""
    import ee

    from config import BAND_RH, BAND_TEMP, GFS_COLLECTION
    from gee_fetch import _grid_definition, bbox_geometry
    from heat_index import heat_index_ee

    grid, lats, lons = _grid_definition()
    bbox = bbox_geometry()
    end = dt.datetime.now(dt.timezone.utc)
    start = end - dt.timedelta(days=days_back)

    base = (
        ee.ImageCollection(GFS_COLLECTION)
        .filter(ee.Filter.eq("forecast_hours", 0))
        .filterDate(start.isoformat(), end.isoformat())
        .select([BAND_TEMP, BAND_RH])
        .map(lambda im: heat_index_ee(im, BAND_TEMP, BAND_RH).clip(bbox))
        .select("heat_index")
    )

    hours = [0, 6, 12, 18]
    out = np.full((len(hours), len(lats), len(lons)), np.nan, dtype=np.float32)
    for i, h in enumerate(hours):
        mean_img = base.filter(
            ee.Filter.calendarRange(h, h, "hour")
        ).mean().rename("heat_index")
        arr = ee.data.computePixels(
            {"expression": mean_img, "fileFormat": "NUMPY_NDARRAY", "grid": grid}
        )
        out[i] = arr["heat_index"].astype(np.float32)

    return xr.DataArray(
        out,
        dims=("hour", "lat", "lon"),
        coords={"hour": hours, "lat": lats, "lon": lons},
        name="gfs_ref_hi",
    )


def delta_field(era5_clim: xr.DataArray, gfs_ref: xr.DataArray,
                doy: int) -> xr.DataArray:
    """Correctieveld delta(uur, lat, lon) voor de opgegeven dag van het jaar.

    De ERA5-klimatologie wordt naar het GFS-grid geïnterpoleerd; als de
    klimatologie geen uur-dimensie heeft wordt één delta voor alle uren
    gebruikt.
    """
    clim_doy = era5_clim.sel(dayofyear=doy, method="nearest")
    clim_on_grid = clim_doy.interp(lat=gfs_ref.lat, lon=gfs_ref.lon)

    if "hour" in clim_on_grid.dims:
        clim_h = clim_on_grid.interp(hour=gfs_ref.hour, method="nearest")
    else:
        clim_h = clim_on_grid.expand_dims(hour=gfs_ref.hour)

    delta = (clim_h - gfs_ref).rename("hi_delta")
    return delta


def apply_to_grid(ds: xr.Dataset, delta: xr.DataArray) -> xr.Dataset:
    """Pas de delta additief toe op hi_p50 in de grid-forecast.

    De spread (P90−P10) blijft ongewijzigd: een niveau-verschuiving verandert
    de onzekerheidsbreedte niet.
    """
    hours = xr.DataArray(
        pd.to_datetime(ds.time.values).hour, dims="time", name="hour"
    )
    d = delta.sel(hour=(hours % 24) // 6 * 6)  # dichtstbijzijnd synoptisch uur
    out = ds.copy()
    out["hi_p50"] = ds["hi_p50"] + d.transpose("time", "lat", "lon").values
    out.attrs["bias_corrected"] = "true"
    return out


def apply_to_stations(df: pd.DataFrame, delta: xr.DataArray) -> pd.DataFrame:
    """Pas de delta toe op de stationsreeksen (kolommen hi_p10/p50/p90)."""
    out = df.copy()
    coords = {s.key: (s.lat, s.lon) for s in STATIONS}
    for key, (lat, lon) in coords.items():
        mask = out["station"] == key
        if not mask.any():
            continue
        hours = out.loc[mask, "valid_time"].dt.hour.values % 24 // 6 * 6
        d_pt = delta.interp(lat=lat, lon=lon)
        d_vals = d_pt.sel(hour=xr.DataArray(hours, dims="p")).values
        for col in ("hi_p10", "hi_p50", "hi_p90"):
            out.loc[mask, col] = out.loc[mask, col] + d_vals
    out.attrs = {"bias_corrected": True}
    return out


def thresholds_from_climatology(era5_clim: xr.DataArray,
                                percentiles=(75, 90, 98, 99.5)) -> dict[float, float]:
    """Hulpfunctie voor het VASTSTELLEN van Suriname-specifieke klassegrenzen:
    landsgemiddelde HI-percentielen uit de eigen klimatologie. Bedoeld om de
    voorlopige grenzen in config.RISK_CATEGORIES te onderbouwen/vervangen —
    de uitkomst wordt bewust niet automatisch toegepast."""
    vals = era5_clim.values
    vals = vals[np.isfinite(vals)]
    return {p: float(np.percentile(vals, p)) for p in percentiles}
