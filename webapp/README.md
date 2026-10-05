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

The acquisition controls browse provenance only; maps continue to show their composite elevation surface. ALOS dates apply to whole tile scene lists, with municipality-specific scene footprints unverified. Copernicus XML supplies acquisition envelopes rather than every individual observation date. No date-specific elevation surfaces are generated from these timelines. DLR TanDEM-X Change Maps are linked as an additional candidate whose Gurugram coverage remains unchecked.

The time control represents each dataset's acquisition period: SRTM (February 2000), ALOS (2006–2011), and Copernicus (2011–2014 for the downloaded tiles). It is not an annual DEM series. Refer to the parent [data notes](../README.md) for source provenance, quality masks, vertical conversion, and flood-modelling limits.

### Dated elevation maps

Select ALOS or Copernicus, then choose **Dated elevation maps** in Map mode.
The date slider switches actual raster surfaces; Play dates cycles the loaded maps.
The difference map shows the selected date minus the earliest loaded date, using
only pixels valid in both maps. Click the elevation map for values across the
loaded dates. Product composite mode retains the original three-product comparison.

**No genuine dated ALOS or TanDEM-X elevation surfaces are supplied.** The 68 ALOS
observation dates and Copernicus acquisition ranges are metadata, not map frames.
The dated slider is disabled until data are loaded. For the Copernicus source group,
provide independently dated TanDEM-X-derived surfaces; do not relabel GLO-30 release
versions as repeat measurements.

Prepare single-band GeoTIFFs in metres with verified acquisition dates and EGM96
heights. The importer horizontally reprojects to the common municipal grid and masks
outside the boundary; it does not convert the vertical datum or denoise data.
From this repository root:

```sh
python3 -m pip install -r requirements.txt
python3 webapp/import_dated_dem.py /path/to/dated_dem.tif \
  --source alos --date 2010-04-20 --label 'ALOS dated surface' \
  --provenance 'Actual scene ID and acquisition evidence' --vertical-datum EGM96
```

The command illustrates the interface; use your actual acquisition date and provenance.
Repeat for additional dates. Default output updates `static/dated-maps.js` for offline
and server use. Alternatively use `--output /path/to/maps.json` and choose that JSON
with **Load prepared dated maps**. Loading replaces the current dated package in
memory; it sends no files to a server. Up to 24 frames per package and 150 MB per
browser import are supported. Maps may cover only part of the municipal area.

Run the app from the repository root with `python3 webapp/server.py`, or open
`webapp/index.html` directly. Dated data packages should be reviewed for acquisition
provenance, co-registration, datum consistency and uncertainty before interpreting
pixel differences as terrain change.
