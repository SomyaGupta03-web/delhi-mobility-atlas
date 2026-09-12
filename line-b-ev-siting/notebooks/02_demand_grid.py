import h3
import geopandas as gpd
from shapely.geometry import Polygon

boundary = gpd.read_file("data/interim/delhi_boundary_utm43n.gpkg").to_crs(4326)
poly = boundary.geometry.union_all()

exterior_lnglat = list(poly.exterior.coords)
outer_latlng = [(lat, lng) for lng, lat in exterior_lnglat]
h3shape = h3.LatLngPoly(outer_latlng)
cells = h3.polygon_to_cells(h3shape, res=8)

hex_polys = []
for h in cells:
    boundary_latlng = h3.cell_to_boundary(h)
    ring_lnglat = [(lng, lat) for lat, lng in boundary_latlng]
    hex_polys.append(Polygon(ring_lnglat))

grid = gpd.GeoDataFrame({"hex_id": list(cells)}, geometry=hex_polys, crs=4326).to_crs(32643)
grid.to_file("data/interim/demand_grid.gpkg", driver="GPKG")

print(f"built {len(grid)} hex cells, total area {grid.geometry.area.sum()/1e6:,.1f} km^2")