# Gurugram DEM Explorer

A local interactive web app for the compiled Gurugram municipal DEM package. It runs without installing a web framework or using a remote service.

## Run it

From the repository root:

```sh
python3 gurugram_dem/webapp/server.py
```

Open [http://127.0.0.1:8787](http://127.0.0.1:8787) in a browser. Stop the server with `Ctrl+C`.

You may also open `index.html` directly as a local file. In that mode, the point inspector uses the compact, bundled read-only elevation lookup. It shows UTM coordinates; the local server adds latitude and longitude conversion.

The app requires the adjacent `../processed/` GeoTIFF directory only when it is served locally. `rasterio` and `pyproj` are the only Python dependencies needed to run the local server. The derived browser layers and direct-file elevation lookup are stored under `static/` and can be regenerated from the compiled GeoTIFFs:

```sh
python3 gurugram_dem/webapp/generate_assets.py
```

## Features

- Choose SRTM, ALOS AW3D30, or Copernicus GLO-30 with buttons or the time slider.
- Pan and zoom the municipal elevation map, and change layer opacity.
- Click a valid municipal pixel to get the three EGM96 elevations and a point comparison chart.
- Use the consistent 200–325 m colour scale to compare elevations visually.
- Explore separate acquisition timelines beneath the maps. ALOS has 68 distinct source-tile dates, with tile filtering, a date slider, scene IDs, path/frame and stereo modes. Copernicus has two tile acquisition ranges with 17 and 22 contributing acquisitions. Download either filtered timeline as CSV.

The acquisition controls browse provenance only; maps continue to show their composite elevation surface. ALOS dates apply to whole tile scene lists, with municipality-specific scene footprints unverified. Copernicus XML supplies acquisition envelopes rather than every individual observation date. No date-specific elevation surfaces are generated from these timelines.

The time control represents each dataset's acquisition period: SRTM (February 2000), ALOS (2006–2011), and Copernicus (2011–2014 for the downloaded tiles). It is not an annual DEM series. Refer to the parent [data notes](../README.md) for source provenance, quality masks, vertical conversion, and flood-modelling limits.

### Public presentation

TanDEM-X and the unloaded dated-map mode have been removed from the app.
Sensor buttons and the comparison slider always restore the original composite
map. The supplied point lookup works on static hosting as well as locally.

GitHub Pages can serve this app for free from the public repository's **main**
branch and **/(root)** folder. The root redirects to `webapp/`. See
[public demo notes](../PUBLIC_DEMO.md). No private TanDEM-X data are included.
