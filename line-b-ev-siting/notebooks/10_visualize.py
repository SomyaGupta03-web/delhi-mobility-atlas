import geopandas as gpd
import folium

grid = gpd.read_file("data/interim/grid_with_demand.gpkg").to_crs(4326)
existing = gpd.read_file("data/interim/chargers_delhigov.gpkg").to_crs(4326)
chosen = gpd.read_file("data/outputs/chosen_sites_k20.gpkg").to_crs(4326)

m = folium.Map(location=[28.61, 77.21], zoom_start=11, tiles="OpenStreetMap")

folium.Choropleth(
    geo_data=grid,
    data=grid,
    columns=["hex_id", "demand_score"],
    key_on="feature.properties.hex_id",
    fill_color="YlGnBu",
    fill_opacity=0.55,
    line_opacity=0.1,
    legend_name="Demand score (population + commercial + fuel-station density)",
    name="Demand heatmap",
).add_to(m)

fg_existing = folium.FeatureGroup(name=f"Existing chargers ({len(existing)})")
for _, row in existing.iterrows():
    folium.CircleMarker(
        [row.geometry.y, row.geometry.x], radius=2, color="#888", fill=True, fill_opacity=0.6, weight=0,
    ).add_to(fg_existing)
fg_existing.add_to(m)

fg_chosen = folium.FeatureGroup(name=f"Proposed new sites, K=20 ({len(chosen)})")
for _, row in chosen.iterrows():
    folium.CircleMarker(
        [row.geometry.y, row.geometry.x], radius=7, color="#1F7A4D", fill=True, fill_color="#1F7A4D",
        fill_opacity=0.95, weight=2,
        tooltip=f"Demand score: {row['demand_score']:.2f} | Source: {row['source']}",
    ).add_to(fg_chosen)
fg_chosen.add_to(m)

title_html = """
<div style="position: fixed; top: 10px; left: 50px; z-index: 9999;
            background: white; padding: 8px 14px; border-radius: 4px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.3); font-family: sans-serif;">
  <div style="font-size:16px; font-weight:bold;">EV Charging Siting — Before / After (K=20)</div>
  <div style="font-size:11px; color:#555;">675 existing stations (Delhi Govt data) vs. 20 proposed new sites, solved via Maximal Covering Location</div>
</div>
"""
m.get_root().html.add_child(folium.Element(title_html))

legend_html = """
<div style="position: fixed; bottom: 30px; left: 10px; z-index: 9999;
            background: white; padding: 10px 14px; border-radius: 4px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.3); font-family: sans-serif; font-size: 12px; line-height:1.6;">
  <div style="font-weight:bold; margin-bottom:4px;">Legend</div>
  <div><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#888;margin-right:6px;"></span>Existing charger (grey)</div>
  <div><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#1F7A4D;margin-right:6px;"></span>Proposed new site (green)</div>
  <div style="margin-top:4px; color:#555;">Background = demand score (darker blue = higher demand)</div>
</div>
"""
m.get_root().html.add_child(folium.Element(legend_html))

folium.LayerControl(collapsed=False).add_to(m)
m.save("app_outputs/coverage_map.html")
print("saved app_outputs/coverage_map.html")
