"""Build a local, quality-masked TanDEM-X timeline from licensed EDEM/DCM ZIPs.

DCM = new mosaic - EDEM (DLR product description, section 5.4).
The EGM2008 EDEM plus DCM is converted to EGM96 using the project geoid offset.
Nearest-neighbour sampling keeps elevation, date and quality from the same pixel.
No temporal interpolation, spatial smoothing or gap filling is performed.
"""
import argparse
import base64
from datetime import datetime
import hashlib
import json
from pathlib import Path
import zipfile

import numpy as np
import rasterio
from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[1]


def encode(data):
    return base64.b64encode(np.asarray(data, dtype='<f4').tobytes()).decode('ascii')


def build(downloads, destination, max_hai=5.0):
    private = destination.parent / 'tandemx'
    private.mkdir(parents=True, exist_ok=True)
    manifests = []
    # Require all six matching packages; don't silently publish partial tile coverage.
    for tile in ('N28E076', 'N28E077'):
        names = [f'TDM1_EDEM_10_{tile}_V01_C.zip'] + [
            f'TDM1_DCM__10_{tile}_{kind}1622_V01_C.zip' for kind in ('FIRST', 'LAST')]
        for name in names:
            path = downloads / name
            with zipfile.ZipFile(path) as archive:
                bad = archive.testzip()
                if bad:
                    raise ValueError(f'Corrupt ZIP member: {bad}')
                for entry in archive.infolist():
                    target = (private / entry.filename).resolve()
                    if not target.is_relative_to(private.resolve()):
                        raise ValueError('Unsafe ZIP member path')
                    if entry.filename.endswith(('.tif', '.xml')):
                        archive.extract(entry, private)
            manifests.append({'filename': name, 'bytes': path.stat().st_size,
                              'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    with rasterio.open(ROOT / 'processed/municipal_mask_30m.tif') as grid:
        municipal = grid.read(1) == 1
        shape = grid.shape
        attrs = {'width': grid.width, 'height': grid.height,
                 'bounds_utm43n': list(grid.bounds)}
        native_grids = {}
        rows, cols = np.indices(shape)
        east = grid.transform.c + (cols + .5) * grid.transform.a
        north = grid.transform.f + (rows + .5) * grid.transform.e
        lon, lat = Transformer.from_crs(grid.crs, 'EPSG:4326', always_xy=True).transform(east, north)
        indices = {}
        def sample(path):
            with rasterio.open(path) as src:
                if not src.crs or not src.crs.is_geographic:
                    raise ValueError('Expected native WGS84 geographic source grids')
                tile = 'N28E076' if 'N28E076' in path.name else 'N28E077'
                native = (src.transform, src.shape)
                if tile in native_grids and native_grids[tile] != native:
                    raise ValueError('EDEM, DCM, dates and quality must share a native pixel grid')
                native_grids[tile] = native
                # YYYYMMDD integers exceed Float32's exact-integer range.
                out = np.full(shape, np.nan, dtype='float64')
                # Exact inverse mapping avoids approximate warp transforms and uses
                # identical native pixel indices for height/date/quality layers.
                if tile not in indices:
                    native_cols = np.floor((lon - src.transform.c) / src.transform.a).astype('int64')
                    native_rows = np.floor((lat - src.transform.f) / src.transform.e).astype('int64')
                    inside = municipal & (native_cols >= 0) & (native_cols < src.width) & (native_rows >= 0) & (native_rows < src.height)
                    indices[tile] = (native_rows, native_cols, inside)
                rr, cc, inside = indices[tile]
                raster = src.read(1)
                out[inside] = raster[rr[inside], cc[inside]]
                if src.nodata is not None:
                    out[out == src.nodata] = np.nan
                return out
        with rasterio.open(ROOT / 'processed/copernicus_EGM2008_to_EGM96_offset_m.tif') as geoid:
            if geoid.shape != shape or geoid.transform != grid.transform or geoid.crs != grid.crs:
                raise ValueError('Geoid offset must match the municipal grid')
            offset = geoid.read(1, masked=True).filled(np.nan)
        reference = np.full(shape, np.nan, dtype='float32')
        dates = {}
        quality_counts = []
        for tile in ('N28E076', 'N28E077'):
            base_path = private / f'TDM1_EDEM_10_{tile}_V01_C/EDEM/TDM1_EDEM_10_{tile}_EDEM_EGM.tif'
            base = sample(base_path)
            valid_base = np.isfinite(base)
            reference[valid_base] = (base + offset)[valid_base]
            for kind in ('FIRST', 'LAST'):
                folder = private / f'TDM1_DCM__10_{tile}_{kind}1622_V01_C'
                def layer(code):
                    matches = list(folder.rglob(f'TDM1_DCM__10_{tile}_{code}*{kind}1622_*.tif'))
                    if len(matches) != 1:
                        raise ValueError(f'Expected one {code} raster in {folder}')
                    return sample(matches[0])
                delta, date, hai, cim = [layer(code) for code in ('DCM_', 'DATE', 'HAI_', 'CIM_')]
                available = municipal & valid_base & np.isfinite(delta) & (delta != -32767) & np.isfinite(date) & (date > 0)
                reliable = available & np.isin(cim, [1, 4]) & np.isfinite(hai) & (hai >= 0) & (hai <= max_hai)
                quality_counts.append({'tile': tile, 'variant': kind, 'available_pixels': int(available.sum()),
                                       'retained_pixels': int(reliable.sum())})
                height = base + delta + offset
                for value in np.unique(date[reliable]).astype('int64'):
                    label = datetime.strptime(str(value), '%Y%m%d').date().isoformat()
                    selected = reliable & (date == value)
                    record = dates.setdefault(label, {'height': np.full(shape, np.nan, dtype='float32'),
                                                       'hai': np.full(shape, np.nan, dtype='float32'),
                                                       'products': set()})
                    # FIRST/LAST can duplicate observations; keep the lower HAI without averaging.
                    choose = selected & (~np.isfinite(record['height']) | (hai < record['hai']))
                    record['height'][choose] = height[choose]
                    record['hai'][choose] = hai[choose]
                    record['products'].add(folder.name)
        if not dates or len(dates) > 24:
            raise ValueError(f'Unsupported number of observed dates: {len(dates)}')
        frames, coverage = [], []
        for date, record in sorted(dates.items()):
            data = record['height']
            valid = np.isfinite(data)
            if np.any(data[valid] < -500) or np.any(data[valid] > 9000):
                raise ValueError('Invalid reconstructed elevations')
            pct = round(100 * valid.sum() / municipal.sum(), 2)
            frames.append(dict(attrs, source='tandemx', date=date,
                               label=f'TanDEM-X · {date}', coverage_percent=pct,
                               provenance=f'DLR EDEM + DCM; per-pixel DATE; {pct}% city coverage; CIM 1/4, HAI ≤ {max_hai:g} m',
                               elevations_base64=encode(data), hai_base64=encode(record['hai'])))
            coverage.append({'date': date, 'pixels': int(valid.sum()), 'coverage_percent': pct,
                             'products': sorted(record['products'])})
        pack = {'version': 1, 'crs': 'EPSG:32643', 'vertical_datum': 'EGM96', 'frames': frames,
                'reference': dict(attrs, label='TanDEM-X EDEM · 2010–15 composite',
                                  elevations_base64=encode(reference))}
        destination.parent.mkdir(parents=True, exist_ok=True)
        encoded = json.dumps(pack, separators=(',', ':'))
        destination.write_text(encoded)
        destination.with_suffix('.js').write_text('window.DEM_DATED_MAPS = ' + encoded + ';\n')
        report = {'source': 'DLR TanDEM-X 30m EDEM/DCM', 'archives': manifests,
                  'grid': attrs, 'dates': coverage, 'quality': quality_counts,
                  'filter': f'CIM 1/4; finite HAI 0–{max_hai:g} m; invalid elevations/dates excluded',
                  'method': 'EDEM_EGM2008 + DCM + project EGM2008-to-EGM96 geoid offset; nearest neighbour; no gap filling',
                  'license': 'Scientific/noncommercial use. Licensed rasters and prepared elevation packages remain local.',
                  'limitations': 'Earliest/latest available observations per pixel, not an annual series. DSM changes include buildings/vegetation. HAI excludes systematic calibration and phase-unwrapping errors.'}
        # This report contains provenance and aggregate coverage only, never raster values.
        (ROOT / 'tandemx_inventory.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps({'dates': coverage, 'output': str(destination)}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--downloads', type=Path, default=Path.home() / 'Downloads')
    parser.add_argument('--output', type=Path, default=ROOT / 'private_data/dated-maps.json')
    parser.add_argument('--max-hai', type=float, default=5.0, help='Conservative screening threshold in metres, not an accuracy guarantee')
    args = parser.parse_args()
    if not np.isfinite(args.max_hai) or args.max_hai <= 0:
        parser.error('--max-hai must be a positive finite number')
    build(args.downloads, args.output, args.max_hai)
