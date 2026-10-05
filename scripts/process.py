"""Build aligned, unconditioned DEMs; no elevation-change inference."""
from pathlib import Path
from contextlib import ExitStack
import csv, json, math
import numpy as np
import rasterio as rio
from rasterio.merge import merge
from rasterio.warp import reproject, Resampling, transform_bounds
from rasterio.transform import from_origin
from rasterio.features import geometry_mask
from shapely.geometry import shape, mapping
from shapely.ops import unary_union, transform
from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[1]
RAW, OUT = ROOT/'raw', ROOT/'processed'
OUT.mkdir(exist_ok=True)
CRS, RES, NODATA = 'EPSG:32643', 30, -9999.0
features = json.loads((ROOT/'boundary/mcg_boundary.geojson').read_text())['features']
city_ll = unary_union([shape(f['geometry']) for f in features])
assert city_ll.is_valid
city = transform(Transformer.from_crs(4326, CRS, always_xy=True).transform, city_ll)
# Five kilometres is a staging margin, not an assertion of catchment completeness.
x0,y0,x1,y1 = city.buffer(5000).bounds
x0,y0 = math.floor(x0/RES)*RES, math.floor(y0/RES)*RES
x1,y1 = math.ceil(x1/RES)*RES, math.ceil(y1/RES)*RES
WIDTH, HEIGHT = round((x1-x0)/RES), round((y1-y0)/RES)
AFF = from_origin(x0, y1, RES, RES)
inside = geometry_mask([mapping(city)], (HEIGHT, WIDTH), AFF, invert=True)
profile = dict(driver='GTiff', width=WIDTH, height=HEIGHT, count=1,
               crs=CRS, transform=AFF, dtype='float32', nodata=NODATA,
               compress='deflate', predictor=3, tiled=True)

def warp(pattern, nearest=False):
    paths = sorted(RAW.glob(pattern))
    if not paths: raise RuntimeError('Missing input: '+pattern)
    with ExitStack() as stack:
        srcs = [stack.enter_context(rio.open(p)) for p in paths]
        left,bottom,right,top = transform_bounds(CRS, srcs[0].crs, x0, y0, x1, y1)
        rx,ry=srcs[0].res
        sx,sy=srcs[0].transform.c,srcs[0].transform.f
        # Preserve native pixel lattice; add two source pixels for interpolation.
        bounds=(sx+(math.floor((left-sx)/rx)-2)*rx,
                sy+(math.floor((bottom-sy)/ry)-2)*ry,
                sx+(math.ceil((right-sx)/rx)+2)*rx,
                sy+(math.ceil((top-sy)/ry)+2)*ry)
        data, aff = merge(srcs, bounds=bounds, nodata=NODATA, dtype='float32')
        dst = np.full((HEIGHT, WIDTH), NODATA, dtype='float32')
        reproject(data[0], dst, src_transform=aff, src_crs=srcs[0].crs,
                  src_nodata=NODATA, dst_transform=AFF, dst_crs=CRS,
                  dst_nodata=NODATA,
                  resampling=Resampling.nearest if nearest else Resampling.bilinear)
    return dst

def write(name, a, **tags):
    a = np.asarray(a, dtype='float32')
    with rio.open(OUT/name, 'w', **profile) as dst:
        dst.write(a, 1)
        dst.update_tags(**tags)

def summary(a, mask):
    v = a[mask & (a != NODATA) & np.isfinite(a)]
    return dict(valid_pixels=int(v.size), coverage_percent=100*v.size/int(mask.sum()),
                min_m=float(v.min()), p05_m=float(np.percentile(v,5)),
                median_m=float(np.median(v)), mean_m=float(v.mean()),
                p95_m=float(np.percentile(v,95)), max_m=float(v.max()))

def counts(a):
    val, cnt = np.unique(a[inside], return_counts=True)
    return {str(int(v)):int(n) for v,n in zip(val,cnt)}

def geoid(filename):
    # Read the small regional window with merge, then bilinearly sample to grid.
    return warp(filename)

if __name__ == '__main__':
    srtm = warp('SRTM_*.tif')
    alos = warp('*_DSM.tif')
    cop = warp('Copernicus*_DEM.tif')
    n96, n08 = geoid('us_nga_egm96_15.tif'), geoid('us_nga_egm08_25.tif')
    assert np.all(n96 != NODATA) and np.all(n08 != NODATA)
    # h = H + N, hence H96 = H08 + N08 - N96.
    correction = n08 - n96
    cop96 = np.where(cop != NODATA, cop + correction, NODATA)
    write('copernicus_EGM2008_to_EGM96_offset_m.tif', correction,
          formula='H96 = H08 + N08 - N96', units='metres')
    write('copernicus_native_EGM2008_buffer_30m.tif', cop,
          vertical_datum='EGM2008', units='metres', conditioning='none')
    products = [('SRTM_2000',srtm),('ALOS_2006_2011',alos),('Copernicus_2011_2014_primary',cop96)]
    rows=[]
    for name,a in products:
        write(name+'_EGM96_buffer_30m.tif',a,vertical_datum='EGM96',units='metres',conditioning='none')
        write(name+'_EGM96_city_30m.tif',np.where(inside,a,NODATA),vertical_datum='EGM96',units='metres',conditioning='none')
        rows.append(dict(dataset=name,**summary(a,inside)))
    write('municipal_mask_30m.tif',inside.astype('float32'),description='1 = municipal interior; 0 = outside; pixel centre rule')
    with (ROOT/'metadata/elevation_summary.csv').open('w') as f:
        writer=csv.DictWriter(f, fieldnames=rows[0].keys()); writer.writeheader(); writer.writerows(rows)
    # Quality classes use nearest-neighbour; categorical zero is a valid class.
    qa={}
    for label,pattern in [('ALOS_MSK','*_MSK.tif'),('ALOS_STK','*_STK.tif'),
                          ('Copernicus_EDM','Copernicus*_EDM.tif'),
                          ('Copernicus_FLM','Copernicus*_FLM.tif'),
                          ('Copernicus_WBM','Copernicus*_WBM.tif')]:
        a=warp(pattern,nearest=True)
        write(label+'_30m.tif',a,resampling='nearest',units='source codes')
        qa[label]=counts(a)
    stack_profile=profile.copy(); stack_profile['count']=3
    with rio.open(OUT/'DEM_three_epoch_stack_EGM96_city_30m.tif','w',**stack_profile) as dst:
        for i,(name,a) in enumerate(products,1):
            dst.write(np.where(inside,a,NODATA),i); dst.set_band_description(i,name)
        dst.update_tags(vertical_datum='EGM96',units='metres',
                        interpretation='Multi-source acquisition-period comparison; not an annual time series',conditioning='none')
    report=dict(crs=CRS,resolution_m=RES,width=WIDTH,height=HEIGHT,
                transform=list(AFF),bounds=[x0,y0,x1,y1],municipal_area_km2=city.area/1e6,
                municipal_grid_area_km2=int(inside.sum())*RES**2/1e6,
                boundary_status='GMDA flood_survey_2 MCG_Boundary snapshot; legal currency unverified',
                buffer_m=5000,buffer_status='Staging extent; upstream catchment completeness unverified',
                vertical_conversion=summary(correction,inside),quality_class_counts=qa,products=rows)
    (ROOT/'metadata/processing_report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
