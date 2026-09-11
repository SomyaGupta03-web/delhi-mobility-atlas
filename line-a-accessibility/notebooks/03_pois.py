import geopandas as gpd
import osmnx as ox

wards = gpd.read_file("data/interim/delhi_wards_utm43n.gpkg").to_crs(4326)
aoi_wgs84 = wards.union_all()

tag_sets = {
    "health":    {"amenity": ["hospital", "clinic"]},
    "education": {"amenity": ["school", "college"]},
    "market":    {"shop": ["supermarket", "convenience"], "amenity": ["marketplace"]},
}

for label, tags in tag_sets.items():
    gdf = ox.features_from_polygon(aoi_wgs84, tags)
    gdf = gdf[gdf.geometry.type.isin(["Point", "Polygon"])].to_crs(32643)
    gdf["geometry"] = gdf.geometry.centroid
    gdf = gdf[["geometry"]].reset_index(drop=True)
    gdf.to_file(f"data/interim/pois_{label}.gpkg", driver="GPKG")
    print(f"{label}: {len(gdf)} points")