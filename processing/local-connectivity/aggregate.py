"""Aggregate the published junction nodes to existing COD-AB admin 2 units.
No network searches or source geometry edits. Run with Shapely 2.x.
"""
from pathlib import Path
import sys,json,hashlib,csv,gzip
from collections import defaultdict
sys.path.insert(0,str(Path(__file__).resolve().parent/'vendor'))
from shapely.geometry import shape,mapping,Point
from shapely.ops import unary_union
from shapely import make_valid

ROOT=Path(__file__).resolve().parent
INPUT=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'inputs'
OUT=Path(sys.argv[2]) if len(sys.argv)>2 else ROOT/'output';OUT.mkdir(parents=True,exist_ok=True)
CODES=['mandera_triangle','moyale_borana','karamoja','dikhil']
NAMES=['Mandera Triangle','Moyale–Borana','Karamoja','Dikhil']
SOURCE='© OpenStreetMap contributors / Geofabrik, 8 October 2026; ODbL 1.0'
def stats(nodes):
    n=len(nodes); t=sum(p['urban_10km'] for p in nodes);v=sum(p['place_10km'] for p in nodes)
    return dict(junctions=n,town_reached=t,town_share=t/n if n else None,place_reached=v,place_share=v/n if n else None)
def key(p):return '|'.join(p.get(k,'') for k in ['country','adm1_name','adm2_name'])
def identity(p):return 'd'+hashlib.sha256(key(p).encode()).hexdigest()[:16]
def write_json(name,data): (OUT/name).write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')))
all_clusters=[];audit=[]
for code,name in zip(CODES,NAMES):
    data=json.loads((INPUT/(code+'_connectivity.json')).read_text())
    admin=json.loads((INPUT/(code+'_admin.json')).read_text())
    core=json.loads((INPUT/(code+'_core.json')).read_text())
    cluster=unary_union([make_valid(shape(f['geometry'])) for f in core['cluster']['features']])
    groups=defaultdict(list); props={}
    for f in admin['admin2']['features']:
        p=f['properties'];k=identity(p);props[k]=p;groups[k].append(make_valid(shape(f['geometry'])))
    original={k:unary_union(gs) for k,gs in groups.items()}
    clipped={k:g.intersection(cluster) for k,g in original.items()}
    assigned=defaultdict(list); country_nodes=defaultdict(list);node_assignments={};issues=[]
    for f in data['nodes']['features']:
        p=f['properties'];pt=Point(f['geometry']['coordinates'])
        matches=[k for k,g in original.items() if g.covers(pt)]
        countries=sorted({props[k]['country'] for k in matches})
        country=countries[0] if len(countries)==1 else 'Unassigned boundaries'
        country_nodes[country].append(p)
        if len(matches)==1: k=matches[0];assigned[k].append(p)
        else:
            k='unassigned';assigned[k].append(p);issues.append({'osm_node_id':p['osm_node_id'],'matches':matches,'country':country})
        node_assignments[p['osm_node_id']]=k
    rows=[];features=[];fragments=[]
    for k,g in sorted(clipped.items(),key=lambda item:key(props[item[0]])):
        if g.is_empty or g.area==0:continue
        p=props[k]; fraction=g.area/original[k].area
        # Tiny incidental overlaps from differently rounded published outlines are
        # retained and labelled explicitly, rather than silently dropped.
        fragment=fraction<.001 and not assigned[k]
        if fragment:fragments.append({'id':k,'name':p['adm2_name'],'fraction':fraction})
        row={'id':k,'level':'district','name':p['adm2_name'] or p['name'],'country':p['country'],'admin1':p.get('adm1_name',''),'boundary_fragment':fragment,**stats(assigned[k])}
        rows.append(row)
        # Analysis uses full source polygons; this simplification is display only.
        simplified=g.simplify(.00015,preserve_topology=True)
        if simplified.geom_type not in ['Polygon','MultiPolygon']:
            parts=[x for x in getattr(simplified,'geoms',[]) if x.geom_type in ['Polygon','MultiPolygon']]
            simplified=unary_union(parts)
        if not simplified.is_empty:
            features.append({'type':'Feature','properties':row,'geometry':mapping(simplified)})
    if assigned['unassigned']:rows.append({'id':'unassigned','level':'district','name':'Unassigned district boundaries','country':'','admin1':'','boundary_fragment':False,**stats(assigned['unassigned'])})
    total={'id':'cluster','level':'cluster','name':name,'country':'','admin1':'',**stats([f['properties'] for f in data['nodes']['features']])}
    countries=[{'id':'country:'+c,'level':'country','name':c,'country':c,'admin1':'',**stats(ns)} for c,ns in sorted(country_nodes.items())]
    assert len(node_assignments)==data['summary']['junction_nodes']==total['junctions']
    for field in ['junctions','town_reached','place_reached']:
        assert sum(r[field] for r in rows)==total[field]
        assert sum(r[field] for r in countries)==total[field]
    for r in rows:
        assert r['town_share'] is None if not r['junctions'] else 0<=r['town_share']<=1
    result={'code':code,'name':name,'cluster':total,'countries':countries,'districts':rows}
    all_clusters.append(result)
    write_json(code+'.json',{'format':'wb-connectivity-districts-v1',**result,'boundaries':{'type':'FeatureCollection','features':features},'node_districts':node_assignments})
    fields=['cluster','level','id','name','country','admin1','junctions','town_reached','town_share','place_reached','place_share','boundary_fragment','source','path_limit_km','coverage']
    with (OUT/(code+'.csv')).open('w',newline='',encoding='utf-8-sig') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
        for r in [total,*countries,*rows]: writer.writerow({**r,'cluster':name,'source':SOURCE,'path_limit_km':10,'coverage':'OSM completeness not independently assessed'})
    raw_nodes={'type':'FeatureCollection','features':[]}
    for f in data['nodes']['features']:
        raw_nodes['features'].append({**f,'properties':{**{k:v for k,v in f['properties'].items() if not any(s in k for s in ['_2km','_5km'])},'district_id':node_assignments[f['properties']['osm_node_id']]}})
    write_json(code+'-junctions.geojson',raw_nodes)
    hashes={kind:hashlib.sha256((INPUT/(code+'_'+kind+'.json')).read_bytes()).hexdigest() for kind in ['connectivity','admin','core']}
    audit.append({'code':code,'source_sha256':hashes,'districts':len(rows),'boundary_fragments':fragments,'assignment_issues':issues,'totals':total,'checks':'Unique node IDs; district and country counts reconcile to source cluster totals; null percentages for zero denominators.'})
    print(code,'districts',len(rows),'fragments',len(fragments),'issues',issues,flush=True)
write_json('summary.json',{'format':'wb-connectivity-district-summary-v1','source':SOURCE,'clusters':all_clusters})
write_json('validation.json',audit)
