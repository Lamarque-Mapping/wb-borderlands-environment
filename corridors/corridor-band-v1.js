(function(){
 'use strict';
 const insideColour='#287c78',outsideColour='#d9d6cd',roadColour='#813853';
 const fmt=n=>Math.round(n).toLocaleString('en-GB'),pct=n=>n.toFixed(1)+'%';
 const people=n=>(Math.round(n/100)*100).toLocaleString('en-GB');
 const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 function bar(row){return '<div class="cb-bar" role="img" aria-label="'+esc(row.geography)+': '+pct(row.inside_percent)+' within 10 km; '+pct(row.outside_percent)+' outside"><span style="width:'+row.inside_percent+'%;background:'+insideColour+'"></span></div>';}
 const method='10 km is a chosen straight-line distance on each side of the road. It does not measure travel access, project coverage or beneficiaries.';
 let resultPromise;
 function result(){return resultPromise||(resultPromise=fetch('data/mandera-corridor-population.json?v=2026-10-20.corridor.72').then(r=>{if(!r.ok)throw Error('Population data unavailable');return r.json();}).catch(e=>{resultPromise=null;throw e;}));}
 window.createWBCorridorBand=function({map,DATA,svgRenderer}){
  let loaded,group;
  return {
   async load(key){if(key!=='corridorBand')return false;loaded=await parent.WBVault.json('mandera_triangle/corridorBand');return true;},
   draw(name){
    if(group){map.removeLayer(group);group=null;}
    if(name!=='corridorBand'||!loaded)return;
    group=L.layerGroup().addTo(map);
    L.geoJSON(loaded.zones,{pane:'hexPane',renderer:svgRenderer('hexPane'),interactive:false,style:f=>({stroke:false,fillColor:f.properties.zone==='Within 10 km'?insideColour:outsideColour,fillOpacity:f.properties.zone==='Within 10 km'?.60:.30})}).addTo(group);
    L.geoJSON(loaded.route,{pane:'linePane',renderer:svgRenderer('linePane'),interactive:false,style:{color:'#fff',weight:5,opacity:.95}}).addTo(group);
    L.geoJSON(loaded.route,{pane:'linePane',renderer:svgRenderer('linePane'),style:{color:roadColour,weight:2.7,opacity:1},onEachFeature:(f,l)=>l.bindPopup('<strong>Isiolo–Mandera corridor</strong><p>Via El Wak, Wargadud and Rhamu.<br>Mapped road alignment: OpenStreetMap / Geofabrik.</p>')}).addTo(group);
   },
   controls(name,box){if(name!=='corridorBand')return;const note=document.createElement('p');note.className='theme-note';note.textContent='Isiolo–Mandera via El Wak and Rhamu · 10 km on each side, clipped to the Mandera Triangle.';box.appendChild(note);},
   legend(name){
    if(name!=='corridorBand'||!loaded)return;
    const r=loaded.summary.rows[0],legend=document.getElementById('legend');
    const key=document.createElement('div');key.className='cb-key';
    key.innerHTML='<strong>Population near the corridor · 2025</strong>'+bar(r)+'<div class="cb-counts"><div><span class="cb-dot" style="background:'+insideColour+'"></span>Within 10 km<strong>'+pct(r.inside_percent)+'</strong><small>About '+people(r.inside_population)+' people</small></div><div><span class="cb-dot" style="background:'+outsideColour+'"></span>Outside 10 km<strong>'+pct(r.outside_percent)+'</strong><small>About '+people(r.outside_population)+' people</small></div></div><p class="cb-total">Whole cluster: about '+people(r.total_population)+' people</p><div class="legend-row"><span class="swatch-line" style="border-color:'+roadColour+'"></span>Isiolo–Mandera corridor</div><div class="legend-row"><span class="land-swatch" style="background:'+insideColour+';opacity:.6"></span>10 km band, clipped to cluster</div><p class="cb-method">'+method+'</p><a class="cb-analysis-link" href="#analysis" onclick="parent.WBVault.go(\'analysis\');return false">Country breakdown in Analysis →</a>';
    legend.prepend(key);
    const source=legend.querySelector('.source-note');if(source)source.textContent='WorldPop 2025 · R2025A, constrained, UN-adjusted, 1 km. Original cells allocated by overlap area; uniform population assumed within each cell. The constrained model allocates people to mapped settlements; masked cells remain excluded. Road: © OpenStreetMap contributors / Geofabrik, checked against KeNHA A13 route.';
   }
  };
 };
 async function analysis(){
  const section=document.getElementById('corridor-population');if(!section)return;
  const body=document.getElementById('corridorPopulationRows');
  try{
   const d=await result();
   const rows=d.rows.filter(r=>r.geography!=='Unassigned or overlapping boundaries');
   body.innerHTML=rows.map(r=>'<div class="cb-analysis-row"><div class="cb-area">'+(r.geography==='Cluster'?'Mandera Triangle':esc(r.geography))+'<small>'+(r.geography==='Cluster'?'Whole cluster':'Portion within the cluster')+'</small></div><div>'+bar(r)+'<div class="cb-share-labels"><span>'+pct(r.inside_percent)+' within 10 km</span><span>'+pct(r.outside_percent)+' outside</span></div></div><div class="cb-numbers"><span>'+people(r.inside_population)+' within</span><span>'+people(r.outside_population)+' outside</span></div></div>').join('');
   const u=d.rows.find(r=>r.geography==='Unassigned or overlapping boundaries');
   document.getElementById('corridorCoverage').textContent='Population estimates rounded to the nearest 100. Valid-valued source cells occupy '+d.rows[0].raster_coverage_percent.toFixed(2)+'% of cluster area: this reflects a constrained settlement-based model and is not a population coverage percentage. Masked cells remain excluded.'+(u?' Boundary gaps or overlaps account for '+u.area_km2.toFixed(2)+' km² and '+(u.total_population<1?'less than one modelled person':fmt(u.total_population)+' modelled people')+'; these remain unassigned to a country.':'');
   const fields=['geography','population_year','inside_population','outside_population','total_population','inside_percent','outside_percent','raster_coverage_percent','area_km2','inside_area_km2'];
   window.WBAnalysisExport.register('corridor-population',()=>window.WBAnalysisExport.saveCSV('corridor-population',[...fields,'band_width_each_side_km','source','method'],d.rows.map(r=>[...fields.map(k=>r[k]),10,d.source.product,'Original cell counts allocated by equal-area overlap; chosen straight-line proximity, not travel access or beneficiaries']),'mandera-corridor-population-2025.csv'));
  }catch(e){body.innerHTML='<p>Corridor population could not load. <button type="button" id="cbRetry">Retry</button></p>';document.getElementById('cbRetry').onclick=analysis;console.error(e);}
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',analysis);else analysis();
})();
