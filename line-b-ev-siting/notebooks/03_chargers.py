import geopandas as gpd
import osmnx as ox

wards = gpd.read_file("data/interim/delhi_wards_utm43n.gpkg").to_crs(4326)
aoi_wgs84 = wards.union_all()

chargers = ox.features_from_polygon(aoi_wgs84, {"amenity": "charging_station"})
chargers = chargers[chargers.geometry.type.isin(["Point", "Polygon"])].to_crs(32643)
chargers["geometry"] = chargers.geometry.centroid
chargers = chargers[["geometry"]].reset_index(drop=True)
chargers.to_file("data/interim/chargers.gpkg", driver="GPKG")

print(f"found {len(chargers)} existing charging stations")