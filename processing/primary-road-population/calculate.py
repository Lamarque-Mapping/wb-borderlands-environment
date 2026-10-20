"""Primary-road proximity using original WorldPop counts and published map geometry.

Run with Python + numpy, rasterio, shapely >=2 and pyproj.
Inputs are the existing website core/admin/roads JSON and the source WorldPop TIFF.
"""
from pathlib import Path
import argparse, csv, gzip, hashlib, json, math, warnings
import numpy as np
import rasterio
from rasterio.windows import Window, from_bounds
import shapely as S
from shapely.geometry import shape, mapping, Polygon, LineString
from shapely.ops import transform, unary_union
from pyproj import Transformer, Proj

warnings.filterwarnings('ignore', category=DeprecationWarning)
BASE = Path(__file__).resolve().parent
WGS, AREA = 'EPSG:4326', 'ESRI:54009'
NAMES = {'mandera_triangle':'Mandera Triangle','moyale_borana':'Moyale–Borana','karamoja':'Karamoja','dikhil':'Dikhil'}
UNASSIGNED = 'Unassigned boundaries'
parser=argparse.ArgumentParser()
parser.add_argument('--raster',type=Path,default=BASE.parent/'upload/global_pop_2025_CN_1km_R2025A_UA_v1.tif')
parser.add_argument('--input',type=Path,default=BASE/'input')
parser.add_argument('--output',type=Path,default=BASE/'output')
parser.add_argument('--cluster',choices=NAMES)
args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)

def source_bytes(p):return p.read_bytes() if p.exists() else gzip.decompress(Path(str(p)+'.gz').read_bytes())
def read(p):return json.loads(source_bytes(p))
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,separators=(',',':'),ensure_ascii=False))
def polygon(g):
    if not g.is_valid:g=S.make_valid(g)
    if g.is_empty:return Polygon()
    if g.geom_type in ('Polygon','MultiPolygon'):return g
    return unary_union([polygon(x) for x in g.geoms if x.area>0])
def lines(g):
    if g.is_empty:return LineString()
    if g.geom_type in ('LineString','MultiLineString'):return g
    return unary_union([lines(x) for x in g.geoms if x.geom_type!='Point'])
def move(g,a,b,poly=False):
    g=transform(Transformer.from_crs(a,b,always_xy=True).transform,g)
    if poly:g=polygon(g)
    return S.set_precision(g,.001) if b==AREA else g
def feature(g,p,crs=AREA,simplify=0):
    # Simplification is for web display only; calculations use original geometry.
    if simplify:g=g.simplify(simplify,preserve_topology=True)
    return {'type':'Feature','properties':p,'geometry':mapping(move(g,crs,WGS,poly=g.area>0))}
def fc(features):return {'type':'FeatureCollection','features':features}
def clip_many(cells,region):
    full=S.contains(region,cells);partial=(~full)&S.intersects(region,cells)
    result=np.empty(len(cells),dtype=object);result[:]=Polygon();result[full]=cells[full]
    if partial.any():result[partial]=S.intersection(cells[partial],region)
    return result

source_hash=hashlib.file_digest(open(args.raster,'rb'),'sha256').hexdigest()
index=[]
for code in ([args.cluster] if args.cluster else NAMES):
    print('START',code,flush=True)
    out=args.output/code;out.mkdir(parents=True,exist_ok=True)
    core=read(args.input/(code+'_core.json'));admin=read(args.input/(code+'_admin.json'));roads=read(args.input/(code+'_roads.json'))
    cl_wgs=polygon(unary_union([shape(f['geometry']) for f in core['cluster']['features']]))
    centre=cl_wgs.centroid
    local=f'+proj=aeqd +lat_0={centre.y:.8f} +lon_0={centre.x:.8f} +datum=WGS84 +units=m +no_defs'
    cluster=move(cl_wgs,WGS,AREA,True)
    cl_local=move(cluster,AREA,local,True)
    raw_countries={}
    for f in admin['admin2']['features']:
        raw_countries.setdefault(f['properties']['country'],[]).append(move(shape(f['geometry']),WGS,AREA,True))
    countries={n:polygon(unary_union(gs).intersection(cluster)) for n,gs in raw_countries.items()}
    countries={n:g for n,g in countries.items() if not g.is_empty and g.area>1}
    values=list(countries.values())
    overlap=polygon(unary_union([values[i].intersection(values[j]) for i in range(len(values)) for j in range(i+1,len(values))]))
    regions={n:polygon(g.difference(overlap)) for n,g in countries.items()}
    regions[UNASSIGNED]=polygon(cluster.difference(unary_union(list(regions.values()))))
    network=lines(unary_union([move(shape(f['geometry']),WGS,local) for f in roads['primaryRoads']['features']]).intersection(cl_local))
    assert not network.is_empty
    national={n:lines(network.intersection(move(g,AREA,local,True))) for n,g in regions.items()}
    band=polygon(move(polygon(network.buffer(10000,quad_segs=96).intersection(cl_local)),local,AREA,True).intersection(cluster))
    bands={'Cluster':band}
    for n,g in regions.items():
        band_local=polygon(national[n].buffer(10000,quad_segs=96)) if not national[n].is_empty else Polygon()
        bands[n]=polygon(move(band_local,local,AREA,True).intersection(g))
    geographies={'Cluster':cluster,**regions}
    for g in [*geographies.values(),*bands.values()]:S.prepare(g)
    geo_delta=sum(g.area for g in regions.values())-cluster.area
    assert abs(geo_delta)<150,geo_delta

    with rasterio.open(args.raster) as ds:
        assert ds.crs.to_epsg()==4326 and ds.count==1
        w=from_bounds(*cl_wgs.bounds,ds.transform)
        win=Window(math.floor(w.col_off),math.floor(w.row_off),math.ceil(w.col_off+w.width)-math.floor(w.col_off),math.ceil(w.row_off+w.height)-math.floor(w.row_off))
        arr=ds.read(1,window=win);grid=ds.window_transform(win);nodata=ds.nodata
        profile=ds.profile.copy();profile.update(width=arr.shape[1],height=arr.shape[0],transform=grid,compress='deflate')
        cutout=out/'worldpop2025_source_window.tif'
        with rasterio.open(cutout,'w',**profile) as dst:dst.write(arr,1)
    source={'product':'WorldPop 2025 R2025A, constrained, UN-adjusted, 1 km v1','year':2025,
      'file':args.raster.name,'sha256':source_hash,'source_window':[int(win.col_off),int(win.row_off),int(win.width),int(win.height)],
      'window_sha256':hashlib.file_digest(open(cutout,'rb'),'sha256').hexdigest(),'nodata':nodata,
      'url':'https://data.worldpop.org/GIS/Population/Global_2015_2030/R2025A/2025/0_Mosaicked/v1/1km_ua/constrained/global_pop_2025_CN_1km_R2025A_UA_v1.tif'}
    totals={n:dict(inside_population=0.,outside_population=0.,cluster_network_inside_population=0.,valid_area_m2=0.,missing_area_m2=0.) for n in geographies}
    to_area=Transformer.from_crs(WGS,AREA,always_xy=True)
    max_roundoff=0.;centre_total=0.
    for row in range(arr.shape[0]):
        xs=grid.c+np.arange(arr.shape[1])*grid.a;y=grid.f+row*grid.e
        vs=np.stack([np.column_stack([xs,np.full_like(xs,y)]),np.column_stack([xs+grid.a,np.full_like(xs,y)]),np.column_stack([xs+grid.a,np.full_like(xs,y+grid.e)]),np.column_stack([xs,np.full_like(xs,y+grid.e)]),np.column_stack([xs,np.full_like(xs,y)])],axis=1)
        xx,yy=to_area.transform(vs[:,:,0],vs[:,:,1]);vs[:,:,0]=xx;vs[:,:,1]=yy
        cells=S.set_precision(S.polygons(vs),.001);keep=S.intersects(cluster,cells)
        cells=cells[keep];v=arr[row][keep].astype(float);denom=S.area(cells)
        valid=np.isfinite(v)&(v>=0)&(v!=nodata)
        pieces=clip_many(cells,cluster);full_inside=clip_many(pieces,band)
        centre_total+=float(v[valid&S.contains(cluster,S.centroid(cells))].sum())
        for n,g in geographies.items():
            pieces_g=pieces if n=='Cluster' else clip_many(pieces,g)
            aa=S.area(pieces_g);ii=S.area(full_inside if n=='Cluster' else clip_many(pieces_g,bands[n]))
            jj=ii if n=='Cluster' else S.area(clip_many(full_inside,g))
            epsilon=S.length(cells)*.002
            assert np.all(ii<=aa+epsilon) and np.all(aa<=denom+epsilon),(code,row,n)
            max_roundoff=max(max_roundoff,float(np.maximum(ii-aa,aa-denom).max(initial=0)))
            aa=np.clip(aa,0,denom);ii=np.clip(ii,0,aa);jj=np.clip(jj,0,aa)
            t=totals[n];t['inside_population']+=float(np.sum(v[valid]*ii[valid]/denom[valid]));t['outside_population']+=float(np.sum(v[valid]*(aa[valid]-ii[valid])/denom[valid]));t['cluster_network_inside_population']+=float(np.sum(v[valid]*jj[valid]/denom[valid]));t['valid_area_m2']+=float(aa[valid].sum());t['missing_area_m2']+=float(aa[~valid].sum())
        if row%80==0:print(code,f'population rows {row+1}/{arr.shape[0]}',flush=True)
    rows=[]
    for n,t in totals.items():
        total=t['inside_population']+t['outside_population'];g=geographies[n]
        rows.append({'geography':n,'scope':'cluster' if n=='Cluster' else 'unassigned' if n==UNASSIGNED else 'country','population_year':2025,**t,
          'total_population':total,'inside_percent':100*t['inside_population']/total if total>0 else None,'outside_percent':100*t['outside_population']/total if total>0 else None,
          'area_km2':g.area/1e6,'inside_area_km2':bands[n].area/1e6,'valid_cell_area_percent':100*t['valid_area_m2']/g.area if g.area else 0,
          'road_length_km':(network if n=='Cluster' else national[n]).length/1000})
    pop_delta=sum(r['total_population'] for r in rows[1:])-rows[0]['total_population']
    cluster_inside_delta=sum(r['cluster_network_inside_population'] for r in rows[1:])-rows[0]['inside_population']
    raster_delta=totals['Cluster']['valid_area_m2']+totals['Cluster']['missing_area_m2']-cluster.area
    assert abs(pop_delta)<.1 and abs(cluster_inside_delta)<.1,(pop_delta,cluster_inside_delta)
    assert abs(raster_delta)<1500,raster_delta
    assert all(g.is_valid for g in [*geographies.values(),*bands.values()])
    assert all(bands[n].difference(geographies[n]).area<10 for n in bands)
    # Difference between national sums and cluster proximity is expected near borders.
    validation={'status':'PASSED','country_total_minus_cluster_people':pop_delta,'country_allocations_of_cluster_band_minus_cluster_people':cluster_inside_delta,'country_area_minus_cluster_m2':geo_delta,'raster_area_minus_cluster_m2':raster_delta,'max_overlay_roundoff_m2':max_roundoff,'independent_cell_centre_total':centre_total,'geometries_valid':True,'source_road_features':len(roads['primaryRoads']['features']),
      'input_sha256':{kind:hashlib.sha256(source_bytes(args.input/(code+'_'+kind+'.json'))).hexdigest() for kind in ['core','roads','admin']},'local_distance_crs':local}
    limitations=[
      'Uses exactly the existing published Primary roads layer. It is not a named project corridor and does not assert that every real-world primary road is mapped.',
      'Road geometry is limited to the cluster; roads outside its boundary are not included. Original geometry is used for calculation; web geometry is simplified by 20 m only for display.',
      '10 km on either side is a chosen straight-line proximity measure, not road-network access, all-season accessibility, a standard project catchment or beneficiary count.',
      'Cluster mode buffers the union of all primary roads and clips to the cluster. Country mode first clips roads to that country within the cluster, buffers them and clips to the same national territory. Cross-border proximity can make national inside counts sum to less than the cluster inside count.',
      'WorldPop 2025 R2025A constrained UN-adjusted 1 km modelled counts; R2025A was released as an alpha product. Not census observations. Counts are allocated by original-cell overlap area in Mollweide, with no raster resampling and uniform population assumed within each cell.',
      'No-data, negative and nonfinite raster values remain excluded; valid zero cells remain zero. Valid-valued cell area is reported, not a population coverage percentage. Constrained settlement mapping can omit or misallocate populations.',
      'National sections are assigned using the existing OCHA COD-AB administrative geometries, not the road country-extract attribute. Boundary overlaps and gaps remain unassigned. All overlaps use a shared 1 mm coordinate precision.',
      'Country population denominators cover only territory within this cluster, not the entire country. Road buffers are dissolved so overlaps count population once.']
    summary={'format':'wb-primary-road-population-v1','code':code,'cluster':NAMES[code],'width_each_side_km':10,'source':source,'rows':rows,'limitations':limitations,'validation':validation}
    save(out/'summary.json',summary)
    bundle={'summary':summary,'territories':fc([feature(g,{'geography':n},simplify=20) for n,g in geographies.items()]),
      'bands':fc([feature(g,{'geography':n},simplify=20) for n,g in bands.items() if not g.is_empty]),
      'roads':fc([feature(g,{'geography':n},local,simplify=20) for n,g in national.items() if not g.is_empty])}
    save(out/'map.json',bundle)
    save(out/'primary_roads.geojson',fc([feature(network,{'scope':'cluster'},local)]))
    save(out/'buffers.geojson',fc([feature(g,{'geography':n}) for n,g in bands.items() if not g.is_empty]))
    save(out/'territories.geojson',fc([feature(g,{'geography':n}) for n,g in geographies.items()]))
    with open(out/'population.csv','w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    index.append(summary)
    print('DONE',code,[(r['geography'],round(r['total_population']),round(r['inside_percent'],2) if r['inside_percent'] is not None else None) for r in rows],validation,flush=True)
if not args.cluster:save(args.output/'summary.json',{'clusters':index})
