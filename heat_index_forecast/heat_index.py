"""NOAA Rothfusz heat-indexberekening.

Zelfde methodiek als de ERA5-Land hittestress-klimatologie 1990–2025 van de
MDS: de Rothfusz-regressie (NWS SR 90-23) inclusief de officiële NWS-
correcties voor lage en hoge relatieve vochtigheid, met de eenvoudige
Steadman-benadering voor koele omstandigheden.

Referentie: https://www.wpc.ncep.noaa.gov/html/heatindex_equation.shtml

De functies zijn volledig gevectoriseerd (numpy) en werken in °C / %.
Er is ook een Earth Engine-variant die dezelfde formule server-side op
ee.Image-banden toepast, zodat grid- en stationsberekening identiek zijn.
"""

from __future__ import annotations

import numpy as np

__all__ = ["heat_index_c", "heat_index_f", "heat_index_ee"]


def heat_index_f(temp_f, rh):
    """Heat index in °F uit temperatuur (°F) en relatieve vochtigheid (%).

    Volgt exact de NWS-beslisboom:
    1. eenvoudige Steadman-formule;
    2. als het gemiddelde van Steadman-HI en T >= 80 °F: volledige
       Rothfusz-regressie;
    3. correctie bij RH < 13 % en 80–112 °F (aftrekken);
    4. correctie bij RH > 85 % en 80–87 °F (optellen) — in Suriname de
       meest relevante correctie.
    """
    t = np.asarray(temp_f, dtype=np.float64)
    r = np.asarray(rh, dtype=np.float64)
    t, r = np.broadcast_arrays(t, r)

    # Stap 1: eenvoudige formule (Steadman)
    hi_simple = 0.5 * (t + 61.0 + (t - 68.0) * 1.2 + r * 0.094)

    # Stap 2: volledige Rothfusz-regressie
    hi_full = (
        -42.379
        + 2.04901523 * t
        + 10.14333127 * r
        - 0.22475541 * t * r
        - 6.83783e-3 * t * t
        - 5.481717e-2 * r * r
        + 1.22874e-3 * t * t * r
        + 8.5282e-4 * t * r * r
        - 1.99e-6 * t * t * r * r
    )

    # Correctie lage RH
    low_rh = (r < 13.0) & (t >= 80.0) & (t <= 112.0)
    adj_low = ((13.0 - r) / 4.0) * np.sqrt(
        np.clip(17.0 - np.abs(t - 95.0), 0.0, None) / 17.0
    )
    hi_full = np.where(low_rh, hi_full - adj_low, hi_full)

    # Correctie hoge RH
    high_rh = (r > 85.0) & (t >= 80.0) & (t <= 87.0)
    adj_high = ((r - 85.0) / 10.0) * ((87.0 - t) / 5.0)
    hi_full = np.where(high_rh, hi_full + adj_high, hi_full)

    use_full = 0.5 * (hi_simple + t) >= 80.0
    hi = np.where(use_full, hi_full, hi_simple)
    return hi if hi.shape else float(hi)


def heat_index_c(temp_c, rh):
    """Heat index in °C uit temperatuur (°C) en relatieve vochtigheid (%)."""
    temp_f = np.asarray(temp_c, dtype=np.float64) * 9.0 / 5.0 + 32.0
    hi_f = heat_index_f(temp_f, rh)
    hi_c = (np.asarray(hi_f) - 32.0) * 5.0 / 9.0
    return hi_c if hi_c.shape else float(hi_c)


def heat_index_ee(image, band_temp_c: str, band_rh: str, out_band: str = "heat_index"):
    """Zelfde berekening als ee.Image-expressie (server-side, °C in/uit).

    Parameters
    ----------
    image : ee.Image met een temperatuurband (°C) en een RH-band (%)
    band_temp_c, band_rh : bandnamen in ``image``
    out_band : naam van de resulterende heat-indexband
    """
    import ee  # lazy import: alleen nodig in de GEE-pipeline

    t = image.select(band_temp_c).multiply(9.0 / 5.0).add(32.0)  # °F
    r = image.select(band_rh)

    hi_simple = t.expression(
        "0.5 * (T + 61.0 + (T - 68.0) * 1.2 + R * 0.094)",
        {"T": t, "R": r},
    )
    hi_full = t.expression(
        "-42.379 + 2.04901523*T + 10.14333127*R - 0.22475541*T*R"
        " - 6.83783e-3*T*T - 5.481717e-2*R*R + 1.22874e-3*T*T*R"
        " + 8.5282e-4*T*R*R - 1.99e-6*T*T*R*R",
        {"T": t, "R": r},
    )

    adj_low = t.expression(
        "((13.0 - R) / 4.0) * sqrt(max(17.0 - abs(T - 95.0), 0.0) / 17.0)",
        {"T": t, "R": r},
    )
    low_mask = r.lt(13).And(t.gte(80)).And(t.lte(112))
    hi_full = hi_full.where(low_mask, hi_full.subtract(adj_low))

    adj_high = t.expression(
        "((R - 85.0) / 10.0) * ((87.0 - T) / 5.0)",
        {"T": t, "R": r},
    )
    high_mask = r.gt(85).And(t.gte(80)).And(t.lte(87))
    hi_full = hi_full.where(high_mask, hi_full.add(adj_high))

    use_full = hi_simple.add(t).multiply(0.5).gte(80)
    hi_f = hi_simple.where(use_full, hi_full)
    hi_c = hi_f.subtract(32.0).multiply(5.0 / 9.0)
    return image.addBands(hi_c.rename(out_band))
