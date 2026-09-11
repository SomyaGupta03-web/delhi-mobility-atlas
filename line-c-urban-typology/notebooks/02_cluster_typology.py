import geopandas as gpd
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

metrics = pd.read_csv("data/interim/ward_street_metrics.csv")
features = ["avg_degree", "streets_per_node", "circuity_avg", "orientation_entropy", "dead_end_ratio"]
X = StandardScaler().fit_transform(metrics[features])

km = KMeans(n_clusters=2, random_state=42, n_init=10)
metrics["form_cluster"] = km.fit_predict(X)
score = silhouette_score(X, metrics["form_cluster"])
print(f"silhouette score: {score:.3f}")

print("\ncluster sizes:\n", metrics["form_cluster"].value_counts())
print("\ncluster centers (mean of raw features):")
print(metrics.groupby("form_cluster")[features].mean())

wards = gpd.read_file("../line-a-accessibility/data/interim/wards_with_access.gpkg")
merged = wards.merge(metrics[["ward_id", "form_cluster"] + features], on="ward_id", how="left")

print("\nwalkability by form cluster:")
print(merged.groupby("form_cluster")[["tmin_health", "tmin_education", "tmin_market"]].mean())

merged.to_file("data/outputs/wards_with_form_cluster.gpkg", driver="GPKG")
print("\nsaved data/outputs/wards_with_form_cluster.gpkg")