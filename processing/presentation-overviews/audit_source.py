from pathlib import Path
import rasterio,json,numpy as np
from rasterio.features import rasterize
from shapely.geometry import shape
from shapely import make_valid
R=Path('work');result={}
with rasterio.open(R/'drought_source_window.tif') as src:
 a=src.read(1); valid=np.isfinite(a)&(a!=src.nodata)&(a>=0)
 for code in ['karamoja','moyale_borana','mandera_triangle','dikhil']:
  fs=json.loads((R/'live'/f'{code}_hexes.json').read_text())['hexGrid']['features']
  zones=rasterize([(make_valid(shape(f['geometry'])),i+1) for i,f in enumerate(fs)],out_shape=a.shape,transform=src.transform,fill=0,dtype='int32')
  counts=np.bincount(zones[valid].ravel(),minlength=len(fs)+1)
  samples=np.bincount(zones.ravel(),minlength=len(fs)+1)
  sums=np.bincount(zones[valid].ravel(),weights=a[valid].ravel(),minlength=len(fs)+1)
  means=np.divide(sums,counts,out=np.full_like(sums,np.nan),where=counts>0)
  missing=[i+1 for i,f in enumerate(fs) if f['properties'].get('wb_hex_drought') is None]
  no_valid=[i for i in missing if counts[i]==0 and samples[i]>0]
  no_pixels=[i for i in missing if samples[i]==0]
  recovered=[{'cell_id':fs[i-1]['properties']['cell_id'],'source_valid_pixels':int(counts[i]),'source_all_pixels':int(samples[i]),'source_mean':float(means[i])} for i in missing if counts[i]>0]
  stats={'export_missing':len(missing),'source_all_nodata':len(no_valid),'no_native_pixel_centres':len(no_pixels),'source_has_valid_pixels':len(recovered),'recoverable':recovered}
  result[code]=stats;print(code,json.dumps({k:v for k,v in stats.items() if k!='recoverable'}))
  if recovered:print('recoverable',recovered[:5])
 result['_source']={'url':'https://data.humdata.org/dataset/global-drought-hazard','resource_id':'3d067bc4-e6bd-413e-a490-2010aa842a63','filename':'global-drought-spei-2.0-return-period-25-years.tif','nodata':src.nodata,'bounds':list(src.bounds),'pixel_size_degrees':src.res,'method':'Native source pixel-centre audit using repaired published hex geometries. Source same product name; original local Africa crop not available.'}
(R/'source_drought_audit.json').write_text(json.dumps(result,indent=2))
