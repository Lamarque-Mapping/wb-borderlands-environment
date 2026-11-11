from pathlib import Path
import json, math, hashlib, subprocess, collections
import numpy as np
from scipy.ndimage import gaussian_filter
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm, LogNorm
from matplotlib.collections import PatchCollection, LineCollection
from matplotlib.patches import Polygon as MPolygon, Patch
from matplotlib import patheffects
from shapely.geometry import shape, Point, box, mapping
from shapely.ops import unary_union, transform
from shapely import make_valid
from pyproj import Transformer, CRS
import rasterio
from rasterio.features import rasterize
from rasterio.transform import from_origin

ROOT=Path(__file__).resolve().parent; DATA=ROOT/'live'; OUT=ROOT.parent/'deliverables';OUT.mkdir(exist_ok=True)
CODES=['karamoja','moyale_borana','mandera_triangle','dikhil']
NAMES={'karamoja':'Karamoja','moyale_borana':'Moyale–Borana','mandera_triangle':'Mandera Triangle','dikhil':'Dikhil'}
CRS_MAP=CRS.from_proj4('+proj=laea +lat_0=6.8 +lon_0=38 +datum=WGS84 +units=m +no_defs')
T=Transformer.from_crs(4326,CRS_MAP,always_xy=True); project=lambda g:transform(T.transform,g)
cores={c:json.loads((DATA/(c+'_core.json')).read_text()) for c in CODES}
G={c:project(unary_union([make_valid(shape(f['geometry'])) for f in cores[c]['cluster']['features']])) for c in CODES}
U=unary_union(list(G.values()))
# A single regional frame in an equal-area projection; units are metres.
EXT=(-830000,760000,-740000,865000)
RES=2000
x0,x1,y0,y1=EXT; W=math.ceil((x1-x0)/RES);H=math.ceil((y1-y0)/RES)
AFF=from_origin(x0,y1,RES,RES); REXT=(x0,x0+W*RES,y1-H*RES,y1)
MASK=rasterize([(U,1)],out_shape=(H,W),transform=AFF,fill=0,dtype='uint8').astype(bool)

world=json.loads((ROOT/'ne_50m_admin_0_countries.geojson').read_text())
COUNTRIES=[]
for f in world['features']:
 g=make_valid(shape(f['geometry']))
 if g.intersects(box(28,-2,48,17)):
  name=f['properties']['ADMIN']
  COUNTRIES.append((name,g))
# Natural Earth separates Somaliland for cartographic purposes; merge its fill into Somalia.
som=[g for n,g in COUNTRIES if n in ('Somalia','Somaliland')]
COUNTRIES=[(n,g) for n,g in COUNTRIES if n not in ('Somalia','Somaliland')]+[('Somalia',unary_union(som))]
COUNTRIES=[(n,project(g)) for n,g in COUNTRIES]

HEX={};AUDIT={};surfaces={}
for c in CODES:
 fs=json.loads((DATA/(c+'_hexes.json')).read_text())['hexGrid']['features']
 HEX[c]=[(project(make_valid(shape(f['geometry']))).intersection(G[c]),f['properties']) for f in fs]
 AUDIT[c]={'name':NAMES[c],'hex_count':len(fs),'area_km2':G[c].area/1e6,'layers':{}}
 for prop in ['wb_hex_drought','wb_hex_river_flood','wb_hex_walking_health','wb_hex_motor_health']:
  vals=[p.get(prop) for g,p in HEX[c]]
  valid=[float(v) for v in vals if v is not None and np.isfinite(v)]
  AUDIT[c]['layers'][prop]={'valid':len(valid),'missing':len(vals)-len(valid),'zeros':sum(v==0 for v in valid),'min':min(valid),'max':max(valid),'missing_area_km2':sum(g.area for g,p in HEX[c] if p.get(prop) is None)/1e6}

for prop in ['wb_hex_drought','wb_hex_river_flood']:
 total=np.zeros((H,W),float);n=np.zeros((H,W),np.uint8);overlapdiff=[];prior=None
 for c in CODES:
  items=[(g,float(p[prop])) for g,p in HEX[c] if p.get(prop) is not None and not g.is_empty]
  arr=rasterize(items,out_shape=(H,W),transform=AFF,fill=np.nan,dtype='float64')
  good=np.isfinite(arr)&MASK
  if prior is not None:
   ov=good&np.isfinite(prior)
   if ov.any():overlapdiff.extend(np.abs(arr[ov]-prior[ov]).tolist())
  total[good]+=arr[good];n[good]+=1;prior=np.where(good,arr,np.nan if prior is None else prior)
 val=np.full((H,W),np.nan);np.divide(total,n,out=val,where=n>0);val[~MASK]=np.nan
 surfaces[prop]=val
 print(prop,'max',np.nanmax(val),'overlap difference p95',np.quantile(overlapdiff,.95) if overlapdiff else None,flush=True)

records={};dups=0;conflicts=[];typecounts=collections.Counter();max_counts=collections.Counter();source_total=0
for c in CODES:
 fs=json.loads((DATA/(c+'_acled.json')).read_text())['acled']['features']
 local_counts=collections.Counter()
 for f in fs:
  source_total+=1
  eid=hashlib.sha256(json.dumps(f,sort_keys=True,separators=(',',':')).encode()).hexdigest()
  local_counts[eid]+=1
  if local_counts[eid]>max_counts[eid]:
   records[eid+'_'+str(local_counts[eid])]=f
 for eid,n in local_counts.items():max_counts[eid]=max(max_counts[eid],n)
dups=source_total-len(records)
points=[]
for f in records.values():
 x,y=T.transform(*f['geometry']['coordinates'][:2]);points.append((x,y));typecounts[f['properties']['event_type']]+=1
hist=np.zeros((H,W),float)
for x,y in points:
 col=int((x-x0)//RES);row=int((y1-y)//RES)
 if 0<=row<H and 0<=col<W:hist[row,col]+=1
heat=gaussian_filter(hist,sigma=25000/RES,mode='constant',truncate=3)/(RES/1000)**2*1000
heat[~MASK]=np.nan
print('ACLED unique',len(records),'duplicates',dups,'max density',np.nanmax(heat),'types',typecounts,flush=True)
assert not conflicts
assert hist.sum()==len(records)

BG='#ffffff'; LAND='#f2f3f1'; SEA='#edf4f5'; INK='#23353d'; MUTED='#66767a'; BORDER='#9da7a8';GREEN='#285b4d'
CLUSTER_COLOURS={'karamoja':('#a9cabc','#285b4d'),'moyale_borana':('#afc9df','#3c617c'),'mandera_triangle':('#e6c798','#876333'),'dikhil':('#c6b5d4','#705486')}
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'text.color':INK,'axes.labelcolor':INK,'hatch.linewidth':.4})

def polygons(g):
 if g.geom_type=='Polygon':yield g
 elif hasattr(g,'geoms'):
  for z in g.geoms:yield from polygons(z)
def draw_polys(ax,g,face,edge='none',lw=.5,z=1,alpha=1):
 ps=[MPolygon(np.asarray(p.exterior.coords),closed=True) for p in polygons(g)]
 pc=PatchCollection(ps,facecolor=face,edgecolor=edge,linewidth=lw,zorder=z,alpha=alpha,antialiaseds=True)
 ax.add_collection(pc);return pc
def lines(ax,g,color=INK,lw=1,z=6,style='solid'):
 segs=[]
 for p in polygons(g):
  segs.append(np.asarray(p.exterior.coords))
  # Small internal artefacts are omitted from display only.
  for r in p.interiors:
   if abs(shape({'type':'Polygon','coordinates':[list(r.coords)]}).area)>2e7:segs.append(np.asarray(r.coords))
 ax.add_collection(LineCollection(segs,colors=color,linewidths=lw,zorder=z,linestyles=style))
def text_at(ax,lon,lat,s,fs=10,colour=MUTED,weight='normal',z=8,ha='center'):
 x,y=T.transform(lon,lat);t=ax.text(x,y,s,fontsize=fs,color=colour,weight=weight,ha=ha,va='center',zorder=z)
 t.set_path_effects([patheffects.withStroke(linewidth=2.5,foreground='white',alpha=.86)])
 return t

def base(ax,small=False):
 ax.set_facecolor(SEA)
 for name,g in COUNTRIES:draw_polys(ax,g,LAND,BORDER,.55 if not small else .4)
 ax.set_xlim(x0,x1);ax.set_ylim(y0,y1);ax.set_aspect('equal');ax.set_xticks([]);ax.set_yticks([])
 for sp in ax.spines.values():sp.set_visible(False)
 fs=9 if small else 12
 for lon,lat,s in [(34.3,9.5,'SOUTH SUDAN'),(37.0,9.8,'ETHIOPIA'),(35.9,0.8,'KENYA'),(31.55,1.25,'UGANDA'),(45.0,6.3,'SOMALIA'),(39.2,14.1,'ERITREA')]:
  text_at(ax,lon,lat,s,fs,colour='#8b9597',z=2)
 # labels for small countries use leader lines to avoid obscuring Dikhil.
 text_at(ax,44.5,11.1,'DJIBOUTI',fs-1,colour='#8b9597',z=2)
 text_at(ax,44.2,1.4,'INDIAN\nOCEAN',fs,colour='#a3b7bd',z=2)
 return ax

# Names remain outside high-density areas and use direct leaders.
LABELS={'karamoja':((32.7,6.0),(30.8,7.7),'left'),
'moyale_borana':((37.7,4.0),(35.3,7.45),'left'),
'mandera_triangle':((42.4,3.5),(43.45,7.5),'left'),
'dikhil':((42.45,11.6),(43.6,13.55),'left')}
def border_lines(ax):
 segs=[]
 def add(g):
  if g.geom_type=='LineString':segs.append(np.asarray(g.coords))
  elif hasattr(g,'geoms'):
   for part in g.geoms:add(part)
 border=unary_union([project(make_valid(shape(f['geometry']))) for c in CODES for f in cores[c]['borders']['features']]).intersection(U)
 add(border)
 ax.add_collection(LineCollection(segs,colors='#53686c',linewidths=.55,linestyles=(0,(3,2)),zorder=5))
def cluster_labels(ax,small=False,distinguish=False):
 border_lines(ax)
 for c,(point,lab,ha) in LABELS.items():
  px,py=T.transform(*point);lx,ly=T.transform(*lab)
  txt=NAMES[c].replace('Mandera Triangle','Mandera\nTriangle') if small else NAMES[c]
  colour=CLUSTER_COLOURS[c][1] if distinguish else GREEN
  an=ax.annotate(txt,xy=(px,py),xytext=(lx,ly),fontsize=10 if small else 12.5,weight='bold',color=colour,ha=ha,va='center',zorder=15,
   arrowprops=dict(arrowstyle='-',lw=.8,color=colour,connectionstyle='angle3,angleA=0,angleB=90',shrinkA=4,shrinkB=0),
   bbox=dict(facecolor='white',edgecolor='none',pad=2,alpha=.94))
def scales(ax,small=False):
 sx,sy=x0+95000,y0+40000
 ax.plot([sx,sx+200000],[sy,sy],color=INK,lw=1.4,zorder=15)
 for x in [sx,sx+100000,sx+200000]:ax.plot([x,x],[sy-7000,sy+7000],color=INK,lw=1,zorder=15)
 ax.text(sx,sy+19000,'0',fontsize=8,ha='center');ax.text(sx+200000,sy+19000,'200 km',fontsize=8,ha='center')
 ax.annotate('N',xy=(x1-70000,y1-140000),xytext=(x1-70000,y1-240000),ha='center',fontsize=10,color=INK,arrowprops=dict(arrowstyle='-|>',color=INK,lw=1),zorder=15)

def frame(title,subtitle):
 fig=plt.figure(figsize=(16,9),facecolor=BG)
 fig.text(.045,.944,title,fontsize=26,weight='bold',ha='left')
 fig.text(.045,.901,subtitle,fontsize=12.5,color=MUTED)
 fig.add_artist(plt.Line2D([.045,.955],[.874,.874],transform=fig.transFigure,color='#d3dcd9',lw=.8))
 return fig

def footer(fig,source,extra=''):
 fig.text(.045,.060,source,fontsize=8.2,color=MUTED)
 if extra:fig.text(.045,.040,extra,fontsize=8.2,color=MUTED)
 fig.text(.045,.020,'Boundaries and names shown do not imply official endorsement.',fontsize=7.5,color='#869196')
def aside(fig,title,lines_text):
 fig.text(.69,.745,title,fontsize=14,weight='bold',color=INK)
 fig.text(.69,.694,lines_text,fontsize=12.5,color=MUTED,linespacing=1.7,va='top')
def save(fig,name):
 path=OUT/name;fig.savefig(path,dpi=240,facecolor='white');plt.close(fig);print('saved',path,flush=True)

def single_map(title,subtitle):
 fig=frame(title,subtitle);ax=base(fig.add_axes([.032,.105,.63,.745]));return fig,ax

fig,ax=single_map('Four priority borderland clusters','Regional overview · cross-border programme areas')
for c,g in G.items():draw_polys(ax,g,CLUSTER_COLOURS[c][0],z=4)
overlap=G['moyale_borana'].intersection(G['mandera_triangle'])
shared=draw_polys(ax,overlap,'#d4d3be',edge='#7c8378',lw=0,z=4.5)
shared.set_hatch('////')
for c,g in G.items():lines(ax,g,CLUSTER_COLOURS[c][1],1.2,6)
cluster_labels(ax,distinguish=True);scales(ax)
fig.text(.69,.745,'Priority clusters',fontsize=14,weight='bold',color=INK)
legax=fig.add_axes([.69,.43,.265,.28]);legax.axis('off')
for i,c in enumerate(CODES):
 y=.88-i*.24;fill,edge=CLUSTER_COLOURS[c]
 legax.add_patch(plt.Rectangle((0,y-.045),.075,.09,facecolor=fill,edgecolor=edge,lw=.7))
 legax.text(.13,y,NAMES[c],fontsize=12.5,va='center',color=edge)
fig.text(.69,.34,'Cluster footprints overlap in parts\nof Moyale–Borana and Mandera.',fontsize=11.5,color=MUTED,linespacing=1.5)
ax2=fig.add_axes([.69,.23,.25,.06]);ax2.axis('off');ax2.add_patch(plt.Rectangle((0,.3),.10,.3,facecolor='#d4d3be',edgecolor='#7c8378',hatch='////',lw=.5));ax2.text(.15,.45,'Shared footprint',va='center',fontsize=11.5)
footer(fig,'Cluster outlines assembled from OCHA Common Operational Datasets (administrative boundaries). Basemap: Natural Earth.','Hatching marks areas shared by the Moyale–Borana and Mandera Triangle clusters.')
save(fig,'01_Four_Priority_Clusters.png')

fig,ax=single_map('Concentrations of recorded ACLED events','1 August 2020–1 August 2025 · all four priority clusters')
draw_polys(ax,U,'#fffaf2',z=3)
cmap=ListedColormap(['#fff4cf','#fee0a3','#fdbb72','#f48a4c','#df4c2c','#af1f26','#6e0d23'])
bins=[0,.5,1,2,5,10,20,100];norm=BoundaryNorm(bins,cmap.N)
ax.imshow(np.ma.masked_where(~MASK,heat),extent=REXT,origin='upper',cmap=cmap,norm=norm,zorder=4,interpolation='nearest')
for g in G.values():lines(ax,g,GREEN,.8,6)
cluster_labels(ax);scales(ax)
fig.text(.69,.755,'Recorded event density',fontsize=14,weight='bold')
fig.text(.69,.715,'Events per 1,000 km²\nSmoothed over 25 km',fontsize=11.5,color=MUTED,linespacing=1.5)
legax=fig.add_axes([.69,.34,.25,.30]);legax.axis('off')
labels=['Less than 0.5','0.5–1','1–2','2–5','5–10','10–20','20 or more']
for i,(color,lab) in enumerate(zip(cmap.colors,labels)):
 y=.92-i*.135;legax.add_patch(plt.Rectangle((0,y-.035),.07,.075,facecolor=color,edgecolor='#d1d5db',lw=.4));legax.text(.11,y,lab,fontsize=11.5,va='center')
fig.text(.69,.27,f'{len(records):,} unique recorded events',fontsize=12,weight='bold')
fig.text(.69,.225,'Includes violence, riots and protests.\nOne shared scale across all clusters.',fontsize=11,color=MUTED,linespacing=1.5)
footer(fig,'Source: ACLED, 1 August 2020–1 August 2025. Events counted equally; duplicate records removed where cluster boundaries overlap.','Event concentrations smoothed over 25 km; records outside the four clusters excluded. Reporting and location precision vary; not a risk forecast.')
save(fig,'02_ACLED_Event_Concentrations.png')

DROUGHT_COL=['#fff9d0','#ffe398','#fec064','#f58b43','#d9532c','#952032']
FLOOD_COL=['#f8fbfe','#d7eaf5','#a9d1e8','#6caed6','#3182bd','#08519c']
DBINS=[0,.25,.5,.75,1,1.5,2];FBINS=[0,.00000001,.02,.05,.1,.25,1.5]
NODATA='#b9bfc1'
def hazard(ax,prop):
 arr=surfaces[prop];drought=prop=='wb_hex_drought';colors=DROUGHT_COL if drought else FLOOD_COL;bins=DBINS if drought else FBINS
 basearr=np.ma.masked_where(~MASK,np.where(np.isfinite(arr),arr,-999))
 cmap=ListedColormap(colors);cmap.set_under(NODATA)
 ax.imshow(basearr,extent=REXT,origin='upper',cmap=cmap,norm=BoundaryNorm(bins,len(colors)),zorder=4,interpolation='nearest')
 for g in G.values():lines(ax,g,GREEN,.75,6)
 return cmap

def hazard_legend(fig,pos,drought,compact=False):
 ax=fig.add_axes(pos);ax.axis('off')
 colors=DROUGHT_COL if drought else FLOOD_COL
 labs=['0–0.25','0.25–0.5','0.5–0.75','0.75–1','1–1.5','1.5–2'] if drought else ['0','>0–0.02','0.02–0.05','0.05–0.1','0.1–0.25','0.25–1.5']
 if compact:
  for i,(color,lab) in enumerate(zip(colors,labs)):
   ax.add_patch(plt.Rectangle((i/6,.52),1/6,.20,facecolor=color,edgecolor='white',lw=.4));ax.text((i+.5)/6,.25,lab,fontsize=8,ha='center')
  ax.add_patch(plt.Rectangle((.0,-.15),.035,.18,facecolor=NODATA,clip_on=False));ax.text(.05,-.06,'No valid data',fontsize=8.5,va='center')
 else:
  for i,(color,lab) in enumerate(zip(colors+[NODATA],labs+['No valid data'])):
   y=.91-i*.13;ax.add_patch(plt.Rectangle((0,y-.035),.07,.07,facecolor=color,edgecolor='#d1d5db',lw=.4));ax.text(.11,y,lab,fontsize=11.5,va='center')

for prop,drought,num in [('wb_hex_drought',True,'04'),('wb_hex_river_flood',False,'05')]:
 title='Drought hazard across the four clusters' if drought else 'River-flood hazard across the four clusters'
 subtitle='Modelled months at SPEI ≤ −2.0 · 25-year return period' if drought else 'Modelled inundation depth · historical baseline · 25-year return period'
 fig,ax=single_map(title,subtitle);hazard(ax,prop);cluster_labels(ax);scales(ax)
 fig.text(.69,.755,'Months at SPEI ≤ −2.0' if drought else 'Mean flood depth (metres)',fontsize=14,weight='bold')
 fig.text(.69,.709,'Mean within each 10 km hexagon',fontsize=11.5,color=MUTED)
 hazard_legend(fig,[.69,.32,.25,.33],drought)
 fig.text(.69,.25,'Grey means no valid data.\nIt does not mean zero hazard.',fontsize=11.5,color=MUTED,linespacing=1.5)
 footer(fig,('Source: Weller & Mann (2022), Global Drought Hazard, IFHV / HDX; climate inputs: CSIC SPEI, 1902–2018.' if drought else 'Source: World Resources Institute, Aqueduct Floods. Historical river-flood hazard; no flood-protection adjustment.'),('Values are averages for 10 km hexagons; grey indicates no valid data.' if drought else 'Values are mean modelled water depths within 10 km hexagons. Grey indicates no valid data; this is not a current flood warning.'))
 save(fig,num+('_Drought_Hazard.png' if drought else '_River_Flood_Hazard.png'))

fig=frame('Drought and flood hazards across the four clusters','Historical/modelled hazards · 25-year return periods · shared scales within each panel')
for left,prop,title,sub in [(.045,'wb_hex_drought','Drought hazard','Modelled months at SPEI ≤ −2.0'),(.525,'wb_hex_river_flood','River-flood hazard','Mean modelled inundation depth (metres)')]:
 fig.text(left,.825,title,fontsize=16,weight='bold');fig.text(left,.793,sub,fontsize=10,color=MUTED)
 ax=base(fig.add_axes([left,.238,.43,.54]),small=True);hazard(ax,prop);cluster_labels(ax,True);scales(ax,True)
 hazard_legend(fig,[left+.015,.12,.40,.09],prop=='wb_hex_drought',True)
footer(fig,'Sources: Weller & Mann (2022), Global Drought Hazard (IFHV / HDX; CSIC SPEI, 1902–2018); WRI Aqueduct Floods.','Values are 10 km hexagon averages; grey indicates no valid data.')
save(fig,'03_Drought_and_Flood_Hazards.png')

meta={'site':'https://lamarque-mapping.github.io/wb-borderlands-environment/','site_commit':subprocess.check_output(['git','-C',str(ROOT.parent/'live_repo'),'rev-parse','HEAD'],text=True).strip(),'build_id':cores['karamoja']['build_id'],'data_period':cores['karamoja']['acledYearRange'],'acled':{'unique_events':len(records),'duplicate_records_removed':dups,'deduplication':'Exact full exported record including geometry and notes; maximum within-cluster multiplicity retained. Published exports do not retain ACLED event IDs.','event_types':dict(typecounts),'bandwidth_km':25,'cell_km':2,'normalization':'events per 1000 square kilometres, accumulated over the source period','outside_cluster_events':'not included; surface masked to union of four clusters'},'clusters':AUDIT,'drought_classes':DBINS,'flood_classes':FBINS,'display_overlap':'Valid per-cluster hex means averaged where footprints overlap; a missing observation never overwrites a valid one. No filling outside valid hex coverage.','projection':CRS_MAP.to_string(),'grey':'No valid exported numeric value; distinct from zero.'}
(OUT/'Map_Data_Audit.json').write_text(json.dumps(meta,indent=2))
