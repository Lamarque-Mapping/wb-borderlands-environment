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
  const originalCrop=cropFor(mapNode),bounds=area==='cluster'?L.latLngBounds(DATA.bounds):L.latLngBounds(map.containerPointToLatLng([originalCrop.left,0]),map.containerPointToLatLng([originalCrop.left+originalCrop.width,originalCrop.height]));
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
