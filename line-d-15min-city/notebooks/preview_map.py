import geopandas as gpd
import folium
import numpy as np

wards = gpd.read_file("data/outputs/wards_with_centrality.gpkg").to_crs(4326)

m = folium.Map(location=[28.61, 77.21], zoom_start=11, tiles="OpenStreetMap")

valid = wards.dropna(subset=["betweenness_mean"])
quantile_bins = list(valid["betweenness_mean"].quantile([0, 0.5, 0.75, 0.9, 0.97, 1.0]))
quantile_bins = sorted(set(quantile_bins))

folium.Choropleth(
    geo_data=wards,
    data=wards,
    columns=["ward_id", "betweenness_mean"],
    key_on="feature.properties.ward_id",
    fill_color="PuRd",
    fill_opacity=0.7,
    line_opacity=0.3,
    bins=quantile_bins,
    legend_name="Mean betweenness centrality (structural chokepoint score)",
    name="Chokepoint score (choropleth)",
    nan_fill_color="grey",
).add_to(m)

folium.GeoJson(
    wards,
    name="Ward boundaries",
    style_function=lambda f: {"color": "#333", "weight": 1, "fillOpacity": 0},
    tooltip=folium.GeoJsonTooltip(
        fields=["ward_id", "ward_name", "betweenness_mean", "betweenness_max", "tmin_market"],
        aliases=["Ward ID:", "Ward:", "Mean chokepoint score:", "Max chokepoint score:", "Walk to market (min):"],
        localize=True,
    ),
).add_to(m)

# Flag wards that are BOTH high-chokepoint AND poorly served: the highest-priority fix targets
bc_thresh = valid["betweenness_mean"].quantile(0.80)
access_thresh = wards["tmin_market"].quantile(0.75)
priority = wards[(wards["betweenness_mean"] >= bc_thresh) & (wards["tmin_market"] >= access_thresh)]
for _, row in priority.iterrows():
    c = row.geometry.centroid
    folium.Marker(
        [c.y, c.x],
        icon=folium.DivIcon(html=f'<div style="font-size:13px;">&#9733; <b style="color:#8B0000;">{row["ward_name"]}</b></div>'),
    ).add_to(m)

title_html = """
<div style="position: fixed; top: 10px; left: 50px; z-index: 9999;
            background: white; padding: 8px 14px; border-radius: 4px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.3); font-family: sans-serif;">
  <div style="font-size:16px; font-weight:bold;">Delhi Walk-Network Chokepoints</div>
  <div style="font-size:11px; color:#555;">Betweenness centrality (500-sample approx.) — wards whose streets many shortest paths must pass through</div>
</div>
"""
m.get_root().html.add_child(folium.Element(title_html))

legend_html = f"""
<div style="position: fixed; bottom: 30px; left: 10px; z-index: 9999;
            background: white; padding: 10px 14px; border-radius: 4px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.3); font-family: sans-serif; font-size: 12px; line-height:1.6;">
  <div style="font-weight:bold; margin-bottom:4px;">Legend</div>
  <div>Darker = more structurally critical (higher chokepoint score)</div>
  <div style="margin-top:4px;">&#9733; <b style="color:#8B0000;">Priority ward</b>: both a major chokepoint AND poorly served ({len(priority)} found)</div>
</div>
"""
m.get_root().html.add_child(folium.Element(legend_html))

folium.LayerControl(collapsed=False).add_to(m)
m.save("app_outputs/centrality_map.html")
print(f"saved app_outputs/centrality_map.html — {len(priority)} priority wards flagged")
print(priority[["ward_id", "ward_name", "betweenness_mean", "tmin_market"]])
