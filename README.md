# Delhi Mobility Atlas

Portfolio-scale spatial analytics on Delhi NCT — real street-network routing,
population data, and graph theory applied to urban mobility and city form.
One repo, one shared Python environment, one Delhi ward boundary (290 wards).

## Lines

### Line A — Transit Accessibility Index ("Mobility Desert Score")
Walk time (real street-network routing, not straight-line) to the nearest
hospital, school, and market, combined with population density into a 0-100
score per ward.

**Finding:** the worst-scoring wards — Dharampura, Khajoori Khas, Jiwanpur,
Gokalpur, Saboli, Gandhi Nagar, Mustafabad, Bhajanpura, Harsh Vihar, Karawal
Nagar West — cluster almost entirely in **Northeast Delhi**, a part of the
city independently known to be underserved. Market access is the weakest
category citywide: ~31% of the walkable street network has no market within
a 30-minute walk.

Map: [`app_outputs/preview_map.html`](line-a-accessibility/app_outputs/preview_map.html)
Scored data: [`data/outputs/wards_scored.gpkg`](line-a-accessibility/data/outputs/wards_scored.gpkg)

### Line B — EV Charging Siting Model
Demand-weighted coverage gap analysis + a Maximal Covering Location solve for
where K new EV chargers should go. *(Scaffolded, not yet built.)*

### Line C — Street-Network Embeddings for Urban Typology
Graph-theoretic street-network metrics (orientation entropy, circuity,
dead-end ratio, degree — a node2vec alternative, since `node2vec`'s `gensim`
dependency couldn't build on this machine) clustered into urban form types
via KMeans (k=2, data-driven via silhouette score).

**Finding:** the two clusters map onto a real, spatially coherent pattern —
**organic street form dominates central/south Delhi** (the historic core),
while **grid-like form rings the periphery** (newer planned colonies). Grid
wards have faster hospital/school access; organic wards have marginally
faster market access.

Map: [`app_outputs/form_cluster_map.html`](line-c-urban-typology/app_outputs/form_cluster_map.html)

### Line D — 15-Minute-City Scorecard via Network Centrality
Betweenness centrality (500-source sampling approximation — exact centrality
on a 228K-node graph is computationally infeasible) over the walk network,
finding structural chokepoints independent of raw distance.

**Finding:** central/old-Delhi wards (Malkaganj, Kashmere Gate, Sangam Park)
are the biggest structural chokepoints — Kashmere Gate is historically the
walled city's northern gate and remains a major transit hub today. 14 wards
are *both* major chokepoints *and* poorly served (e.g. Baljit Nagar, Gandhi
Nagar) — the highest-priority fix targets, since improving them improves
flow for everyone routed through them, not just residents.

Map: [`app_outputs/centrality_map.html`](line-d-15min-city/app_outputs/centrality_map.html)

### Line E — Satellite Segmentation for Informal Settlements *(planned)*
### Line F — GNN-Based Transit Demand Prediction *(planned, data availability uncertain)*

## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # .venv\Scripts\Activate.ps1 on Windows
pip install -r requirements.txt
python shared/prepare_boundary.py
```

Ward boundaries: [datameet/Municipal_Spatial_Data](https://github.com/datameet/Municipal_Spatial_Data/tree/master/Delhi) (290 wards).
Population: [WorldPop India, 1km UN-adjusted](https://data.worldpop.org/GIS/Population/Global_2000_2020_1km_UNadj/2020/IND/ind_ppp_2020_1km_Aggregated_UNadj.tif) — used the 1km product (18MB) rather than the 100m one (1.65GB); still validated against Delhi's real ~19.4M population.
Street network + POIs: OpenStreetMap via OSMnx (pulled live, no download needed).

`pandana` (from the original build guide) doesn't have a prebuilt Windows
wheel and needs a C++ compiler this machine doesn't have — swapped for
`scipy.sparse.csgraph.dijkstra` for nearest-POI travel times. Same reasoning
for `node2vec`/`gensim` in Line C, swapped for direct graph-theoretic metrics.

## Repo layout

```
delhi-mobility-atlas/
├── shared/                      # boundary prep, shared across all lines
├── line-a-accessibility/
├── line-b-ev-siting/
├── line-c-urban-typology/
├── line-d-15min-city/
├── requirements.txt
└── README.md
```
