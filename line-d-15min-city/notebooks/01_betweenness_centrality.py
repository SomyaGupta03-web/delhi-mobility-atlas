import pickle
import time
import networkx as nx
import pandas as pd
import geopandas as gpd

LINE_A = "../line-a-accessibility/data/interim"

with open(f"{LINE_A}/delhi_walk_network_weighted.pkl", "rb") as f:
    G = pickle.load(f)

Gs = nx.DiGraph(G)  # collapse parallel edges (MultiDiGraph -> DiGraph) for centrality
print(f"graph: {Gs.number_of_nodes()} nodes, {Gs.number_of_edges()} edges")

t0 = time.time()
bc = nx.betweenness_centrality(Gs, k=500, weight="weight_min", seed=42, normalized=True)
print(f"betweenness computed in {time.time()-t0:.0f}s")

bc_df = pd.DataFrame({"osmid": list(bc.keys()), "betweenness": list(bc.values())})
bc_df.to_csv("data/interim/node_betweenness.csv", index=False)

wards = gpd.read_file(f"{LINE_A}/wards_with_access.gpkg")
node_gdf = gpd.GeoDataFrame(
    bc_df,
    geometry=gpd.points_from_xy(
        [G.nodes[n]["x"] for n in bc_df["osmid"]],
        [G.nodes[n]["y"] for n in bc_df["osmid"]],
    ),
    crs=wards.crs,
)
joined = gpd.sjoin(node_gdf, wards[["ward_id", "geometry"]], predicate="within")
ward_bc = joined.groupby("ward_id")["betweenness"].agg(["mean", "max"]).rename(
    columns={"mean": "betweenness_mean", "max": "betweenness_max"})

merged = wards.merge(ward_bc, on="ward_id", how="left")
merged.to_file("data/outputs/wards_with_centrality.gpkg", driver="GPKG")

print(merged[["ward_id", "ward_name", "betweenness_mean", "betweenness_max", "tmin_market"]]
      .sort_values("betweenness_mean", ascending=False).head(10))