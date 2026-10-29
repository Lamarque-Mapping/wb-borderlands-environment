"""Update the four decoded map pages, keeping analytical assets unchanged."""
import pathlib, re

ROOT = pathlib.Path(__file__).resolve().parents[2]
WORK = ROOT / '.work'
REV = '2026-10-29.panel-export.85'

EXPORT_STATE = r'''
function mapExportState(){
 const firstStyle=layer=>{
  if(!layer)return null;
  if(layer.options&&layer.options.color)return layer.options;
  let found=null;layer.eachLayer?.(child=>{if(!found)found=firstStyle(child);});return found;
 };
 const lineNames={borders:'International borders',cluster:'Cluster boundary',ruralCountryBorders:'Country divisions · SEDAC source',admin2:'District / zone boundaries',admin3:'Sub-district boundaries',primaryRoads:'Primary roads',secondaryRoads:'Secondary roads',tertiaryRoads:'Tertiary roads',tracks:'Tracks',paths:'Paths',railways:'Railways',powerTransmission:'Power transmission',pipelines:'Oil / gas pipelines'};
 const context=Object.entries(lineNames).filter(([key])=>active[key]).map(([key,label])=>{const s=firstStyle(active[key])||{};return {label,colour:s.color,opacity:s.opacity??1,weight:s.weight,dashArray:s.dashArray||''};}).filter(s=>s.colour);
 const contextReference=Object.entries(lineNames).map(([key,label])=>{const s=mapContextLineStyles()[key];return {label,colour:s.color,opacity:s.opacity??1,weight:s.weight,dashArray:s.dashArray||'',visible:!!active[key]};});
 let metric=sedac.exportMetric(),meta=null,layer=null;
 if(!metric&&ruralAccessActive()){
  const s=firstStyle(active.ruralAccess)||ruralAccessStyle({properties:{}});
  metric={label:'Rural population within 2 km of an all-season road',unit:'percent',low:0,high:100,opacity:s.fillOpacity,classes:ruralAccessBands.map((b,i)=>({label:b.label,colour:b.colour,max:i===4?100:b.upper,lower_inclusive:true,upper_inclusive:i===4})),noData:{label:'No valid rural-population denominator',colour:ruralAccessStyle({properties:{}}).fillColor},notes:['NASA SEDAC Rural Access Index · 2023 release. WorldPop 2020 population; OSM roads dated 31 March 2022.','Values describe whole SEDAC source units, including territory outside the cluster.']};
 }else if(!metric){
  if(themeMetricMeta(currentPreset)){meta=themeMetricMeta(currentPreset);layer=active.themeHex;}
  else if(currentPreset==='access'&&themeState.access==='travel'){meta=DATA.accessHexMetrics[currentAccessMode];layer=active.accessHex;}
  else if(currentPreset==='builtup'&&themeState.builtup==='raster'){meta=DATA.hexMetrics.builtUp;layer=active.builtNight;}
  else if(currentPreset==='dataHex'){meta=DATA.hexMetrics[currentHexMetric];layer=active.hexMetric;}
  else if(currentPreset==='climate'){meta=DATA.climateHexMetrics[currentClimateMode];layer=active.climateHex;}
  else if(analysisActive()){meta=currentAnalysisMeta();layer=active.analysisHex;}
  else if(environmentViews.includes(currentPreset)){meta=environmentMeta(currentPreset);layer=active.environmentHex;}
  if(meta){
   const s=firstStyle(layer)||layer?.options||{};
   const gradient=meta.gradient||'',stops=gradient.match(/#[0-9a-f]{6}/gi);
   metric={label:meta.label,unit:meta.unit,low:meta.low,high:meta.high,opacity:s.fillOpacity??s.opacity??1,classes:meta.classes,stops:meta.classes?undefined:stops,noData:currentPreset==='builtup'&&themeState.builtup==='raster'?undefined:{label:'No valid source value',colour:metricFill({properties:{}},meta)},notes:[meta.method||meta.summaryMethod||''].filter(Boolean)};
   if(meta.source_year)metric.notes.unshift('Source year: '+meta.source_year+'.');
   if(meta.transform&&meta.transform!=='linear')metric.transform=meta.transform;
  }
 }
 return {metric,context,contextReference};
}
'''

def patch_pages():
 for code in ['karamoja','dikhil','moyale_borana','mandera_triangle']:
  p=WORK/(code+'.html');s=p.read_text()
  if 'function mapExportState()' in s:continue
  names=['borders','cluster','ruralCountryBorders','admin2','admin3','primaryRoads','secondaryRoads','tertiaryRoads','tracks','paths','railways','powerTransmission','pipelines']
  entries=[]
  for name in names:
   match=re.search(r'  '+name+r':\(\)=>geo\((.*?),\{([^\n]+?)\},',s)
   if not match:raise ValueError('Missing context style: '+name)
   entries.append(name+':{'+match.group(2)+'}')
   old=match.group(0);s=s.replace(old,old[:old.index(',{')]+',mapContextLineStyles().'+name+',',1)
  s=s.replace('const defs={\n','function mapContextLineStyles(){return {'+','.join(entries)+'};}\nconst defs={\n')
  s=re.sub(r'sedac/sedac-v7.js\?v=[^"<]+',f'sedac/sedac-v8.js?v={REV}',s)
  s=re.sub(r'export/save-view-v5.css\?v=[^"<]+',f'export/save-view-v6.css?v={REV}',s)
  s=re.sub(r'<script src="export/save-view-v7.js\?v=[^"]+"></script>',f'<script src="export/legend-download-v1.js?v={REV}"></script><script src="export/save-view-v8.js?v={REV}"></script>',s)
  s=s.replace('window.setupWBMapExport({map,DATA,isReady:()=>viewReady});',EXPORT_STATE+'\nwindow.setupWBMapExport({map,DATA,isReady:()=>viewReady,getState:mapExportState});')
  s=s.replace('if(currentContext.has("majorCorridors"))rows.push(legendItem(\'<span class="swatch-line" style="border-color:#f97316"></span>\',\'Primary roads / railways\'));','if(currentContext.has("majorCorridors")){if(active.primaryRoads)rows.push(legendItem(\'<span class="swatch-line" style="border-color:#f97316"></span>\',\'Primary roads\'));if(active.railways)rows.push(legendItem(\'<span class="swatch-dash" style="border-color:#111827"></span>\',\'Railways\'));}')
  s=s.replace('if(currentContext.has("feederRoads"))rows.push(legendItem(\'<span class="swatch-line" style="border-color:#2563eb"></span>\',\'Secondary / tertiary roads\'));','if(currentContext.has("feederRoads")){if(active.secondaryRoads)rows.push(legendItem(\'<span class="swatch-line" style="border-color:#2563eb"></span>\',\'Secondary roads\'));if(active.tertiaryRoads)rows.push(legendItem(\'<span class="swatch-line" style="border-color:#7c3aed"></span>\',\'Tertiary roads\'));}')
  # Explicit links for the requested slide panels; normal navigation still opens Clean.
  s=s.replace("if(startView==='ruralAccess')themeState.access='ruralAccess';", "if(startView==='ruralAccess')themeState.access='ruralAccess';\nif(startView==='builtUp2018')themeState.builtup='builtUp';\nif(startView==='travelCities'){themeState.access='travel';currentAccessMode='travelCities';}")
  s=s.replace("await setPreset(startView==='ruralAccess'?'access':", "await setPreset(startView==='builtUp2018'?'builtup':startView==='travelCities'?'access':startView==='ruralAccess'?'access':")
  assert 'getState:mapExportState' in s
  p.write_text(s)

def patch_sedac():
 s=(ROOT/'sedac/sedac-v7.js').read_text()
 old=' return {load,controls,draw,legend,prepare,urbanActive,active,selectTown,state};'
 new=r''' function exportMetric(){
  if(!data||!metric())return null;
  const r=raster(),isHex=hexActive(),isGRDI=metric()==='grdi';
  return {label:isGRDI?(isHex?'Mean relative deprivation · 10 km hexes':'Relative deprivation index'):'Historical humid heat',unit:isGRDI?'index':'days/year',low:0,high:isGRDI?100:undefined,classes:r.bands.map(b=>({label:b.label,max:b.upper,colour:b.colour})),opacity:isHex?hexStyle({properties:{mean:0}}).fillOpacity:1,noData:{label:isHex?'No valid source pixels in this hex':'No source value',colour:isHex?hexStyle({properties:{mean:null}}).fillColor:'#e5e7eb',opacity:isHex?.9:.7},notes:isGRDI?['GRDI v1 · 2022 release · inputs 2010–2020.','Display bands, not official poverty categories. The index is not a poverty percentage.',...(isHex?['Area-weighted mean of available source pixels; not population-weighted.']:[])]:['Mean days above '+state.threshold+'°C WBGT · 1983–2016.']};
 }
 return {load,controls,draw,legend,prepare,urbanActive,active,selectTown,state,exportMetric};'''
 assert old in s
 (ROOT/'sedac/sedac-v8.js').write_text(s.replace(old,new))

if __name__=='__main__':
 patch_pages();patch_sedac()
