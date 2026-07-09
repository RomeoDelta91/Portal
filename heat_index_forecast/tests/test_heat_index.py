"""Tests voor de Rothfusz heat-indexberekening.

Referentiewaarden komen uit de officiële NOAA/NWS heat-indextabel
(https://www.weather.gov/ama/heatindex). Tolerantie ±1.5 °F omdat de
tabel op hele graden is afgerond.
"""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from heat_index import heat_index_c, heat_index_f  # noqa: E402


# (T °F, RH %, verwachte HI °F volgens NOAA-tabel)
NOAA_TABLE = [
    (80, 40, 80),
    (84, 60, 88),
    (90, 55, 97),
    (90, 70, 105),
    (96, 45, 104),
    (96, 65, 121),
    (100, 55, 124),
    (104, 40, 119),
    (110, 40, 136),
]


@pytest.mark.parametrize("t_f, rh, expected", NOAA_TABLE)
def test_matches_noaa_table(t_f, rh, expected):
    assert heat_index_f(t_f, rh) == pytest.approx(expected, abs=1.5)


def test_cool_conditions_use_simple_formula():
    # Bij lage temperaturen moet de HI dicht bij de luchttemperatuur liggen
    # en mag de volledige regressie (die daar ongeldig is) niet gebruikt worden.
    hi = heat_index_c(20.0, 90.0)
    assert abs(hi - 20.0) < 2.5


def test_high_rh_adjustment_applied():
    # Suriname-regime: 80-87 °F met RH > 85 % -> correctie wordt opgeteld.
    t_f, rh = 84.0, 95.0
    base = (
        -42.379 + 2.04901523 * t_f + 10.14333127 * rh - 0.22475541 * t_f * rh
        - 6.83783e-3 * t_f**2 - 5.481717e-2 * rh**2 + 1.22874e-3 * t_f**2 * rh
        + 8.5282e-4 * t_f * rh**2 - 1.99e-6 * t_f**2 * rh**2
    )
    expected_adj = ((rh - 85.0) / 10.0) * ((87.0 - t_f) / 5.0)
    assert heat_index_f(t_f, rh) == pytest.approx(base + expected_adj, abs=1e-9)


def test_vectorized_matches_scalar():
    t = np.array([28.0, 32.0, 35.0])
    rh = np.array([90.0, 75.0, 60.0])
    vec = heat_index_c(t, rh)
    scal = [heat_index_c(float(a), float(b)) for a, b in zip(t, rh)]
    assert np.allclose(vec, scal)


def test_celsius_roundtrip():
    # 32.2 °C (90 °F) bij RH 70 % -> ±105 °F = 40.6 °C
    assert heat_index_c(32.222, 70.0) == pytest.approx(40.6, abs=1.0)
