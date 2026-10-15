"""Aggregate native GRDI pixels to the existing cluster-clipped 10 km hexes.
Uses exact polygon intersections in EPSG:6933; no interpolation or population weighting.
Run with /usr/bin/python3 (GDAL/OGR and NumPy environment).
"""
import json,math,hashlib
from pathlib import Path
from osgeo import ogr,osr,gdal
osr.UseExceptions();ogr.UseExceptions()
ROOT=Path(__file__).resolve().parent
CODES=['mandera_triangle','moyale_borana','karamoja','dikhil']
wgs=osr.SpatialReference();wgs.ImportFromEPSG(4326);wgs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
ea=osr.SpatialReference();ea.ImportFromEPSG(6933)
tx=osr.CoordinateTransformation(wgs,ea)
def project(g):
 g=g.Clone();g.Transform(tx);return g
def rectangle(x0,y0,x1,y1):
 ring=ogr.Geometry(ogr.wkbLinearRing)
 for x,y in [(x0,y0),(x1,y0),(x1,y1),(x0,y1),(x0,y0)]:ring.AddPoint_2D(x,y)
 p=ogr.Geometry(ogr.wkbPolygon);p.AddGeometry(ring);return p
report={'method':'Exact intersection-area-weighted mean of valid source pixels; EPSG:6933; no population weighting','maps':[]}
for code in CODES:
 source=ROOT.parent/'sedac_integration/data'/f'{code}_sedac.json'
 gridfile=ROOT/'input'/f'{code}_hexes.json'
 r=json.loads(source.read_text())['grdi'];hexes=json.loads(gridfile.read_text())['hexGrid']['features']
 values=dict(r['cells']);g=r['grid'];width=r['width'];height=r['height'];pixel_cache={};repaired=0;total_covered=0.;total_weighted=0.;total_area=0.;records=[];areas_by_pixel={}
 assert g[1]>0 and g[5]<0 and g[2]==0 and g[4]==0
 for f in hexes:
  shape=ogr.CreateGeometryFromJson(json.dumps(f['geometry']));west,east,south,north=shape.GetEnvelope();poly=project(shape)
  if not poly.IsValid():poly=poly.MakeValid();repaired+=1
  area=poly.GetArea();assert area>0
  cols=range(max(0,math.floor((west-g[0])/g[1])),min(width,math.ceil((east-g[0])/g[1])))
  rows=range(max(0,math.floor((north-g[3])/g[5])),min(height,math.ceil((south-g[3])/g[5])))
  weighted=0.;covered=0.;count=0;low=math.inf;high=-math.inf
  for row in rows:
   for col in cols:
    index=row*width+col;v=values.get(index)
    if v is None:continue
    if index not in pixel_cache:pixel_cache[index]=project(rectangle(g[0]+col*g[1],g[3]+(row+1)*g[5],g[0]+(col+1)*g[1],g[3]+row*g[5]))
    inter=poly.Intersection(pixel_cache[index]);a=inter.GetArea() if inter else 0.
    if a<=1e-6:continue
    covered+=a;weighted+=v*a;count+=1;low=min(low,v);high=max(high,v);areas_by_pixel[index]=areas_by_pixel.get(index,0)+a
  mean=weighted/covered if covered else None
  assert covered<=area*(1+1e-7),(code,f['properties']['cell_id'],covered/area)
  assert mean is None or low-1e-9<=mean<=high+1e-9
  p={'cell_id':f['properties']['cell_id'],'mean':mean,'coverage_pct':100*covered/area,'source_pixels':count,'mapped_km2':covered/1e6,'hex_km2':area/1e6}
  records.append({'type':'Feature','geometry':f['geometry'],'properties':p})
  total_covered+=covered;total_weighted+=weighted;total_area+=area
 # A source pixel cannot contribute more than its area across this non-overlapping grid.
 assert all(a<=pixel_cache[i].GetArea()*(1+1e-5) for i,a in areas_by_pixel.items())
 assert len({str(f['properties']['cell_id']) for f in records})==len(records)
 valid=[f['properties'] for f in records if f['properties']['mean'] is not None]
 doc={'format':'wb-grdi-hex-v1','code':code,'method':report['method'],'reference':'GRDI v1 inputs 2010–2020','geometry':'Existing cluster-clipped 10 km analysis grid','features':records,'type':'FeatureCollection','summary':{'hexes':len(records),'with_data':len(valid),'without_data':len(records)-len(valid),'mapped_area_share':total_covered/total_area,'area_mean':total_weighted/total_covered}}
 (ROOT/'data'/f'{code}_grdi_hex.json').write_text(json.dumps(doc,separators=(',',':'),allow_nan=False))
 report['maps'].append({'code':code,**doc['summary'],'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'hex_input_sha256':hashlib.sha256(gridfile.read_bytes()).hexdigest(),'geometry_identical':True,'invalid_hexes_repaired_for_area_calculation':repaired,'zero_filled':False,'coverage_bounds_checked':True,'pixel_area_conservation_checked':True,'means_within_contributing_values':True})
 print(code,doc['summary'],flush=True)
 pixel_cache.clear();poly=shape=inter=None
(ROOT/'data/validation.json').write_text(json.dumps(report,indent=2)+'\n')

tx=None;wgs=None;ea=None
