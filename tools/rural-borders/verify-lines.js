const fs=require('fs'),vm=require('vm'),assert=require('assert');
const root=__dirname,context={window:{}};vm.createContext(context);
vm.runInContext(fs.readFileSync(root+'/site/analysis/rural-country-lines-v1.js','utf8'),context);
const results=[];
for(const [code,expected] of Object.entries({karamoja:1310,mandera_triangle:219,moyale_borana:325,dikhil:110})){
 const units=JSON.parse(fs.readFileSync(root+'/../rai_live/working/data/'+code+'_ruralAccess.json','utf8')).ruralAccessUnits;
 const before=JSON.stringify(units),lines=context.window.wbRuralCountryLines(units);
 assert.equal(lines.features[0].geometry.coordinates.length,expected);
 assert.equal(JSON.stringify(units),before);
 const originalEdges=new Map();
 for(const f of units.features){const g=f.geometry;for(const polygon of g.type==='Polygon'?[g.coordinates]:g.coordinates)for(const ring of polygon)for(let i=1;i<ring.length;i++){
  const key=[JSON.stringify(ring[i-1]),JSON.stringify(ring[i])].sort().join('|');
  if(!originalEdges.has(key))originalEdges.set(key,new Set());originalEdges.get(key).add(f.properties.NAME_0);
 }}
 for(const segment of lines.features[0].geometry.coordinates){const key=segment.map(x=>JSON.stringify(x)).sort().join('|');assert(originalEdges.get(key)?.size>1);}
 results.push({code,exact_shared_country_segments:expected,source_polygons_unchanged:true,all_output_segments_belong_to_different_source_countries:true});
}
fs.writeFileSync(root+'/geometry-checks.json',JSON.stringify(results,null,2)+'\n');console.log(JSON.stringify(results));
