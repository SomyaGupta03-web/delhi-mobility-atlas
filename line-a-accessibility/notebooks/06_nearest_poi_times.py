import pickle
import geopandas as gpd
import osmnx as ox
import pandas as pd
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

with open("data/interim/delhi_walk_network_weighted.pkl", "rb") as f:
    G = pickle.load(f)

nodes = list(G.nodes)
node_index = {n: i for i, n in enumerate(nodes)}
n = len(nodes)

rows, cols, weights = [], [], []
for u, v, d in G.edges(data=True):
    rows.append(node_index[u]); cols.append(node_index[v]); weights.append(d["weight_min"])
graph = csr_matrix((weights, (rows, cols)), shape=(n, n))

pois = {
    "health": gpd.read_file("data/interim/pois_health.gpkg"),
    "education": gpd.read_file("data/interim/pois_education.gpkg"),
    "market": gpd.read_file("data/interim/pois_market.gpkg"),
}

out = pd.DataFrame({"osmid": nodes})
for label, gdf in pois.items():
    nearest_node_ids = ox.distance.nearest_nodes(G, gdf.geometry.x.values, gdf.geometry.y.values)
    source_idx = sorted(set(node_index[nid] for nid in nearest_node_ids))
    dist = dijkstra(graph, directed=True, indices=source_idx, min_only=True, limit=30)
    dist = np.where(np.isinf(dist), np.nan, dist)
    out[f"tmin_{label}"] = dist

out.to_csv("data/interim/node_travel_times.csv", index=False)
print(out.describe())