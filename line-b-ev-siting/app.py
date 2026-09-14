import geopandas as gpd
import pandas as pd
import numpy as np
import altair as alt
import pydeck as pdk
import streamlit as st

st.set_page_config(page_title="Delhi EV Charging Siting", layout="wide", initial_sidebar_state="expanded")

PAPER = "#F6F3EC"
PAPER_ALT = "#EFEADC"
INK = "#1E2A33"
INK_SOFT = "#4B5760"
RUST = "#B94E22"
RUST_DEEP = "#8F3A18"
TEAL = "#3C6B6E"
LINE = "#DAD4C3"

st.markdown(f"""
<style>
  .stApp {{ background-color: {PAPER}; }}
  html, body, [class*="css"] {{ font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; color: {INK}; }}
  h1, h2, h3 {{ font-family: Georgia, "Iowan Old Style", "Palatino Linotype", serif !important; color: {INK} !important; }}
  section[data-testid="stSidebar"] {{ background-color: {PAPER_ALT}; border-right: 2px solid {INK}; }}
  .eyebrow {{
    font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size: 11px; letter-spacing: 0.14em;
    text-transform: uppercase; color: {RUST_DEEP}; margin-bottom: 6px;
  }}
  .hero-title {{ font-family: Georgia, serif; font-size: 40px; color: {INK}; margin: 0 0 4px; }}
  .hero-sub {{ font-family: Georgia, serif; font-style: italic; font-size: 18px; color: {TEAL}; margin: 0 0 6px; max-width: 720px; }}
  .lede {{ font-size: 15.5px; color: {INK_SOFT}; max-width: 720px; margin-bottom: 22px; }}
  .kpi-row {{ display: flex; gap: 1px; background: {INK}; border: 1px solid {INK}; margin-bottom: 22px; }}
  .kpi {{ background: {PAPER_ALT}; padding: 14px 18px; flex: 1; text-align: center; }}
  .kpi .num {{ font-family: ui-monospace, monospace; font-size: 24px; font-weight: 700; color: {TEAL}; display: block; }}
  .kpi .label {{ font-size: 11px; color: {INK_SOFT}; letter-spacing: 0.02em; }}
  .legend-box {{
    background: white; border: 1px solid {LINE}; border-radius: 4px; padding: 10px 16px;
    font-size: 12.5px; color: {INK_SOFT}; margin-top: 8px;
  }}
  .finding-box {{
    border-left: 4px solid {RUST}; background: {PAPER_ALT}; padding: 18px 22px;
    font-size: 16px; color: {INK}; margin: 4px 0 32px; border-radius: 0 4px 4px 0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  }}
  .finding-label {{ font-family: ui-monospace, monospace; font-size: 11px; letter-spacing: 0.1em; text-transform: uppercase; color: {RUST_DEEP}; margin-bottom: 6px; display: block; }}
  .section-label {{
    font-family: ui-monospace, monospace; font-size: 11px; letter-spacing: 0.1em; text-transform: uppercase;
    color: {INK_SOFT}; border-bottom: 2px solid {INK}; padding-bottom: 6px; margin: 30px 0 14px;
  }}
  [data-testid="stMetricValue"] {{ color: {TEAL}; }}
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_data():
    grid = gpd.read_file("data/interim/grid_with_demand.gpkg").to_crs(4326)
    existing = gpd.read_file("data/interim/chargers_delhigov.gpkg").to_crs(4326)
    sensitivity = pd.read_csv("data/outputs/sensitivity_results.csv")
    scenarios = {}
    for k in [10, 20, 40]:
        try:
            scenarios[k] = gpd.read_file(f"data/outputs/chosen_sites_k{k}.gpkg").to_crs(4326)
        except Exception:
            pass
    return grid, existing, sensitivity, scenarios


grid, existing, sensitivity, scenarios = load_data()
total_demand = grid["demand_score"].sum()

# ---------------- Header + narrative hook ----------------
st.markdown('<div class="eyebrow">Urban Mobility &middot; Site Selection &middot; Delhi NCT</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-title">Where Should Delhi Build Its Next EV Chargers?</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">675 charging stations already exist. Demand is not evenly distributed. Neither is coverage.</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="lede">Official records list 891 charging stations across Delhi — but nearly a third have no usable '
    'coordinates, and OpenStreetMap (the default source most analyses would reach for) knows about only 171 of them. '
    'Once the real 675 are mapped, a clear pattern emerges: demand for charging — driven by population, commercial '
    'activity, and existing fuel-station traffic — is concentrated in specific pockets that today\'s charger network '
    'does not reach. This model finds exactly where a fixed budget of new stations would close that gap fastest.</div>',
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### Explore the scenarios")
    available_k = sorted(scenarios.keys())
    K = st.select_slider("Budget: number of new charging sites", options=available_k, value=available_k[min(1, len(available_k)-1)])
    chosen = scenarios[K]

    st.markdown("---")
    show_demand = st.checkbox("Demand heatmap (3D)", value=True)
    show_coverage = st.checkbox("Coverage radius (3km)", value=True)
    show_existing = st.checkbox("Existing chargers", value=True)
    show_new = st.checkbox("Proposed new sites", value=True)

    with st.expander("Method"):
        st.markdown(
            "A 1,945-cell H3 hex grid scores demand from population, commercial activity, "
            "and fuel-station density. Drive-time coverage from 675 real government-listed "
            "chargers is computed over the OSM road network. New sites are chosen via a "
            "Maximal Covering Location solve (PuLP/CBC), within a 3km service radius."
        )

row_at_k = sensitivity[(sensitivity["radius_m"] == 3000) & (sensitivity["K"] == K)]
pct_covered = row_at_k["pct_of_total_demand"].iloc[0] if len(row_at_k) else np.nan

st.markdown(f"""
<div class="kpi-row">
  <div class="kpi"><span class="num">{K}</span><span class="label">New sites in this scenario</span></div>
  <div class="kpi"><span class="num">675</span><span class="label">Existing chargers (Delhi Govt data)</span></div>
  <div class="kpi"><span class="num">{pct_covered:.1f}%</span><span class="label">Demand covered @ 3km radius</span></div>
  <div class="kpi"><span class="num">4x</span><span class="label">More stations found than OSM alone</span></div>
</div>
""", unsafe_allow_html=True)

# ---------------- The map: 3D demand skyline + coverage bubbles ----------------
vals = grid["demand_score"].astype(float)
norm = ((vals - vals.min()) / (vals.max() - vals.min() + 1e-9)).clip(0, 1)
low = np.array([239, 234, 220])
high = np.array([185, 78, 34])
grid_colors = np.outer(1 - norm, low) + np.outer(norm, high)
grid["fill_color"] = [[int(r), int(g), int(b), 200] for r, g, b in grid_colors]
grid["elevation"] = (norm * 1800).astype(int)

layers = []
if show_demand:
    layers.append(pdk.Layer(
        "GeoJsonLayer", data=grid.__geo_interface__, get_fill_color="properties.fill_color",
        get_line_color=[218, 212, 195, 60], line_width_min_pixels=0.2,
        extruded=True, get_elevation="properties.elevation", elevation_scale=1, pickable=False,
    ))
MARKER_Z = 2000  # float above the tallest hex column (max elevation 1800) so points aren't buried
GROUND_Z = 5      # coverage bubbles stay near-ground, just enough to avoid z-fighting with hexes

if show_coverage and show_existing:
    layers.append(pdk.Layer(
        "ScatterplotLayer",
        data=pd.DataFrame({"lon": existing.geometry.x, "lat": existing.geometry.y, "z": GROUND_Z}),
        get_position=["lon", "lat", "z"], get_fill_color=[75, 87, 96, 28], get_radius=3000, pickable=False,
    ))
if show_existing:
    layers.append(pdk.Layer(
        "ScatterplotLayer",
        data=pd.DataFrame({"lon": existing.geometry.x, "lat": existing.geometry.y, "z": MARKER_Z}),
        get_position=["lon", "lat", "z"], get_fill_color=[75, 87, 96, 230], get_radius=90, pickable=False,
    ))
if show_coverage and show_new:
    layers.append(pdk.Layer(
        "ScatterplotLayer",
        data=pd.DataFrame({"lon": chosen.geometry.x, "lat": chosen.geometry.y, "z": GROUND_Z}),
        get_position=["lon", "lat", "z"], get_fill_color=[60, 107, 110, 45], get_radius=3000, pickable=False,
    ))
if show_new:
    chosen_df = pd.DataFrame({
        "lon": chosen.geometry.x, "lat": chosen.geometry.y, "z": MARKER_Z,
        "demand_score": chosen["demand_score"].round(2), "source": chosen["source"],
    })
    layers.append(pdk.Layer(
        "ScatterplotLayer", data=chosen_df, get_position=["lon", "lat", "z"],
        get_fill_color=[60, 107, 110, 250], get_radius=260, get_line_color=[255, 255, 255], line_width_min_pixels=2,
        stroked=True, pickable=True,
    ))

st.pydeck_chart(
    pdk.Deck(
        map_provider="carto",
        map_style="light",
        initial_view_state=pdk.ViewState(latitude=28.61, longitude=77.21, zoom=9.6, pitch=45, bearing=-10),
        layers=layers,
        tooltip={
            "html": "<b>Proposed site</b><br/>Demand score: {demand_score}<br/>Source: {source}",
            "style": {"backgroundColor": INK, "color": "white", "fontSize": "12px"},
        },
    ),
    height=580,
)
st.markdown(f"""
<div class="legend-box">
  Taller/darker hex = higher demand &nbsp;|&nbsp;
  <span style="color:#4B5760">&#9679;</span> Existing charger &nbsp;|&nbsp;
  <span style="color:{TEAL}">&#9679;</span> Proposed new site (K={K}) &nbsp;|&nbsp;
  faint circles = 3km service radius — gaps between circles are the uncovered demand
</div>
""", unsafe_allow_html=True)

# ---------------- The finding, prominent ----------------
st.markdown(
    f"""
    <div class="finding-box">
    <span class="finding-label">The finding</span>
    Service radius matters more than station count. A 5km radius alone covers 37–49% of demand
    <i>regardless of K</i>, while a 1.5km radius tops out at just 13.6% even with 40 stations. At the
    realistic 3km radius, {K} new sites close {pct_covered:.1f}% of the coverage gap — visible above as new
    teal bubbles filling the empty space between existing grey ones, concentrated where the demand skyline
    peaks highest.
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------- Explore further ----------------
st.markdown('<div class="section-label">Explore the budget tradeoff</div>', unsafe_allow_html=True)
col_chart, col_table = st.columns([1.6, 1])
with col_chart:
    st.caption("% of total demand-weighted cells covered, by service radius")
    chart = alt.Chart(sensitivity).mark_line(point=True, strokeWidth=2.5).encode(
        x=alt.X("K:O", title="New sites (K)"),
        y=alt.Y("pct_of_total_demand:Q", title="% demand covered"),
        color=alt.Color("radius_m:N", title="Radius (m)", scale=alt.Scale(range=[RUST, TEAL, INK_SOFT])),
    ).properties(height=280)
    st.altair_chart(chart, use_container_width=True)
with col_table:
    st.caption(f"Chosen sites, K={K} scenario")
    st.dataframe(
        chosen[["demand_score", "source"]].rename(columns={"demand_score": "Demand score", "source": "Site type"})
        .sort_values("Demand score", ascending=False).reset_index(drop=True),
        hide_index=True, use_container_width=True, height=280,
    )
