import geopandas as gpd
import numpy as np
import pandas as pd
import altair as alt
import pydeck as pdk
import streamlit as st

st.set_page_config(page_title="Delhi Mobility Desert Index", layout="wide", initial_sidebar_state="expanded")

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
  .hero-sub {{ font-family: Georgia, serif; font-style: italic; font-size: 18px; color: {RUST}; margin: 0 0 6px; max-width: 720px; }}
  .lede {{ font-size: 15.5px; color: {INK_SOFT}; max-width: 720px; margin-bottom: 22px; }}
  .kpi-row {{ display: flex; gap: 1px; background: {INK}; border: 1px solid {INK}; margin-bottom: 22px; }}
  .kpi {{ background: {PAPER_ALT}; padding: 14px 18px; flex: 1; text-align: center; }}
  .kpi .num {{ font-family: ui-monospace, monospace; font-size: 24px; font-weight: 700; color: {RUST}; display: block; }}
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
  [data-testid="stMetricValue"] {{ color: {RUST}; }}
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_data():
    wards = gpd.read_file("data/outputs/wards_scored.gpkg").to_crs(4326)
    pois = {}
    for label in ["health", "education", "market"]:
        try:
            pois[label] = gpd.read_file(f"data/interim/pois_{label}.gpkg").to_crs(4326)
        except Exception:
            pois[label] = None
    return wards, pois


wards, pois = load_data()

METRICS = {
    "mobility_desert_score": ("Mobility Desert Score", "0 (best access) to 100 (worst)"),
    "tmin_health": ("Hospital access", "walk minutes to nearest hospital/clinic"),
    "tmin_education": ("School access", "walk minutes to nearest school/college"),
    "tmin_market": ("Market access", "walk minutes to nearest market/supermarket"),
    "population": ("Population", "estimated ward population"),
}

# ---------------- Header + narrative hook ----------------
st.markdown('<div class="eyebrow">Urban Mobility &middot; Spatial Analytics &middot; Delhi NCT</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-title">The Wards Delhi\'s Transit Map Forgot</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">Where is it genuinely hard to reach a hospital, school, or market on foot — and who lives there?</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="lede">Straight-line distance says a ward is "close" to a market. Actually walking there, along real '
    'streets, often tells a different story. This model routes every one of 228,000 street-network points to its '
    'nearest hospital, school, and market — then weights the result by population density, so a slow-but-empty ward '
    'and a slow-and-crowded one aren\'t scored the same. What falls out is a named, mappable list of Delhi\'s '
    'mobility deserts, not just a color scale.</div>',
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### Explore the wards")
    metric = st.selectbox("Metric", list(METRICS.keys()), format_func=lambda c: METRICS[c][0])
    st.caption(METRICS[metric][1])

    show_health = st.checkbox("Show hospitals/clinics", value=False)
    show_edu = st.checkbox("Show schools/colleges", value=False)
    show_market = st.checkbox("Show markets", value=False)

    st.markdown("---")
    ward_names = sorted(wards["ward_name"].dropna().unique().tolist())
    selected_ward = st.selectbox("Look up a ward", ["(none)"] + ward_names)

    with st.expander("Method"):
        st.markdown(
            "Walk time is computed via shortest-path routing over the real OpenStreetMap "
            "street network (not straight-line distance), combined with population density "
            "into a single 0-100 score. See the [GitHub repo](https://github.com/SomyaGupta03-web/delhi-mobility-atlas) for the full pipeline."
        )

vals = wards[metric].astype(float)
vals_filled = vals.fillna(vals.median())
vmin, vmax = vals_filled.min(), vals_filled.max()
norm = ((vals_filled - vmin) / (vmax - vmin + 1e-9)).clip(0, 1)

teal_rgb = np.array([60, 107, 110])
rust_rgb = np.array([185, 78, 34])
colors = np.outer(1 - norm, teal_rgb) + np.outer(norm, rust_rgb)
wards["fill_color"] = [[int(r), int(g), int(b), 205] for r, g, b in colors]
wards["metric_display"] = vals.round(1)

n_wards = len(wards)
worst_val = vals.max()
worst_ward = wards.loc[vals.idxmax(), "ward_name"]
best_ward = wards.loc[vals.idxmin(), "ward_name"]
no_market_pct = (wards["tmin_market"].isna().mean() * 100) if "tmin_market" in wards else 0

st.markdown(f"""
<div class="kpi-row">
  <div class="kpi"><span class="num">{n_wards}</span><span class="label">Wards analyzed</span></div>
  <div class="kpi"><span class="num">{worst_ward.title()}</span><span class="label">Worst on {METRICS[metric][0]}</span></div>
  <div class="kpi"><span class="num">{best_ward.title()}</span><span class="label">Best on {METRICS[metric][0]}</span></div>
  <div class="kpi"><span class="num">{no_market_pct:.0f}%</span><span class="label">Network with no market in 30 min</span></div>
</div>
""", unsafe_allow_html=True)

# ---------------- The map ----------------
layers = [
    pdk.Layer(
        "GeoJsonLayer",
        data=wards.__geo_interface__,
        get_fill_color="properties.fill_color",
        get_line_color=[30, 42, 51, 120],
        line_width_min_pixels=0.5,
        pickable=True,
        auto_highlight=True,
        highlight_color=[255, 255, 255, 110],
    )
]

poi_specs = [(show_health, "health", [217, 95, 60]), (show_edu, "education", [60, 107, 110]), (show_market, "market", [140, 60, 180])]
for show, label, color in poi_specs:
    if show and pois.get(label) is not None:
        gdf = pois[label]
        layers.append(pdk.Layer(
            "ScatterplotLayer",
            data=pd.DataFrame({"lon": gdf.geometry.x, "lat": gdf.geometry.y}),
            get_position=["lon", "lat"],
            get_fill_color=color + [210],
            get_radius=45,
            pickable=False,
        ))

view_state = pdk.ViewState(latitude=28.61, longitude=77.21, zoom=9.6)
if selected_ward != "(none)":
    match = wards[wards["ward_name"] == selected_ward]
    if len(match):
        c = match.geometry.iloc[0].centroid
        view_state = pdk.ViewState(latitude=c.y, longitude=c.x, zoom=13)

st.pydeck_chart(
    pdk.Deck(
        map_provider="carto",
        map_style="light",
        initial_view_state=view_state,
        layers=layers,
        tooltip={
            "html": "<b>{ward_name}</b><br/>" + METRICS[metric][0] + ": {metric_display}",
            "style": {"backgroundColor": INK, "color": "white", "fontSize": "12px"},
        },
    ),
    height=560,
)
st.markdown(f"""
<div class="legend-box">
  Rust = worse on <b>{METRICS[metric][0]}</b>, teal = better &nbsp;|&nbsp;
  {'<span style="color:#D95F3C">&#9679;</span> Hospitals &nbsp;' if show_health else ''}
  {'<span style="color:#3C6B6E">&#9679;</span> Schools &nbsp;' if show_edu else ''}
  {'<span style="color:#8C3CB4">&#9679;</span> Markets' if show_market else ''}
</div>
""", unsafe_allow_html=True)

# ---------------- The finding, prominent ----------------
st.markdown(
    """
    <div class="finding-box">
    <span class="finding-label">The finding</span>
    The worst-scoring wards — Dharampura, Khajoori Khas, Jiwanpur, Gokalpur, Saboli, Gandhi Nagar,
    Mustafabad, Bhajanpura, Harsh Vihar, Karawal Nagar West — aren't scattered at random. They cluster
    almost entirely in <b>Northeast Delhi</b>, a part of the city independently known to be underserved.
    Market access is the weakest category citywide: roughly 31% of the walkable street network has no
    market within a 30-minute walk at all.
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------- Explore further ----------------
st.markdown('<div class="section-label">Look up a ward or compare the extremes</div>', unsafe_allow_html=True)
col_detail, col_chart = st.columns([1, 1.4])

with col_detail:
    if selected_ward != "(none)":
        match = wards[wards["ward_name"] == selected_ward].iloc[0]
        hosp = f"{match['tmin_health']:.0f} min" if pd.notna(match['tmin_health']) else "N/A"
        edu = f"{match['tmin_education']:.0f} min" if pd.notna(match['tmin_education']) else "N/A"
        mkt = f"{match['tmin_market']:.0f} min" if pd.notna(match['tmin_market']) else "N/A"
        st.markdown(f"""
        <div class="legend-box">
        <div style="font-family: Georgia, serif; font-size: 18px; margin-bottom: 8px;">{selected_ward.title()}</div>
        <div style="font-size: 26px; color: {RUST}; font-weight: 700; font-family: ui-monospace, monospace;">{match['mobility_desert_score']:.1f}</div>
        <div style="font-size: 11px; color: {INK_SOFT}; margin-bottom: 10px;">Mobility Desert Score</div>
        <table style="width:100%; font-size: 13px;">
          <tr><td style="color:{INK_SOFT};">Hospital</td><td style="text-align:right; font-weight:600;">{hosp}</td></tr>
          <tr><td style="color:{INK_SOFT};">School</td><td style="text-align:right; font-weight:600;">{edu}</td></tr>
          <tr><td style="color:{INK_SOFT};">Market</td><td style="text-align:right; font-weight:600;">{mkt}</td></tr>
        </table>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("Use \"Look up a ward\" in the sidebar to see its full stats here.")

with col_chart:
    st.markdown("**Top 8 worst-served wards**")
    top_worst = wards.nlargest(8, metric)[["ward_name", metric]].copy()
    top_worst["ward_name"] = top_worst["ward_name"].str.title()
    chart = alt.Chart(top_worst).mark_bar(color=RUST).encode(
        x=alt.X(metric, title=None),
        y=alt.Y("ward_name", sort="-x", title=None),
    ).properties(height=260)
    st.altair_chart(chart, use_container_width=True)

display_cols = ["ward_name", "mobility_desert_score", "tmin_health", "tmin_education", "tmin_market"]
col_rename = {"ward_name": "Ward", "mobility_desert_score": "Score", "tmin_health": "Hospital (min)", "tmin_education": "School (min)", "tmin_market": "Market (min)"}
col_config = {
    "Score": st.column_config.NumberColumn(format="%.1f"),
    "Hospital (min)": st.column_config.NumberColumn(format="%.1f"),
    "School (min)": st.column_config.NumberColumn(format="%.1f"),
    "Market (min)": st.column_config.NumberColumn(format="%.1f"),
}

tab1, tab2 = st.tabs(["Worst 10", "Best 10"])
with tab1:
    st.dataframe(
        wards.sort_values(metric, ascending=False)[display_cols]
        .head(10).rename(columns=col_rename)
        .reset_index(drop=True), hide_index=True, use_container_width=True, column_config=col_config,
    )
with tab2:
    st.dataframe(
        wards.sort_values(metric, ascending=True)[display_cols]
        .head(10).rename(columns=col_rename)
        .reset_index(drop=True), hide_index=True, use_container_width=True, column_config=col_config,
    )
