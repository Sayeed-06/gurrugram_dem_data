"""Create a map, cell table, source inventory, and validate delivered rasters."""
from pathlib import Path
import csv, gzip, hashlib, json, re, shutil, xml.etree.ElementTree as ET
import numpy as np
import rasterio as rio
from pyproj import Transformer
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'processed'
report=json.loads((ROOT/'metadata/processing_report.json').read_text())
with rio.open(OUT/'DEM_three_epoch_stack_EGM96_city_30m.tif') as src:
    a=src.read(masked=True); aff=src.transform; crs=src.crs
    dims=src.shape
    bounds=src.bounds
    assert src.count==3 and src.res==(30,30)
    assert all(int((~a.mask[i]).sum())==331420 for i in range(3))
    assert all(np.isfinite(a[i].compressed()).all() for i in range(3))
qa={}
for name in ('ALOS_MSK','Copernicus_FLM','Copernicus_EDM','Copernicus_WBM'):
    with rio.open(OUT/(name+'_30m.tif')) as d:qa[name]=d.read(1)
row,col=np.where(~a.mask[0])
x,y=rio.transform.xy(aff,row,col)
lon,lat=Transformer.from_crs(crs,4326,always_xy=True).transform(x,y)
with gzip.open(ROOT/'municipal_elevation_cells.csv.gz','wt',newline='') as f:
    w=csv.writer(f)
    w.writerow(['row','col','easting_m','northing_m','longitude','latitude',
                'SRTM_2000_EGM96_m','ALOS_2006_2011_EGM96_m','Copernicus_2011_2014_primary_EGM96_m',
                'ALOS_MSK','Copernicus_FLM','Copernicus_EDM','Copernicus_WBM'])
    for k,(r,c) in enumerate(zip(row,col)):
        w.writerow([r,c,round(x[k],1),round(y[k],1),round(lon[k],7),round(lat[k],7),
                    *[round(float(a[i,r,c]),3) for i in range(3)],
                    *[int(qa[n][r,c]) for n in qa]])
fig,axs=plt.subplots(1,3,figsize=(14,6),layout='constrained')
for i,(ax,title) in enumerate(zip(axs,['SRTM | February 2000','ALOS AW3D30 | 2006–2011','Copernicus GLO-30 | 2011–2014*'])):
    im=ax.imshow(a[i],extent=[bounds.left/1000,bounds.right/1000,bounds.bottom/1000,bounds.top/1000],
                 cmap='terrain',vmin=200,vmax=325,interpolation='nearest')
    ax.set_title(title,fontsize=11);ax.set_xlabel('UTM 43N easting (km)')
    ax.set_ylabel('Northing (km)');ax.set_facecolor('#f0f2f4')
    ax.text(.95,.95,'N ↑',transform=ax.transAxes,ha='right')
fig.colorbar(im,ax=axs,shrink=.65,label='Elevation (m), EGM96')
fig.suptitle('Gurugram municipal DEM compilation · 30 m common grid',fontsize=16)
fig.supxlabel('GMDA boundary snapshot · *Copernicus tile acquisition envelope; fill dates vary.\nUnconditioned surface elevations: suitable for screening, not a validated flood model.',fontsize=10)
fig.savefig(ROOT/'DEM_comparison.png',dpi=180);plt.close(fig)
inventory=[]
for p in sorted((ROOT/'raw').glob('*_LST.txt')):
    dates=sorted(set(re.findall(r',((?:200|201)\d{5}),',p.read_text())))
    inventory.append(dict(dataset='ALOS AW3D30 v4.1',tile=p.stem.replace('_LST',''),
                          earliest_source_date=dates[0],latest_source_date=dates[-1],
                          native_vertical_datum='EGM96',date_scope='full tile source-scene list, not city pixel dates'))
for p in sorted((ROOT/'metadata').glob('Copernicus*.xml')):
    values={e.tag.split('}')[-1]:e.text.strip() for e in ET.parse(p).iter() if e.text and e.text.strip()}
    inventory.append(dict(dataset='Copernicus GLO-30 AWS COG tile v'+values['tileVersion'],tile=p.stem,
                          earliest_source_date=values['tsxx_startTime'],latest_source_date=values['tsxx_stopTime'],
                          native_vertical_datum='EGM2008',date_scope='tile primary acquisition envelope; external fills excluded'))
for tile in ('N28E076','N28E077'):
    inventory.append(dict(dataset='SRTM GL1 (OpenTopography mirror)',tile=tile,
                          earliest_source_date='2000-02-11',latest_source_date='2000-02-22',
                          native_vertical_datum='EGM96',date_scope='mission period; void-fill dates may differ'))
with (ROOT/'metadata/source_inventory.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=inventory[0].keys());w.writeheader();w.writerows(inventory)
checks=[]
for p in OUT.glob('*.tif'):
    with rio.open(p) as d:
        assert d.transform==aff and d.crs==crs and d.shape==dims,p.name
        checks.append(dict(file=p.name,shape=d.shape,bands=d.count,grid_match=True))
# Independently check the geoid sign and numerical interpolation at city centre.
grid08=(ROOT/'raw/us_nga_egm08_25.tif').resolve()
grid96=(ROOT/'raw/us_nga_egm96_15.tif').resolve()
pipeline=f'+proj=pipeline +step +proj=unitconvert +xy_in=deg +xy_out=rad +step +proj=vgridshift +grids={grid08} +multiplier=1 +step +inv +proj=vgridshift +grids={grid96} +multiplier=1'
t=Transformer.from_pipeline(pipeline)
_,_,offset=t.transform(77.05,28.43,0)
with rio.open(OUT/'copernicus_EGM2008_to_EGM96_offset_m.tif') as d:
    xx,yy=Transformer.from_crs(4326,crs,always_xy=True).transform(77.05,28.43)
    sampled=float(next(d.sample([(xx,yy)]))[0])
assert abs(offset-sampled)<0.005,(offset,sampled)
validation=dict(raster_checks=checks,municipal_cell_count=len(row),
                geoid_offset_PROJ_m=offset,geoid_offset_raster_m=sampled,
                geoid_check_tolerance_m=.005,status='passed',
                not_validated=['current legal municipal boundary','local survey vertical accuracy',
                               'horizontal co-registration against control','hydrological conditioning',
                               'upstream catchment completeness','flood performance'])
(ROOT/'metadata/validation.json').write_text(json.dumps(validation,indent=2))
print(json.dumps(validation,indent=2))
