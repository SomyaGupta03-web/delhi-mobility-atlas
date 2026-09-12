import geopandas as gpd
import numpy as np
from scipy.spatial import cKDTree
import pulp

grid = gpd.read_file("data/interim/grid_with_coverage.gpkg").dropna(subset=["tmin_to_charger"]).reset_index(drop=True)
sites = gpd.read_file("data/interim/candidate_sites.gpkg").reset_index(drop=True)

K, RADIUS_M = 20, 3000

demand_coords = np.array([(pt.x, pt.y) for pt in grid.geometry.centroid])
site_coords = np.array([(pt.x, pt.y) for pt in sites.geometry])
tree = cKDTree(site_coords)
covering = tree.query_ball_point(demand_coords, r=RADIUS_M)
print(f"{sum(1 for c in covering if len(c) > 0)} of {len(grid)} demand cells have >=1 candidate within {RADIUS_M}m")

prob = pulp.LpProblem("MCLP", pulp.LpMaximize)
x = {j: pulp.LpVariable(f"site_{j}", cat="Binary") for j in range(len(sites))}
y = {i: pulp.LpVariable(f"cover_{i}", cat="Binary") for i in range(len(grid))}

prob += pulp.lpSum(grid.loc[i, "demand_score"] * y[i] for i in range(len(grid)))
prob += pulp.lpSum(x.values()) <= K
for i in range(len(grid)):
    if covering[i]:
        prob += y[i] <= pulp.lpSum(x[j] for j in covering[i])
    else:
        prob += y[i] == 0

status = prob.solve(pulp.PULP_CBC_CMD(msg=0))
print("solve status:", pulp.LpStatus[status])

sites["chosen"] = [x[j].value() == 1 for j in range(len(sites))]
chosen_sites = sites[sites["chosen"]]
chosen_sites.to_file("data/outputs/chosen_sites_k20.gpkg", driver="GPKG")

print(f"\nchosen {len(chosen_sites)} sites, covering {pulp.value(prob.objective):.1f} demand-weighted cells")
print(chosen_sites[["hex_id", "demand_score", "source"]])