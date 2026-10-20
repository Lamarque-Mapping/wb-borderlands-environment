(function(){
 'use strict';
 const version='2026-10-20.network.75',inside='#287c78',outside='#ddd9cd',road='#813853';
 const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const pct=n=>Number.isFinite(n)?n.toFixed(1)+'%':'No population estimate';
 const people=n=>n>0&&n<100?'<100':(Math.round(n/100)*100).toLocaleString('en-GB');
 const bar=r=>'<div class="nr-bar" role="img" aria-label="'+esc(pct(r.inside_percent)+' within 10 km; '+pct(r.outside_percent)+' outside')+'"><span style="width:'+(r.inside_percent||0)+'%"></span></div>';
 const method='Chosen straight-line proximity, not travel access or project beneficiaries.';
 const source='WorldPop 2025 · R2025A, constrained, UN-adjusted, 1 km. Original-cell counts allocated by overlap area. Roads: existing Primary roads layer, © OpenStreetMap contributors. Boundaries: OCHA COD-AB / HDX.';
 const fields=['geography','scope','population_year','inside_population','outside_population','total_population','inside_percent','outside_percent','road_length_km','area_km2','inside_area_km2','valid_cell_area_percent','cluster_network_inside_population'];
 const displayRows=d=>d.rows.filter(r=>r.scope==='cluster'||(r.scope==='country'&&(r.area_km2>=1||r.road_length_km>=.001)));
 const csvQuote=v=>'"'+String(v??'').replace(/"/g,'""')+'"';
 function downloadRow(d,r){
  const text='\ufeff'+[['cluster',...fields,'buffer_each_side_km','denominator','method'],[d.cluster,...fields.map(k=>r[k]),10,r.scope==='cluster'?'Whole cluster':'Selected country within the cluster','10 km straight-line buffer around selected primary roads; overlapping buffers dissolved; original WorldPop cells allocated by equal-area overlap']].map(a=>a.map(csvQuote).join(',')).join('\r\n');
  const url=URL.createObjectURL(new Blob([text],{type:'text/csv;charset=utf-8'})),a=document.createElement('a');a.href=url;a.download=d.code+'-'+r.geography.toLowerCase().replace(/[^a-z]+/g,'-')+'-primary-road-population.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),60000);
 }
 window.createWBCorridorBand=function({map,DATA,svgRenderer,refreshLegend}){
  let loaded,group,selected='Cluster',initial=true,active=false,extentControl;
  function row(){return loaded.summary.rows.find(r=>r.geography===selected)||loaded.summary.rows[0];}
  document.addEventListener('click',e=>{if(active&&loaded&&e.target.closest('[data-network-download]'))downloadRow(loaded.summary,row());});
  function select(country,zoom=true){
   if(!active||!loaded.summary.rows.some(r=>r.geography===country))return;
   selected=country;draw('corridorBand');refreshLegend('corridorBand');
   const control=document.getElementById('networkCountry');if(control)control.value=selected;
   if(zoom){const territory=loaded.territories.features.find(f=>f.properties.geography===selected);if(territory){map.stop();map.fitBounds(L.geoJSON(territory).getBounds(),{paddingTopLeft:[24,24],paddingBottomRight:[window.innerWidth>1024?370:24,30],maxZoom:10,animate:false});}}
  }
  function draw(name){
   if(group){map.removeLayer(group);group=null;}
   active=name==='corridorBand';
   if(!active){selected='Cluster';if(extentControl)extentControl.remove();return;}
   if(!loaded)return;
   if(!extentControl){
    extentControl=L.control({position:'topleft'});
    extentControl.onAdd=function(){
     const container=L.DomUtil.create('div','nr-map-reset leaflet-bar');
     L.DomEvent.disableClickPropagation(container);L.DomEvent.disableScrollPropagation(container);
     const button=document.createElement('button');button.type='button';
     button.textContent='Show whole cluster';
     button.title='Zoom out to the whole cluster and restore all primary roads and population totals';
     button.setAttribute('aria-label','Show whole cluster');
     button.onclick=()=>select('Cluster');container.appendChild(button);return container;
    };
   }
   if(!extentControl.getContainer()||!extentControl.getContainer().isConnected)extentControl.addTo(map);
   group=L.layerGroup().addTo(map);
   const territory=loaded.territories.features.find(f=>f.properties.geography===selected);
   const band=loaded.bands.features.find(f=>f.properties.geography===selected);
   if(territory)L.geoJSON(territory,{pane:'hexPane',renderer:svgRenderer('hexPane'),interactive:false,style:{color:'#3f5751',weight:selected==='Cluster'?0:1.5,fillColor:outside,fillOpacity:.48}}).addTo(group);
   if(band)L.geoJSON(band,{pane:'hexPane',renderer:svgRenderer('hexPane'),interactive:false,style:{stroke:false,fillColor:inside,fillOpacity:.66}}).addTo(group);
   for(const f of loaded.roads.features){
    const country=f.properties.geography,isSelected=selected==='Cluster'||selected===country,selectable=country!=='Unassigned boundaries';
    if(isSelected)L.geoJSON(f,{pane:'linePane',renderer:svgRenderer('linePane'),interactive:false,style:{color:'#fff',weight:5.5,opacity:.85}}).addTo(group);
    const paths=L.geoJSON(f,{pane:'linePane',renderer:svgRenderer('linePane'),interactive:selectable,style:{color:isSelected?road:'#7e8582',weight:isSelected?2.8:1.5,opacity:isSelected?1:.4},onEachFeature:(feature,layer)=>{
     if(!selectable)return;
     layer.bindTooltip(esc(country)+' · click for its national road network',{sticky:true});
     layer.on('click',()=>select(country));
     layer.on('add',()=>{const el=layer.getElement();if(el){el.setAttribute('tabindex','0');el.setAttribute('role','button');el.setAttribute('aria-label','Focus '+country+' primary roads');el.setAttribute('data-national-road',country);el.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();select(country);}});}});
    }}).addTo(group);
    // A generous invisible hit area makes thin roads easy to select.
    if(selectable)L.geoJSON(f,{pane:'linePane',renderer:svgRenderer('linePane'),style:{color:road,weight:14,opacity:.001},onEachFeature:(feature,layer)=>{layer.on('click',()=>select(country));layer.bindTooltip(esc(country)+' · click to focus',{sticky:true});}}).addTo(group);
   }
  }
  return {
   async load(key){
    if(key!=='corridorBand')return false;
    if(!loaded)loaded=await parent.WBVault.json(DATA.code+'/corridorBand');
    if(initial){const country=new URLSearchParams(parent.location.search).get('country');if(loaded.summary.rows.some(r=>r.scope==='country'&&r.geography===country))selected=country;initial=false;}
    return true;
   },draw,
   controls(name,box){
    if(name!=='corridorBand'||!loaded)return;
    const controls=document.createElement('div');controls.className='nr-controls';
    const label=document.createElement('label');label.htmlFor='networkCountry';label.textContent='Network and population area';
    const chooser=document.createElement('select');chooser.id='networkCountry';
    for(const r of displayRows(loaded.summary)){const opt=document.createElement('option');opt.value=r.geography;opt.textContent=r.scope==='cluster'?'Whole cluster':r.geography+' · within cluster';chooser.appendChild(opt);}
    chooser.value=selected;chooser.onchange=()=>select(chooser.value);
    const reset=document.createElement('button');reset.type='button';reset.id='networkReset';reset.className='nr-reset';reset.textContent='Show whole cluster';reset.onclick=()=>select('Cluster');
    const note=document.createElement('p');note.className='theme-note';note.textContent='Click any primary road to focus on that country’s network and its 10 km buffer. The country total covers only territory inside this cluster.';
    controls.append(label,chooser,reset,note);box.appendChild(controls);
   },
   legend(name){
    if(name!=='corridorBand'||!loaded)return;
    const r=row(),legend=document.getElementById('legend'),key=document.createElement('div');key.className='nr-key';
    const scope=r.scope==='cluster'?loaded.summary.cluster+' · whole cluster':r.geography+' · within '+loaded.summary.cluster;
    key.innerHTML='<strong>Population near primary roads · 2025</strong><p class="nr-scope">'+esc(scope)+'</p>'+bar(r)+'<div class="nr-counts"><div><span class="nr-dot"></span>Within 10 km<strong>'+pct(r.inside_percent)+'</strong><small>About '+esc(people(r.inside_population))+' people</small></div><div><span class="nr-dot nr-outside"></span>Outside 10 km<strong>'+pct(r.outside_percent)+'</strong><small>About '+esc(people(r.outside_population))+' people</small></div></div><p class="nr-total">Population denominator: about '+esc(people(r.total_population))+' people<br>'+(r.scope==='cluster'?'Entire cluster':'This country’s territory within the cluster')+'</p><div class="legend-row"><span class="swatch-line" style="border-color:'+road+'"></span>'+(r.scope==='cluster'?'All mapped primary roads':esc(r.geography)+' primary roads')+'</div><p class="nr-method">10 km on each side; overlapping buffers count people once. '+method+'</p>'+(r.road_length_km<.001?'<p class="nr-method">No primary-road geometry is mapped in this national portion.</p>':'')+'<div class="nr-actions"><button type="button" id="networkDownload">Download figures · CSV</button><a href="#analysis" onclick="parent.WBVault.go(\'analysis\');return false">Compare in Analysis →</a></div>';
    const download=key.querySelector('#networkDownload');download.removeAttribute('id');download.setAttribute('data-network-download','');legend.prepend(key);
    const sourceNote=legend.querySelector('.source-note');if(sourceNote)sourceNote.textContent=source;
   }
  };
 };
 async function analysis(){
  const section=document.getElementById('corridor-population');if(!section)return;
  const body=document.getElementById('corridorPopulationRows');
  try{
   const response=await fetch('data/primary-road-population.json?v='+version);if(!response.ok)throw Error('Road population unavailable');
   const {clusters}=await response.json(),chooser=document.getElementById('networkAnalysisCluster');
   for(const d of clusters){const opt=document.createElement('option');opt.value=d.code;opt.textContent=d.cluster+' · national sections';chooser.appendChild(opt);}
   function render(){
    const selected=clusters.find(d=>d.code===chooser.value),items=selected?displayRows(selected).map(r=>({d:selected,r})):clusters.map(d=>({d,r:d.rows[0]}));
    body.innerHTML=items.map(({d,r})=>'<div class="nr-analysis-row"><div class="nr-area"><a target="_top" href="?view=corridorBand'+(r.scope==='country'?'&amp;country='+encodeURIComponent(r.geography):'')+'#map='+d.code+'">'+esc(r.scope==='cluster'?d.cluster:r.geography)+'</a><small>'+(r.scope==='cluster'?'Whole cluster':'National roads and territory within cluster')+'</small></div><div>'+bar(r)+'<div class="nr-share-labels"><span>'+pct(r.inside_percent)+' within 10 km</span><span>'+pct(r.outside_percent)+' outside</span></div></div><div class="nr-numbers"><strong>'+esc(people(r.inside_population))+' within</strong><span>'+esc(people(r.outside_population))+' outside</span><small>'+esc(people(r.total_population))+' total</small></div></div>').join('');
    const unassigned=selected?.rows.find(r=>r.scope==='unassigned');
    document.getElementById('corridorCoverage').textContent='Estimates rounded to the nearest 100. Country rows use only that country’s roads and population within the cluster. They need not add to the cluster’s “within 10 km” count, because cluster mode also includes proximity across borders.'+(unassigned?' Boundary gaps or overlaps: '+unassigned.area_km2.toFixed(2)+' km², about '+people(unassigned.total_population)+' modelled people; retained as unassigned in the CSV.':'')+' Country boundary fragments smaller than 1 km² with no mapped primary roads are retained in totals and CSV, but omitted from the comparison controls.';
    const exportItems=selected?selected.rows.map(r=>({d:selected,r})):clusters.flatMap(d=>d.rows.map(r=>({d,r})));
    window.WBAnalysisExport.register('corridor-population',()=>window.WBAnalysisExport.saveCSV('corridor-population',['cluster',...fields,'buffer_each_side_km','source','method'],exportItems.map(({d,r})=>[d.cluster,...fields.map(k=>r[k]),10,d.source.product,'Country scope uses only that country’s roads and territory within the cluster; original-cell area weighting; no double counting of buffer overlaps']), (selected?selected.code:'all-clusters')+'-primary-road-population-2025.csv'));
   }
   chooser.onchange=render;render();
  }catch(e){body.innerHTML='<p>Road population could not load. <button type="button" id="networkRetry">Retry</button></p>';document.getElementById('networkRetry').onclick=()=>{const s=document.getElementById('networkAnalysisCluster');while(s.options.length>1)s.remove(1);analysis();};console.error(e);}
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',analysis);else analysis();
})();

