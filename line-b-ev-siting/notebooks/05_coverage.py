import pickle
import geopandas as gpd
import osmnx as ox
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

wards = gpd.read_file("data/interim/delhi_wards_utm43n.gpkg").to_crs(4326)
aoi_wgs84 = wards.union_all()

print("pulling drive network (this can take several minutes)...")
G = ox.graph_from_polygon(aoi_wgs84, network_type="drive", simplify=True)
G = ox.routing.add_edge_speeds(G)
G = ox.routing.add_edge_travel_times(G)
G = ox.project_graph(G, to_crs="EPSG:32643")
print(f"drive network: {len(G.nodes)} nodes, {len(G.edges)} edges")

with open("data/interim/delhi_drive_network.pkl", "wb") as f:
    pickle.dump(G, f)

nodes = list(G.nodes)
node_index = {n: i for i, n in enumerate(nodes)}
rows, cols, weights = [], [], []
for u, v, d in G.edges(data=True):
    rows.append(node_index[u]); cols.append(node_index[v])
    weights.append(d["travel_time"] / 60)  # seconds -> minutes
graph = csr_matrix((weights, (rows, cols)), shape=(len(nodes), len(nodes)))

chargers = gpd.read_file("data/interim/chargers_delhigov.gpkg")
nearest_ids = ox.distance.nearest_nodes(G, chargers.geometry.x.values, chargers.geometry.y.values)
source_idx = sorted(set(node_index[nid] for nid in nearest_ids))
dist = dijkstra(graph, directed=True, indices=source_idx, min_only=True)
dist = np.where(np.isinf(dist), np.nan, dist)
node_tmin = dict(zip(nodes, dist))

grid = gpd.read_file("data/interim/grid_with_demand.gpkg")
centroids = grid.geometry.centroid
nearest_grid_nodes = ox.distance.nearest_nodes(G, centroids.x.values, centroids.y.values)
grid["tmin_to_charger"] = [node_tmin[n] for n in nearest_grid_nodes]

grid.to_file("data/interim/grid_with_coverage.gpkg", driver="GPKG")
print(grid[["hex_id", "demand_score", "tmin_to_charger"]].describe())