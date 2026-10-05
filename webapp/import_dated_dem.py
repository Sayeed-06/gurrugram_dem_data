"""Prepare a genuinely dated, metre-valued EGM96 GeoTIFF for the map slider.

Does horizontal reprojection only. Convert vertical datum before import.
"""
import argparse
import base64
from datetime import date
import hashlib
import json
from pathlib import Path
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / 'webapp/static'


def prepare(path, source, acquisition_date, label, provenance, vertical_datum):
    if vertical_datum != 'EGM96':
        raise ValueError('Convert elevations to EGM96 metres before import; vertical conversion is not performed here.')
    date.fromisoformat(acquisition_date)
    if source not in ('alos', 'copernicus') or not label.strip() or not provenance.strip():
        raise ValueError('Source, map label and acquisition provenance are required.')
    with rasterio.open(ROOT / 'processed/municipal_mask_30m.tif') as mask:
        municipal = mask.read(1) == 1
        output = np.full(mask.shape, np.nan, dtype='<f4')
        with rasterio.open(path) as src:
            if not src.crs or src.count != 1:
                raise ValueError('Provide one georeferenced elevation band in metres.')
            data=src.read(1, masked=True).astype('float32').filled(np.nan)
            reproject(source=data, destination=output, src_transform=src.transform,
                      src_crs=src.crs, src_nodata=np.nan, dst_transform=mask.transform,
                      dst_crs=mask.crs, dst_nodata=np.nan, resampling=Resampling.bilinear)
        output[~municipal] = np.nan
        valid=output[np.isfinite(output)]
        if not valid.size or np.any(valid < -500) or np.any(valid > 9000):
            raise ValueError('No valid municipal coverage, or invalid elevations in metres.')
        return {'source':source, 'date':acquisition_date, 'label':label, 'provenance':provenance,
                'sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest(),
                'width':mask.width, 'height':mask.height, 'bounds_utm43n':list(mask.bounds),
                'elevations_base64':base64.b64encode(output.tobytes()).decode('ascii')}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('geotiff', type=Path)
    parser.add_argument('--source', choices=['alos','copernicus'], required=True)
    parser.add_argument('--date', required=True, help='Actual acquisition date YYYY-MM-DD, not a release date')
    parser.add_argument('--label', required=True)
    parser.add_argument('--provenance', required=True, help='Scene/surface ID and acquisition-date evidence')
    parser.add_argument('--vertical-datum', choices=['EGM96'], required=True, help='Explicitly confirm input elevations are EGM96 metres')
    parser.add_argument('--output', type=Path, default=ROOT/'private_data/dated-maps.json')
    args=parser.parse_args()
    frame=prepare(args.geotiff,args.source,args.date,args.label,args.provenance,args.vertical_datum)
    pack=json.loads(args.output.read_text()) if args.output.exists() else {'version':1,'crs':'EPSG:32643','vertical_datum':'EGM96','frames':[]}
    if pack.get('version')!=1 or pack.get('crs')!='EPSG:32643' or pack.get('vertical_datum')!='EGM96':
        raise ValueError('Existing package has an incompatible grid or datum.')
    if any(f['source']==args.source and f['date']==args.date for f in pack['frames']):
        raise ValueError('A map already exists for this source and date; choose a separate output or resolve the duplicate.')
    if len(pack['frames'])>=24:
        raise ValueError('Use a separate package for more than 24 frames.')
    pack['frames'].append(frame)
    pack['frames'].sort(key=lambda f:(f['source'],f['date']))
    encoded=json.dumps(pack, separators=(',',':'))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(encoded)
    args.output.with_suffix('.js').write_text('window.DEM_DATED_MAPS = '+encoded+';\n')
    print(f'Prepared {len(pack["frames"])} dated maps. Load {args.output} using Load prepared dated maps in the app. Review the source redistribution licence before sharing any package.')


if __name__=='__main__':
    main()
