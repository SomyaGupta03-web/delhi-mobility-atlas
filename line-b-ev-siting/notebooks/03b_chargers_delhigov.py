"""
Real charging-station locations from Delhi Govt's public EV Finder portal
(ev.delhi.gov.in/charging_station), extracted via browser automation since
the ~900 station records are embedded in the page's JS, not a REST API.
The 3 batch JSON files in data/raw/ are the raw extraction; this script
cleans and clips them to Delhi's AOI.

Cross-check finding: OSM's `amenity=charging_station` tag only found 171
stations in the same area (see 03_chargers.py) -- the government's own
portal lists far more, confirming the original guide's caveat that OSM
badly under-counts India's charging networks.
"""
import json

import geopandas as gpd
import pandas as pd

RAW = "data/raw"
records = []
for i in [1, 2, 3]:
    with open(f"{RAW}/chargers_batch{i}.json", encoding="utf-8") as f:
        records.extend(json.load(f))

df = pd.DataFrame(records)
print(f"raw records: {len(df)}")

df = df.dropna(subset=["lat", "lng"])
df = df.drop_duplicates(subset=["lat", "lng"])
print(f"after dropping unmapped/duplicate rows: {len(df)}")

gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df["lng"], df["lat"]), crs=4326)

wards = gpd.read_file("data/interim/delhi_wards_utm43n.gpkg").to_crs(4326)
aoi = wards.union_all().buffer(0.02)  # ~2km lenient buffer for boundary geocoding slop
clipped = gdf[gdf.within(aoi)].to_crs(32643)
print(f"within Delhi AOI: {len(clipped)}")

clipped[["id", "address", "vendor", "charger_type", "no_of_chargers", "geometry"]].to_file(
    "data/interim/chargers_delhigov.gpkg", driver="GPKG"
)
print("saved data/interim/chargers_delhigov.gpkg")
