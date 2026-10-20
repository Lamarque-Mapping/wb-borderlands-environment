(function(){
 'use strict';
 const section=document.getElementById('local-connectivity');if(!section)return;
 const $=id=>document.getElementById(id),esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const number=v=>Number(v).toLocaleString('en-GB'),pct=v=>v==null?'Unavailable':(v*100).toLocaleString('en-GB',{maximumFractionDigits:1})+'%';
 const params=new URLSearchParams(parent.location.search),initial=params.get('connectivityCluster');
 let data;
 const selectedCluster=() => data.clusters.find(c=>c.code===$('connectivityCluster').value);
 function mapLink(code,id,kind){return '?view=connectivity'+(id&&id!=='cluster'?'&district='+encodeURIComponent(id):'')+'&places='+kind+'#map='+code;}
 function render(){
  const c=selectedCluster(),level=$('connectivityLevel').value,kind=$('connectivityPlaces').value,country=$('connectivityCountry').value,field=kind==='urban'?'town':'place';
  $('connectivityCountryLabel').hidden=level!=='district';$('connectivityClusterLabel').hidden=level==='cluster';
  const rows=level==='cluster'?data.clusters.map(d=>({code:d.code,r:d.cluster})): (level==='country'?c.countries:c.districts.filter(r=>!r.boundary_fragment&&(!country||r.country===country))).map(r=>({code:c.code,r}));
  const target=kind==='urban'?'city/town':'city/town/village';
  $('connectivityComparisonTitle').textContent=(level==='cluster'?'Four clusters':c.name+' · '+(level==='country'?'country portions':(country?country+' · ':'')+'districts / zones'))+' · '+target+' within 10 km';
  $('connectivityRows').innerHTML=rows.map(({code,r})=>{
   const value=r[field+'_share'],reached=r[field+'_reached'],link=level==='country'?'?view=connectivity&connectivityCountry='+encodeURIComponent(r.country)+'&places='+kind+'#map='+code:mapLink(code,r.id,kind);
   const name=r.id==='unassigned'?esc(r.name):'<a target="_top" href="'+esc(link)+'">'+esc(r.name)+'</a>';
   return '<div class="lc-row"><div class="lc-name">'+name+'<small>'+esc(level==='district'?[r.country,r.admin1].filter(Boolean).join(' · '):'Within the cluster boundary')+'</small></div><div class="lc-result"><div class="lc-bar '+(value==null?'lc-undefined':'')+'">'+(value==null?'':'<span style="width:'+(value*100)+'%;background:'+(value===0?'#c58e56':'#388982')+'"></span>')+'</div><strong>'+pct(value)+'</strong></div><div class="lc-count">'+number(reached)+' / '+number(r.junctions)+'<small>'+(r.junctions?'junctions reach a mapped '+target:'No qualifying mapped junctions')+'</small></div></div>';
  }).join('')||'<p>No districts match this selection.</p>';
  const fragments=c.districts.filter(r=>r.boundary_fragment).length;
  $('connectivityComparisonNote').textContent='Counts refer to junction locations inside each area. Routes can cross administrative and national borders. '+(level==='district'?'Click a district to inspect its 10 km hexagons. '+(fragments?fragments+' tiny boundary fragments with no junctions are retained in the source download. ':''):'Click a name to open its map. ')+'All shares use the same 10 km local-road path limit.';
  const fields=['cluster','level','area','country','admin1','mapped_junctions','reaching_city_town_10km','share_reaching_city_town_10km','reaching_city_town_village_10km','share_reaching_city_town_village_10km','source_date','path_limit_km','coverage'];
  window.WBAnalysisExport.register('local-connectivity',()=>window.WBAnalysisExport.saveCSV('local-connectivity',fields,rows.map(({code,r})=>[data.clusters.find(d=>d.code===code).name,r.level,r.name,r.country,r.admin1,r.junctions,r.town_reached,r.town_share,r.place_reached,r.place_share,'2026-10-08',10,'OSM completeness not independently assessed']), 'local-connectivity-'+(level==='cluster'?'all-clusters':c.code)+'-'+level+'.csv'));
  $('connectivitySourceFiles').innerHTML=(level==='cluster'?data.clusters:[c]).map(d=>'<a href="data/local-connectivity/'+d.code+'.zip" download>'+esc(d.name)+' · underlying data ZIP</a>').join('');
 }
 function countries(){const c=selectedCluster(),select=$('connectivityCountry');select.replaceChildren(new Option('All countries',''));for(const r of c.countries)select.add(new Option(r.country,r.country));}
 async function load(){
  try{
   const response=await fetch('data/local-connectivity/summary.json?v=2026-10-21.districts.77');if(!response.ok)throw Error('Connectivity data unavailable');data=await response.json();
   const select=$('connectivityCluster');select.replaceChildren();for(const c of data.clusters)select.add(new Option(c.name,c.code));select.value=data.clusters.some(c=>c.code===initial)?initial:'karamoja';
   if(params.get('places')==='place')$('connectivityPlaces').value='place';
   countries();select.onchange=()=>{countries();render();};for(const id of ['connectivityLevel','connectivityPlaces','connectivityCountry'])$(id).onchange=render;
   render();$('connectivityAnalysisLoading').hidden=true;$('connectivityAnalysisContent').hidden=false;
   if(initial)requestAnimationFrame(()=>section.scrollIntoView({block:'start'}));
  }catch(e){$('connectivityAnalysisLoading').innerHTML='Connectivity figures could not load. <button type="button" id="connectivityRetry">Retry</button>';$('connectivityRetry').onclick=load;console.error(e);}
 }
 load();
})();
