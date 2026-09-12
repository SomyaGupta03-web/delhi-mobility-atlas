import pickle
import geopandas as gpd
import osmnx as ox

candidates_cells = gpd.read_file("data/interim/candidate_cells.gpkg")
fuel = gpd.read_file("data/interim/pois_fuel.gpkg") if False else None

# re-pull fuel station geometries from the same source 04 used (kept separately for reuse)
wards = gpd.read_file("data/interim/delhi_wards_utm43n.gpkg").to_crs(4326)
aoi_wgs84 = wards.union_all()
fuel = ox.features_from_polygon(aoi_wgs84, {"amenity": "fuel"})
fuel = fuel[fuel.geometry.type.isin(["Point", "Polygon"])].to_crs(32643)
fuel["geometry"] = fuel.geometry.centroid

with open("data/interim/delhi_drive_network.pkl", "rb") as f:
    G = pickle.load(f)

sites = []
for _, cell in candidates_cells.iterrows():
    in_cell_fuel = fuel[fuel.within(cell.geometry)]
    if len(in_cell_fuel) > 0:
        geom = in_cell_fuel.iloc[0].geometry
        source = "fuel_station"
    else:
        centroid = cell.geometry.centroid
        node_id = ox.distance.nearest_nodes(G, centroid.x, centroid.y)
        geom = __import__("shapely.geometry", fromlist=["Point"]).Point(G.nodes[node_id]["x"], G.nodes[node_id]["y"])
        source = "road_node"
    sites.append({"hex_id": cell["hex_id"], "demand_score": cell["demand_score"],
                  "priority": cell["priority"], "source": source, "geometry": geom})

sites_gdf = gpd.GeoDataFrame(sites, crs=32643)
sites_gdf.to_file("data/interim/candidate_sites.gpkg", driver="GPKG")
print(sites_gdf["source"].value_counts())
print(f"saved {len(sites_gdf)} candidate sites")