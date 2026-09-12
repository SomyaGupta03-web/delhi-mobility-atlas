import geopandas as gpd
import osmnx as ox
import rasterstats as rs

grid = gpd.read_file("data/interim/demand_grid.gpkg")
wards = gpd.read_file("data/interim/delhi_wards_utm43n.gpkg").to_crs(4326)
aoi_wgs84 = wards.union_all()

# ---- Pull commercial POIs and fuel stations ----
commercial = ox.features_from_polygon(aoi_wgs84, {"shop": True})
commercial = commercial[commercial.geometry.type.isin(["Point", "Polygon"])].to_crs(32643)
commercial["geometry"] = commercial.geometry.centroid
print(f"commercial POIs: {len(commercial)}")

fuel = ox.features_from_polygon(aoi_wgs84, {"amenity": "fuel"})
fuel = fuel[fuel.geometry.type.isin(["Point", "Polygon"])].to_crs(32643)
fuel["geometry"] = fuel.geometry.centroid
print(f"fuel stations: {len(fuel)}")

# ---- Population per cell (with small-cell imputation, same fix as Line A) ----
stats = rs.zonal_stats(grid.to_crs(4326), "../shared/data/raw/ind_ppp_2020_1km_Aggregated_UNadj.tif", stats=["sum"], geojson_out=False)
grid["pop"] = [s["sum"] or 0 for s in stats]
grid["pop_imputed"] = grid["pop"] == 0
area_km2 = grid.geometry.area / 1e6
city_avg_density = grid.loc[~grid["pop_imputed"], "pop"].sum() / area_km2[~grid["pop_imputed"]].sum()
grid.loc[grid["pop_imputed"], "pop"] = city_avg_density * area_km2[grid["pop_imputed"]]

# ---- Count POIs per cell ----
def count_points_in_grid(grid, points, colname):
    joined = gpd.sjoin(points[["geometry"]], grid[["hex_id", "geometry"]], predicate="within")
    counts = joined.groupby("hex_id").size()
    grid[colname] = grid["hex_id"].map(counts).fillna(0)

count_points_in_grid(grid, commercial, "commercial_poi")
count_points_in_grid(grid, fuel, "fuel_stations")

# ---- Demand score ----
grid["demand_score"] = (
    grid["pop"].rank(pct=True) * 0.40 +
    grid["commercial_poi"].rank(pct=True) * 0.35 +
    grid["fuel_stations"].rank(pct=True) * 0.25
)

grid.to_file("data/interim/grid_with_demand.gpkg", driver="GPKG")
print(f"\nimputed {grid['pop_imputed'].sum()} of {len(grid)} cells")
print(grid[["hex_id", "pop", "commercial_poi", "fuel_stations", "demand_score"]].sort_values("demand_score", ascending=False).head(10))