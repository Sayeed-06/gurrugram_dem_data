# Gurugram municipal DEM compilation

Prepared 27 September 2026 for flood and drainage modelling.

Three DEMs have been downloaded, mosaicked, projected onto the same 30 m grid, and converted to a common EGM96 vertical reference. The delivery includes municipal extracts, a surrounding processing extent, source quality flags, a three-band stack and a cell-level elevation table. These are unconditioned elevation inputs, not a completed or calibrated flood model.

## Web app

Open `webapp/index.html` directly, or install `requirements.txt` and run
`python3 webapp/server.py`, then visit http://127.0.0.1:8787/.

The app shows SRTM, ALOS AW3D30 and Copernicus GLO-30 with map switching,
pixel differences, point inspection and separate acquisition-date history.
TanDEM-X has been removed from the app. The detailed acquisition sliders browse
metadata; the three supplied maps remain composite elevation surfaces.

For a free hosted demonstration, use GitHub Pages from **main / (root)**.
The root page redirects to `webapp/`. See [presentation and deployment notes](PUBLIC_DEMO.md).

Raw download files are excluded from Git; download provenance and compiled
municipal products are included. Synthetic validation maps are not included.

## Start here

- `processed/DEM_three_epoch_stack_EGM96_city_30m.tif`: three bands, ordered SRTM, ALOS, Copernicus.
- `processed/*_EGM96_city_30m.tif`: individual municipal DEMs, ready to load into QGIS or other GIS software.
- `processed/*_EGM96_buffer_30m.tif`: rectangular processing domain enclosing the municipal polygon plus a 5 km margin. Use these rather than city-clipped rasters when beginning drainage analysis. The margin is provisional; it is not a delineated watershed.
- `municipal_elevation_cells.csv.gz`: 331,420 municipal grid cells, each with coordinates, all three elevations and source quality classes. Decompress the CSV to open it in a spreadsheet or statistical tool. Row and column indices are zero-based.
- `DEM_comparison.png`: consistent-scale map of all three DEMs.
- `metadata/source_inventory.csv`: source acquisition envelopes for each tile.
- `metadata/elevation_summary.csv`: municipal elevation statistics.
- `metadata/processing_report.json` and `metadata/validation.json`: grid, quality and verification results.
- `raw/`: downloaded source files, ALOS scene lists and geoid grids. Retained locally; excluded from the smaller delivery ZIP. Download URLs and SHA256 checksums are in `metadata/download_manifest.json`.

## What the dates mean

| DEM | Primary acquisition period in this compilation | Source and version | Native vertical reference |
|---|---|---|---|
| SRTM GL1 | February 2000 mission | OpenTopography SRTM GL1 GeoTIFF mirror | EGM96 |
| ALOS AW3D30 | 18 August 2006–21 April 2011 across the two source-tile scene lists | JAXA April 2024 download; metadata identifies gap-fill version 4.1 | EGM96 |
| Copernicus GLO-30 | 25 January 2011–3 March 2014 across the two tile acquisition envelopes | AWS COG snapshot; source XML tile version 01 | EGM2008 |

These are acquisition-period surfaces, not three observations at exact single dates, and not an annual time series. ALOS and Copernicus are mosaics assembled from multiple acquisitions; their primary periods overlap in 2011. Tile date envelopes do not identify the observation date of every city pixel. Release dates and processing dates are not observation dates. External gap filling can introduce elevations from other periods and other DEMs.

The Copernicus download is the archived public AWS COG snapshot documented by the retained XML, not a claim to the latest Copernicus release. Its two primary tile ranges are 2011-05-26 to 2012-12-23 for E076, and 2011-01-25 to 2014-03-03 for E077. This metadata is more informative here than the generic mission label 2011–2015.

## Boundary and grid

The boundary is the public `MCG_Boundary` layer from GMDA's `flood_survey_2` service. The retrieved polygon is valid and measures **298.274 km²** in UTM 43N. It is a municipal GIS snapshot, not the district boundary. The service does not establish its current legal notification date; verify that date before statutory reporting. The same polygon is applied to every DEM to prevent changing reporting area from affecting comparison. It does not reconstruct historical municipal limits.

- Horizontal CRS: WGS 84 / UTM zone 43N, EPSG:32643.
- Vertical reference: EGM96 orthometric height, metres; recorded in GeoTIFF tags and this documentation. The raster CRS itself describes the horizontal system.
- Resolution: 30 × 30 m; identical origin, extent and dimensions for all outputs.
- Grid: 1,125 columns × 1,109 rows; upper-left corner 684450 E, 3162870 N.
- Extent: 684450–718200 E; 3129600–3162870 N.
- Municipal mask: pixel-centre rule, 331,420 cells (298.278 km² rasterized area).
- NoData: -9999; all three municipal DEMs have 100% valid-cell coverage.
- Elevation resampling: bilinear after native-grid mosaicking. Quality classes: nearest neighbour.

Nominal source resolution is approximately one arc-second, not exactly 30 m square at Gurugram's latitude. Reprojection aligns sampling; it does not improve source detail or perform empirical terrain co-registration.

## Vertical conversion

SRTM and ALOS are retained in EGM96. Copernicus is converted using NGA geoid grids distributed by PROJ:

`H_EGM96 = H_EGM2008 + N_EGM2008 - N_EGM96`

The EGM2008 grid has 2.5 arc-minute spacing; EGM96 has 15 arc-minute spacing. Both are sampled bilinearly. This is a geoid-model conversion, not local benchmark calibration or a centimetre-accuracy claim. The city correction ranges from approximately **−0.199 to −0.027 m**, with a mean of **−0.108 m**. The correction raster and original EGM2008 Copernicus raster are retained. An independent PROJ vertical-grid pipeline checks the correction's sign and magnitude at a city reference point.

## Quality findings

| Source mask | Municipal cells on the common grid | Interpretation |
|---|---:|---|
| ALOS MSK = 48 | 1,198 (0.361%) | Copernicus gap fill; not independent ALOS observations |
| Copernicus FLM = 5 | 2,200 (0.664%) | SRTM30 gap fill |
| Copernicus FLM = 3 | 49 (0.015%) | ASTER gap fill |
| Copernicus WBM = 2 | 334 (0.101%) | Lake/water pixels |

These counts describe nearest-neighbour quality classes on the common grid. Bilinear elevation resampling can mix adjacent source classes, so these flags do not guarantee pure source provenance at interpolation boundaries. For temporal inference, exclude contaminated neighbourhoods, water and edited pixels as appropriate. SRTM source-pixel lineage masks are not included in this mirror download; do not assume every SRTM cell is an unfilled 2000 observation.

All raw surface values are preserved through the documented interpolation; no sinks have been filled, channels burned, buildings removed or empirical elevation biases fitted. In the municipal extract SRTM reaches approximately 174.8 m, versus minima of 207.7 m for ALOS and 206.4 m for Copernicus. Inspect that low SRTM tail before routing water; the difference alone does not identify which measurement is correct.

## How to use this for flood and drainage work

Treat the three DEMs as alternative terrain inputs in a sensitivity experiment. Keep rainfall, land cover, roughness, infiltration, drains and boundary conditions fixed when testing DEM choice. Do not interpret differing modelled flood areas as historical flood change unless all epoch-specific inputs and terrain quality have been established.

1. Confirm the municipal boundary and select a domain containing all upstream contributing catchments and downstream outlets. A city boundary and an arbitrary buffer can cut flow paths.
2. Compare elevations with survey benchmarks, drainage invert levels or a trusted local bare-earth terrain model. Check offsets, tile seams, outliers, water surfaces and road embankments. Choose the best-supported baseline; this compilation does not establish which DEM is most accurate locally.
3. Retain these unconditioned files. Create separate, documented hydrologically conditioned copies using verified drains, culverts and outlets. Distinguish spurious pits from real urban storage; indiscriminate sink filling can erase flood-prone depressions.
4. Derive flow direction, contributing area, slope and drainage networks on the full hydrologic domain, then clip reporting outputs to the municipality. Check networks against mapped drains and observed waterlogging locations.
5. Use the three terrain alternatives with the same model and report sensitivity plus validation against observed events. Flood depth or extent also needs rainfall/runoff, drainage capacity, hydraulic boundary conditions and surface roughness; a DEM alone cannot provide it.

At 30 m these surface models support regional screening. Buildings, trees, different radar responses and stereo reconstruction can affect elevations. Street-scale drainage, individual culverts and engineering flood depths generally need finer, surveyed bare-earth terrain and drainage information. The DEMs should not be subtracted and labelled subsidence or land uplift.

## Reproduce

Python dependencies: `requests`, `numpy`, `rasterio`, `shapely`, `pyproj`, `matplotlib`.

From the directory containing this folder, run:

```sh
python3 gurugram_dem/scripts/download.py
python3 gurugram_dem/scripts/process.py
python3 gurugram_dem/scripts/package.py
```

The original boundary snapshot is included. Its REST query and checksum are recorded in `metadata/boundary_provenance.json`. Re-fetching the same live service may produce a different boundary later. Downloaded files are cached; delete only the relevant cached file if deliberately refreshing a source, and preserve the original manifest for version comparison.

## Sources and attribution

- [GMDA municipal boundary service](https://onemapdepts.gmda.gov.in/server/rest/services/flood_survey_2/FeatureServer/5).
- [USGS SRTM product description](https://www.usgs.gov/centers/eros/science/usgs-eros-archive-digital-elevation-shuttle-radar-topography-mission-srtm).
- [OpenTopography authors' public COG access workflow](https://earthcube2021.github.io/ec21_book/notebooks/ec21_beckley_etal/OT_01_BulkAccessCOGs.html).
- [JAXA AW3D30 product](https://www.eorc.jaxa.jp/ALOS/en/aw3d30/) and [documented AW3D30 mask definitions](https://developers.google.com/earth-engine/datasets/catalog/JAXA_ALOS_AW3D30_V4_1). ALOS World 3D–30m is provided by JAXA. Retain the applicable JAXA terms with redistribution.
- [Copernicus DEM product description and licence](https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM) and [AWS distribution](https://registry.opendata.aws/copernicus-dem/).
- [PROJ datum grid distribution](https://cdn.proj.org/). NGA geoid grids are public-domain derivatives as stated in their embedded metadata.

Copernicus-derived outputs: produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved.

The organisations in charge of the Copernicus programme by law or by delegation do not incur any liability for any use of the Copernicus WorldDEM-30.

Validation covers raster coverage, matching grids, finite elevations and the geoid conversion check. It does not establish survey accuracy, hydraulic performance, current legal boundary validity or complete catchment coverage.
