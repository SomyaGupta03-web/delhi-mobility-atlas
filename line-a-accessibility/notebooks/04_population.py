import geopandas as gpd
import rasterstats as rs

wards = gpd.read_file("data/interim/wards_with_access.gpkg")

stats = rs.zonal_stats(
    wards.to_crs(4326),
    "../shared/data/raw/ind_ppp_2020_1km_Aggregated_UNadj.tif",
    stats=["sum"], geojson_out=False,
)
wards["population"] = [s["sum"] or 0 for s in stats]
wards["population_imputed"] = wards["population"] == 0

# 19 small central wards fall below the 1km grid's resolution and get 0 directly;
# impute them using city-average density * their own area, flagged for transparency
area_km2 = wards.geometry.area / 1e6
city_avg_density = wards.loc[~wards["population_imputed"], "population"].sum() / area_km2[~wards["population_imputed"]].sum()
wards.loc[wards["population_imputed"], "population"] = city_avg_density * area_km2[wards["population_imputed"]]

wards.to_file("data/interim/wards_with_population.gpkg", driver="GPKG")

print(f"total Delhi population estimate: {wards['population'].sum():,.0f}")
print(f"wards imputed: {wards['population_imputed'].sum()} of {len(wards)}")
print(wards[["ward_id", "ward_name", "population", "population_imputed"]].sort_values("population", ascending=False).head())