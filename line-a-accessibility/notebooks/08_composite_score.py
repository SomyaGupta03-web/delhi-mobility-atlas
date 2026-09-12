import geopandas as gpd
from scipy.stats import rankdata

wards = gpd.read_file("data/interim/wards_with_population.gpkg")

for col in ["tmin_health", "tmin_education", "tmin_market"]:
    valid = wards[col].notna()
    wards.loc[valid, f"pct_{col}"] = rankdata(wards.loc[valid, col]) / valid.sum()

pct_cols = [c for c in wards.columns if c.startswith("pct_tmin")]
wards["access_gap"] = wards[pct_cols].mean(axis=1)
wards["pop_density"] = wards["population"] / (wards.geometry.area / 1e6)

wards["mobility_desert_score"] = (
    wards["access_gap"].rank(pct=True) * 0.7 +
    wards["pop_density"].rank(pct=True) * 0.3
) * 100

wards.to_file("data/outputs/wards_scored.gpkg", driver="GPKG")

print(wards[["ward_id", "ward_name", "mobility_desert_score"]]
      .sort_values("mobility_desert_score", ascending=False).head(10))