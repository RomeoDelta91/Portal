"""CF-1.8-conforme NetCDF-export van de heat-indexforecast.

Structuur volgt de MDS-conventie van de spatiale neerslagforecast-pipeline:
een centrale P50-schatting plus een spread-/onzekerheidsveld, dims
(time, lat, lon), CF-metadata op alle coördinaten en variabelen.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd
import xarray as xr

from config import OUTPUT_DIR


def export_forecast(
    ds: xr.Dataset,
    run_time: pd.Timestamp,
    bias_corrected: bool,
    outfile: str | Path | None = None,
) -> Path:
    """Schrijf de grid-forecast (hi_p50, hi_spread) als CF-1.8 NetCDF.

    Parameters
    ----------
    ds : Dataset met dims (time, lat, lon) en variabelen hi_p50, hi_spread (°C)
    run_time : initialisatietijd (UTC) van de nieuwste GFS-run
    bias_corrected : of de ERA5-Land-deltacorrectie is toegepast
    outfile : uitvoerpad; standaard OUTPUT_DIR/heat_index_forecast_<run>.nc
    """
    out = ds.copy()

    out["lat"].attrs = {
        "standard_name": "latitude",
        "long_name": "latitude",
        "units": "degrees_north",
        "axis": "Y",
    }
    out["lon"].attrs = {
        "standard_name": "longitude",
        "long_name": "longitude",
        "units": "degrees_east",
        "axis": "X",
    }
    out["time"].attrs = {"standard_name": "time", "long_name": "forecast valid time", "axis": "T"}

    # Heat index heeft geen CF standard_name; long_name + units volstaan (CF §3).
    out["hi_p50"].attrs = {
        "long_name": "NOAA heat index, lagged-ensemble median (P50)",
        "units": "degree_Celsius",
        "cell_methods": "realization: median",
        "comment": (
            "Rothfusz-regressie (NWS SR 90-23) op GFS0P25 2m-temperatuur en "
            "2m-relatieve vochtigheid; mediaan over een lagged ensemble van "
            "opeenvolgende GFS-runs."
            + (" Additieve deltacorrectie t.o.v. ERA5-Land HI-klimatologie "
               "1990-2025 toegepast." if bias_corrected else
               " GEEN biascorrectie toegepast.")
        ),
    }
    out["hi_spread"].attrs = {
        "long_name": "NOAA heat index, lagged-ensemble spread (P90 minus P10)",
        "units": "degree_Celsius",
        "cell_methods": "realization: range",
        "comment": "Onzekerheidsmaat: P90-P10 over de lagged ensemble van GFS-runs.",
    }

    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    run_str = run_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    out.attrs = {
        "Conventions": "CF-1.8",
        "title": "Heat Index forecast Suriname (GFS 0.25, bias-gecorrigeerd)"
                 if bias_corrected else
                 "Heat Index forecast Suriname (GFS 0.25, ongecorrigeerd)",
        "institution": "Meteorologische Dienst Suriname (MDS)",
        "source": "NOAA GFS 0.25 deg (NOAA/GFS0P25 via Google Earth Engine), "
                  "lagged ensemble",
        "history": f"{now}: gegenereerd door heat_index_forecast pipeline",
        "references": "Rothfusz (1990), NWS SR 90-23; "
                      "https://www.wpc.ncep.noaa.gov/html/heatindex_equation.shtml",
        "comment": "P50 = centrale schatting; hi_spread = P90-P10 onzekerheidsband.",
        "forecast_reference_time": run_str,
        "bias_corrected": str(bias_corrected).lower(),
        "geospatial_lat_min": float(out.lat.min()),
        "geospatial_lat_max": float(out.lat.max()),
        "geospatial_lon_min": float(out.lon.min()),
        "geospatial_lon_max": float(out.lon.max()),
    }

    if outfile is None:
        outfile = OUTPUT_DIR / f"heat_index_forecast_{run_time.strftime('%Y%m%d%H')}.nc"
    outfile = Path(outfile)
    outfile.parent.mkdir(parents=True, exist_ok=True)

    encoding = {
        "hi_p50": {"zlib": True, "complevel": 4, "dtype": "float32",
                   "_FillValue": -9999.0},
        "hi_spread": {"zlib": True, "complevel": 4, "dtype": "float32",
                      "_FillValue": -9999.0},
        "time": {"units": "hours since 1970-01-01 00:00:00", "dtype": "float64"},
    }
    out.to_netcdf(outfile, format="NETCDF4", encoding=encoding)
    return outfile
