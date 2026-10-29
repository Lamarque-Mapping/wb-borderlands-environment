'use strict';
(function(root){
 const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&apos;'}[c]));
 const hex=c=>{if(!c)return '';if(/^#[0-9a-f]{6}$/i.test(c))return c.toUpperCase();if(/^#[0-9a-f]{3}$/i.test(c))return '#'+c.slice(1).split('').map(v=>v+v).join('').toUpperCase();const m=c.match(/^rgba?\(\s*(\d+)[, ]+\s*(\d+)[, ]+\s*(\d+)/);return m?'#'+m.slice(1,4).map(v=>(+v).toString(16).padStart(2,'0')).join('').toUpperCase():c;};
 const rgb=c=>/^#[0-9A-F]{6}$/.test(hex(c))?hex(c).slice(1).match(/../g).map(v=>parseInt(v,16)):[];
 const csvCell=x=>'"'+String(x??'').replace(/"/g,'""')+'"';
 function rows(spec){
  const out=[],m=spec.metric;
  if(m){
   if(m.classes){let lower=m.low??0;m.classes.forEach((b,i)=>{const upper=b.max??b.upper??null;out.push({section:m.label,label:b.label,kind:'fill',colour:b.colour,opacity:m.opacity,lower:b.lower??lower,upper,lower_inclusive:b.lower_inclusive??i===0,upper_inclusive:b.upper_inclusive??true,unit:m.unit});lower=upper;});}
   if(m.stops)m.stops.forEach((colour,i)=>{const position=i/(m.stops.length-1);out.push({section:m.label,label:'Gradient stop '+(i+1),kind:'gradient',colour,opacity:m.opacity,position,value:m.low+(m.high-m.low)*(m.transform==='sqrt'?position*position:position),unit:m.unit});});
   if(m.noData)out.push({section:m.label,label:m.noData.label||'No data',kind:'fill',colour:m.noData.colour,opacity:m.noData.opacity??m.opacity});
  }
  for(const r of spec.context||[])out.push({section:'Context',kind:'line',...r});
  for(const r of spec.contextReference||[])if(!(spec.context||[]).some(x=>x.label===r.label))out.push({section:'Context reference (not shown)',kind:'line',...r});
  for(const r of spec.other||[])out.push({section:'Other legend symbols',...r});
  return out.map(r=>({...r,colour:hex(r.colour),rgb:rgb(r.colour),transparency:r.opacity==null?null:Math.round((1-r.opacity)*10000)/100}));
 }
 function csv(spec){
  const fields=['section','label','kind','colour','red','green','blue','opacity','transparency_percent','line_width_css_px','dash_pattern_css_px','lower','upper','lower_inclusive','upper_inclusive','gradient_position','value','unit'];
  const data=rows(spec).map(r=>[r.section,r.label,r.kind,r.colour,...[0,1,2].map(i=>r.rgb[i]),r.opacity,r.transparency,r.weight,r.dashArray,r.lower,r.upper,r.lower_inclusive,r.upper_inclusive,r.position,r.value,r.unit]);
  return '\ufeff'+[fields,...data].map(a=>a.map(csvCell).join(',')).join('\r\n')+'\r\n';
 }
 function wrap(text,max=74){const lines=[];let line='';for(const w of String(text).split(/\s+/)){if((line+' '+w).length>max&&line){lines.push(line);line=w;}else line+=(line?' ':'')+w;}if(line)lines.push(line);return lines;}
 function svg(spec){
  let y=28;const parts=[],width=640;
  const text=(s,size=15,weight=400)=>{for(const line of wrap(s,size>=18?49:74)){parts.push('<text x="20" y="'+y+'" font-size="'+size+'" font-weight="'+weight+'">'+esc(line)+'</text>');y+=size+7;}};
  text(spec.cluster,20,700);text(spec.view,16,600);y+=8;
  const m=spec.metric;if(m){text(m.label,16,600);
   if(m.stops){parts.push('<defs><linearGradient id="ramp">'+m.stops.map((c,i)=>'<stop offset="'+(100*i/(m.stops.length-1))+'%" stop-color="'+hex(c)+'"/>').join('')+'</linearGradient></defs><rect x="20" y="'+y+'" width="580" height="18" fill="url(#ramp)" fill-opacity="'+(m.opacity??1)+'"/>');y+=38;parts.push('<text x="20" y="'+y+'" font-size="14">'+esc(m.low+' '+m.unit)+'</text><text x="600" y="'+y+'" text-anchor="end" font-size="14">'+esc(m.high+' '+m.unit)+'</text>');y+=26;}
   for(const r of rows({...spec,context:[],contextReference:[],other:[]}).filter(r=>r.kind!=='gradient')){parts.push('<rect x="20" y="'+(y-13)+'" width="28" height="16" fill="'+r.colour+'" fill-opacity="'+(r.opacity??1)+'"/><text x="60" y="'+y+'" font-size="15">'+esc(r.label)+'</text>');y+=26;}
  }
  if(spec.context?.length){y+=8;text('Context',16,600);for(const r of spec.context){parts.push('<line x1="20" x2="48" y1="'+(y-5)+'" y2="'+(y-5)+'" stroke="'+hex(r.colour)+'" stroke-width="'+(r.weight||2)+'" stroke-opacity="'+(r.opacity??1)+'"'+(r.dashArray?' stroke-dasharray="'+esc(r.dashArray)+'"':'')+'/><text x="60" y="'+y+'" font-size="15">'+esc(r.label)+'</text>');y+=26;}}
  if(spec.other?.length){y+=8;for(const r of spec.other){parts.push('<rect x="20" y="'+(y-13)+'" width="28" height="16" fill="'+hex(r.colour)+'"/><text x="60" y="'+y+'" font-size="15">'+esc(r.label)+'</text>');y+=26;}}
  for(const note of spec.notes||[]){y+=9;text(note,12);}
  return '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="'+(y+8)+'" viewBox="0 0 640 '+(y+8)+'"><title>'+esc(spec.cluster+' · '+spec.view+' legend')+'</title><g font-family="Arial, Helvetica, sans-serif" fill="#233a45">'+parts.join('')+'</g></svg>';
 }
 function credits(spec){return [spec.cluster+' · '+spec.view,'',...(spec.notes||[]),'',...(spec.sources||[]),'',spec.attribution||'','Mapping by Hugh Lamarque','','Map-panel exports omit the printed credits. Include the relevant source and basemap credits in your slide or figure caption.','','Colours are sRGB. Opacity is 0–1; PowerPoint transparency is 100 × (1 − opacity).','Semi-transparent fills blend with the map beneath them; a flat swatch cannot reproduce every background pixel.','Line widths and dash lengths are in map CSS pixels before export scaling.','Generated '+spec.exported].join('\n');}
 root.WBMapLegend={rows,csv,svg,credits,hex,rgb};
 if(typeof module!=='undefined')module.exports=root.WBMapLegend;
})(typeof window!=='undefined'?window:globalThis);
