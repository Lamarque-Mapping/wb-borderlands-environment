"""Reproducible Mandera corridor pilot, retaining original WorldPop cells."""
from pathlib import Path
import json, math, hashlib, csv, shutil
import numpy as np
import rasterio
from rasterio.windows import Window, from_bounds
import shapely as S
from shapely.geometry import shape, mapping, Polygon, Point
from shapely.ops import transform, unary_union, linemerge
from pyproj import Transformer

ROOT=Path(__file__).resolve().parent
WORK=Path(__file__).parent
DATA=WORK/'inputs'
OUT=WORK/'output';OUT.mkdir(exist_ok=True)
WGS='EPSG:4326'; AREA='ESRI:54009'
LOCAL='+proj=aeqd +lat_0=3 +lon_0=41 +datum=WGS84 +units=m +no_defs'
ANCHORS={'El Wak':(40.928779,2.807648),'Wargadud':(40.867395,3.183795),'Rhamu':(41.221595,3.929003),'Mandera':(41.857324,3.938421)}
def read(p):return json.loads(Path(p).read_text())
def save(p,d):Path(p).write_text(json.dumps(d,indent=2,ensure_ascii=False))
def polygon(g):
    g=S.make_valid(g) if not g.is_valid else g
    if g.is_empty:return Polygon()
    if g.geom_type in ('Polygon','MultiPolygon'):return g
    return unary_union([polygon(p) for p in g.geoms if p.area>0])
def move(g,a,b,poly=False):
    g=transform(Transformer.from_crs(a,b,always_xy=True).transform,g)
    g=polygon(g) if poly else g
    # A shared millimetre precision model prevents floating-point slivers at
    # coincident boundaries from turning into spurious polygon interiors.
    return S.set_precision(g,0.001) if b==AREA else g
def fc(p):return unary_union([shape(f['geometry']) for f in read(p)['features']])
def export(name,rows,crs=AREA):
    save(OUT/name,{'type':'FeatureCollection','features':[{'type':'Feature','properties':p,'geometry':mapping(move(g,crs,WGS,poly=g.area>0))} for g,p in rows if not g.is_empty]})

cluster_local=polygon(unary_union([move(shape(f['geometry']),WGS,LOCAL,True) for f in read(DATA/'mandera_triangle_boundary.geojson')['features']]))
route_source=WORK/'inputs/source_corridor_centreline.geojson'
parts=list(linemerge(fc(route_source)).geoms)
roads=read(WORK/'inputs/source_roads.json')
attributed=[f for f in roads['tertiaryRoads']['features'] if f['properties'].get('road_name')=='Khorof Harar -Kutulo Road']
assert len(attributed)==1
branch_ref=move(shape(attributed[0]['geometry']),WGS,LOCAL)
matches=[(i,move(g,WGS,LOCAL).intersection(branch_ref.buffer(2)).length) for i,g in enumerate(parts)]
drop=[i for i,n in matches if n>1000]
assert len(drop)==1,drop
excluded=move(parts[drop[0]],WGS,LOCAL)
assert 31500<excluded.length<31600
route=unary_union([move(g,WGS,LOCAL) for i,g in enumerate(parts) if i not in drop])
distances={n:route.distance(move(Point(p),WGS,LOCAL)) for n,p in ANCHORS.items()}
assert max(distances.values())<1000
band_local=polygon(route.buffer(10000,quad_segs=96).intersection(cluster_local))
cluster=move(cluster_local,LOCAL,AREA,True)
band=polygon(move(band_local,LOCAL,AREA,True).intersection(cluster))
outside=polygon(cluster.difference(band))
assert abs(cluster.area-band.area-outside.area)<1
regions_raw={}
for f in read(DATA/'mandera_admin2.geojson')['features']:
    regions_raw.setdefault(f['properties']['country'],[]).append(move(shape(f['geometry']),WGS,AREA,True))
countries={n:polygon(unary_union(gs).intersection(cluster)) for n,gs in regions_raw.items()}
vals=list(countries.values())
overlap=polygon(unary_union([vals[i].intersection(vals[j]) for i in range(len(vals)) for j in range(i+1,len(vals))]))
regions={n:polygon(g.difference(overlap)) for n,g in countries.items()}
regions['Unassigned or overlapping boundaries']=polygon(cluster.difference(unary_union(list(regions.values()))))
print('Country geometry area delta m2',sum(g.area for g in regions.values())-cluster.area,flush=True)
assert abs(sum(g.area for g in regions.values())-cluster.area)<100
route_check={'source':'Returned QGIS centreline from Kenya Geofabrik roads, kenya-260623-free.shp.zip',
 'source_sha256':hashlib.file_digest(open(route_source,'rb'),'sha256').hexdigest(),
 'route':'Isiolo–Mandera via El Wak, Wargadud and Rhamu',
 'reference':'https://kenha.co.ke/isiolo-modogashe-wajir-elwak-rhamu-manderaa13/',
 'correction':'Removed the unique merged branch matching the attributed Khorof Harar–Kutulo Road (old B9), which is not the named corridor. No new connecting lines were drawn.',
 'excluded_length_km':excluded.length/1000,'attributed_reference':attributed[0]['properties'],
 'overlap_with_reference_m':dict(matches)[drop[0]],'anchor_distances_m':distances,
 'route_length_in_cluster_km':route.intersection(cluster_local).length/1000,
 'retained_halo_route_length_km':route.length/1000,
 'extent':'Source centreline covers the cluster plus 15 km halo; the analysis buffer is 10 km. Clipping to the wider halo cannot truncate the band within the cluster.',
 'distance_method':'10,000 m buffer in local azimuthal equidistant CRS centred at 3N, 41E; 96 segments per quadrant; clipped to cluster; area allocation in Mollweide ESRI:54009',
 'local_crs':LOCAL,'status':'Geometry and named-route anchor checks passed; see route_review.png'}
save(OUT/'route_validation.json',route_check)
export('mandera_corridor_centreline.geojson',[(route,{'route':route_check['route'],'source':'© OpenStreetMap contributors / Geofabrik','coverage':'Cluster plus 15 km halo'})],LOCAL)
export('excluded_B9_side_road.geojson',[(excluded,{'name':'Khorof Harar–Kutulo Road','reason':'Separate named road sharing old B9 reference'})],LOCAL)
export('mandera_cluster.geojson',[(cluster,{'name':'Mandera Triangle'})])
export('mandera_country_regions.geojson',[(g,{'country':n}) for n,g in regions.items()])

source=WORK.parent/'data/mandera_worldpop2025_source_window.tif'
with rasterio.open(source) as ds:
    assert ds.crs.to_epsg()==4326 and ds.count==1
    b=move(cluster,AREA,WGS,True).bounds
    w=from_bounds(*b,ds.transform)
    left=max(0,math.floor(w.col_off));top=max(0,math.floor(w.row_off));right=min(ds.width,math.ceil(w.col_off+w.width));bottom=min(ds.height,math.ceil(w.row_off+w.height));window=Window(left,top,right-left,bottom-top)
    arr=ds.read(1,window=window); grid=ds.window_transform(window)
    nodata=ds.nodata
    profile=ds.profile.copy();profile.update(width=arr.shape[1],height=arr.shape[0],transform=grid,compress='deflate')
    cutout=OUT/'mandera_worldpop2025_source_window.tif'
    with rasterio.open(cutout,'w',**profile) as dst:dst.write(arr,1)
    source_info={'file':source.name,'sha256':hashlib.file_digest(open(source,'rb'),'sha256').hexdigest(),
      'url':'https://data.worldpop.org/GIS/Population/Global_2015_2030/R2025A/2025/0_Mosaicked/v1/1km_ua/constrained/'+source.name,
      'year':2025,'product':'WorldPop R2025A, constrained, UN-adjusted, 1 km, v1','nodata':nodata,
      'source_window':[int(window.col_off),int(window.row_off),int(window.width),int(window.height)],
      'crs':str(ds.crs),'cell_size_degrees':list(ds.res),'window_file':cutout.name,
      'window_sha256':hashlib.file_digest(open(cutout,'rb'),'sha256').hexdigest(),
      'method':'Integer pixel window copied without resampling. Original Float32 count values, no-data and grid alignment retained.'}
save(OUT/'population_source.json',source_info)
to_area=Transformer.from_crs(WGS,AREA,always_xy=True)
geographies={'Cluster':cluster,**regions}
totals={n:{'inside_population':0.,'outside_population':0.,'valid_area_m2':0.,'missing_area_m2':0.,'cells':0,'valid_cells':0} for n in geographies}
for g in [cluster,band,*regions.values()]:S.prepare(g)
counts=[]
max_overlay_adjustment_m2=0.
def clip_many(geometries,region):
    full=S.contains(region,geometries)
    partial=(~full)&S.intersects(region,geometries)
    result=np.empty(len(geometries),dtype=object);result[:]=Polygon()
    result[full]=geometries[full]
    if partial.any():result[partial]=S.intersection(geometries[partial],region)
    return result
for row in range(arr.shape[0]):
    xs=grid.c+np.arange(arr.shape[1])*grid.a;y=grid.f+row*grid.e
    vertices=np.stack([np.column_stack([xs,np.full_like(xs,y)]),np.column_stack([xs+grid.a,np.full_like(xs,y)]),np.column_stack([xs+grid.a,np.full_like(xs,y+grid.e)]),np.column_stack([xs,np.full_like(xs,y+grid.e)]),np.column_stack([xs,np.full_like(xs,y)])],axis=1)
    xx,yy=to_area.transform(vertices[:,:,0],vertices[:,:,1]);vertices[:,:,0]=xx;vertices[:,:,1]=yy
    cells=S.set_precision(S.polygons(vertices),0.001);keep=S.intersects(cluster,cells)
    cells=cells[keep];values=arr[row][keep].astype('float64');denom=S.area(cells)
    valid=np.isfinite(values)&(values>=0)&(values!=nodata)
    pieces=clip_many(cells,cluster);inside=clip_many(pieces,band)
    for n,g in geographies.items():
        pg=pieces if n=='Cluster' else clip_many(pieces,g)
        aa=S.area(pg);ii=S.area(inside if n=='Cluster' else clip_many(inside,g))
        # Millimetre snapping can move an intersection by at most a millimetre
        # along an edge. Use a perimeter-derived area tolerance, not a population
        # tolerance, and reject anything larger rather than silently clipping it.
        epsilon=S.length(cells)*0.002
        max_overlay_adjustment_m2=max(max_overlay_adjustment_m2,float(np.maximum(ii-aa,aa-denom).max(initial=0)))
        if not (np.all(ii<=aa+epsilon) and np.all(aa<=denom+epsilon)):
            save(OUT/'cell_overlay_diagnostic.json',{'row':row,'geography':n,'max_inside_excess_m2':float((ii-aa).max()),'max_cell_excess_m2':float((aa-denom).max()),'cells':[mapping(cells[i]) for i in np.where((ii>aa+0.01)|(aa>denom+0.01))[0]]})
            raise RuntimeError('Cell overlap bounds failed: '+(OUT/'cell_overlay_diagnostic.json').read_text()[:500])
        aa=np.clip(aa,0,denom);ii=np.clip(ii,0,aa);t=totals[n]
        t['inside_population']+=float(np.sum(values[valid]*ii[valid]/denom[valid]))
        t['outside_population']+=float(np.sum(values[valid]*(aa[valid]-ii[valid])/denom[valid]))
        t['valid_area_m2']+=float(aa[valid].sum());t['missing_area_m2']+=float(aa[~valid].sum())
        t['cells']+=int((aa>0).sum());t['valid_cells']+=int(((aa>0)&valid).sum())
    if row%50==0:print(f'Population rows {row+1}/{arr.shape[0]}',flush=True)
rows=[]
for n,t in totals.items():
    total=t['inside_population']+t['outside_population']
    rows.append({'geography':n,'population_year':2025,**t,'total_population':total,
      'inside_percent':100*t['inside_population']/total if total else None,
      'outside_percent':100*t['outside_population']/total if total else None,
      'raster_coverage_percent':100*t['valid_area_m2']/geographies[n].area,
      'area_km2':geographies[n].area/1e6,'inside_area_km2':geographies[n].intersection(band).area/1e6})
errors={k:sum(t[k] for n,t in totals.items() if n!='Cluster')-totals['Cluster'][k] for k in ['inside_population','outside_population','valid_area_m2','missing_area_m2']}
assert max(abs(errors[k]) for k in ['inside_population','outside_population'])<0.01
assert max(abs(errors[k]) for k in ['valid_area_m2','missing_area_m2'])<100
area_error=totals['Cluster']['valid_area_m2']+totals['Cluster']['missing_area_m2']-cluster.area
assert abs(area_error)<1000,area_error
validation={'country_minus_cluster':errors,'raster_grid_area_minus_cluster_m2':area_error,'max_cell_overlay_roundoff_m2':max_overlay_adjustment_m2,
 'geometries_valid':all(g.is_valid for g in [cluster,band,outside,*regions.values()]),
 'country_area_sum_minus_cluster_m2':sum(g.area for g in regions.values())-cluster.area,
 'inside_plus_outside_area_minus_cluster_m2':band.area+outside.area-cluster.area,
 'checks':'Original-cell overlaps; independent Cluster and country allocation; unassigned gaps/overlaps retained; nodata excluded and reported. Shared 1 mm coordinate precision for stable polygon overlays; source cell values are not resampled.',
 'status':'PASSED'}
limitations=['10 km is a chosen straight-line analytical width on each side, not a universal project catchment, travel distance or measured access.',
 'Counts are modelled WorldPop 2025 estimates, not a census or project beneficiary count.',
 'Partially intersected 1 km cells are allocated by overlap area in Mollweide, assuming uniform population within each source cell. Polygon overlays use a shared 1 mm coordinate precision to avoid floating-point topology errors. No raster resampling.',
 'Raster no-data, negative and nonfinite values are excluded and their area coverage reported; valid zero cells remain zero.',
 'Country boundaries are the existing map boundaries; small overlaps and gaps are kept as unassigned rather than guessed.',
 'Corridor follows mapped OSM geometry checked against the KeNHA route via El Wak and Rhamu; mapping completeness and alignment can affect estimates.']
result={'title':'Population near the Isiolo–Mandera corridor','cluster':'Mandera Triangle','route':route_check['route'],'width_each_side_km':10,'population_year':2025,'source':source_info,'rows':rows,'limitations':limitations,'validation':validation,'route_validation':route_check}
save(OUT/'mandera_corridor_population.json',result)
save(OUT/'population_validation.json',validation)
with open(OUT/'mandera_corridor_population.csv','w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
total=rows[0]
export('mandera_corridor_10km.geojson',[(band,{'zone':'Within 10 km','population_2025':total['inside_population'],'share_percent':total['inside_percent']}),(outside,{'zone':'Outside 10 km','population_2025':total['outside_population'],'share_percent':total['outside_percent']})])
print(json.dumps({'rows':rows,'validation':validation},indent=2),flush=True)
