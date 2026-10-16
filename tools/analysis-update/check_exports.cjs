const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert/strict');
const root=__dirname, read=p=>fs.readFileSync(path.join(root,p),'utf8'),spec=JSON.parse(read('dom-spec.json'));
class Element{
 constructor(id='',s={}){this.id=id;this.tagName=s.tag||'div';this.textContent=s.text||'';this.options=(s.options||[]).map(o=>({value:o.value,text:o.text,textContent:o.text}));this.value=s.value||this.options[0]?.value||'';this.disabled=id.endsWith('ExportCSV')||id.endsWith('ExportPNG');this.attrs={};this.style={};this.dataset={};this.children=[];this.buttons=(s.buttons||[]).map(b=>{const x=new Element();x.dataset.value=b.value;x.textContent=b.text;x.attrs['aria-pressed']=b.pressed;return x;});this.classList={add(){}};}
 get selectedOptions(){return this.options.filter(o=>o.value===this.value);}
 set innerHTML(v){this.html=v;if(this.tagName==='select'){this.options=[...v.matchAll(/<option value="([^"]*)"[^>]*>(.*?)<\/option>/g)].map(m=>({value:m[1],text:m[2],textContent:m[2]}));this.value=this.options[0]?.value||'';}}
 get innerHTML(){return this.html||'';}
 replaceChildren(...xs){this.children=xs;if(this.tagName==='select')this.options=xs;}
 append(x){this.children.push(x);if(this.tagName==='select')this.options.push(x);}
 set text(v){this.textContent=v;} get text(){return this.textContent;}
 addEventListener(t,f){this['on'+t]=f;}setAttribute(k,v){this.attrs[k]=v;}getAttribute(k){return this.attrs[k];}removeAttribute(k){delete this.attrs[k];}remove(){}focus(){}click(){this.onclick?.();}
 querySelectorAll(sel){if(sel==='button')return this.buttons;if(sel==='table tbody tr')return spec.source_rows.map(row=>({cells:row.map(x=>({textContent:x,querySelectorAll:()=>[]}))}));return [];}
}
const els=Object.fromEntries(Object.entries(spec).filter(([k])=>k!=='source_rows').map(([k,v])=>[k,new Element(k,v)]));
const errors=[],downloads=[];const datasets={'analysis/summary':JSON.parse(read('baseline/summary.json')),'analysis/geography':JSON.parse(read('baseline/geography.json')),'analysis/sedac':JSON.parse(read('baseline/sedac.json')),'analysis/ruralAccess':JSON.parse(read('baseline/rural.json'))};
const doc={getElementById:id=>{if(id!=='data-sourcesExportPNG')assert(els[id],'Missing DOM id: '+id);return els[id]||null;},createElement:tag=>new Element('',{tag}),createTextNode:text=>({textContent:text}),querySelectorAll:sel=>sel==='[data-export-chart]'?Object.values(els).filter(e=>e.id.endsWith('ExportPNG')).map(e=>{e.dataset.exportChart=e.id.slice(0,-9);return e;}):[]};
const ctx={document:doc,console:{error:e=>errors.push(String(e))},URL:{createObjectURL:blob=>{downloads.push(blob);return 'blob:test';},revokeObjectURL(){}},URLSearchParams,Blob,setTimeout,Number,Map,Date,parent:{WBVault:{json:async key=>datasets[key]},location:{search:'?raiCluster=karamoja'}}};ctx.window=ctx;vm.createContext(ctx);
async function run(){
 vm.runInContext(read('site/analysis/exports-v1.js'),ctx);
 const exports={},realSave=ctx.WBAnalysisExport.saveCSV;
 ctx.WBAnalysisExport.saveCSV=(id,fields,rows,filename)=>{exports[id]=JSON.parse(JSON.stringify({fields,rows,filename}));};
 await vm.runInContext(read('site/sedac/analysis-v4.js'),ctx);
 vm.runInContext(read('site/analysis/rural-access-v2.js'),ctx);
 await vm.runInContext(read('inline-3.js'),ctx);
 await new Promise(resolve=>setImmediate(resolve));
 assert.deepEqual(errors,[]);
 const ids=['population','urban-settlements','settlement','landcover','deprivation','rural-access','healthcare','violence','historical-heat','portfolio','data-sources'];
 for(const id of ids.filter(x=>x!=='data-sources')){assert.equal(els[id+'ExportCSV'].disabled,false,id);els[id+'ExportCSV'].click();assert(exports[id],id);for(const row of exports[id].rows)assert.equal(row.length,exports[id].fields.length,id);if(id!=='data-sources')assert.equal(els[id+'ExportPNG'].disabled,false,id);}
 const value=(id,row,key)=>exports[id].rows[row][exports[id].fields.indexOf(key)];
 assert.equal(exports.population.rows.length,92);assert.equal(value('population',0,'population_2025'),267927.112); // exact original source value, not display rounding
 const change=(id,value)=>{els[id].value=value;els[id].onchange();};
 change('countrySelect','Kenya');els.populationExportCSV.click();assert.equal(exports.population.rows.length,10);assert(exports.population.rows.every(r=>r[3]==='Kenya'));
 change('levelSelect','cluster');els.populationExportCSV.click();assert.equal(exports.population.rows.length,4);assert.equal(new Set(exports.population.rows.map(r=>r[2])).size,4);
 const walk=els.healthModeButtons.buttons.find(b=>b.dataset.value==='walk');walk.click();els.healthcareExportCSV.click();assert(exports.healthcare.rows.every(r=>r[7]==='walk'));assert.equal(value('healthcare',0,'population_total_2025'),datasets['analysis/summary'].flatMap(s=>s.breakdowns.units).find(u=>u.key===value('healthcare',0,'area_id')).healthcare.walk.population_total);
 els.violenceExportCSV.click();const last=exports.violence.rows.at(-1);assert.equal(last[7],'2025-08');assert.equal(last[10],true);assert.equal(last[12],'2025-08-01');
 change('portfolioOrganisation','World Bank');els.portfolioExportCSV.click();assert(exports.portfolio.rows.length>0);for(const r of exports.portfolio.rows){assert.equal(r[4],'World Bank');assert.equal(r[8],r[10].split('; ').length);}
 change('portfolioOrganisation','No such organisation');els.portfolioExportCSV.click();assert.equal(exports.portfolio.rows.length,0);
 change('deprivationAnalysisCluster','dikhil');els['deprivationExportCSV'].click();assert.equal(exports.deprivation.rows.length,9);assert.equal(value('deprivation',4,'cluster'),'Dikhil');assert.equal(value('deprivation',4,'cluster_area_coverage_share'),datasets['analysis/sedac'].clusters.find(c=>c.code==='dikhil').grdi.coverage_share);
 change('heatAnalysisThreshold','32');els['historical-heatExportCSV'].click();assert.equal(exports['historical-heat'].rows.length,38);assert(exports['historical-heat'].rows.every(r=>r[3]===32));assert.equal(value('historical-heat',4,'year'),1983);
 change('urbanAnalysisCluster','dikhil');els['urban-settlementsExportCSV'].click();assert.equal(exports['urban-settlements'].rows.length,18);
 change('raiCountry','Kenya');els['rural-accessExportCSV'].click();const rural=exports['rural-access'];assert.equal(rural.rows.slice(0,4).filter(r=>r[0]==='cluster_summary').length,4);assert(rural.rows.slice(4).every(r=>r[5]==='Kenya'));const missing=rural.rows.find(r=>r[3]==='unknown 8');assert(missing);assert.equal(missing[6],null);assert.equal(missing[7],0);assert.equal(missing[9],null);
 els['data-sourcesExportCSV'].click();assert.equal(downloads.length,1);assert.equal((await downloads[0].text()).trim().split('\r\n').length,30);downloads.length=0;
 const csv=ctx.WBAnalysisExport.csv(['a','b','c'],[[null,0,-5],['=SUM(1,2)','line\nquote"','@CMD']]);assert(csv.includes(',0,-5'));assert(csv.includes("'"+'=SUM(1,2)'));assert(csv.includes('quote""'));assert(csv.charCodeAt(0)===0xfeff);
 realSave('population',['a'],[[0],[null]],'test.csv');assert.equal(downloads.length,1);assert.equal(await downloads[0].text(),'"a"\r\n0\r\n""\r\n');
 assert.deepEqual(errors,[]);
 const result={sections:10,data_exports:11,chart_buttons_ready:10,checks:['Exact population value and displayed ranking','Country and all-cluster filters','Walking healthcare mode and denominator','Partial-month ACLED metadata','Project filters, family IDs and empty selections','Deprivation selected cluster plus four summaries','Heat threshold plus 34 annual values','Urban footprint cohort','Rural filtered records plus four weighted summaries; zero denominator remains missing','29 source rows','CSV quoting, formula protection, UTF-8 BOM, zero and missing values']};
 fs.writeFileSync(path.join(root,'validation.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
}
run().catch(e=>{console.error(e,errors);process.exitCode=1;});
