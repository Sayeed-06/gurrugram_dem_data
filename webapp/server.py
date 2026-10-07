"""Zero-dependency local server for the DEM explorer.

Run from the repository root: python3 gurugram_dem/webapp/server.py
Then open http://127.0.0.1:8787.
"""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import argparse
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import json

import rasterio
from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "webapp"
PRODUCTS = {
    "srtm": "SRTM_2000_EGM96_city_30m.tif",
    "alos": "ALOS_2006_2011_EGM96_city_30m.tif",
    "copernicus": "Copernicus_2011_2014_primary_EGM96_city_30m.tif",
}
TO_WGS84 = Transformer.from_crs("EPSG:32643", "EPSG:4326", always_xy=True)


class ExplorerHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/static/dated-maps.js':
            local = ROOT / 'private_data/dated-maps.js'
            if local.exists():
                body = local.read_bytes()
                self.send_response(200)
                self.send_header('Content-Type', 'text/javascript; charset=utf-8')
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
        if parsed.path == "/api/elevation":
            return self.point_elevation(parse_qs(parsed.query))
        if parsed.path == "/README.md":
            body = (ROOT / "README.md").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/markdown; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        return super().do_GET()

    def point_elevation(self, query):
        try:
            easting = float(query["easting"][0])
            northing = float(query["northing"][0])
            result = {"easting_m": easting, "northing_m": northing}
            result["longitude"], result["latitude"] = TO_WGS84.transform(easting, northing)
            for key, filename in PRODUCTS.items():
                with rasterio.open(ROOT / "processed" / filename) as src:
                    value = next(src.sample([(easting, northing)], masked=True))[0]
                    result[key] = None if value is None or getattr(value, "mask", False) else round(float(value), 2)
            body = json.dumps(result).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (KeyError, ValueError, IndexError):
            self.send_error(400, "Use numeric easting and northing query parameters.")

    def log_message(self, fmt, *args):
        print("[DEM explorer] " + fmt % args)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Serve the local Gurugram DEM Explorer.")
    parser.add_argument("--port", type=int, default=8787, help="local port (default: 8787)")
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), ExplorerHandler)
    print(f"Gurugram DEM Explorer: http://127.0.0.1:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
