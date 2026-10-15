'use strict';
// Trace only exact source edges shared by units assigned to different countries.
// No snapping, interpolation, polygon changes, or outside edges are introduced.
window.wbRuralCountryLines=function(units){
 const edges=new Map();
 for(const feature of units.features||[]){
  const country=feature.properties?.NAME_0,geometry=feature.geometry;
  if(!country||!geometry)continue;
  const polygons=geometry.type==='Polygon'?[geometry.coordinates]:geometry.type==='MultiPolygon'?geometry.coordinates:[];
  for(const polygon of polygons)for(const ring of polygon)for(let i=1;i<ring.length;i++){
   const a=ring[i-1],b=ring[i],aKey=JSON.stringify(a),bKey=JSON.stringify(b);
   if(aKey===bKey)continue;
   const key=aKey<bKey?aKey+'|'+bKey:bKey+'|'+aKey;
   const edge=edges.get(key);
   if(edge)edge.countries.add(country);else edges.set(key,{coordinates:[a,b],countries:new Set([country])});
  }
 }
 const shared=[...edges.values()].filter(edge=>edge.countries.size>1);
 return {type:'FeatureCollection',features:shared.length?[{type:'Feature',properties:{source:'NASA SEDAC RAI 2023 / GADM v3.6',method:'Exact edges shared by source units from different countries'},geometry:{type:'MultiLineString',coordinates:shared.map(edge=>edge.coordinates)}}]:[]};
};
