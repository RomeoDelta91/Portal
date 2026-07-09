"""Districtsgrenzen van Suriname en een land-masker voor het forecastgrid.

Gebruikt de vooraf geconverteerde WGS84-GeoJSON
(data/geo/districten_suriname.geojson, zie scripts/convert_districts.py),
zodat er geen geopandas/pyproj/shapely nodig is op de hosting — alleen
numpy en de standaardbibliotheek.
"""

from __future__ import annotations

import json
from functools import lru_cache

import numpy as np

from config import PACKAGE_DIR

GEOJSON_PATH = PACKAGE_DIR / "data" / "geo" / "districten_suriname.geojson"


@lru_cache(maxsize=1)
def load_districts() -> dict:
    """FeatureCollection met per district 'code' en 'district' als properties."""
    return json.loads(GEOJSON_PATH.read_text())


def _iter_rings(geometry: dict):
    if geometry["type"] == "Polygon":
        yield from geometry["coordinates"]
    elif geometry["type"] == "MultiPolygon":
        for poly in geometry["coordinates"]:
            yield from poly


def _in_ring(px: np.ndarray, py: np.ndarray, ring: np.ndarray) -> np.ndarray:
    """Ray-casting punt-in-polygoon, gevectoriseerd over de punten."""
    x, y = ring[:, 0], ring[:, 1]
    inside = np.zeros(px.shape, dtype=bool)
    j = len(ring) - 1
    for i in range(len(ring)):
        crosses = (y[i] > py) != (y[j] > py)
        with np.errstate(divide="ignore", invalid="ignore"):
            x_cross = (x[j] - x[i]) * (py - y[i]) / (y[j] - y[i]) + x[i]
        inside ^= crosses & (px < x_cross)
        j = i
    return inside


def suriname_mask(lats: np.ndarray, lons: np.ndarray) -> np.ndarray:
    """Booleaans masker (lat, lon): True voor gridcellen waarvan het middel-
    punt binnen een van de districten van Suriname ligt."""
    lon_grid, lat_grid = np.meshgrid(lons, lats)
    px, py = lon_grid.ravel(), lat_grid.ravel()
    inside = np.zeros(px.shape, dtype=bool)
    for feature in load_districts()["features"]:
        for ring in _iter_rings(feature["geometry"]):
            inside |= _in_ring(px, py, np.asarray(ring, dtype=float))
    return inside.reshape(lat_grid.shape)
