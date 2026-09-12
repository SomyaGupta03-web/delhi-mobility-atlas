import geopandas as gpd

grid = gpd.read_file("data/interim/grid_with_coverage.gpkg")
grid = grid.dropna(subset=["tmin_to_charger"])

grid["priority"] = grid["demand_score"] * (grid["tmin_to_charger"] / grid["tmin_to_charger"].max())

candidates_cells = grid[grid["tmin_to_charger"] > 10].sort_values("priority", ascending=False)
print(f"{len(candidates_cells)} cells are >10 min from the nearest charger")

candidates_cells.to_file("data/interim/candidate_cells.gpkg", driver="GPKG")
print(candidates_cells[["hex_id", "demand_score", "tmin_to_charger", "priority"]].head(10))