import geopandas as gpd
import folium

wards = gpd.read_file("data/outputs/wards_with_form_cluster.gpkg").to_crs(4326)

m = folium.Map(location=[28.61, 77.21], zoom_start=11, tiles="OpenStreetMap")

cluster_colors = {0: "#3454D1", 1: "#E07A1F"}  # 0 = more grid-like, 1 = more organic
cluster_labels = {0: "Grid-like (low entropy, few dead-ends)", 1: "Organic (high entropy, more dead-ends)"}

def style_fn(feature):
    c = feature["properties"].get("form_cluster")
    return {
        "fillColor": cluster_colors.get(c, "grey"),
        "color": "#333",
        "weight": 0.5,
        "fillOpacity": 0.6,
    }

folium.GeoJson(
    wards,
    name="Urban form cluster",
    style_function=style_fn,
    tooltip=folium.GeoJsonTooltip(
        fields=["ward_id", "ward_name", "form_cluster", "orientation_entropy", "circuity_avg", "dead_end_ratio", "tmin_market"],
        aliases=["Ward ID:", "Ward:", "Form cluster:", "Orientation entropy:", "Circuity:", "Dead-end ratio:", "Walk to market (min):"],
        localize=True,
    ),
).add_to(m)

title_html = """
<div style="position: fixed; top: 10px; left: 50px; z-index: 9999;
            background: white; padding: 8px 14px; border-radius: 4px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.3); font-family: sans-serif;">
  <div style="font-size:16px; font-weight:bold;">Delhi Street-Network Urban Form Clusters</div>
  <div style="font-size:11px; color:#555;">k=2 clusters from node2vec-alternative street-network metrics (orientation entropy, circuity, dead-end ratio, degree)</div>
</div>
"""
m.get_root().html.add_child(folium.Element(title_html))

legend_html = f"""
<div style="position: fixed; bottom: 30px; left: 10px; z-index: 9999;
            background: white; padding: 10px 14px; border-radius: 4px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.3); font-family: sans-serif; font-size: 12px; line-height:1.6;">
  <div style="font-weight:bold; margin-bottom:4px;">Legend</div>
  <div><span style="display:inline-block;width:12px;height:12px;background:{cluster_colors[0]};margin-right:6px;"></span>{cluster_labels[0]}</div>
  <div><span style="display:inline-block;width:12px;height:12px;background:{cluster_colors[1]};margin-right:6px;"></span>{cluster_labels[1]}</div>
  <div style="margin-top:6px; color:#555;">Cluster 0 (grid): faster hospital/school access.<br>Cluster 1 (organic): faster market access.</div>
</div>
"""
m.get_root().html.add_child(folium.Element(legend_html))

folium.LayerControl(collapsed=False).add_to(m)
m.save("app_outputs/form_cluster_map.html")
print("saved app_outputs/form_cluster_map.html")
