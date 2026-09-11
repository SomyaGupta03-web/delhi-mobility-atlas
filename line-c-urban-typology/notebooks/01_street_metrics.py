import pickle
import geopandas as gpd
import osmnx as ox
import pandas as pd
import numpy as np

LINE_A = "../line-a-accessibility/data/interim"

with open(f"{LINE_A}/delhi_walk_network_weighted.pkl", "rb") as f:
    G = pickle.load(f)

wards = gpd.read_file(f"{LINE_A}/wards_with_access.gpkg")

node_gdf = gpd.GeoDataFrame(
    {"osmid": list(G.nodes)},
    geometry=gpd.points_from_xy(
        [G.nodes[n]["x"] for n in G.nodes],
        [G.nodes[n]["y"] for n in G.nodes],
    ),
    crs=wards.crs,
)
joined = gpd.sjoin(node_gdf, wards[["ward_id", "geometry"]], predicate="within")
print(f"assigned {len(joined)} of {len(node_gdf)} nodes to wards")

G_wgs84 = ox.project_graph(G, to_crs="EPSG:4326")

records = []
for ward_id, group in joined.groupby("ward_id"):
    ward_nodes = list(group["osmid"])
    if len(ward_nodes) < 10:
        continue
    sub = G.subgraph(ward_nodes).copy()
    sub_wgs = G_wgs84.subgraph(ward_nodes).copy()

    n_nodes = sub.number_of_nodes()
    n_edges = sub.number_of_edges()
    if n_nodes == 0 or n_edges == 0:
        continue

    avg_degree = float(np.mean([d for _, d in sub.degree()]))
    streets_per_node = ox.stats.streets_per_node_avg(sub)

    try:
        circuity = ox.stats.circuity_avg(ox.convert.to_undirected(sub))
    except Exception:
        circuity = np.nan

    try:
        sub_wgs_u = ox.convert.to_undirected(sub_wgs)
        sub_wgs_u = ox.bearing.add_edge_bearings(sub_wgs_u)
        entropy = ox.bearing.orientation_entropy(sub_wgs_u)
    except Exception:
        entropy = np.nan

    dead_ends = sum(1 for _, d in sub.degree() if d <= 1)
    dead_end_ratio = dead_ends / n_nodes

    records.append({
        "ward_id": ward_id, "n_nodes": n_nodes, "n_edges": n_edges,
        "avg_degree": avg_degree, "streets_per_node": streets_per_node,
        "circuity_avg": circuity, "orientation_entropy": entropy,
        "dead_end_ratio": dead_end_ratio,
    })

metrics = pd.DataFrame(records)
metrics.to_csv("data/interim/ward_street_metrics.csv", index=False)
print(metrics.describe())
print(f"\ncomputed metrics for {len(metrics)} of {len(wards)} wards")