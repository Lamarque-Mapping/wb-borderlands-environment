'use strict';
(async()=>{
 const panel=document.querySelector('.regional-map');if(!panel)return;
 const block=panel.closest('.map-panel'),error=block.querySelector('.map-error');
 try{
  if(!window.L)throw Error('Map library unavailable');
  const response=await fetch('clusters.json');if(!response.ok)throw Error('Cluster outlines unavailable');
  const data=await response.json();
  const colours={moyale_borana:'#2d7b6c',mandera_triangle:'#4c7692',karamoja:'#9b7150',dikhil:'#7c8050'};
  const map=L.map(panel,{zoomControl:false,scrollWheelZoom:false,zoomSnap:.25,zoomDelta:.5,attributionControl:true});
  L.control.zoom({position:'topright'}).addTo(map);
  L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}',{maxZoom:16,attribution:'Tiles &copy; Esri, HERE, Garmin, OpenStreetMap contributors'}).addTo(map);
  const layers={},links=[...document.querySelectorAll('[data-code]')];
  function highlight(code){for(const [id,layer] of Object.entries(layers)){const active=id===code;layer.setStyle({weight:active?3:1.8,fillOpacity:active?.38:code?.10:.23,opacity:code&&!active?.65:1});if(active)layer.bringToFront();}links.forEach(a=>a.classList.toggle('is-active',a.dataset.code===code));}
  function open(code){location.href='../#map='+encodeURIComponent(code);}
  data.features.forEach((feature,i)=>{
   const code=feature.properties.code,colour=colours[code];
   const layer=L.geoJSON(feature,{style:{color:colour,weight:1.8,fillColor:colour,fillOpacity:.23},onEachFeature:(f,p)=>{p.bindTooltip(feature.properties.name+' · Open map',{className:'cluster-tooltip',sticky:true});p.on({mouseover:()=>highlight(code),mouseout:()=>highlight(null),click:()=>open(code)});}}).addTo(map);layers[code]=layer;
   const long=document.body.classList.contains('theme-immersive')&&matchMedia('(min-width:761px)').matches;
   const number=String(i+1).padStart(2,'0');
   const marker=L.marker(layer.getBounds().getCenter(),{title:feature.properties.name+' · Open map',alt:feature.properties.name+' cluster',icon:L.divIcon({className:'cluster-map-label'+(long?' long':''),html:'<span style="--cluster:'+colour+'">'+(long?'<b>'+number+'</b>'+feature.properties.name:number)+'</span>',iconSize:long?[140,34]:[30,30],iconAnchor:long?(code==='moyale_borana'?[70,-10]:code==='mandera_triangle'?[70,45]:[70,17]):[15,15]})}).addTo(map);
   marker.on({mouseover:()=>highlight(code),mouseout:()=>highlight(null),click:()=>open(code)});
  });
  const extent=L.featureGroup(Object.values(layers)).getBounds();
  function fit(){map.invalidateSize({animate:false});const immersive=document.body.classList.contains('theme-immersive'),wide=matchMedia('(min-width:761px)').matches;map.fitBounds(extent,{paddingTopLeft:immersive&&wide?[305,50]:[34,38],paddingBottomRight:immersive&&wide?[80,168]:[34,65],animate:false});}
  fit();block.querySelector('.map-reset').addEventListener('click',fit);
  let resize;window.addEventListener('resize',()=>{clearTimeout(resize);resize=setTimeout(fit,120);});
  links.forEach(a=>{for(const event of ['mouseenter','focus'])a.addEventListener(event,()=>highlight(a.dataset.code));for(const event of ['mouseleave','blur'])a.addEventListener(event,()=>highlight(null));});
  panel.dataset.mapReady='true';
 }catch(e){error.hidden=false;console.error(e);}
})();
