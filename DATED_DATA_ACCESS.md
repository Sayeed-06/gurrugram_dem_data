# Dated elevation data: access status

Checked 5 October 2026 for the Gurugram municipal boundary. No dated elevation
rasters were downloaded during this check; no new dated rasters were uploaded to
GitHub. This document records the concrete access limitations and next steps.

## TanDEM-X: viable temporal source, account required

The [DLR data guide](https://geoservice.dlr.de/web/dataguide/tdm30/) describes
30 m DEM Change Maps (DCM) with per-pixel acquisition dates. Products distinguish
the earliest and latest observations from the 2016–2022 acquisition period. These
are TanDEM-X products, not additional Copernicus GLO-30 release dates.

Required geographical cells are N28E076 and N28E077, based on this compilation's
municipal extent. Actual valid coverage and distinct acquisition dates within
Gurugram still require checking the downloadable DATE and quality layers.

Download both cells from:

- [EDEM reference](https://download.geoservice.dlr.de/TDM30_EDEM/files/)
- [DCM earliest/latest changes](https://download.geoservice.dlr.de/TDM30_DCM/files/)

For each cell, obtain the EDEM archive and both FIRST1622 and LAST1622 DCM
archives, retaining their XML metadata, DATE, CIM and HAI layers. The download
service currently redirects to a login form in the browser. Registration requires
the user to supply personal details, verify email, and accept the provider's terms.

The [DLR licence](https://geoservice.dlr.de/resources/licenses/tdm30-edited/License_for_the_Utilization_of_TanDEM-X_30m-EDEM_DCM_for_Scientific_Use.pdf)
allows non-commercial/scientific use but explicitly prohibits publication or
transfer of the original EDEM/DCM products to third parties (clauses 2–3).
Do not push downloaded rasters or encoded copies of those products to this
repository. Written permission would be needed for redistribution outside the
standard terms. Keep local source data and prepared packages in `private_data/`.

After access is available, inspect acquisition dates and quality within Gurugram.
Use the matching EDEM reference to reconstruct later elevations from DCM
differences, following the product specification; do not add DCM values directly
to Copernicus GLO-30. Convert heights to EGM96, partition pixels by their actual
DATE values before resampling, and preserve missing coverage rather than filling
dates with another epoch. The EDEM reference is itself a composite and must not
be assigned an invented single acquisition date. Local dated packages can be
loaded with the app's file picker.

## ALOS: no public dated PRISM download established

The [JAXA FAQ](https://www.eorc.jaxa.jp/ALOS/en/inquiry/faq_e.htm) explains that
AW3D30 stacks observations from 2006–2011. The existing 68 dates are source-list
metadata, not 68 elevation surfaces.

The [G-Portal support page](https://gportal.jaxa.jp/gpr/information/support?lang=en)
states that ALOS PRISM data are excluded from the Open and Free download products
and that there are currently no PRISM distributors. Consequently, a downloadable
dated PRISM stereo dataset for Gurugram has not been established. Authorized stereo
scenes and separate elevation processing would be required for an ALOS timeline.
Repeated PALSAR images or the DEM supplied for radar terrain correction must not
be substituted as independent dated elevation measurements.
