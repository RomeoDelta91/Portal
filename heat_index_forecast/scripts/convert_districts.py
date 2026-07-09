"""Eenmalige conversie: DistriktenSuriname-shapefile (UTM 21N) → WGS84-GeoJSON.

Het dashboard gebruikt de GeoJSON (data/geo/districten_suriname.geojson),
zodat er op de hosting geen geopandas/pyproj nodig is. Opnieuw draaien is
alleen nodig als de shapefile verandert:

    pip install pyshp pyproj
    python scripts/convert_districts.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pyproj
import shapefile

GEO_DIR = Path(__file__).resolve().parents[1] / "data" / "geo"
SHP = GEO_DIR / "DistriktenSuriname.shp"
OUT = GEO_DIR / "districten_suriname.geojson"

# ~110 m; ruim voldoende voor een overzichtskaart en houdt het bestand klein
SIMPLIFY_TOL_DEG = 0.001


def douglas_peucker(points: list[tuple[float, float]], tol: float) -> list[tuple[float, float]]:
    if len(points) < 3:
        return points
    x1, y1 = points[0]
    x2, y2 = points[-1]
    dx, dy = x2 - x1, y2 - y1
    norm = (dx * dx + dy * dy) ** 0.5
    dmax, idx = 0.0, 0
    for i in range(1, len(points) - 1):
        px, py = points[i]
        if norm == 0:
            d = ((px - x1) ** 2 + (py - y1) ** 2) ** 0.5
        else:
            d = abs(dy * px - dx * py + x2 * y1 - y2 * x1) / norm
        if d > dmax:
            dmax, idx = d, i
    if dmax > tol:
        left = douglas_peucker(points[: idx + 1], tol)
        right = douglas_peucker(points[idx:], tol)
        return left[:-1] + right
    return [points[0], points[-1]]


def main() -> None:
    transformer = pyproj.Transformer.from_crs("EPSG:32621", "EPSG:4326", always_xy=True)
    reader = shapefile.Reader(str(SHP))
    fields = [f[0] for f in reader.fields[1:]]

    features = []
    for sr in reader.shapeRecords():
        props = dict(zip(fields, sr.record))
        shape = sr.shape
        parts = list(shape.parts) + [len(shape.points)]
        rings = []
        for i in range(len(parts) - 1):
            ring = shape.points[parts[i]: parts[i + 1]]
            lonlat = [transformer.transform(x, y) for x, y in ring]
            simplified = douglas_peucker(lonlat, SIMPLIFY_TOL_DEG)
            if len(simplified) >= 4:
                rings.append([[round(lo, 5), round(la, 5)] for lo, la in simplified])
        if not rings:
            continue
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "code": props.get("DISTR_CODE", "").strip(),
                    "district": props.get("DISTR_NM", "").strip(),
                },
                # Elke ring als aparte polygon behandelen is hier veilig genoeg:
                # het bronbestand bevat per district één buitenring (evt. eilanden).
                "geometry": {"type": "Polygon", "coordinates": rings}
                if len(rings) == 1
                else {"type": "MultiPolygon", "coordinates": [[r] for r in rings]},
            }
        )

    OUT.write_text(json.dumps({"type": "FeatureCollection", "features": features}))
    print(f"{len(features)} districten -> {OUT} ({OUT.stat().st_size/1024:.0f} kB)")


if __name__ == "__main__":
    main()
