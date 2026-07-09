"""Stap 2 — minimale rooktest voor Earth Engine-authenticatie.

Draai dit script éénmalig lokaal om te bevestigen dat authenticatie met het
project `my-project-brokopondo` werkt vóórdat de volledige pipeline wordt gebruikt:

    cd heat_index_forecast
    python scripts/test_gee_auth.py

Bij de eerste keer opent `ee.Authenticate()` een browservenster; log in met
ritish199187@gmail.com. Er is geen wachtwoord of API-key in dit script
nodig — de credentials worden door de earthengine-api zelf lokaal opgeslagen.
"""

from __future__ import annotations

import sys
from pathlib import Path

import ee

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import BAND_RH, BAND_TEMP, EE_PROJECT, GFS_COLLECTION, SURINAME_BBOX


def main() -> None:
    try:
        ee.Initialize(project=EE_PROJECT)
    except Exception:
        print("Nog geen geldige credentials gevonden — browser-login starten…")
        ee.Authenticate()
        ee.Initialize(project=EE_PROJECT)

    print(f"OK: geauthenticeerd met project '{EE_PROJECT}'.")

    bbox = ee.Geometry.Rectangle(list(SURINAME_BBOX))
    latest = (
        ee.ImageCollection(GFS_COLLECTION)
        .filterBounds(bbox)
        .filter(ee.Filter.eq("forecast_hours", 0))
        .sort("creation_time", False)
        .first()
    )

    info = latest.getInfo()
    props = info.get("properties", {})
    print("Meest recente GFS-run gevonden:")
    print(f"  creation_time : {props.get('creation_time')}")
    print(f"  forecast_time : {props.get('forecast_time')}")

    stats = (
        latest.select([BAND_TEMP, BAND_RH])
        .reduceRegion(ee.Reducer.mean(), geometry=bbox, scale=27830)
        .getInfo()
    )
    print("Gemiddelden over de Suriname-bbox (analyse, +0 u):")
    print(f"  2m-temperatuur : {stats.get(BAND_TEMP):.1f} °C")
    print(f"  2m-RH          : {stats.get(BAND_RH):.1f} %")
    print("\nAuthenticatie en datatoegang werken — pipeline kan gebruikt worden.")


if __name__ == "__main__":
    main()
