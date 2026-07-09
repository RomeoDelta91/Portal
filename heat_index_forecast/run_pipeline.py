"""Orchestrator: volledige dagelijkse heat-indexforecast-run.

Stappen:
1. Earth Engine initialiseren (gebruiker of service account)
2. Laatste N GFS-runs bepalen (lagged ensemble)
3. Stationsreeksen ophalen + ensemblestatistiek (P10/P50/P90)
4. Grid-forecast ophalen (P50 + spread)
5. Biascorrectie met ERA5-Land-klimatologie (indien beschikbaar)
6. Risicoclassificatie per station
7. Export: CSV (stations) + CF-1.8 NetCDF (grid) naar data/output/

Gebruik:
    python run_pipeline.py                 # volledige run
    python run_pipeline.py --skip-grid     # alleen stations (sneller, test)
"""

from __future__ import annotations

import argparse
import logging
import sys

import pandas as pd

from config import (
    FORECAST_HOURS,
    LAGGED_ENSEMBLE_RUNS,
    OUTPUT_DIR,
    classify_hi,
)

log = logging.getLogger("pipeline")


def main() -> int:
    parser = argparse.ArgumentParser(description="Heat Index forecast Suriname")
    parser.add_argument("--skip-grid", action="store_true",
                        help="alleen stationsforecast (geen grid/NetCDF)")
    parser.add_argument("--runs", type=int, default=LAGGED_ENSEMBLE_RUNS,
                        help="aantal GFS-runs in de lagged ensemble")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    import gee_fetch
    from bias_correction import (
        ClimatologyUnavailable,
        apply_to_grid,
        apply_to_stations,
        delta_field,
        gfs_reference_by_hour,
        load_era5_climatology,
    )
    from netcdf_export import export_forecast

    # 1-2. EE + runs
    gee_fetch.init_ee()
    runs = gee_fetch.latest_runs(args.runs)
    newest = runs[-1]
    run_time = pd.Timestamp(newest, unit="ms", tz="UTC")
    valid_times = gee_fetch.valid_times_for_run(newest, FORECAST_HOURS)
    log.info("Nieuwste GFS-run: %s | ensemble: %d runs | %d tijdstippen",
             run_time, len(runs), len(valid_times))

    # 3. Stations
    log.info("Stationsreeksen ophalen…")
    raw = gee_fetch.station_forecast(runs, valid_times)
    stations = gee_fetch.station_ensemble_stats(raw)

    # 4. Grid
    grid = None
    if not args.skip_grid:
        log.info("Grid-forecast ophalen (P50 + spread)…")
        grid = gee_fetch.grid_forecast(runs, valid_times)

    # 5. Biascorrectie
    bias_corrected = False
    try:
        clim = load_era5_climatology()
        log.info("ERA5-Land-klimatologie geladen; GFS-referentie berekenen…")
        gfs_ref = gfs_reference_by_hour()
        delta = delta_field(clim, gfs_ref, doy=run_time.dayofyear)
        stations = apply_to_stations(stations, delta)
        if grid is not None:
            grid = apply_to_grid(grid, delta)
        bias_corrected = True
        log.info("Biascorrectie toegepast (additieve delta).")
    except ClimatologyUnavailable as exc:
        log.warning("Biascorrectie OVERGESLAGEN: %s", exc)

    # 6. Classificatie (op de bias-gecorrigeerde P50)
    stations["risico"] = stations["hi_p50"].map(lambda v: classify_hi(v).naam_nl)
    stations["risico_key"] = stations["hi_p50"].map(lambda v: classify_hi(v).key)
    stations["bias_corrected"] = bias_corrected

    # 7. Export
    csv_path = OUTPUT_DIR / f"station_forecast_{run_time.strftime('%Y%m%d%H')}.csv"
    stations.to_csv(csv_path, index=False)
    stations.to_csv(OUTPUT_DIR / "station_forecast_latest.csv", index=False)
    log.info("Stationsforecast weggeschreven: %s", csv_path)

    if grid is not None:
        nc_path = export_forecast(grid, run_time, bias_corrected)
        latest_nc = OUTPUT_DIR / "heat_index_forecast_latest.nc"
        latest_nc.unlink(missing_ok=True)
        export_forecast(grid, run_time, bias_corrected, latest_nc)
        log.info("NetCDF weggeschreven: %s", nc_path)

    log.info("Run afgerond%s.", "" if bias_corrected else " (ZONDER biascorrectie)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
