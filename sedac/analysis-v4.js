(async function(){
'use strict';
const sections=[['towns','urbanAnalysis'],['grdi','deprivationAnalysis'],['heat','heatAnalysis']];
try{
 const data=await parent.WBVault.json('analysis/sedac');
 if(data.format!=='wb-sedac-summary-v1')throw Error('Invalid SEDAC summary');
 for(const [mode,prefix] of sections)mount(mode,prefix);
 function mount(mode,prefix){
const $=id=>document.getElementById(id.replace('sedacAnalysis',prefix)),esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),num=(v,d=0)=>Number.isFinite(v)?v.toLocaleString('en-GB',{maximumFractionDigits:d}):'Not available';
let code='karamoja',threshold='28';
const sectionId=mode==='towns'?'urban-settlements':mode==='grdi'?'deprivation':'historical-heat';
function link(c,id){return '?view='+(mode==='towns'?'urban':mode==='grdi'?'deprivation':'heat')+(id?'&settlement='+encodeURIComponent(id):'')+(mode==='heat'?'&heatThreshold='+threshold:'')+'#map='+c;}
function histogram(rows){return '<div class="sedac-histogram">'+rows.map(r=>'<div class="sedac-hist-row"><span>'+esc(r.label)+'</span><div class="sedac-bar" role="img" aria-label="'+esc(r.label)+': '+num(r.area_share*100,1)+' percent of mapped area"><span style="width:'+r.area_share*100+'%;background:'+r.colour+'"></span></div><strong>'+num(r.area_share*100,1)+'%</strong></div>').join('')+'</div>';}
function series(rows){const w=800,h=240,p={l:48,r:20,t:16,b:35},max=Math.max(10,Math.ceil(Math.max(...rows.map(r=>r.area_mean_days))/10)*10),x=y=>p.l+(y-1983)/33*(w-p.l-p.r),y=v=>h-p.b-v/max*(h-p.t-p.b),line=rows.map((r,i)=>(i?'L':'M')+x(r.year).toFixed(2)+' '+y(r.area_mean_days).toFixed(2)).join(' ');let svg='<svg class="sedac-series" viewBox="0 0 '+w+' '+h+'" role="img" aria-label="Area-weighted mean annual days above '+threshold+' degrees WBGT, 1983 to 2016"><title>Historical humid heat, '+esc(data.clusters.find(c=>c.code===code).label)+'</title>';
 for(let i=0;i<=4;i++){const value=max*i/4,yy=y(value);svg+='<line x1="'+p.l+'" y1="'+yy+'" x2="'+(w-p.r)+'" y2="'+yy+'" stroke="#dce5df"/><text x="'+(p.l-8)+'" y="'+(yy+4)+'" text-anchor="end" font-size="11" fill="#53656c">'+num(value,1)+'</text>';}
 for(const year of [1983,1990,2000,2010,2016])svg+='<text x="'+x(year)+'" y="'+(h-10)+'" text-anchor="middle" font-size="11" fill="#53656c">'+year+'</text>';
 svg+='<path d="'+line+'" fill="none" stroke="#b96b22" stroke-width="2.5"/>';
 for(const r of rows)svg+='<circle cx="'+x(r.year)+'" cy="'+y(r.area_mean_days)+'" r="3" fill="#b96b22"><title>'+r.year+': '+num(r.area_mean_days,2)+' days/year, area-weighted</title></circle>';
 return svg+'</svg>';
}
function render(){const c=data.clusters.find(c=>c.code===code),out=$('sedacAnalysisBody');$('sedacAnalysisMap').href=link(code);
 if(mode==='towns'){
  const max=Math.max(1,...c.towns.map(t=>t.population_2020||0));
  out.innerHTML='<p class="sedac-caution">These are modelled populations inside circa-2015 source settlement footprints. A footprint can combine neighbouring places and extend beyond the cluster; a familiar place name does not make the value a town census total.</p><p class="chart-foot">'+c.towns.length+' source representative points inside '+esc(c.label)+'. Population reference: GHSL R2023 estimates for 2020. Select a name to inspect its footprint.</p><div class="sedac-table-wrap" tabindex="0" role="region" aria-label="Settlement populations"><table class="sedac-table"><thead><tr><th>Source settlement</th><th class="sedac-bar-cell">Population within source footprint</th><th>2020 estimate</th></tr></thead><tbody>'+c.towns.map(t=>'<tr><th scope="row"><a target="_top" href="'+link(code,t.id)+'">'+esc(t.name)+' ↗</a><small>'+esc(t.country)+' · '+esc(t.type)+'</small></th><td class="sedac-bar-cell"><div class="sedac-bar" aria-hidden="true"><span style="width:'+(t.population_2020||0)/max*100+'%"></span></div></td><td>'+num(t.population_2020)+'</td></tr>').join('')+'</tbody></table></div><p class="chart-foot">The list counts each source settlement once using its country and SMOD identity. Points and polygons are paired, not added together. Overlapping cluster selections must not be summed. Names follow the supplied fields; unnamed records remain unnamed.</p>';
 }else if(mode==='grdi'){
  const r=c.grdi;out.innerHTML='<div class="sedac-analysis-cards">'+data.clusters.map(k=>'<div class="sedac-analysis-card"><small>'+esc(k.label)+'</small><strong>'+num(k.grdi.area_mean,1)+'</strong><small>Mean mapped index · 0–100<br>'+num(k.grdi.coverage_share*100,1)+'% area coverage</small></div>').join('')+'</div><p class="sedac-caution">GRDI is a relative deprivation index, not a poverty rate. Coverage depends on source building footprints. These means describe the available mapped area and are not weighted by population; they cannot establish a ranking of residents’ poverty.</p><h3>'+esc(c.label)+' · distribution of mapped values</h3>'+histogram(r.histogram.map((row,i)=>({...row,colour:['#f2f0f7', '#cbc9e2', '#9e9ac8', '#756bb1', '#54278f'][i]})))+'<p class="chart-foot">Bars show the area share within each display band, among valid source pixels. Approximately '+num(r.coverage_share*100,1)+'% of the cluster area has an index value; gaps are excluded. All maps use the same bands, chosen for display rather than official poverty categories.</p>';
 }else{
  const r=c.heat[threshold];out.innerHTML='<div class="sedac-analysis-cards">'+data.clusters.map(k=>'<div class="sedac-analysis-card"><small>'+esc(k.label)+'</small><strong>'+num(k.heat[threshold].area_mean,1)+'</strong><small>Mean days/year above '+threshold+'°C WBGT<br>Mapped area · 1983–2016</small></div>').join('')+'</div><p class="sedac-caution">Historical humid heat, ending in 2016. WBGT incorporates humidity and is not ordinary air temperature. Area averages do not measure how many people, journeys or working hours were exposed.</p><h3>'+esc(c.label)+' · annual variation</h3>'+series(r.annual)+'<p class="chart-foot">Each year averages the same source-grid locations across the cluster, weighted by approximate grid-cell area. The map shows the 34-year average at each pixel. This selection covers '+num(r.coverage_share*100,1)+'% of the cluster’s grid-based area.</p><details class="method-note"><summary>Annual values</summary><div class="sedac-table-wrap"><table class="sedac-table"><thead><tr><th>Year</th><th>Area-weighted days/year</th></tr></thead><tbody>'+r.annual.map(x=>'<tr><td>'+x.year+'</td><td>'+num(x.area_mean_days,2)+'</td></tr>').join('')+'</tbody></table></div></details>';
 }
}
function download(){
 const c=data.clusters.find(c=>c.code===code);let fields,rows;
 if(mode==='towns'){
  fields=['cluster','source_id','name','country','source_class','population_2020','source_footprint_km2','source','footprint_reference','notes'];
  rows=c.towns.map(t=>[c.label,t.id,t.name,t.country,t.type,t.population_2020,t.area_sqkm,'SEDAC GUPPD v1 (2024); GHSL R2023 population','circa 2015','Whole source footprint selected by representative point inside cluster; not municipal census totals']);
 }else if(mode==='grdi'){
  fields=['record_type','cluster','index_band','share_of_valid_mapped_area','cluster_area_coverage_share','area_mean_index','source','input_years','weighting'];
  rows=[...data.clusters.map(k=>['cluster_summary',k.label,'','',k.grdi.coverage_share,k.grdi.area_mean,'SEDAC GRDI v1 (2022)','2010-2020','Approximate cell area; not population']),...c.grdi.histogram.map(r=>['selected_distribution',c.label,r.label,r.area_share,c.grdi.coverage_share,c.grdi.area_mean,'SEDAC GRDI v1 (2022)','2010-2020','Approximate cell area; not population'])];
 }else{
  fields=['record_type','cluster','year','wbgt_threshold_c','area_weighted_mean_days','cluster_area_coverage_share','source','period','weighting'];
  rows=[...data.clusters.map(k=>['cluster_summary',k.label,'',Number(threshold),k.heat[threshold].area_mean,k.heat[threshold].coverage_share,'SEDAC GEHE (2023)','1983-2016','Same valid pixels; approximate cell area; not population']),...c.heat[threshold].annual.map(r=>['selected_annual_series',c.label,r.year,Number(threshold),r.area_mean_days,c.heat[threshold].coverage_share,'SEDAC GEHE (2023)','1983-2016','Same valid pixels; approximate cell area; not population'])];
 }
 window.WBAnalysisExport.saveCSV(sectionId,fields,rows,code+'_sedac_'+mode+(mode==='heat'?'_'+threshold:'')+'.csv');
}


 $('sedacAnalysisCluster').innerHTML=data.clusters.map(c=>'<option value="'+c.code+'">'+esc(c.label)+'</option>').join('');
 $('sedacAnalysisCluster').value=code;
 $('sedacAnalysisCluster').onchange=()=>{code=$('sedacAnalysisCluster').value;render();};
 if(mode==='heat')$('sedacAnalysisThreshold').onchange=()=>{threshold=$('sedacAnalysisThreshold').value;render();};
 window.WBAnalysisExport.register(sectionId,download);render();
 $('sedacAnalysisLoading').hidden=true;$('sedacAnalysisContent').hidden=false;
 }
}catch(e){for(const [,prefix] of sections){const loading=document.getElementById(prefix+'Loading');if(loading)loading.textContent='This analysis could not load. Reopen Analysis to retry.';}console.error(e);}
})();
