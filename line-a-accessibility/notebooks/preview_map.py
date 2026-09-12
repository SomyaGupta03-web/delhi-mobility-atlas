import pickle
import random
from pathlib import Path

import folium
import geopandas as gpd

scored_path = Path("data/outputs/wards_scored.gpkg")
access_path = Path("data/interim/wards_with_access.gpkg")
if scored_path.exists():
    wards = gpd.read_file(scored_path).to_crs(4326)
elif access_path.exists():
    wards = gpd.read_file(access_path).to_crs(4326)
else:
    wards = gpd.read_file("data/interim/delhi_wards_utm43n.gpkg").to_crs(4326)
has_access = "tmin_market" in wards.columns
has_score = "mobility_desert_score" in wards.columns
rank_col = "mobility_desert_score" if has_score else "tmin_market"

m = folium.Map(location=[28.61, 77.21], zoom_start=11, tiles="OpenStreetMap")

# ---- Choropleth: final Mobility Desert Score (falls back to market-access time) ----
if has_score:
    folium.Choropleth(
        geo_data=wards,
        data=wards,
        columns=["ward_id", "mobility_desert_score"],
        key_on="feature.properties.ward_id",
        fill_color="YlOrRd",
        fill_opacity=0.65,
        line_opacity=0.3,
        legend_name="Mobility Desert Score (0=best access, 100=worst; walk time + population density)",
        name="Choropleth: Mobility Desert Score",
        nan_fill_color="grey",
    ).add_to(m)
elif has_access:
    folium.Choropleth(
        geo_data=wards,
        data=wards,
        columns=["ward_id", "tmin_market"],
        key_on="feature.properties.ward_id",
        fill_color="YlOrRd",
        fill_opacity=0.65,
        line_opacity=0.3,
        legend_name="Walk minutes to nearest market (darker = worse access)",
        name="Choropleth: market access",
        nan_fill_color="grey",
    ).add_to(m)

# ---- Ward outlines + tooltip with real numbers ----
tooltip_fields = [c for c in ["ward_id", "ward_name", "mobility_desert_score", "tmin_health", "tmin_education", "tmin_market", "population"] if c in wards.columns]
tooltip_aliases = {
    "ward_id": "Ward ID:", "ward_name": "Ward:",
    "mobility_desert_score": "Mobility Desert Score:",
    "tmin_health": "Walk to nearest hospital (min):",
    "tmin_education": "Walk to nearest school (min):",
    "tmin_market": "Walk to nearest market (min):",
    "population": "Population:",
}
folium.GeoJson(
    wards,
    name="Ward boundaries",
    style_function=lambda f: {"color": "#3454D1", "weight": 1, "fillOpacity": 0},
    tooltip=folium.GeoJsonTooltip(
        fields=tooltip_fields,
        aliases=[tooltip_aliases[c] for c in tooltip_fields],
        localize=True,
    ),
).add_to(m)

# ---- Highlight the 10 worst / 10 best wards, labeled ----
if has_score or has_access:
    ranked = wards.dropna(subset=[rank_col]).sort_values(rank_col)
    for _, row in ranked.tail(10).iterrows():  # worst
        c = row.geometry.centroid
        folium.Marker(
            [c.y, c.x],
            icon=folium.DivIcon(html=f'<div style="font-size:10px;font-weight:bold;color:#8B0000;white-space:nowrap;">&#9660; {row["ward_name"]}</div>'),
        ).add_to(m)
    for _, row in ranked.head(10).iterrows():  # best
        c = row.geometry.centroid
        folium.Marker(
            [c.y, c.x],
            icon=folium.DivIcon(html=f'<div style="font-size:10px;font-weight:bold;color:#1F7A4D;white-space:nowrap;">&#9650; {row["ward_name"]}</div>'),
        ).add_to(m)

# ---- POI layers ----
poi_meta = {
    "health": ("red", "Hospitals / clinics"),
    "education": ("blue", "Schools / colleges"),
    "market": ("green", "Markets / supermarkets"),
}
for label, (color, readable) in poi_meta.items():
    try:
        gdf = gpd.read_file(f"data/interim/pois_{label}.gpkg").to_crs(4326)
        fg = folium.FeatureGroup(name=f"{readable} ({len(gdf)})")
        for _, row in gdf.iterrows():
            folium.CircleMarker(
                [row.geometry.y, row.geometry.x], radius=2.5, color=color, fill=True, fill_opacity=0.8, weight=0,
            ).add_to(fg)
        fg.add_to(m)
    except Exception as e:
        print(f"skipped {label}: {e}")

# ---- Street network nodes (sample) — shows what a "node" actually is ----
graph_path = Path("data/interim/delhi_walk_network_weighted.pkl")
if graph_path.exists():
    with open(graph_path, "rb") as f:
        G = pickle.load(f)
    nodes = list(G.nodes)
    sample = random.Random(42).sample(nodes, min(4000, len(nodes)))
    fg_nodes = folium.FeatureGroup(name=f"Street network nodes (sample of {len(sample)} of {len(nodes)})", show=False)
    node_gdf = gpd.GeoDataFrame(
        geometry=gpd.points_from_xy([G.nodes[n]["x"] for n in sample], [G.nodes[n]["y"] for n in sample]),
        crs=G.graph.get("crs", "EPSG:32643"),
    ).to_crs(4326)
    for pt in node_gdf.geometry:
        folium.CircleMarker([pt.y, pt.x], radius=1, color="#555555", fill=True, fill_opacity=0.5, weight=0).add_to(fg_nodes)
    fg_nodes.add_to(m)

# ---- Title + explanatory legend (custom HTML overlay) ----
title_html = """
<div style="position: fixed; top: 10px; left: 50px; z-index: 9999;
            background: white; padding: 8px 14px; border-radius: 4px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.3); font-family: sans-serif;">
  <div style="font-size:16px; font-weight:bold;">Delhi Mobility Desert Index</div>
  <div style="font-size:11px; color:#555;">Walk time (hospitals/schools/markets) + population density, computed over the real street network — not straight-line distance</div>
</div>
"""
m.get_root().html.add_child(folium.Element(title_html))

legend_html = """
<div style="position: fixed; bottom: 30px; left: 10px; z-index: 9999;
            background: white; padding: 10px 14px; border-radius: 4px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.3); font-family: sans-serif; font-size: 12px; line-height:1.6;">
  <div style="font-weight:bold; margin-bottom:4px;">Legend</div>
  <div><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:red;margin-right:6px;"></span>Hospital / clinic</div>
  <div><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:blue;margin-right:6px;"></span>School / college</div>
  <div><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:green;margin-right:6px;"></span>Market / supermarket</div>
  <div><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#555;margin-right:6px;"></span>Street network node (a real intersection / path point used to compute routes)</div>
  <div style="margin-top:4px;"><span style="color:#8B0000;font-weight:bold;">&#9660;</span> Worst-served ward &nbsp; <span style="color:#1F7A4D;font-weight:bold;">&#9650;</span> Best-served ward</div>
  <div style="margin-top:4px; color:#555;">Ward shading = Mobility Desert Score, 0 (best) to 100 (worst)</div>
</div>
"""
m.get_root().html.add_child(folium.Element(legend_html))

folium.LayerControl(collapsed=False).add_to(m)
m.save("app_outputs/preview_map.html")
print("saved app_outputs/preview_map.html")
