"""Download public source tiles; retain URLs and SHA256 checksums."""
from pathlib import Path
import concurrent.futures, hashlib, json, requests, zipfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
jobs = []
for lon in (76, 77):
    tile = f'N28E{lon:03d}'
    jobs.append((f'https://opentopography.s3.sdsc.edu/raster/SRTM_GL1/SRTM_GL1_srtm/{tile}.tif', f'raw/SRTM_{tile}.tif'))
    jobs.append((f'https://www.eorc.jaxa.jp/ALOS/aw3d30/data/release_v2404/N025E075/N028E{lon:03d}.zip', f'raw/ALOS_N028E{lon:03d}.zip'))
    stem = f'Copernicus_DSM_COG_10_N28_00_E{lon:03d}_00'
    base = f'https://copernicus-dem-30m.s3.amazonaws.com/{stem}_DEM/'
    jobs.append((base + stem + '_DEM.tif', f'raw/{stem}_DEM.tif'))
    for band in ('EDM', 'FLM', 'WBM'):
        jobs.append((base + f'AUXFILES/{stem}_{band}.tif', f'raw/{stem}_{band}.tif'))
    xml = f'Copernicus_DSM_10_N28_00_E{lon:03d}_00.xml'
    jobs.append((base + xml, f'metadata/{xml}'))
for grid in ('us_nga_egm96_15.tif', 'us_nga_egm08_25.tif'):
    jobs.append((f'https://cdn.proj.org/{grid}', f'raw/{grid}'))

def download(job):
    url, name = job
    path = ROOT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with requests.get(url, stream=True, timeout=(30, 120)) as r:
            r.raise_for_status()
            with path.with_suffix(path.suffix + '.part').open('wb') as f:
                for chunk in r.iter_content(1024 * 1024): f.write(chunk)
        path.with_suffix(path.suffix + '.part').rename(path)
    sha = hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()
    print(name, path.stat().st_size, flush=True)
    return dict(url=url, file=name, bytes=path.stat().st_size, sha256=sha,
                retrieved_utc=datetime.now(timezone.utc).isoformat())

if __name__ == '__main__':
    rows, failures = [], []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(download, job): job for job in jobs}
        for future in concurrent.futures.as_completed(futures):
            try: rows.append(future.result())
            except Exception as e:
                failures.append(dict(url=futures[future][0], error=str(e)))
                print('FAILED', futures[future], str(e), flush=True)
    (ROOT / 'metadata/download_manifest.json').write_text(json.dumps(dict(downloads=rows, failures=failures), indent=2))
    for path in (ROOT / 'raw').glob('ALOS_*.zip'):
        with zipfile.ZipFile(path) as z:
            for info in z.infolist():
                if info.is_dir(): continue
                target = ROOT / 'raw' / Path(info.filename).name
                target.write_bytes(z.read(info))
    if failures: raise SystemExit('Some downloads failed; inspect manifest.')
