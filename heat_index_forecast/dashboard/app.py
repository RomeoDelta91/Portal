"""Streamlit-dashboard — Heat Index verwachting Suriname (MDS).

Leest de uitvoer van run_pipeline.py uit data/output/:
  - station_forecast_latest.csv   (stationsreeksen, P10/P50/P90 + risico)
  - heat_index_forecast_latest.nc (grid, hi_p50 + hi_spread)

Starten:  streamlit run dashboard/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import altair as alt
import folium
import numpy as np
import pandas as pd
import streamlit as st
import xarray as xr
from streamlit_folium import st_folium

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import (  # noqa: E402
    LOCAL_UTC_OFFSET_HOURS,
    OUTPUT_DIR,
    RISK_CATEGORIES,
    STATIONS,
    SURINAME_BBOX,
    classify_hi,
)

st.set_page_config(
    page_title="Heat Index verwachting Suriname — MDS",
    page_icon="🌡️",
    layout="wide",
)

CSV_PATH = OUTPUT_DIR / "station_forecast_latest.csv"
NC_PATH = OUTPUT_DIR / "heat_index_forecast_latest.nc"

DAGEN_NL = ["maandag", "dinsdag", "woensdag", "donderdag",
            "vrijdag", "zaterdag", "zondag"]


# ---------------------------------------------------------------------------
# Data laden
# ---------------------------------------------------------------------------
@st.cache_data(ttl=900)
def load_stations() -> pd.DataFrame | None:
    if not CSV_PATH.exists():
        return None
    df = pd.read_csv(CSV_PATH, parse_dates=["valid_time", "run"])
    df["lokale_tijd"] = df["valid_time"] + pd.Timedelta(hours=LOCAL_UTC_OFFSET_HOURS)
    df["lokale_tijd"] = df["lokale_tijd"].dt.tz_localize(None)
    return df


@st.cache_data(ttl=900)
def load_grid():
    if not NC_PATH.exists():
        return None
    ds = xr.open_dataset(NC_PATH)
    ds.load()
    ds.close()
    return ds


def kleur_voor(hi: float) -> str:
    return classify_hi(hi).kleur


df = load_stations()

if df is None:
    st.title("🌡️ Heat Index verwachting Suriname")
    st.error(
        "Nog geen forecastdata gevonden. Draai eerst de pipeline:\n\n"
        "```\npython run_pipeline.py\n```"
    )
    st.stop()

grid = load_grid()
run_utc = df["run"].max()
bias_ok = bool(df["bias_corrected"].iloc[0]) if "bias_corrected" in df else False

# ---------------------------------------------------------------------------
# Kop
# ---------------------------------------------------------------------------
st.title("🌡️ Heat Index verwachting Suriname")
st.markdown(
    f"**Meteorologische Dienst Suriname** · 5-daagse verwachting van de "
    f"hitte-index (gevoelstemperatuur) · GFS-run: "
    f"{run_utc.strftime('%d-%m-%Y %H:%M')} UTC"
)
if not bias_ok:
    st.warning(
        "⚠️ Deze run is **niet** bias-gecorrigeerd met de ERA5-Land-"
        "klimatologie (klimatologiebestand niet beschikbaar). Absolute "
        "waarden kunnen lokaal afwijken."
    )

# ---------------------------------------------------------------------------
# Overzichtstegels: maximum per station (komende 24 u)
# ---------------------------------------------------------------------------
st.subheader("Hoogste hitte-index komende 24 uur")
kolommen = st.columns(len(STATIONS))
eerste_24u = df[df["valid_time"] <= df["valid_time"].min() + pd.Timedelta(hours=24)]
for col, s in zip(kolommen, STATIONS):
    sub = eerste_24u[eerste_24u["station"] == s.key]
    if sub.empty:
        continue
    piek = sub.loc[sub["hi_p50"].idxmax()]
    cat = classify_hi(piek["hi_p50"])
    col.markdown(
        f"""
        <div style="border-left:6px solid {cat.kleur}; padding:0.4rem 0.8rem;
                    background:rgba(127,127,127,0.07); border-radius:4px;">
          <div style="font-size:0.85rem; opacity:0.8;">{s.naam}</div>
          <div style="font-size:1.6rem; font-weight:700;">{piek['hi_p50']:.1f} °C</div>
          <div style="font-size:0.9rem;"><b>{cat.naam_nl}</b> ·
               rond {piek['lokale_tijd'].strftime('%H:%M')} uur</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.divider()

# ---------------------------------------------------------------------------
# Kaart + tijdreeks naast elkaar
# ---------------------------------------------------------------------------
kaart_kolom, reeks_kolom = st.columns([1, 1.4])

with kaart_kolom:
    st.subheader("Kaart")
    tijden = sorted(df["valid_time"].unique())
    labels = {
        t: (lambda lt: f"{DAGEN_NL[lt.weekday()]} {lt.strftime('%d-%m %H:%M')} uur")(
            (pd.Timestamp(t) + pd.Timedelta(hours=LOCAL_UTC_OFFSET_HOURS)).tz_localize(None)
        )
        for t in tijden
    }
    keuze_tijd = st.select_slider(
        "Tijdstip (lokale tijd)", options=tijden, format_func=lambda t: labels[t],
        value=tijden[min(4, len(tijden) - 1)],
    )

    west, zuid, oost, noord = SURINAME_BBOX
    m = folium.Map(
        location=[(zuid + noord) / 2, (west + oost) / 2],
        zoom_start=7, tiles="cartodbpositron",
    )

    if grid is not None:
        keuze_np = pd.Timestamp(keuze_tijd).tz_localize(None)
        veld = grid["hi_p50"].sel(time=keuze_np, method="nearest")
        arr = veld.values
        rgba = np.zeros((*arr.shape, 4), dtype=np.uint8)
        for cat in RISK_CATEGORIES:
            mask = np.isfinite(arr) & (arr >= cat.hi_min_c)
            h = cat.kleur.lstrip("#")
            rgba[mask] = [int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 170]
        folium.raster_layers.ImageOverlay(
            image=rgba,
            bounds=[[float(grid.lat.min()) - 0.125, float(grid.lon.min()) - 0.125],
                    [float(grid.lat.max()) + 0.125, float(grid.lon.max()) + 0.125]],
            opacity=0.75, origin="upper",
        ).add_to(m)
    else:
        st.info("Geen grid-bestand gevonden — alleen stations worden getoond.")

    tijdstip_df = df[df["valid_time"] == keuze_tijd]
    for s in STATIONS:
        rij = tijdstip_df[tijdstip_df["station"] == s.key]
        if rij.empty:
            continue
        hi = float(rij["hi_p50"].iloc[0])
        cat = classify_hi(hi)
        folium.CircleMarker(
            location=[s.lat, s.lon], radius=9,
            color="#333333", weight=1.5, fill=True,
            fill_color=cat.kleur, fill_opacity=0.95,
            tooltip=f"{s.naam}: {hi:.1f} °C — {cat.naam_nl}",
            popup=folium.Popup(
                f"<b>{s.naam}</b><br>Hitte-index: {hi:.1f} °C<br>"
                f"Categorie: <b>{cat.naam_nl}</b><br>{cat.beschrijving_nl}",
                max_width=260,
            ),
        ).add_to(m)

    st_folium(m, height=430, use_container_width=True)

    # Legenda
    legenda = "".join(
        f'<span style="display:inline-block; margin-right:0.9rem;">'
        f'<span style="display:inline-block; width:0.8rem; height:0.8rem; '
        f'background:{c.kleur}; border-radius:2px; margin-right:0.3rem;"></span>'
        f'{c.naam_nl}</span>'
        for c in RISK_CATEGORIES
    )
    st.markdown(legenda, unsafe_allow_html=True)

with reeks_kolom:
    st.subheader("Verloop per station")
    station_naam = st.selectbox(
        "Station", [s.naam for s in STATIONS], label_visibility="collapsed"
    )
    s_key = next(s.key for s in STATIONS if s.naam == station_naam)
    sub = df[df["station"] == s_key].sort_values("valid_time").copy()

    y_min = float(min(sub["hi_p10"].min(), 24.0)) - 1.0
    y_max = float(max(sub["hi_p90"].max(), 44.0)) + 1.5

    # Achtergrondbanden per risicocategorie (met tekstlabel — kleur is
    # nooit de enige drager van de categorie)
    banden = []
    for i, cat in enumerate(RISK_CATEGORIES):
        onder = max(cat.hi_min_c, y_min)
        boven = RISK_CATEGORIES[i + 1].hi_min_c if i + 1 < len(RISK_CATEGORIES) else y_max
        boven = min(boven, y_max)
        if boven <= y_min or onder >= y_max:
            continue
        banden.append({"onder": max(onder, y_min), "boven": boven,
                       "naam": cat.naam_nl, "kleur": cat.kleur})
    banden_df = pd.DataFrame(banden)

    x_as = alt.X("lokale_tijd:T", title="Lokale tijd (UTC−3)",
                 axis=alt.Axis(format="%a %d-%m %Hu", labelAngle=-40))
    y_schaal = alt.Scale(domain=[y_min, y_max])

    laag_banden = alt.Chart(banden_df).mark_rect(opacity=0.14).encode(
        y=alt.Y("onder:Q", scale=y_schaal, title="Hitte-index (°C)"),
        y2="boven:Q",
        color=alt.Color("kleur:N", scale=None),
    )
    laag_bandlabels = alt.Chart(banden_df).mark_text(
        align="left", dx=4, dy=8, fontSize=10, opacity=0.75
    ).encode(
        y=alt.Y("boven:Q", scale=y_schaal),
        text="naam:N",
        x=alt.value(4),
    )

    laag_onzeker = alt.Chart(sub).mark_area(
        opacity=0.28, color="#4d7ea8"
    ).encode(
        x=x_as,
        y=alt.Y("hi_p10:Q", scale=y_schaal),
        y2="hi_p90:Q",
    )
    laag_p50 = alt.Chart(sub).mark_line(
        color="#1f4e79", strokeWidth=2, point=alt.OverlayMarkDef(size=26, filled=True)
    ).encode(
        x=x_as,
        y=alt.Y("hi_p50:Q", scale=y_schaal),
        tooltip=[
            alt.Tooltip("lokale_tijd:T", title="Lokale tijd", format="%a %d-%m %H:%M"),
            alt.Tooltip("hi_p50:Q", title="Hitte-index P50 (°C)", format=".1f"),
            alt.Tooltip("hi_p10:Q", title="Ondergrens P10 (°C)", format=".1f"),
            alt.Tooltip("hi_p90:Q", title="Bovengrens P90 (°C)", format=".1f"),
            alt.Tooltip("temp_c:Q", title="Temperatuur (°C)", format=".1f"),
            alt.Tooltip("rh:Q", title="Rel. vochtigheid (%)", format=".0f"),
            alt.Tooltip("risico:N", title="Risico"),
        ],
    )

    grafiek = (laag_banden + laag_bandlabels + laag_onzeker + laag_p50).properties(
        height=420
    ).configure_axis(grid=True, gridOpacity=0.25)
    st.altair_chart(grafiek, use_container_width=True)
    st.caption(
        "Donkerblauwe lijn: centrale verwachting (P50). Blauwe band: "
        "onzekerheidsmarge (P10–P90, spreiding tussen opeenvolgende GFS-runs). "
        "Gekleurde achtergrondbanden: hitte-risicocategorieën."
    )

st.divider()

# ---------------------------------------------------------------------------
# Toelichting risicocategorieën + tabelweergave
# ---------------------------------------------------------------------------
uitleg_kolom, tabel_kolom = st.columns([1, 1.4])

with uitleg_kolom:
    st.subheader("Risicocategorieën")
    st.caption(
        "Suriname-geadapteerde hitte-indexschaal (voorlopige klassegrenzen, "
        "vastgesteld o.b.v. de lokale klimatologie — niet de NOAA/VS-schaal)."
    )
    for i, cat in enumerate(RISK_CATEGORIES):
        bereik = (
            f"< {RISK_CATEGORIES[1].hi_min_c:.0f} °C" if i == 0
            else f"≥ {cat.hi_min_c:.0f} °C"
        )
        st.markdown(
            f'<div style="margin-bottom:0.5rem;">'
            f'<span style="display:inline-block; width:0.9rem; height:0.9rem; '
            f'background:{cat.kleur}; border-radius:2px; margin-right:0.4rem;"></span>'
            f'<b>{cat.naam_nl}</b> ({bereik})<br>'
            f'<span style="font-size:0.9rem; opacity:0.85;">{cat.beschrijving_nl}</span>'
            f"</div>",
            unsafe_allow_html=True,
        )

with tabel_kolom:
    st.subheader("Tabel — dagelijkse maxima per station")
    dag_df = df.copy()
    dag_df["datum"] = dag_df["lokale_tijd"].dt.date
    piv = (
        dag_df.groupby(["station_naam", "datum"])["hi_p50"].max()
        .round(1).unstack("datum")
    )
    piv.index.name = "Station"
    st.dataframe(piv, use_container_width=True)
    st.caption("Maximale hitte-index (P50, °C) per dag, lokale tijd.")

st.divider()
st.caption(
    "Bron: NOAA GFS 0.25° via Google Earth Engine · Heat index: NOAA/Rothfusz-"
    "regressie · Onzekerheid: lagged ensemble van opeenvolgende GFS-runs · "
    "© Meteorologische Dienst Suriname"
)
