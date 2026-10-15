'use strict';
window.setupWBMapExport=function({map,DATA,isReady}){
 const button=document.getElementById('wbSaveView');let busy=false,libraryPromise;
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
  return legend;
 }
 function label(){const group=document.querySelector('.preset-grid .active')?.textContent?.trim()||'Map';const sub=document.querySelector('#themeControls .environment-choices button[aria-pressed="true"]')?.textContent?.trim();return sub?group+' / '+sub:group;}
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
 button.addEventListener('click',async()=>{
  if(busy)return;
  document.querySelectorAll('.wb-export-status').forEach(el=>el.remove());
  const status=element('div','wb-export-status','Preparing high-resolution map…');status.setAttribute('role','status');status.setAttribute('aria-live','polite');document.body.appendChild(status);
  if(!isReady()){status.textContent='Wait for this view to finish loading, then select Save view again.';setTimeout(()=>status.remove(),8000);return;}
  busy=true;button.disabled=true;button.textContent='Saving…';map.stop();
  const cover=element('div','wb-export-cover');document.body.appendChild(cover);let sheet;
  try{
   const mapNode=map.getContainer(),crop=cropFor(mapNode),title=document.querySelector('.panel .title').textContent.trim(),view=label(),options=optionsText(),legend=cleanLegend(),scaleBar=scale(crop);
   const period=document.body.classList.contains('deprivation-view')?'GRDI v1 · 2022 release · inputs 2010–2020':'';
   const attribution=document.querySelector('.leaflet-control-attribution')?.textContent.trim()||'';
   const capture=await library();await waitImages(mapNode);
   const frameWidth=crop.width+380,ratio=Math.min(6,4800/frameWidth);
   const filter=node=>!node.classList?.contains('leaflet-control-container')&&!node.classList?.contains('leaflet-tooltip-pane');
   const mapCanvas=await capture.toCanvas(mapNode,{pixelRatio:ratio,skipFonts:true,includeQueryParams:true,filter,onImageErrorHandler:()=>{throw Error('A map image could not be included. Please try again.');}});
   const cropped=document.createElement('canvas');cropped.width=Math.round(crop.width*ratio);cropped.height=Math.round(crop.height*ratio);
   cropped.getContext('2d').drawImage(mapCanvas,Math.round(crop.left*ratio),0,cropped.width,cropped.height,0,0,cropped.width,cropped.height);
   sheet=element('article','wb-export-sheet');sheet.style.width=frameWidth+'px';sheet.setAttribute('aria-hidden','true');
   const header=element('header');header.append(element('p','export-eyebrow','BORDERLAND MAPS'),element('h1','',title),element('p','export-subtitle',view));
   if(period)header.appendChild(element('p','export-period',period));if(options)header.appendChild(element('p','export-period',options));sheet.appendChild(header);
   const body=element('div','export-body'),mapBox=element('div','export-map');mapBox.style.width=crop.width+'px';
   const img=element('img','export-image');img.alt=view;img.src=cropped.toDataURL('image/png');mapBox.appendChild(img);
   const mapFoot=element('div','export-map-footer'),bar=element('div','export-scale',scaleBar.label);bar.style.width=scaleBar.width+'px';mapFoot.append(bar,element('span','','Scale at map centre'),element('span','export-north','↑ N'));mapBox.appendChild(mapFoot);
   const key=element('aside','export-key');key.append(element('h2','','KEY & SOURCES'),legend);body.append(mapBox,key);sheet.appendChild(body);
   const footer=element('footer'),credits=element('div');credits.append(element('div','export-credit','Mapping by Hugh Lamarque'),element('div','',attribution));
   const exported=new Date();footer.append(credits,element('div','','Exported '+exported.toLocaleDateString('en-GB',{day:'numeric',month:'long',year:'numeric'})+' · current view'));sheet.appendChild(footer);document.body.appendChild(sheet);await img.decode();
   status.textContent='Creating framed PNG…';
   const finalRatio=Math.min(ratio,5400/sheet.getBoundingClientRect().height);
   const output=await capture.toCanvas(sheet,{pixelRatio:finalRatio,skipFonts:true,includeQueryParams:true,backgroundColor:'#fff'});
   const blob=await new Promise((resolve,reject)=>output.toBlob(b=>b?resolve(b):reject(Error('The PNG could not be created.')),'image/png'));
   const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=DATA.code+'_'+view.toLowerCase().replace(/[^a-z0-9]+/g,'_').replace(/_$/,'')+'_'+exported.toISOString().slice(0,10)+'.png';document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);
   status.textContent='Map downloaded · '+output.width.toLocaleString()+' × '+output.height.toLocaleString()+' pixels';setTimeout(()=>status.remove(),8000);
  }catch(error){console.error('Map export failed',error);status.textContent=error.message||'The map could not be saved. Please try again.';const close=element('button','','Close');close.type='button';close.onclick=()=>status.remove();status.appendChild(close);}
  finally{sheet?.remove();cover.remove();busy=false;button.disabled=false;button.textContent='Save view';}
 });
};
