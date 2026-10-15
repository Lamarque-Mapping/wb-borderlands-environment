from pathlib import Path
import json,re,shutil
ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent/'source_balance'
REV='2026-10-15.grdi-hex.50'
def once(s,old,new):
 assert s.count(old)==1,old[:100]
 return s.replace(old,new,1)
js=(BASE/'site/sedac/sedac-v3.js').read_text()
js=once(js,"threshold:'28',pixel:null","threshold:'28',pixel:null,grdiDisplay:'hex',hex:null")
js=once(js,'let data,promise;','let data,promise,hexData,hexPromise,hexLayer;')
js=once(js," const active=", " const hexActive=(name=currentView())=>metric(name)==='grdi'&&state.grdiDisplay==='hex';\n const active=")
js=once(js,'polyLayer=null;}','polyLayer=null;hexLayer=null;}')
js=once(js,"state.pixel=null;}\n function add", "state.pixel=null;state.hex=null;}\n function add")
js=once(js,"async function load(group){if(group!=='sedac')", """async function load(group){
  if(group==='grdiHex'){
   if(!hexPromise)hexPromise=parent.WBVault.json(DATA.code+'/grdiHex').then(d=>{if(d.format!=='wb-grdi-hex-v1'||d.code!==DATA.code)throw Error('Invalid GRDI hex data');hexData=d;}).catch(e=>{hexPromise=null;throw e;});
   await hexPromise;return true;
  }
  if(group!=='sedac')""")
js=once(js,"   const r=raster(),kind=metric();", """   const r=raster(),kind=metric();
   if(kind==='grdi')select(box,'Deprivation display','grdiDisplay',[['hex','10 km hexagons'],['grid','Source grid · approximately 1 km']],state.grdiDisplay,v=>{state.grdiDisplay=v;setPreset('population',{keepContext:true});});""")
js=once(js,"num(r.summary.coverage_share*100,1)","num((hexActive()?hexData.summary.mapped_area_share:r.summary.coverage_share)*100,1)")
js=once(js,"<small>Grey = no source value. Missing data are not zero.</small>","<small>Grey = no source value. Missing data are not zero.</small>")
js=once(js,"   note(box,'Click the map to read the source-grid value.');", "   note(box,hexActive()?'Hex colours average the mapped parts only. Click a hex to see its value and source coverage.':'Click the map to read the source-grid value.');")
js=once(js,"button(box,'Download mapped values · CSV',downloadGrid);", "button(box,hexActive()?'Download hex values · CSV':'Download mapped values · CSV',hexActive()?downloadHexes:downloadGrid);")
js=once(js,'It is not the percentage of people in poverty; missing building-footprint coverage', 'Hex means weight each available pixel by its area of overlap with the existing cluster-clipped 10 km grid (equal-area projection). Gaps are excluded, never filled or counted as zero; these are not population-weighted means. It is not the percentage of people in poverty; missing building-footprint coverage')
helper=''' function downloadHexes(){const keys=['cell_id','mean','coverage_pct','source_pixels','mapped_km2','hex_km2'];csv(DATA.code+'_relative_deprivation_10km_hexes.csv',[...keys,'reference','weighting'],hexData.features.map(f=>[...keys.map(k=>f.properties[k]),'GRDI v1 inputs 2010–2020','valid pixel–hex overlap area; not population']));}
 function hexStyle(f){const p=f.properties,selected=state.hex===p.cell_id,b=p.mean===null?null:data.grdi.bands.find(b=>p.mean<=b.upper);return {color:selected?'#201037':'#fff',weight:selected?2.5:.65,opacity:1,fillColor:b?b.colour:'#e5e7eb',fillOpacity:.9};}
 function selectHex(f){
  state.hex=f?f.properties.cell_id:null;hexLayer?.setStyle(hexStyle);const box=$('sedacSelection');if(!box)return;
  if(!f){box.replaceChildren();return;}const p=f.properties;
  box.innerHTML='<header><div><small>10 km analysis hex · '+esc(p.cell_id)+'</small></div><button id="sedacClear" type="button" aria-label="Clear hex selection">×</button></header><div class="sedac-value">'+(p.mean===null?'No source value':num(p.mean,1))+'</div><small>Mean relative deprivation index · 0–100</small><dl><dt>Source coverage within this hex</dt><dd><strong>'+num(p.coverage_pct,1)+'%</strong> · '+num(p.mapped_km2,2)+' of '+num(p.hex_km2,2)+' km²</dd><dt>Source pixels contributing</dt><dd>'+num(p.source_pixels)+'</dd></dl><p class="sedac-note">'+(p.mean===null?'No valid source pixels overlap this hex. This is not a zero value.':'Average of the mapped parts only, weighted by their area. Unmapped parts may differ. This is not a poverty percentage or a population-weighted estimate.')+'</p>';
  $('sedacClear').onclick=()=>selectHex(null);showSidebar();box.scrollIntoView({block:'nearest'});
 }
 function drawHexes(){
  hexLayer=add(L.geoJSON(hexData,{pane:'hexPane',renderer:svgRenderer('hexPane'),bubblingMouseEvents:false,style:hexStyle,onEachFeature:(f,l)=>{
   const p=f.properties,label='Hex '+p.cell_id+' · '+(p.mean===null?'No source value':'Mean index '+num(p.mean,1))+' · '+num(p.coverage_pct,1)+'% source coverage';
   l.bindTooltip(esc(label),{sticky:true});l.on('click',e=>{if(e.originalEvent)L.DomEvent.stopPropagation(e.originalEvent);selectHex(f);l.bringToFront();});
   l.on('add',()=>{const el=l.getElement();if(!el)return;el.setAttribute('role','button');el.setAttribute('tabindex','0');el.setAttribute('aria-label',label);el.classList.add('sedac-path');el.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();selectHex(f);l.bringToFront();}};});
  }}));
 }
'''
js=once(js,' function draw(name){',helper+' function draw(name){')
js=once(js,"  if(urbanActive(name)){drawTowns();return;}","  if(urbanActive(name)){drawTowns();return;}\n  if(hexActive(name)){drawHexes();return;}")
js=once(js,'<strong>Relative deprivation index · 0–100</strong>',"<strong>'+ (hexActive(name)?'Mean relative deprivation · 10 km hexes':'Relative deprivation index · source grid')+' · 0–100</strong>")
js=once(js,'Inputs: 2010–2020 · approximately 1 km grid.<br>Same scale across all four maps.',"'+(hexActive(name)?'Mean of mapped parts only. Click a hex for source coverage.':'Approximately 1 km source grid.')+'<br>Inputs: 2010–2020 · same scale across all four maps.")
js=once(js,"map.on('click',e=>{if(metric())readPixel(e.latlng);", "map.on('click',e=>{if(hexActive())selectHex(null);else if(metric())readPixel(e.latlng);")
site=ROOT/'site';(site/'sedac').mkdir(parents=True,exist_ok=True);(site/'sedac/sedac-v4.js').write_text(js)
method=' The 10 km hex view uses the existing cluster-clipped analysis grid. Hex means are weighted by the exact area of overlap with valid source pixels in an equal-area projection (EPSG:6933), without population weighting. Each hex reports source coverage; gaps are excluded and a hex with no valid source data has no value. The mean describes only the mapped parts and must not be read as an estimate for unmapped parts.'
for filename in [f'page_map_{c}.html' for c in ['mandera_triangle','moyale_borana','karamoja','dikhil']]+['analysis.html']:
 page=(BASE/'working'/filename).read_text()
 needle='Raster values and source-grid alignment are retained; the overview image uses nearest-neighbour reprojection, and click values use the original grid. No admin-unit join is inferred.'
 page=once(page,needle,needle+method)
 if filename!='analysis.html':
  page=once(page,'sedac/sedac-v3.js?v=2026-10-15.views.49','sedac/sedac-v4.js?v='+REV)
  page=once(page,"themeState.population==='deprivation'?['sedac']", "themeState.population==='deprivation'?['sedac','grdiHex']")
 (ROOT/'working'/filename).write_text(page)
print('Updated shared controls and all five sources tables.')
