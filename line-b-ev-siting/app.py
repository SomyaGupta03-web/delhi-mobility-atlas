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
  .hero-sub {{ font-family: Georgia, serif; font-style: italic; font-size: 17px; color: {TEAL}; margin: 0 0 18px; }}
  .kpi-row {{ display: flex; gap: 1px; background: {INK}; border: 1px solid {INK}; margin-bottom: 24px; }}
  .kpi {{ background: {PAPER_ALT}; padding: 14px 18px; flex: 1; text-align: center; }}
  .kpi .num {{ font-family: ui-monospace, monospace; font-size: 24px; font-weight: 700; color: {TEAL}; display: block; }}
  .kpi .label {{ font-size: 11px; color: {INK_SOFT}; letter-spacing: 0.02em; }}
  .legend-box {{
    background: white; border: 1px solid {LINE}; border-radius: 4px; padding: 12px 16px;
    font-size: 12.5px; color: {INK_SOFT}; margin-top: 8px;
  }}
  .finding-box {{
    border-left: 3px solid {TEAL}; background: {PAPER_ALT}; padding: 14px 18px;
    font-size: 14.5px; color: {INK}; margin-top: 20px; border-radius: 0 4px 4px 0;
  }}
  .section-label {{
    font-family: ui-monospace, monospace; font-size: 11px; letter-spacing: 0.1em; text-transform: uppercase;
    color: {INK_SOFT}; border-bottom: 2px solid {INK}; padding-bottom: 6px; margin: 28px 0 14px;
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

st.markdown('<div class="eyebrow">Urban Mobility &middot; Site Selection &middot; Delhi NCT</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-title">Delhi EV Charging Siting Model</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">Given a fixed budget of K new charging stations, where should they go to cover the most unmet demand?</div>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### Controls")
    available_k = sorted(scenarios.keys())
    K = st.select_slider("Number of new charging sites (K)", options=available_k, value=available_k[min(1, len(available_k)-1)])
    chosen = scenarios[K]

    st.markdown("---")
    show_demand = st.checkbox("Show demand heatmap", value=True)
    show_existing = st.checkbox("Show existing chargers", value=True)
    show_new = st.checkbox("Show proposed new sites", value=True)

    st.markdown("---")
    st.markdown(
        "**Method:** a 1,945-cell H3 hex grid scores demand from population, commercial "
        "activity, and fuel-station density; drive-time coverage from 675 real government-"
        "listed chargers is computed over the OSM road network; new sites are chosen via a "
        "Maximal Covering Location solve (PuLP/CBC), within a 3km service radius."
    )

row_at_k = sensitivity[(sensitivity["radius_m"] == 3000) & (sensitivity["K"] == K)]
pct_covered = row_at_k["pct_of_total_demand"].iloc[0] if len(row_at_k) else np.nan

st.markdown(f"""
<div class="kpi-row">
  <div class="kpi"><span class="num">{K}</span><span class="label">Proposed new sites</span></div>
  <div class="kpi"><span class="num">{len(existing)}</span><span class="label">Existing chargers (Delhi Govt data)</span></div>
  <div class="kpi"><span class="num">{pct_covered:.1f}%</span><span class="label">Demand covered @ 3km radius</span></div>
  <div class="kpi"><span class="num">{(chosen['source']=='fuel_station').sum()}/{K}</span><span class="label">New sites at existing fuel stations</span></div>
</div>
""", unsafe_allow_html=True)

vals = grid["demand_score"].astype(float)
norm = ((vals - vals.min()) / (vals.max() - vals.min() + 1e-9)).clip(0, 1)
paper_rgb = np.array([239, 234, 220])
teal_rgb = np.array([60, 107, 110])
grid_colors = np.outer(1 - norm, paper_rgb) + np.outer(norm, teal_rgb)
grid["fill_color"] = [[int(r), int(g), int(b), 170] for r, g, b in grid_colors]

layers = []
if show_demand:
    layers.append(pdk.Layer(
        "GeoJsonLayer", data=grid.__geo_interface__, get_fill_color="properties.fill_color",
        get_line_color=[218, 212, 195, 80], line_width_min_pixels=0.2, pickable=False,
    ))
if show_existing:
    layers.append(pdk.Layer(
        "ScatterplotLayer",
        data=pd.DataFrame({"lon": existing.geometry.x, "lat": existing.geometry.y}),
        get_position=["lon", "lat"], get_fill_color=[75, 87, 96, 150], get_radius=55, pickable=False,
    ))
if show_new:
    chosen_df = pd.DataFrame({
        "lon": chosen.geometry.x, "lat": chosen.geometry.y,
        "demand_score": chosen["demand_score"].round(2), "source": chosen["source"],
    })
    layers.append(pdk.Layer(
        "ScatterplotLayer", data=chosen_df, get_position=["lon", "lat"],
        get_fill_color=[185, 78, 34, 235], get_radius=200, get_line_color=[255, 255, 255], line_width_min_pixels=1.5,
        stroked=True, pickable=True,
    ))

col_map, col_side = st.columns([2.2, 1])

with col_map:
    st.pydeck_chart(
        pdk.Deck(
            map_provider="carto",
            map_style="light",
            initial_view_state=pdk.ViewState(latitude=28.61, longitude=77.21, zoom=9.6),
            layers=layers,
            tooltip={
                "html": "<b>Proposed site</b><br/>Demand score: {demand_score}<br/>Source: {source}",
                "style": {"backgroundColor": INK, "color": "white", "fontSize": "12px"},
            },
        ),
        height=540,
    )
    st.markdown(f"""
    <div class="legend-box">
      <span style="color:{TEAL}">&#9679;</span> Higher demand &nbsp;|&nbsp;
      <span style="color:#4B5760">&#9679;</span> Existing charger &nbsp;|&nbsp;
      <span style="color:{RUST}">&#9679;</span> Proposed new site (K={K})
    </div>
    """, unsafe_allow_html=True)

with col_side:
    st.markdown("**Budget vs. coverage**")
    st.caption("% of total demand-weighted cells covered, by service radius")
    chart = alt.Chart(sensitivity).mark_line(point=True).encode(
        x=alt.X("K:O", title="New sites (K)"),
        y=alt.Y("pct_of_total_demand:Q", title="% demand covered"),
        color=alt.Color("radius_m:N", title="Radius (m)", scale=alt.Scale(range=[RUST, TEAL, INK_SOFT])),
    ).properties(height=280)
    st.altair_chart(chart, use_container_width=True)

    st.markdown("**Chosen sites, this scenario**")
    st.dataframe(
        chosen[["demand_score", "source"]].rename(columns={"demand_score": "Demand score", "source": "Site type"})
        .sort_values("Demand score", ascending=False).reset_index(drop=True),
        hide_index=True, use_container_width=True, height=200,
    )

st.markdown(
    f"""
    <div class="finding-box">
    <b>Finding:</b> OSM's <code>amenity=charging_station</code> tag found only 171 stations citywide;
    Delhi Govt's own EV Finder portal lists 675 real, geocoded stations within the AOI after cleaning —
    ~4x more. For K=20 new sites within a 3km radius, the optimizer covers 25.7% of total demand-weighted
    cells; <b>service radius matters more than station count</b> at this scale — a 5km radius alone covers
    37-49% of demand regardless of K, while 1.5km tops out at 13.6% even with 40 stations.
    </div>
    """,
    unsafe_allow_html=True,
)
