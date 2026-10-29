'use strict';
window.setupWBMapExport=function({map,DATA,isReady,getState}){
 const button=document.getElementById('wbSaveView');let busy=false,libraryPromise;
 const PIXEL_RATIO=2008/680,DPI=300;
 button.title='Save a map panel, a map with its key, or the legend colours';
 button.setAttribute('aria-haspopup','dialog');
 function library(){
  if(window.htmlToImage)return Promise.resolve(window.htmlToImage);
  if(!libraryPromise)libraryPromise=new Promise((resolve,reject)=>{const s=document.createElement('script');s.src='vendor/html-to-image.js?v=1.11.13';s.onload=()=>resolve(window.htmlToImage);s.onerror=()=>{libraryPromise=null;reject(Error('The image exporter could not load. Please try again.'));};document.head.appendChild(s);});
  return libraryPromise;
 }
 function element(tag,cls,text){const el=document.createElement(tag);if(cls)el.className=cls;if(text!=null)el.textContent=text;return el;}
 function visible(el){if(!el)return false;const r=el.getBoundingClientRect();return r.width>0&&r.height>0&&getComputedStyle(el).display!=='none';}
 function cropFor(node){
  const rect=node.getBoundingClientRect();let left=0,right=rect.width;
  // Exclude the area covered by desktop directories and the view menu.
  // On small screens, retain the full map extent behind the overlay menu.
  if(window.innerWidth>1024){
   const panel=document.querySelector('.panel');if(visible(panel))right=Math.min(right,panel.getBoundingClientRect().left-rect.left-12);
   for(const id of ['projectPanel','eventPanel']){const p=document.getElementById(id);if(visible(p)){const r=p.getBoundingClientRect();if(r.left<rect.left+rect.width/2)left=Math.max(left,r.right-rect.left+12);}}
  }
  if(right-left<300){left=0;right=rect.width;}
  return {left:Math.max(0,left),top:0,width:Math.floor(right-left),height:Math.floor(rect.height)};
 }
 async function waitImages(node){
  const rect=node.getBoundingClientRect();
  const images=[...node.querySelectorAll('img')].filter(img=>{const r=img.getBoundingClientRect();return r.width>0&&r.height>0&&r.right>rect.left&&r.left<rect.right&&r.bottom>rect.top&&r.top<rect.bottom&&getComputedStyle(img).opacity!=='0';});
  await Promise.all(images.map(img=>img.complete?(img.naturalWidth?Promise.resolve():Promise.reject(Error('A map image has not loaded. Wait for the map, then try again.'))):new Promise((resolve,reject)=>{
   const timeout=setTimeout(()=>{cleanup();reject(Error('Map images are still loading. Please try again.'));},15000);
   const done=()=>{cleanup();resolve();},fail=()=>{cleanup();reject(Error('A map image could not load. Please try again.'));};
   function cleanup(){clearTimeout(timeout);img.removeEventListener('load',done);img.removeEventListener('error',fail);}img.addEventListener('load',done,{once:true});img.addEventListener('error',fail,{once:true});
  })));
 }
 function cleanLegend(){
  const legend=document.getElementById('legend').cloneNode(true);legend.removeAttribute('id');
  legend.querySelectorAll('[id]').forEach(el=>el.removeAttribute('id'));
  legend.querySelectorAll('details').forEach(el=>el.open=true);
  legend.querySelectorAll('button,input,select,.credit-note').forEach(el=>el.remove());
  legend.classList.add('export-legend');
  const context=element('div','export-context'),sources=element('div','export-sources');
  [...legend.children].forEach(child=>{
   if(child.classList.contains('source-note'))sources.appendChild(child);
   else if(child.classList.contains('legend-row')){
    // Country names are self-explanatory; do not spend a legend row on them.
    if(child.querySelector('.country-label'))child.remove();else{
     for(const node of child.childNodes)if(node.nodeType===3)node.textContent=node.textContent.replace('Borderland Analysis boundary','Cluster boundary');
     context.appendChild(child);
    }
   }
  });
  for(const note of [...legend.querySelectorAll('.sedac-key p,.rural-access-key p,.scale-note')]){
   const text=note.textContent.trim();
   if(/^(Same .*scale|Same class breaks|Click |Select )/i.test(text)){note.remove();continue;}
   if(note.querySelector('i')||note.classList.contains('grdi-direction'))continue;
   note.querySelectorAll('br').forEach(br=>br.replaceWith(document.createTextNode(' · ')));
   note.classList.add('export-method');sources.prepend(note);
  }
  // Keep interpretation warnings and source dates, without repeated cross-map instructions.
  sources.querySelectorAll('.export-method').forEach(note=>{
   note.textContent=note.textContent.replace(/\s*·?\s*Same scale across all four maps\.?/gi,'').trim();
  });
  legend.querySelectorAll('.metric-title,.sedac-key>strong').forEach(el=>{
   el.textContent=el.textContent.replace(/\s*·\s*source grid/gi,'');
  });
  if(context.childElementCount)legend.appendChild(context);
  return {legend,sources};
 }
 function reportLabels(node,crop,displayWidth,panel=false){
  const changed=[],factor=crop.width/displayWidth;
  for(const el of node.querySelectorAll('.country-label,.admin-label,.admin3-label,.town-label,.place-label,.leaflet-tooltip,.leaflet-popup-content')){
   const original=el.getAttribute('style'),current=parseFloat(getComputedStyle(el).fontSize)||12;
   const country=el.matches('.country-label'),target=country?(panel?13.5:10.5):(panel?15:11.5);
   el.style.setProperty('font-size',(target*factor)+'px','important');
   el.style.setProperty('line-height','1.2','important');
   if(country){el.style.setProperty('font-weight','600','important');el.style.setProperty('letter-spacing','.08em','important');}
   changed.push([el,original]);
  }
  return ()=>changed.forEach(([el,original])=>original===null?el.removeAttribute('style'):el.setAttribute('style',original));
 }
 async function pngResolution(blob,dpi){
  const data=new Uint8Array(await blob.arrayBuffer()),parts=[data.slice(0,8)];
  const chunk=new Uint8Array(21),view=new DataView(chunk.buffer);
  view.setUint32(0,9);chunk.set([112,72,89,115],4);
  view.setUint32(8,Math.round(dpi/0.0254));view.setUint32(12,Math.round(dpi/0.0254));chunk[16]=1;
  let crc=0xffffffff;
  for(let i=4;i<17;i++){crc^=chunk[i];for(let k=0;k<8;k++)crc=(crc>>>1)^((crc&1)?0xedb88320:0);}
  view.setUint32(17,(crc^0xffffffff)>>>0);
  let pos=8;
  while(pos<data.length){
   const length=new DataView(data.buffer,data.byteOffset+pos,4).getUint32(0);
   const type=String.fromCharCode(...data.slice(pos+4,pos+8)),end=pos+12+length;
   if(type!=='pHYs')parts.push(data.slice(pos,end));
   if(type==='IHDR')parts.push(chunk);
   pos=end;
  }
  return new Blob(parts,{type:'image/png'});
 }
 function plainViewName(text){
  return text.replace(/\b(?:Relative\s+)?deprivation\b/gi,'Relative deprivation').replace(/\s*·\s*(?:raster|(?:10 km\s+)?hexagons?)\b/gi,'').replace(/\bPopulation surface\b/gi,'Population').trim();
 }
 function label(){
  const group=document.querySelector('.preset-grid .active')?.textContent?.trim()||'Map';
  const sub=document.querySelector('#themeControls .environment-choices button[aria-pressed="true"]')?.textContent?.trim();
  return plainViewName(sub||group);
 }
 function optionsText(){
  const parts=[];
  for(const s of document.querySelectorAll('#themeControls select,#analysisControls select'))if(visible(s)){const opt=s.selectedOptions[0];if(opt&&s.value)parts.push(opt.textContent.trim());}
  for(const b of document.querySelectorAll('.view-options .choice-buttons button.active'))if(visible(b))parts.push(b.textContent.trim());
  const years=[...document.querySelectorAll('#acledYearFilters .active')].map(x=>x.textContent.trim());if(visible(document.getElementById('acledFilters'))&&years.length)parts.push('Selected years: '+years.join(', '));
  for(const id of ['projectSummary','eventSummary']){const el=document.getElementById(id);if(visible(el)&&el.textContent.trim())parts.push(el.textContent.trim());}
  return [...new Set(parts)].join(' · ');
 }
 function scale(crop){
  const y=crop.height/2,x=crop.left+crop.width/2;
  const metres=map.distance(map.containerPointToLatLng([x,y]),map.containerPointToLatLng([x+100,y]));
  const unit=Math.pow(10,Math.floor(Math.log10(metres))),nice=[1,2,5,10].filter(n=>n*unit<=metres).pop()*unit;
  return {width:100*nice/metres,label:nice>=1000?(nice/1000).toLocaleString('en-GB')+' km':nice.toLocaleString('en-GB')+' m'};
 }
 // Shared legend files are derived from the current renderer and metric metadata.
 function legendDocument(){
  const state=getState?.()||{},parts=cleanLegend();
  const sources=[...parts.sources.children].map(e=>e.textContent.trim()).filter(Boolean);
  const spec={format:'wb-map-legend-v1',cluster:DATA.title||document.title,clusterCode:DATA.code,view:state.metric?.label||label(),exported:new Date().toISOString(),metric:state.metric||null,context:state.context||[],contextReference:state.contextReference||[],notes:state.metric?.notes||[],sources,attribution:document.querySelector('.leaflet-control-attribution')?.textContent.trim()||''};
  // Preserve supplementary symbol colours for views without a metric contract.
  const symbols=[];
  if(!spec.metric)for(const row of document.querySelectorAll('#legend .legend-classes .legend-row,#legend .land-class-item')){
   const swatch=row.querySelector('span,i');if(!swatch)continue;
   const colour=getComputedStyle(swatch).backgroundColor;
   if(colour&&colour!=='rgba(0, 0, 0, 0)')symbols.push({label:row.textContent.trim(),colour,kind:'fill'});
  }
  spec.other=symbols;
  return spec;
 }
 const slug=s=>String(s).toLowerCase().replace(/[^a-z0-9]+/g,'_').replace(/^_|_$/g,'');
 function downloadLink(blob,name,labelText,urls){
  const url=URL.createObjectURL(blob);urls.push(url);
  const a=element('a','wb-export-download',labelText);a.href=url;a.download=name;return a;
 }
 function legendLinks(spec,urls){
  const box=element('div','wb-export-legend-downloads'),name=DATA.code+'_'+slug(spec.view);
  box.append(element('strong','','Legend and colours'));
  const files=[['svg','image/svg+xml',WBMapLegend.svg(spec),'Legend · SVG'],['csv','text/csv;charset=utf-8',WBMapLegend.csv(spec),'Colours · CSV'],['json','application/json',JSON.stringify({...spec,styles:WBMapLegend.rows(spec)},null,2),'Full specification · JSON'],['txt','text/plain;charset=utf-8',WBMapLegend.credits(spec),'Sources and notes · TXT']];
  for(const [ext,type,data,title] of files)box.append(downloadLink(new Blob([data],{type}),name+'_legend.'+ext,title,urls));
  return box;
 }
 function mountDialog(dialog,urls=[]){
  const close=element('button','wb-export-dismiss','×');close.type='button';close.setAttribute('aria-label','Close save map');close.onclick=()=>dialog.close();dialog.prepend(close);
  dialog.addEventListener('close',()=>{dialog.remove();urls.forEach(URL.revokeObjectURL);button.focus();},{once:true});
  dialog.addEventListener('click',event=>{if(event.target===dialog){const r=dialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)dialog.close();}});
  document.body.appendChild(dialog);dialog.showModal();
 }
 let settings={content:'framed',orientation:'landscape',area:'current'};
 function chooseOrientation(){
  if(busy||document.querySelector('.wb-export-dialog'))return;
  const dialog=element('dialog','wb-export-dialog wb-export-options'),urls=[];
  dialog.setAttribute('aria-labelledby','wbExportDialogTitle');
  const heading=element('h2','','Save map');heading.id='wbExportDialogTitle';dialog.append(heading);
  dialog.append(element('p','','Download the current view, or save its legend separately.'));
  const form=element('form','wb-export-form');form.method='dialog';
  const content=element('fieldset'),contentTitle=element('legend','','Include');content.append(contentTitle);
  for(const [value,title,detail] of [['framed','Map with legend','Title, key and sources'],['panel','Map panel only','No title, key or footer']]){
   const item=element('label','wb-export-radio'),input=element('input');input.type='radio';input.name='exportContent';input.value=value;input.checked=settings.content===value;
   const text=element('span');text.append(element('strong','',title),element('small','',detail));item.append(input,text);content.append(item);
  }
  const orientation=element('fieldset'),orientationTitle=element('legend','','Shape');orientation.append(orientationTitle);
  for(const [value,title,detail] of [['landscape','Landscape','16:9 · PowerPoint'],['portrait','Portrait','3:4 · reports']]){
   const item=element('label','wb-export-radio'),input=element('input');input.type='radio';input.name='exportOrientation';input.value=value;input.checked=settings.orientation===value;
   const text=element('span');text.append(element('strong','',title),element('small','',detail));item.append(input,text);orientation.append(item);
  }
  const areaLabel=element('label','wb-export-area','Map area'),area=element('select');area.name='exportArea';area.setAttribute('aria-label','Map area');for(const [value,title] of [['current','Current map area'],['cluster','Fit whole cluster']]){const option=element('option','',title);option.value=value;option.selected=settings.area===value;area.append(option);}areaLabel.append(area);
  const note=element('p','wb-export-layout-note');
  const update=()=>{const panel=form.querySelector('[name="exportContent"]:checked')?.value==='panel';areaLabel.hidden=!panel;note.textContent=panel?'Fits the selected map area into the chosen shape; extra surroundings may appear. Preview before downloading.':'Keeps your current map extent, with the key beside or below the map.';};
  form.append(content,orientation,areaLabel,note);form.addEventListener('change',update);update();
  const create=element('button','wb-export-primary','Create map');create.type='submit';form.append(create);
  form.onsubmit=e=>{e.preventDefault();settings={content:form.querySelector('[name="exportContent"]:checked').value,orientation:form.querySelector('[name="exportOrientation"]:checked').value,area:area.value};dialog.close();settings.content==='panel'?savePanel(settings.orientation,settings.area):save(settings.orientation);};
  if(!isReady()){create.disabled=true;note.textContent='Wait for this view to finish loading, then reopen Save view.';}
  dialog.append(form);if(isReady())dialog.append(legendLinks(legendDocument(),urls));mountDialog(dialog,urls);
 }
 const frames=()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
 async function waitMapTiles(){
  const jobs=[];map.eachLayer(layer=>{if(layer.isLoading?.())jobs.push(new Promise((resolve,reject)=>{const done=()=>{clearTimeout(timer);layer.off('load',done);resolve();};const timer=setTimeout(()=>{layer.off('load',done);reject(Error('Map tiles are still loading. Please try again.'));},20000);layer.on('load',done);}));});await Promise.all(jobs);await frames();
 }
 async function savePanel(orientation,area){
  if(busy)return;
  const status=element('div','wb-export-status','Preparing map panel…');status.setAttribute('role','status');document.body.append(status);
  if(!isReady()){status.textContent='Wait for this view to finish loading, then try again.';setTimeout(()=>status.remove(),7000);return;}
  busy=true;button.disabled=true;button.textContent='Saving…';map.stop();
  const cover=element('div','wb-export-cover');document.body.append(cover);
  const mapNode=map.getContainer(),oldStyle=mapNode.getAttribute('style'),oldCentre=map.getCenter(),oldZoom=map.getZoom();
  const originalCrop=cropFor(mapNode),bounds=area==='cluster'?L.geoJSON(DATA.cluster).getBounds():L.latLngBounds(map.containerPointToLatLng([originalCrop.left,0]),map.containerPointToLatLng([originalCrop.left+originalCrop.width,originalCrop.height]));
  const landscape=orientation==='landscape',width=landscape?1280:900,height=landscape?720:1200;
  let restoreLabels,result;
  try{
   const spec=legendDocument(),capture=await library();
   mapNode.style.cssText='position:fixed!important;left:0!important;top:0!important;right:auto!important;bottom:auto!important;width:'+width+'px!important;height:'+height+'px!important;';
   map.invalidateSize({pan:false,animate:false});map.fitBounds(bounds,{padding:area==='cluster'?[24,24]:[8,8],animate:false});
   await waitMapTiles();await waitImages(mapNode);
   restoreLabels=reportLabels(mapNode,{width},width*720/height,true);
   const filter=node=>!node.classList?.contains('leaflet-control-container')&&!node.classList?.contains('leaflet-popup-pane')&&!node.classList?.contains('leaflet-tooltip-pane');
   const canvas=await capture.toCanvas(mapNode,{width,height,pixelRatio:3200/Math.max(width,height),skipFonts:true,includeQueryParams:true,filter,onImageErrorHandler:()=>{throw Error('A map image could not be included. Please try again.');}});
   const raw=await new Promise((resolve,reject)=>canvas.toBlob(b=>b?resolve(b):reject(Error('The PNG could not be created.')),'image/png'));
   const blob=await pngResolution(raw,DPI);
   spec.output={content:'map-panel-only',orientation,area,width:canvas.width,height:canvas.height,dpi:DPI,bounds:map.getBounds().toBBoxString()};
   result={blob,spec,width:canvas.width,height:canvas.height};
  }catch(error){console.error('Map panel export failed',error);status.textContent=error.message||'The map could not be saved.';const close=element('button','','Close');close.onclick=()=>status.remove();status.append(close);}
  finally{
   restoreLabels?.();oldStyle===null?mapNode.removeAttribute('style'):mapNode.setAttribute('style',oldStyle);
   map.invalidateSize({pan:false,animate:false});map.setView(oldCentre,oldZoom,{animate:false});
   cover.remove();busy=false;button.disabled=false;button.textContent='Save view';
  }
  if(result){status.remove();showPanel(result);}
 }
 function showPanel({blob,spec,width,height}){
  const urls=[],dialog=element('dialog','wb-export-dialog wb-export-preview');dialog.setAttribute('aria-label','Map panel preview');
  dialog.append(element('h2','','Map panel preview'),element('p','',width.toLocaleString()+' × '+height.toLocaleString()+' pixels · 300 dpi'));
  const url=URL.createObjectURL(blob);urls.push(url);const img=element('img','wb-export-preview-image');img.src=url;img.alt=spec.cluster+' · '+spec.view;dialog.append(img);
  const actions=element('div','wb-export-actions'),name=DATA.code+'_'+slug(spec.view)+'_panel_'+spec.output.orientation+'.png';
  const download=element('a','wb-export-primary','Download PNG');download.href=url;download.download=name;actions.append(download);
  if(window.ClipboardItem&&navigator.clipboard?.write){const copy=element('button','wb-export-secondary','Copy image');copy.type='button';copy.onclick=async()=>{try{await navigator.clipboard.write([new ClipboardItem({'image/png':blob})]);copy.textContent='Copied — paste into PowerPoint';}catch(e){copy.textContent='Use Download PNG';}};actions.append(copy);}
  const back=element('button','wb-export-secondary','Change options');back.type='button';back.onclick=()=>{dialog.addEventListener('close',chooseOrientation,{once:true});dialog.close();};actions.append(back);dialog.append(actions,legendLinks(spec,urls));mountDialog(dialog,urls);
 }

 button.addEventListener('click',chooseOrientation);
 async function save(orientation){
  if(busy)return;
  document.querySelectorAll('.wb-export-status').forEach(el=>el.remove());
  const status=element('div','wb-export-status','Preparing report-ready map…');status.setAttribute('role','status');status.setAttribute('aria-live','polite');document.body.appendChild(status);
  if(!isReady()){status.textContent='Wait for this view to finish loading, then select Save view again.';setTimeout(()=>status.remove(),8000);return;}
  busy=true;button.disabled=true;button.textContent='Saving…';map.stop();
  const cover=element('div','wb-export-cover');document.body.appendChild(cover);let sheet,restoreLabels;
  try{
   const mapNode=map.getContainer(),crop=cropFor(mapNode),title=document.querySelector('.panel .title').textContent.trim().replace(/\s+Borderland(?:s)?(?: Cluster)?$/i,''),view=label(),options=optionsText(),legendParts=cleanLegend(),scaleBar=scale(crop);
   const period=document.body.classList.contains('deprivation-view')?'2022 release · inputs 2010–2020':'';
   const attribution=document.querySelector('.leaflet-control-attribution')?.textContent.trim()||'';
   const capture=await library();await waitImages(mapNode);
   const landscape=orientation==='landscape',aspect=landscape?16/9:3/4;
   let frameWidth=landscape?1088:680;
   sheet=element('article','wb-export-sheet export-'+orientation);sheet.style.width=frameWidth+'px';sheet.style.height=(frameWidth/aspect)+'px';sheet.setAttribute('aria-hidden','true');
   const header=element('header');header.append(element('h1','',title+' · '+view));
   if(options||period)header.appendChild(element('p','export-period',[options,period].filter(Boolean).join(' · ')));sheet.appendChild(header);
   const body=element('div','export-body'),mapFrame=element('div','export-map-frame'),mapBox=element('div','export-map');
   const img=element('img','export-image');img.alt=view;mapBox.appendChild(img);
   const mapFoot=element('div','export-map-footer'),bar=element('div','export-scale',scaleBar.label);bar.title='Scale at map centre';mapFoot.append(bar,element('span','export-north','↑ N'));mapBox.appendChild(mapFoot);mapFrame.appendChild(mapBox);
   const caption=element('div','export-caption'),key=element('aside','export-key');key.append(legendParts.legend);caption.appendChild(key);
   if(legendParts.sources.childElementCount)caption.appendChild(legendParts.sources);else caption.classList.add('key-only');
   body.append(mapFrame,caption);sheet.appendChild(body);
   const footer=element('footer'),credits=element('div');credits.append(element('div','export-credit','Mapping by Hugh Lamarque'),element('div','',attribution));
   const exported=new Date();footer.append(credits,element('div','','Exported '+exported.toLocaleDateString('en-GB',{day:'numeric',month:'long',year:'numeric'})));sheet.appendChild(footer);document.body.appendChild(sheet);
   // Keep all legend/source text. Unusually long captions grow the complete frame,
   // retaining its chosen ratio and print-scale typography instead of clipping it.
   let fits=false;
   for(let attempt=0;attempt<8;attempt++){
    const available=body.clientHeight,captionHeight=caption.scrollHeight;
    fits=landscape?captionHeight<=available+1:(available-caption.getBoundingClientRect().height>=260);
    if(fits)break;
    frameWidth*=1.12;sheet.style.width=frameWidth+'px';sheet.style.height=(frameWidth/aspect)+'px';
   }
   if(!fits)throw Error('The key is too long to fit this layout. Try the other orientation.');
   const maxWidth=mapFrame.clientWidth,maxHeight=mapFrame.clientHeight-28;
   const displayWidth=Math.min(maxWidth,maxHeight*crop.width/crop.height);
   if(displayWidth<120)throw Error('There is not enough room for the map. Try the other orientation.');
   mapBox.style.width=displayWidth+'px';bar.style.width=(scaleBar.width*displayWidth/crop.width)+'px';
   restoreLabels=reportLabels(mapNode,crop,displayWidth);
   const mapRatio=Math.min(6,Math.max(1,PIXEL_RATIO*displayWidth/crop.width));
   const filter=node=>!node.classList?.contains('leaflet-control-container')&&!node.classList?.contains('leaflet-popup-pane')&&!node.classList?.contains('leaflet-tooltip-pane');
   const mapCanvas=await capture.toCanvas(mapNode,{pixelRatio:mapRatio,skipFonts:true,includeQueryParams:true,filter,onImageErrorHandler:()=>{throw Error('A map image could not be included. Please try again.');}});
   const cropped=document.createElement('canvas');cropped.width=Math.round(crop.width*mapRatio);cropped.height=Math.round(crop.height*mapRatio);
   cropped.getContext('2d').drawImage(mapCanvas,Math.round(crop.left*mapRatio),0,cropped.width,cropped.height,0,0,cropped.width,cropped.height);
   restoreLabels();restoreLabels=null;img.src=cropped.toDataURL('image/png');await img.decode();
   status.textContent='Creating report PNG…';
   const finalRatio=PIXEL_RATIO;
   const output=await capture.toCanvas(sheet,{pixelRatio:finalRatio,skipFonts:true,includeQueryParams:true,backgroundColor:'#fff',style:{position:'static',left:'auto',top:'auto',transform:'none'}});
   const rawBlob=await new Promise((resolve,reject)=>output.toBlob(b=>b?resolve(b):reject(Error('The PNG could not be created.')),'image/png'));
   const blob=await pngResolution(rawBlob,DPI);
   const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=DATA.code+'_'+view.toLowerCase().replace(/[^a-z0-9]+/g,'_').replace(/_$/,'')+'_'+orientation+'_'+exported.toISOString().slice(0,10)+'.png';document.body.appendChild(a);a.click();a.textContent='Download PNG';a.style.cssText='display:inline-block;margin-left:14px;color:#244e46;font-weight:600';
   status.textContent=(landscape?'Landscape PNG · 16:9':'Portrait PNG · 3:4')+' · 300 dpi · '+output.width.toLocaleString()+' × '+output.height.toLocaleString()+' pixels';status.appendChild(a);const preview=element('a','','Preview');preview.href=url;preview.target='_blank';preview.rel='noopener';preview.style.cssText=a.style.cssText;status.appendChild(preview);
   if(window.ClipboardItem&&navigator.clipboard?.write){
    const copy=element('button','','Copy image');copy.type='button';
    copy.onclick=async()=>{try{await navigator.clipboard.write([new ClipboardItem({'image/png':blob})]);copy.textContent='Copied — paste into '+(landscape?'PowerPoint':'Word');}catch(e){copy.textContent='Use Download PNG to insert the image';}};
    status.appendChild(copy);
   }
   const close=element('button','','Close');close.type='button';close.onclick=()=>status.remove();status.appendChild(close);setTimeout(()=>{status.remove();URL.revokeObjectURL(url);},120000);
  }catch(error){console.error('Map export failed',error);status.textContent=error.message||'The map could not be saved. Please try again.';const close=element('button','','Close');close.type='button';close.onclick=()=>status.remove();status.appendChild(close);}
  finally{restoreLabels?.();sheet?.remove();cover.remove();busy=false;button.disabled=false;button.textContent='Save view';}
 }
};


