import geopandas as gpd
import osmnx as ox

wards = gpd.read_file("data/interim/delhi_wards_utm43n.gpkg").to_crs(4326)
aoi_wgs84 = wards.union_all()

G_walk = ox.graph_from_polygon(aoi_wgs84, network_type="walk", simplify=True)
G_walk = ox.project_graph(G_walk, to_crs="EPSG:32643")
ox.save_graphml(G_walk, "data/interim/delhi_walk_network.graphml")

print(f"Walk network: {len(G_walk.nodes)} nodes, {len(G_walk.edges)} edges")