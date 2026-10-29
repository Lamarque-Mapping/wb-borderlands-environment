'use strict';
window.createWBSEDAC=function({DATA,map,svgRenderer,setPreset,currentView,populationMode,showSidebar}){
 const $=id=>document.getElementById(id),esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),num=(v,d=0)=>Number.isFinite(v)?v.toLocaleString('en-GB',{maximumFractionDigits:d}):'Not available';
 const backgroundPane=map.createPane('sedacNoDataPane');backgroundPane.style.zIndex='350';backgroundPane.style.pointerEvents='none';
 const state={townSource:'osm',footprints:true,town:null,threshold:'28',pixel:null,hex:null};
 let data,promise,hexData,hexPromise,hexLayer;const layers=[],lookup=new Map();let pointLayers=new Map(),polyLayer;
 const urbanActive=(name=currentView())=>name==='crossings'&&state.townSource==='sedac';
 const metric=(name=currentView())=>name==='population'&&['deprivation','deprivationHex'].includes(populationMode())?'grdi':name==='heat'?'heat':null;
 const hexActive=(name=currentView())=>metric(name)==='grdi'&&populationMode()==='deprivationHex';
 const active=(name=currentView())=>urbanActive(name)||!!metric(name);
 const raster=()=>metric()==='grdi'?data.grdi:data.heat[state.threshold];
 function clear(){for(const layer of layers)map.removeLayer(layer);layers.length=0;pointLayers.clear();polyLayer=null;hexLayer=null;}
 function prepare(){clear();document.body.classList.remove('deprivation-view');state.pixel=null;state.hex=null;}
 function add(layer){layers.push(layer);layer.addTo(map);return layer;}
 async function load(group){
  if(group==='grdiHex'){
   if(!hexPromise)hexPromise=parent.WBVault.json(DATA.code+'/grdiHex').then(d=>{if(d.format!=='wb-grdi-hex-v1'||d.code!==DATA.code)throw Error('Invalid GRDI hex data');hexData=d;}).catch(e=>{hexPromise=null;throw e;});
   await hexPromise;return true;
  }
  if(group!=='sedac')return false;if(data)return true;if(!promise)promise=parent.WBVault.json(DATA.code+'/sedac').then(async d=>{if(d.format!=='wb-sedac-v1'||d.code!==DATA.code)throw Error('Invalid SEDAC data');await recolourGRDI(d.grdi);data=d;for(const f of d.settlements.features)lookup.set(f.properties.sedac_id,f);for(const r of [d.grdi,...Object.values(d.heat)])r.values=new Map(r.cells);}).catch(e=>{promise=null;throw e;});await promise;return true;}
 const grdiPalette=['#f2f0f7','#cbc9e2','#9e9ac8','#756bb1','#54278f'];
 async function recolourGRDI(r){
  // Recolour the already-projected display image; native values and geometry stay untouched.
  const img=new Image();img.src=r.image;await img.decode();
  const canvas=document.createElement('canvas');canvas.width=img.naturalWidth;canvas.height=img.naturalHeight;
  const ctx=canvas.getContext('2d');ctx.drawImage(img,0,0);const pixels=ctx.getImageData(0,0,canvas.width,canvas.height),rgba=pixels.data;
  const colours=new Map(r.bands.map((b,i)=>[parseInt(b.colour.slice(1),16),grdiPalette[i].slice(1).match(/../g).map(x=>parseInt(x,16))]));
  for(let i=0;i<rgba.length;i+=4){if(!rgba[i+3])continue;const colour=colours.get((rgba[i]<<16)|(rgba[i+1]<<8)|rgba[i+2]);if(!colour)throw Error('Unexpected GRDI display colour');rgba.set(colour,i);}
  ctx.putImageData(pixels,0,0);r.image=canvas.toDataURL('image/png');r.bands.forEach((b,i)=>b.colour=grdiPalette[i]);
 }
 function select(box,label,id,choices,value,change){const l=document.createElement('label');l.textContent=label;const s=document.createElement('select');s.id=id;for(const [v,t] of choices){const o=document.createElement('option');o.value=v;o.textContent=t;s.appendChild(o);}s.value=value;s.onchange=()=>change(s.value);l.appendChild(s);box.appendChild(l);return s;}
 function note(box,text,cls='sedac-note'){const p=document.createElement('p');p.className=cls;p.textContent=text;box.appendChild(p);return p;}
 function button(box,label,fn){const b=document.createElement('button');b.type='button';b.textContent=label;b.onclick=fn;box.appendChild(b);return b;}
 function csv(filename,fields,rows){const q=v=>{let s=v==null?'':String(v);if(typeof v!=='number'&&/^[=+@\-\t\r]/.test(s))s="'"+s;return '"'+s.replace(/"/g,'""')+'"';};const u=URL.createObjectURL(new Blob(['\ufeff'+[fields,...rows].map(r=>r.map(q).join(',')).join('\r\n')],{type:'text/csv;charset=utf-8'})),a=document.createElement('a');a.href=u;a.download=filename;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(u),1000);}
 function downloadTowns(){const fields=['sedac_id','display_name','display_name_source','CNTRY_NAME','SMOD_LEVEL','AREA_SQKM','GHSPOP_R23_2020','JRC_NAME_MAIN','CIESIN_NAME','CIESIN_NAME_TL','wb_source_fid'];csv(DATA.code+'_sedac_settlements_2020.csv',[...fields,'longitude','latitude','footprint_reference'],data.settlements.features.map(f=>[...fields.map(k=>f.properties[k]),...f.geometry.coordinates,'circa 2015; whole source footprint']));}
 function downloadGrid(){const r=raster(),kind=metric(),g=r.grid;csv(DATA.code+'_'+(kind==='grdi'?'grdi':'heat_wbgt'+state.threshold+'_1983_2016')+'.csv',['column','row','longitude','latitude','value','measure','reference_period'],r.cells.map(([i,v])=>{const row=Math.floor(i/r.width),col=i%r.width;return [col,row,g[0]+(col+.5)*g[1],g[3]+(row+.5)*g[5],v,kind==='grdi'?'relative deprivation index 0-100':'mean annual days WBGTmax > '+state.threshold+' C',kind==='grdi'?'inputs 2010-2020':'1983-2016'];}));}
 function controls(name,container){
  if(name!=='crossings'&&!metric(name))return;
  const box=document.createElement('div');box.className='sedac-controls';container.appendChild(box);
  if(name==='crossings'){
   select(box,'Town source','sedacTownSource',[['osm','Mapped towns · OpenStreetMap'],['sedac','Urban footprints & population · SEDAC']],state.townSource,v=>{state.townSource=v;state.town=null;setPreset('crossings',{keepContext:true});});
   if(!urbanActive(name))return;
   note(box,data.settlements.features.length+' source settlements with representative points inside this cluster.');
   select(box,'Select a settlement','sedacTownSelect',[['','Click a settlement on the map…'],...data.settlements.features.slice().sort((a,b)=>a.properties.display_name.localeCompare(b.properties.display_name)).map(f=>[f.properties.sedac_id,f.properties.display_name+' · '+f.properties.CNTRY_NAME])],state.town||'',v=>selectTown(v,true));
   const label=document.createElement('label');label.className='sedac-inline';label.innerHTML='<input type="checkbox" id="sedacFootprints"> Show circa-2015 source footprints';box.appendChild(label);$('sedacFootprints').checked=state.footprints;$('sedacFootprints').onchange=()=>{state.footprints=$('sedacFootprints').checked;draw(currentView());};
   const detail=document.createElement('div');detail.id='sedacSelection';detail.className='sedac-selection';detail.setAttribute('aria-live','polite');box.appendChild(detail);
   button(box,'Download settlement data · CSV',downloadTowns);
   note(box,'Population is modelled for 2020 inside each whole source footprint. Footprints may combine places or cross the cluster edge; these are not current town census totals.');
   renderTown();
  }else{
   if(name==='heat')select(box,'Humid-heat threshold · WBGT','sedacHeatThreshold',[['28','Above 28°C WBGT'],['30','Above 30°C WBGT'],['32','Above 32°C WBGT']],state.threshold,v=>{state.threshold=v;setPreset('heat',{keepContext:true}).then(()=>$('sedacHeatThreshold')?.focus({preventScroll:true}));});
   const r=raster(),kind=metric();
   if(kind==='grdi'){const period=note(box,'');period.innerHTML='<strong>2022 release · inputs 2010–2020</strong>';}
   note(box,kind==='grdi'?'Relative deprivation index, 0–100. Higher values indicate more deprivation.':'Average days per year above this humid-heat threshold, 1983–2016. WBGT is not ordinary air temperature.');
   if(kind==='grdi'){
    const coverage=document.createElement('div');coverage.className='grdi-coverage';
    coverage.innerHTML='<strong>'+num((hexActive()?hexData.summary.mapped_area_share:r.summary.coverage_share)*100,1)+'% of cluster area has source values</strong><div class="grdi-coverage-track" aria-hidden="true"><span style="width:'+(hexActive()?hexData.summary.mapped_area_share:r.summary.coverage_share)*100+'%"></span></div><small>'+(hexActive()?'Coloured hexes can contain large gaps in source coverage.':'Grey = no source value. Missing data are not zero.')+'</small>';box.appendChild(coverage);
   }
   note(box,hexActive()?'Hex colours show averages of the available pixels, not values for the whole hex. Click a hex for its mean and source coverage.':'Click the map to read the source-grid value.');
   const detail=document.createElement('div');detail.id='sedacSelection';detail.className='sedac-selection';detail.setAttribute('aria-live','polite');box.appendChild(detail);
   button(box,hexActive()?'Download hex values · CSV':'Download mapped values · CSV',hexActive()?downloadHexes:downloadGrid);
   const about=document.createElement('details');about.innerHTML='<summary>Source and interpretation</summary><p class="sedac-note">'+(kind==='grdi'?'This composite uses demographics, human development, built-up area and night-time lights. Some inputs vary only between broad administrative areas. Hex means weight each available pixel by its area of overlap with the existing cluster-clipped 10 km grid (equal-area projection). Gaps are excluded, never filled or counted as zero; these are not population-weighted means. It is not the percentage of people in poverty; missing building-footprint coverage does not establish that an area is uninhabited.':'Each pixel averages 34 annual counts, requiring valid data in every year. The approximately 5 km grid is historical, ending in 2016. It does not establish present conditions, traffic, outdoor exposure or heat-related illness.')+'</p><p><a href="'+(kind==='grdi'?data.sources.grdi.doi:data.sources.heat.doi)+'" target="_blank" rel="noopener noreferrer">NASA SEDAC source ↗</a></p>';box.appendChild(about);
  }
 }
 function renderTown(){const box=$('sedacSelection');if(!box||!urbanActive())return;const f=lookup.get(state.town);if(!f){box.replaceChildren();return;}const p=f.properties;box.innerHTML='<header><div><small>'+esc(p.settlement_type)+' · '+esc(p.CNTRY_NAME)+'</small><h3>'+esc(p.display_name)+'</h3></div><button id="sedacClear" type="button" aria-label="Clear settlement selection">×</button></header><div class="sedac-value">'+num(p.population_2020)+'</div><small>Modelled population · 2020<br>Within the whole source footprint</small><dl><dt>Source footprint · circa 2015</dt><dd>'+num(p.AREA_SQKM,1)+' km²</dd><dt>Source identity</dt><dd>'+esc(p.sedac_id)+'</dd></dl><button type="button" id="sedacLocate">Locate footprint</button><p class="sedac-note">The named footprint can include neighbouring settlements. It is not a municipal boundary.</p>';$('sedacClear').onclick=()=>selectTown(null);$('sedacLocate').onclick=()=>locateTown();}
 function styleFootprint(f){return {color:f.properties.sedac_id===state.town?'#063e33':'#16745e',weight:f.properties.sedac_id===state.town?2.5:.8,fillColor:'#59a28c',fillOpacity:f.properties.sedac_id===state.town?.5:.2};}
 function highlight(){polyLayer?.setStyle(styleFootprint);for(const [id,marker] of pointLayers)marker.setStyle({radius:id===state.town?8:5,color:id===state.town?'#143b34':'#fff',weight:id===state.town?2.5:1.3});}
 function locateTown(){const f=data.footprints.features.find(f=>f.properties.sedac_id===state.town);if(!f)return;const b=L.geoJSON(f).getBounds();map.fitBounds(b,{paddingTopLeft:[25,30],paddingBottomRight:[window.innerWidth>1024?365:25,75],maxZoom:12,animate:false});if(window.innerWidth<=1024)$('mobileMap').click();}
 function selectTown(id,locate=false){state.town=lookup.has(id)?id:null;if($('sedacTownSelect'))$('sedacTownSelect').value=state.town||'';renderTown();highlight();if(locate&&state.town)locateTown();if(state.town&&(!locate||window.innerWidth>1024)){showSidebar();$('sedacSelection')?.scrollIntoView({block:'nearest'});}}
 function drawTowns(){
  if(state.footprints)polyLayer=add(L.geoJSON(data.footprints,{pane:'hexPane',renderer:svgRenderer('hexPane'),bubblingMouseEvents:false,style:styleFootprint,onEachFeature:(f,l)=>{l.on('click',e=>{if(e.originalEvent)L.DomEvent.stopPropagation(e.originalEvent);selectTown(f.properties.sedac_id);});}}));
  const group=L.markerClusterGroup({animate:false,maxClusterRadius:42,disableClusteringAtZoom:12,showCoverageOnHover:false,spiderfyOnMaxZoom:true,clusterPane:'pointPane',iconCreateFunction:c=>{const n=c.getChildCount(),size=n>=100?28:22,label=n+' settlements · zoom in to separate';c.options.title=label;c.options.alt=label;c.bindTooltip(label,{direction:'top'});return L.divIcon({className:'sedac-cluster',html:'<span>'+n+'</span>',iconSize:[size,size],iconAnchor:[size/2,size/2]});}});
  for(const f of data.settlements.features){const p=f.properties,xy=f.geometry.coordinates,m=L.circleMarker([xy[1],xy[0]],{pane:'pointPane',renderer:svgRenderer('pointPane'),radius:5,color:'#fff',weight:1.3,fillColor:'#16745e',fillOpacity:1,bubblingMouseEvents:false});m.bindTooltip(esc(p.display_name));m.on('click',e=>{if(e.originalEvent)L.DomEvent.stopPropagation(e.originalEvent);selectTown(p.sedac_id);});m.on('add',()=>{const el=m.getElement();if(!el)return;el.setAttribute('role','button');el.setAttribute('tabindex','0');el.setAttribute('aria-label',p.display_name+', SEDAC settlement');el.classList.add('sedac-path');el.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();selectTown(p.sedac_id);}};});pointLayers.set(p.sedac_id,m);group.addLayer(m);}
  add(group);highlight();
 }
 function downloadHexes(){const keys=['cell_id','mean','coverage_pct','source_pixels','mapped_km2','hex_km2'];csv(DATA.code+'_relative_deprivation_10km_hexes.csv',[...keys,'reference','weighting'],hexData.features.map(f=>[...keys.map(k=>f.properties[k]),'GRDI v1 inputs 2010–2020','valid pixel–hex overlap area; not population']));}
 function hexStyle(f){const p=f.properties,selected=state.hex===p.cell_id,b=p.mean===null?null:data.grdi.bands.find(b=>p.mean<=b.upper);return {color:selected?'#201037':'#fff',weight:selected?2.5:.65,opacity:1,fillColor:b?b.colour:'#d1d5db',fillOpacity:.9};}
 function selectHex(f){
  state.hex=f?f.properties.cell_id:null;hexLayer?.setStyle(hexStyle);const box=$('sedacSelection');if(!box)return;
  if(!f){box.replaceChildren();return;}const p=f.properties;
  box.innerHTML='<header><div><small>10 km analysis hex · '+esc(p.cell_id)+'</small></div><button id="sedacClear" type="button" aria-label="Clear hex selection">×</button></header><div class="sedac-value">'+(p.mean===null?'No source value':num(p.mean,1))+'</div><small>Mean relative deprivation index · 0–100</small><dl><dt>Source coverage within this hex</dt><dd><strong>'+num(p.coverage_pct,1)+'%</strong> · '+num(p.mapped_km2,2)+' of '+num(p.hex_km2,2)+' km²</dd><dt>Source pixels contributing</dt><dd>'+num(p.source_pixels)+'</dd></dl><p class="sedac-note">'+(p.mean===null?'No valid source pixels overlap this hex. This is not a zero value.':'Average of the mapped parts only, weighted by their area. Unmapped parts may differ. This is not a poverty percentage or a population-weighted estimate.')+'</p>';
  $('sedacClear').onclick=()=>selectHex(null);showSidebar();box.scrollIntoView({block:'nearest'});
 }
 function drawHexes(){
  hexLayer=add(L.geoJSON(hexData,{pane:'hexPane',renderer:svgRenderer('hexPane'),bubblingMouseEvents:false,style:hexStyle,onEachFeature:(f,l)=>{
   const p=f.properties,label='Hex '+p.cell_id+' · '+(p.mean===null?'No source value':'Mean index '+num(p.mean,1))+' · '+num(p.coverage_pct,1)+'% source coverage';
   l.on('click',e=>{if(e.originalEvent)L.DomEvent.stopPropagation(e.originalEvent);selectHex(f);l.bringToFront();});
   l.on('add',()=>{const el=l.getElement();if(!el)return;el.setAttribute('role','button');el.setAttribute('tabindex','0');el.setAttribute('aria-label',label);el.classList.add('sedac-path');el.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();selectHex(f);l.bringToFront();}};});
  }}));
 }
 function draw(name){clear();if(!data||!active(name))return;
  document.body.classList.toggle('deprivation-view',metric(name)==='grdi');
  if(urbanActive(name)){drawTowns();return;}
  if(hexActive(name)){drawHexes();return;}
  add(L.geoJSON(DATA.cluster,{pane:'sedacNoDataPane',interactive:false,style:{stroke:false,fillColor:'#e5e7eb',fillOpacity:.7}}));const r=raster();
  add(L.imageOverlay(r.image,r.bounds,{pane:'rasterPane',interactive:false,opacity:1,className:'sedac-raster'}));
 }
 function legend(name){if(!data||!active(name))return '';if(urbanActive(name))return '<div class="sedac-key"><strong>Urban settlements · NASA SEDAC</strong><p><i style="background:#59a28c"></i>Circa-2015 source footprints<br>Dots mark source representative points.<br>Small numbered markers group nearby settlements; zoom in to separate them. Counts are places, not people.</p><p>Population: GHSL R2023, 2020 estimates. Source geometry and modelling may differ from current towns.</p></div>';
  const r=raster(),kind=metric(name);
  if(kind==='grdi')return '<div class="sedac-key grdi-key"><strong>'+ (hexActive(name)?'Mean relative deprivation · 10 km hexes':'Relative deprivation index · source grid')+' · 0–100</strong><p class="grdi-direction">Lighter = lower · darker = higher</p><div class="grdi-bands">'+r.bands.map((b,i)=>'<div><i style="background:'+b.colour+'"></i><span>'+b.label+'</span><small>'+(i===0?'Lower index':i===r.bands.length-1?'Higher index':'')+'</small></div>').join('')+'</div><p><i style="background:'+(hexActive(name)?'#d1d5db':'#e5e7eb')+'"></i>'+(hexActive(name)?'No valid source pixels in this hex':'No source value')+'</p><p>Display bands, not official poverty categories. The index is not a poverty percentage.</p><p>'+(hexActive(name)?'Whole hexes are shaded, but means cover available pixels only. Click a hex to check coverage.':'Approximately 1 km source grid.')+'<br>GRDI v1 · 2022 release · inputs 2010–2020.<br>Same scale across all four maps.</p></div>';
  return '<div class="sedac-key"><strong>'+(kind==='grdi'?'Relative deprivation · 0–100':'Historical humid heat · days/year')+'</strong><div class="legend-classes">'+r.bands.map(b=>'<div><i style="background:'+b.colour+'"></i>'+b.label+'</div>').join('')+'<div><i style="background:#e5e7eb"></i>No source value</div></div><p>'+(kind==='grdi'?'Higher = more deprived. Not a poverty percentage.':'Mean days above '+state.threshold+'°C WBGT, 1983–2016.')+' Same display bands in all four maps.</p></div>';
 }
 function readPixel(latlng){if(!data||!metric())return;const r=raster(),g=r.grid,c=Math.floor((latlng.lng-g[0])/g[1]),row=Math.floor((latlng.lat-g[3])/g[5]),inside=c>=0&&row>=0&&c<r.width&&row<r.height,value=inside?r.values.get(row*r.width+c):undefined;state.pixel={c,row,value};const box=$('sedacSelection');if(!box)return;
  box.innerHTML='<header><div><small>Selected source-grid location</small></div><button id="sedacClear" type="button" aria-label="Clear grid selection">×</button></header><div class="sedac-value">'+(value===undefined?'No source value':num(value,1))+'</div><small>'+(value===undefined?'Missing data are not zero.':metric()==='grdi'?'Relative deprivation index · 0–100':'Mean days/year above '+state.threshold+'°C WBGT · 1983–2016')+'</small><p class="sedac-note">'+num(latlng.lat,4)+'°N, '+num(latlng.lng,4)+'°E · approximately '+(metric()==='grdi'?'1':'5')+' km source grid</p>';
  const old=layers.find(l=>l._sedacSelected);if(old){map.removeLayer(old);layers.splice(layers.indexOf(old),1);}if(inside){const highlight=L.rectangle([[g[3]+(row+1)*g[5],g[0]+c*g[1]],[g[3]+row*g[5],g[0]+(c+1)*g[1]]],{pane:'hexPane',color:'#172f3d',weight:2,fill:false,interactive:false});highlight._sedacSelected=true;add(highlight);}
  $('sedacClear').onclick=()=>{box.replaceChildren();const sel=layers.find(l=>l._sedacSelected);if(sel){map.removeLayer(sel);layers.splice(layers.indexOf(sel),1);}state.pixel=null;};showSidebar();box.scrollIntoView({block:'nearest'});
 }
 map.on('click',e=>{if(hexActive())selectHex(null);else if(metric())readPixel(e.latlng);else if(urbanActive())selectTown(null);});
 function exportMetric(){
  if(!data||!metric())return null;
  const r=raster(),isHex=hexActive(),isGRDI=metric()==='grdi';
  return {label:isGRDI?(isHex?'Mean relative deprivation · 10 km hexes':'Relative deprivation index'):'Historical humid heat',unit:isGRDI?'index':'days/year',low:0,high:isGRDI?100:undefined,classes:r.bands.map(b=>({label:b.label,max:b.upper,colour:b.colour})),opacity:isHex?hexStyle({properties:{mean:0}}).fillOpacity:1,noData:{label:isHex?'No valid source pixels in this hex':'No source value',colour:isHex?hexStyle({properties:{mean:null}}).fillColor:'#e5e7eb',opacity:isHex?.9:.7},notes:isGRDI?['GRDI v1 · 2022 release · inputs 2010–2020.','Display bands, not official poverty categories. The index is not a poverty percentage.',...(isHex?['Area-weighted mean of available source pixels; not population-weighted.']:[])]:['Mean days above '+state.threshold+'°C WBGT · 1983–2016.']};
 }
 return {load,controls,draw,legend,prepare,urbanActive,active,selectTown,state,exportMetric};
};

