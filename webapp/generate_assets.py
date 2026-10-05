"""Generate browser-friendly visual layers from the compiled DEM GeoTIFFs."""
from pathlib import Path
import base64
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from generate_timeline import build_timeline

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "webapp" / "static" / "layers"
OUT.mkdir(parents=True, exist_ok=True)
PRODUCTS = {
    "srtm": ("SRTM", "February 2000", "SRTM_2000_EGM96_city_30m.tif"),
    "alos": ("ALOS AW3D30", "2006–2011", "ALOS_2006_2011_EGM96_city_30m.tif"),
    "copernicus": ("Copernicus GLO-30", "2011–2014", "Copernicus_2011_2014_primary_EGM96_city_30m.tif"),
}
DIFFERENCES = {
    "alos_minus_srtm": ("alos", "srtm"),
    "copernicus_minus_srtm": ("copernicus", "srtm"),
    "copernicus_minus_alos": ("copernicus", "alos"),
}


def save_layer(key: str, raster_name: str) -> dict:
    with rasterio.open(ROOT / "processed" / raster_name) as src:
        data = src.read(1, masked=True)
        bounds = list(src.bounds)
        transform = list(src.transform)
        shape = list(src.shape)
    cmap = plt.get_cmap("terrain").copy()
    rgba = cmap(np.clip((data.filled(200) - 200) / 125, 0, 1), bytes=True)
    rgba[data.mask, 3] = 0
    plt.imsave(OUT / f"{key}.png", rgba)
    return {"bounds_utm43n": bounds, "transform": transform, "shape": shape}


def read_dem(key: str) -> np.ma.MaskedArray:
    with rasterio.open(ROOT / "processed" / PRODUCTS[key][2]) as src:
        return src.read(1, masked=True)


def write_embedded_elevations(metadata: dict) -> None:
    """Write a compact lookup so the point inspector also works from file://."""
    grids = [read_dem(key) for key in PRODUCTS]
    height, width = grids[0].shape
    packed = []
    for grid in grids:
        values = np.rint(grid.filled(-3276.8) * 10).astype("<i2")
        packed.append(values)
    binary = np.stack(packed).tobytes(order="C")
    encoded = base64.b64encode(binary).decode("ascii")
    payload = {
        "width": width,
        "height": height,
        "nodata_decimetres": -32768,
        "band_order": list(PRODUCTS),
        "data_base64": encoded,
    }
    (ROOT / "webapp" / "static" / "elevations.js").write_text(
        "window.DEM_EMBEDDED_ELEVATIONS = " + json.dumps(payload, separators=(",", ":")) + ";\n"
    )


def save_difference(key: str, active: str, baseline: str) -> dict:
    difference = read_dem(active) - read_dem(baseline)
    cmap = plt.get_cmap("RdBu_r").copy()
    rgba = cmap(np.clip((difference.filled(0) + 20) / 40, 0, 1), bytes=True)
    rgba[difference.mask, 3] = 0
    plt.imsave(OUT / f"{key}.png", rgba)
    valid = difference.compressed()
    return {
        "active": active,
        "baseline": baseline,
        "min_m": float(valid.min()),
        "median_m": float(np.median(valid)),
        "max_m": float(valid.max()),
    }


if __name__ == "__main__":
    metadata = {"products": {}, "color_scale": {"min_m": 200, "max_m": 325}}
    for key, (label, period, raster) in PRODUCTS.items():
        metadata["products"][key] = {"label": label, "period": period, "raster": raster, **save_layer(key, raster)}
    metadata["differences"] = {
        key: save_difference(key, active, baseline)
        for key, (active, baseline) in DIFFERENCES.items()
    }
    metadata["difference_color_scale"] = {"min_m": -20, "zero_m": 0, "max_m": 20}
    metadata["municipal_area_km2"] = 298.274
    metadata["crs"] = "EPSG:32643"
    (ROOT / "webapp" / "static" / "metadata.json").write_text(json.dumps(metadata, indent=2))
    (ROOT / "webapp" / "static" / "metadata.js").write_text(
        "window.DEM_EXPLORER_METADATA = " + json.dumps(metadata, separators=(",", ":")) + ";\n"
    )
    write_embedded_elevations(metadata)
    timeline = build_timeline()
    (ROOT / 'webapp/static/timeline.json').write_text(json.dumps(timeline, indent=2))
    (ROOT / 'webapp/static/timeline.js').write_text('window.DEM_ACQUISITION_TIMELINE = ' + json.dumps(timeline) + ';\n')
