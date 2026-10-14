(function(){
'use strict';
const valid=r=>typeof r.access_pct==='number'&&Number.isFinite(r.access_pct)&&r.access_pct>=0&&r.access_pct<=100&&Number.isFinite(r.rural_population)&&r.rural_population>0&&Number.isFinite(r.within_2km);
function summary(rows){const usable=rows.filter(valid),rural=usable.reduce((n,r)=>n+r.rural_population,0),within=usable.reduce((n,r)=>n+r.within_2km,0);return {count:rows.length,valid:usable.length,missing:rows.length-usable.length,rural,within,weighted:rural>0?100*within/rural:null,min:usable.length?Math.min(...usable.map(r=>r.access_pct)):null,max:usable.length?Math.max(...usable.map(r=>r.access_pct)):null};}
function ordered(rows,order){return rows.slice().sort((a,b)=>{if(valid(a)!==valid(b))return valid(a)?-1:1;if(order==='name')return a.name.localeCompare(b.name)||a.id.localeCompare(b.id);const av=order==='population'?a.rural_population:order==='beyond'?a.rural_population-a.within_2km:a.access_pct,bv=order==='population'?b.rural_population:order==='beyond'?b.rural_population-b.within_2km:b.access_pct;return (order==='low'?av-bv:bv-av)||a.name.localeCompare(b.name)||a.id.localeCompare(b.id);});}
function csv(rows){const fields=['cluster','id','name','region','country','source_country','access_pct','rural_population','within_2km','beyond_2km','status','selection_tag','boundary_basis','population_year','road_date','release'];const quote=v=>'"'+String(v??'').replace(/"/g,'""')+'"';return fields.join(',')+'\r\n'+rows.map(r=>fields.map(k=>quote(k==='beyond_2km'?(valid(r)?r.rural_population-r.within_2km:null):k==='boundary_basis'?'GADM v3.6 full source unit':k==='population_year'?2020:k==='road_date'?'2022-03-31':k==='release'?2023:r[k])).join(',')).join('\r\n')+'\r\n';}
if(typeof module!=='undefined'&&module.exports){module.exports={valid,summary,ordered,csv};return;}
const $=id=>document.getElementById(id),esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=(v,d=0)=>Number.isFinite(v)?v.toLocaleString('en-GB',{minimumFractionDigits:d,maximumFractionDigits:d}):'Not available';
let data,cluster='mandera_triangle',country='';
function rows(){return data.rows.filter(r=>r.cluster===cluster&&(!country||r.country===country));}
function mapURL(r){return '?view=ruralAccess&unit='+encodeURIComponent(r.id)+'#map='+encodeURIComponent(r.cluster);}
function renderCards(){
 $('raiClusterCards').innerHTML=data.clusters.map(c=>{const s=summary(data.rows.filter(r=>r.cluster===c.code));return '<button type="button" class="rai-cluster-card" data-cluster="'+esc(c.code)+'" aria-pressed="'+(cluster===c.code)+'"><span>'+esc(c.name)+'</span><strong>'+fmt(s.weighted,1)+'<small>%</small></strong><span class="rai-card-meta">'+s.valid+' valid source units'+(s.missing?' · '+s.missing+' no data':'')+'</span><span class="rai-card-range">Unit range '+fmt(s.min,1)+'–'+fmt(s.max,1)+'%</span></button>';}).join('');
 $('raiClusterCards').querySelectorAll('button').forEach(b=>b.onclick=()=>{cluster=b.dataset.cluster;country='';fillCountries();render();$('raiClusterCards').querySelector('[data-cluster="'+cluster+'"]').focus({preventScroll:true});});
}
function fillCountries(){const countries=[...new Set(data.rows.filter(r=>r.cluster===cluster).map(r=>r.country))].sort();$('raiCountry').innerHTML='<option value="">All countries / sides</option>'+countries.map(c=>'<option value="'+esc(c)+'">'+esc(c)+'</option>').join('');$('raiCountry').value=country;}
function render(){
 renderCards();const selected=rows(),s=summary(selected),name=data.clusters.find(c=>c.code===cluster).name,sorted=ordered(selected,$('raiSort').value);
 $('raiSelectionTitle').textContent=name+(country?' · '+country:'');
 $('raiCount').textContent=s.valid+' of '+s.count+' source units have valid access values.'+(s.missing?' '+s.missing+' remains listed as no data.':'');
 const low=ordered(selected.filter(valid),'low')[0],high=ordered(selected.filter(valid),'high')[0];
 $('raiInsight').textContent=low&&high&&s.valid>1?'Among these source units, access ranges from '+fmt(low.access_pct,1)+'% in '+low.name+' to '+fmt(high.access_pct,1)+'% in '+high.name+' — a '+fmt(high.access_pct-low.access_pct,1)+' percentage-point gap.':low?'This selection contains one source unit with a valid access value.':'This selection has no valid access percentage.';
 $('raiRows').innerHTML=sorted.map(r=>{const ok=valid(r),context=[r.region,r.country].filter(Boolean).join(' · ');return '<tr data-source-id="'+esc(r.id)+'"><th scope="row"><a href="'+mapURL(r)+'" target="_top" title="Open '+esc(r.name)+' on the rural-access map">'+esc(r.name)+' <span aria-hidden="true">↗</span></a><small>'+esc(context)+'</small></th><td>'+(ok?'<div class="rai-value"><div class="rai-track" aria-hidden="true"><span style="width:'+r.access_pct+'%"></span></div><strong>'+fmt(r.access_pct,1)+'%</strong></div>':'<span class="rai-no-data">Not available</span>')+'</td><td class="rai-pop">'+fmt(r.rural_population)+(ok?'':'<small>No valid denominator</small>')+'</td></tr>';}).join('');
 $('raiDownload').disabled=!selected.length;
}
async function init(){try{
 data=await parent.WBVault.json('analysis/ruralAccess');
 if(data.format!=='wb-rural-access-analysis-v1'||!Array.isArray(data.rows)||new Set(data.rows.map(r=>r.id)).size!==data.rows.length)throw Error('Invalid rural-access summary');
 const requested=new URLSearchParams(parent.location.search).get('raiCluster');if(data.clusters.some(c=>c.code===requested))cluster=requested;
 fillCountries();$('raiCountry').onchange=()=>{country=$('raiCountry').value;render();};$('raiSort').onchange=render;
 $('raiDownload').onclick=()=>{const file=new Blob(['\ufeff'+csv(ordered(rows(),$('raiSort').value))],{type:'text/csv;charset=utf-8'}),url=URL.createObjectURL(file),a=document.createElement('a');a.href=url;a.download='rural-access-'+cluster+(country?'-'+country.toLowerCase().replace(/[^a-z0-9]+/g,'-'):'')+'.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
 render();$('raiControls').hidden=false;$('raiLoading').hidden=true;
 }catch(error){$('raiLoading').textContent='Rural-access data could not load. Reopen Analysis to retry.';console.error(error);}}
init();
})();
