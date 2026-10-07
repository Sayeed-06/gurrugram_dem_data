# Dated elevation data: access status

Updated 7 October 2026. All six DLR packages for N28E076/N28E077 have been
successfully downloaded and ZIP integrity checked. Licensed products and prepared
rasters remain local. The repository includes processing code and aggregate
provenance/coverage only; see `tandemx_inventory.json`.

The quality-masked municipal timeline has three dates: 2019-04-10 (78.84% coverage),
2019-04-27 (19.13%), and 2021-07-30 (76.76%). These are partial observed surfaces,
not annual coverage. TanDEM-X was subsequently removed from the app at the user’s request; this file preserves acquisition provenance only.

## TanDEM-X: viable temporal source, account required

The [DLR data guide](https://geoservice.dlr.de/web/dataguide/tdm30/) describes
30 m DEM Change Maps (DCM) with per-pixel acquisition dates. Products distinguish
the earliest and latest observations from the 2016–2022 acquisition period. These
are TanDEM-X products, not additional Copernicus GLO-30 release dates.

Required geographical cells are N28E076 and N28E077, based on this compilation's
municipal extent. DATE and quality layers have been checked within the municipality.

Download both cells from:

- [EDEM reference](https://download.geoservice.dlr.de/TDM30_EDEM/files/)
- [DCM earliest/latest changes](https://download.geoservice.dlr.de/TDM30_DCM/files/)

For each cell, obtain the EDEM archive and both FIRST1622 and LAST1622 DCM
archives, retaining their XML metadata, DATE, CIM and HAI layers. The download
service requires an authenticated session. Registration requires
the user to supply personal details, verify email, and accept the provider's terms.

The [DLR licence](https://geoservice.dlr.de/resources/licenses/tdm30-edited/License_for_the_Utilization_of_TanDEM-X_30m-EDEM_DCM_for_Scientific_Use.pdf)
allows non-commercial/scientific use but explicitly prohibits publication or
transfer of the original EDEM/DCM products to third parties (clauses 2–3).
Do not push downloaded rasters or encoded copies of those products to this
repository. Written permission would be needed for redistribution outside the
standard terms. Keep local source data and prepared packages in `private_data/`.

`webapp/prepare_tandemx.py` reconstructs dated elevations with the matching EDEM
reference and DCM differences, then converts EGM2008 heights to EGM96 using the
project geoid offset. The common native source grid is sampled with nearest
neighbour so dates and values remain paired. CIM 1/4 and HAI ≤ 5 m are retained;
missing/screened coverage remains empty. The EDEM is a composite and is shown as a
reference rather than assigned an invented acquisition date. See the webapp README
for commands and limitations.

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
