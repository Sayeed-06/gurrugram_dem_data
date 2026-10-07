# Gurugram DEM demonstration

The hosted app runs entirely in the browser and contains SRTM, ALOS AW3D30 and
Copernicus GLO-30. TanDEM-X has been removed from the app. No licensed TanDEM-X
rasters or local data packages are deployed.

## What to show

- Choose a DEM using its button or the three-product comparison slider.
- Compare elevation and pixel differences against SRTM or ALOS.
- Click within the city to inspect the three EGM96 elevation values.
- Browse ALOS source observation dates and Copernicus acquisition ranges below
  the maps; export the observation lists as CSV.

Each product is a composite elevation surface. The detailed observation slider
browses acquisition metadata and does not change the composite map. These products
are not annual DEM observations. Differences may reflect buildings, vegetation,
processing and datum uncertainty rather than verified terrain change. The layers
are inputs for drainage screening, not a calibrated flood model.

## Hosting for free

Use GitHub repository **Settings → Pages → Deploy from a branch → main → /(root)**.
The root redirects to `webapp/`. GitHub Pages is free for public repositories.
The embedded read-only elevation lookup lets the point inspector work without a
Python server, API key, paid hosting or a custom domain.

Site address after deployment:
https://sayeed-06.github.io/gurrugram_dem_data/

## Credits

SRTM: NASA/JPL-Caltech. ALOS World 3D AW3D30: JAXA. Copernicus DEM GLO-30:
Copernicus programme. See [compilation notes](README.md) for exact source
attributions, common-grid and EGM96 conversion, acquisition windows, quality
masks and municipal boundary details.
