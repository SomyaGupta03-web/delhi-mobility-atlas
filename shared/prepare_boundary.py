from pathlib import Path
import geopandas as gpd

ROOT = Path(__file__).resolve().parent.parent
RAW_WARDS = ROOT / "shared" / "data" / "raw" / "delhi_wards.geojson"
RAW_BOUNDARY = ROOT / "shared" / "data" / "raw" / "delhi_boundary.geojson"
UTM43N = "EPSG:32643"


def prepare_wards():
    wards = gpd.read_file(RAW_WARDS)
    wards["ward_id"] = wards["Ward_No"].astype(str).str.strip()
    dupes = (
        wards["ward_id"].isna()
        | (wards["ward_id"].astype(str).str.lower() == "nan")
        | (wards["ward_id"] == "")
        | wards["ward_id"].duplicated(keep=False)
    )
    wards.loc[dupes, "ward_id"] = "W" + wards.loc[dupes].index.astype(str)
    wards = wards.rename(columns={"Ward_Name": "ward_name"})[["ward_id", "ward_name", "geometry"]]
    wards = wards.set_crs("EPSG:4326", allow_override=True).to_crs(UTM43N)
    wards["geometry"] = wards.geometry.buffer(0)
    return wards


def prepare_boundary():
    boundary = gpd.read_file(RAW_BOUNDARY)
    return boundary.set_crs("EPSG:4326", allow_override=True).to_crs(UTM43N)


def main():
    wards = prepare_wards()
    boundary = prepare_boundary()
    print(f"wards: {len(wards)} features, CRS={wards.crs}")
    print(f"total ward area: {wards.geometry.area.sum() / 1e6:,.1f} km^2")

    for line_dir in ["line-a-accessibility", "line-b-ev-siting"]:
        out_dir = ROOT / line_dir / "data" / "interim"
        out_dir.mkdir(parents=True, exist_ok=True)
        wards.to_file(out_dir / "delhi_wards_utm43n.gpkg", driver="GPKG")
        boundary.to_file(out_dir / "delhi_boundary_utm43n.gpkg", driver="GPKG")
        print(f"wrote {out_dir / 'delhi_wards_utm43n.gpkg'}")


if __name__ == "__main__":
    main()