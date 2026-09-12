import matplotlib
matplotlib.use("Agg")
import geopandas as gpd
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.spatial import cKDTree
import pulp

grid = gpd.read_file("data/interim/grid_with_coverage.gpkg").dropna(subset=["tmin_to_charger"]).reset_index(drop=True)
sites = gpd.read_file("data/interim/candidate_sites.gpkg").reset_index(drop=True)

demand_coords = np.array([(pt.x, pt.y) for pt in grid.geometry.centroid])
site_coords = np.array([(pt.x, pt.y) for pt in sites.geometry])
total_demand = grid["demand_score"].sum()

def solve_mclp(K, radius_m):
    tree = cKDTree(site_coords)
    covering = tree.query_ball_point(demand_coords, r=radius_m)
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
    prob.solve(pulp.PULP_CBC_CMD(msg=0))
    return pulp.value(prob.objective)

results = []
for radius_m in [1500, 3000, 5000]:
    for K in [10, 20, 40]:
        covered = solve_mclp(K, radius_m)
        results.append({"K": K, "radius_m": radius_m, "covered_demand": covered, "pct_of_total_demand": covered / total_demand * 100})
        print(f"K={K}, radius={radius_m}m -> covered {covered:.1f} ({covered/total_demand*100:.1f}% of total demand)")

df = pd.DataFrame(results)
df.to_csv("data/outputs/sensitivity_results.csv", index=False)

fig, ax = plt.subplots(figsize=(7, 5))
for radius_m, group in df.groupby("radius_m"):
    ax.plot(group["K"], group["pct_of_total_demand"], marker="o", label=f"{radius_m}m radius")
ax.set_xlabel("Number of new charging sites (K)")
ax.set_ylabel("% of total demand-weighted cells covered")
ax.set_title("EV Charging Siting: Budget vs. Coverage")
ax.legend()
fig.tight_layout()
fig.savefig("app_outputs/sensitivity_curve.png", dpi=150)
print("\nsaved app_outputs/sensitivity_curve.png")