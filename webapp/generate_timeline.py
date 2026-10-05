"""Extract acquisition provenance from the retained tile metadata."""
import csv
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def build_timeline():
    dates = {}
    for path in sorted((ROOT / 'raw').glob('*_LST.txt')):
        tile = path.stem.split('_')[1]
        for row in csv.reader(path.open()):
            if len(row) < 7 or len(row[6]) != 8:
                continue
            raw = row[6]
            date = f'{raw[:4]}-{raw[4:6]}-{raw[6:]}'
            dates.setdefault(date, []).append({'tile': tile, 'scene': row[0],
                                               'path': row[3], 'frame': row[4], 'stereo_mode': row[5]})
    alos = [{'date': date, 'scenes': scenes} for date, scenes in sorted(dates.items())]
    copernicus = []
    for path in sorted((ROOT / 'metadata').glob('Copernicus*.xml')):
        fields = {el.tag.split('}')[-1]: el.text.strip() for el in ET.parse(path).iter()
                  if el.text and el.text.strip()}
        tile = 'N028E076' if 'E076' in path.name else 'N028E077'
        copernicus.append({'tile': tile, 'start': fields['tsxx_startTime'],
                           'end': fields['tsxx_stopTime'],
                           'acquisitions': int(fields['numberOfUsedAcquisitions']),
                           'tile_version': fields['tileVersion']})
    return {'alos': alos, 'copernicus': copernicus,
            'scope': 'Whole source tiles; individual scene coverage of the municipality is unverified.'}


if __name__ == '__main__':
    timeline = build_timeline()
    static = ROOT / 'webapp/static'
    (static / 'timeline.json').write_text(json.dumps(timeline, indent=2))
    (static / 'timeline.js').write_text('window.DEM_ACQUISITION_TIMELINE = ' + json.dumps(timeline) + ';\n')
    print(f"ALOS: {len(timeline['alos'])} distinct dates; Copernicus: {len(timeline['copernicus'])} tile ranges")
