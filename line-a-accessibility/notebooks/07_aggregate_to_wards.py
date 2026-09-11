import pickle
import geopandas as gpd
import pandas as pd

with open("data/interim/delhi_walk_network_weighted.pkl", "rb") as f:
    G = pickle.load(f)

times = pd.read_csv("data/interim/node_travel_times.csv")
node_pts = gpd.GeoDataFrame(
    times,
    geometry=gpd.points_from_xy(
        [G.nodes[n]["x"] for n in times["osmid"]],
        [G.nodes[n]["y"] for n in times["osmid"]],
    ),
    crs="EPSG:32643",
)

wards = gpd.read_file("data/interim/delhi_wards_utm43n.gpkg")
joined = gpd.sjoin(node_pts, wards[["ward_id", "geometry"]], predicate="within")

cols = ["tmin_health", "tmin_education", "tmin_market"]
ward_access = joined.groupby("ward_id")[cols].mean()
wards = wards.merge(ward_access, on="ward_id", how="left")
wards.to_file("data/interim/wards_with_access.gpkg", driver="GPKG")

print(wards[["ward_id", "ward_name"] + cols].sort_values("tmin_market", ascending=False).head(10))