"""Keep map controls stable and give GRDI a sequential purple display scale."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent/'sedac_integration'
REV='2026-10-15.views.48'
PALETTE=['#f2f0f7','#cbc9e2','#9e9ac8','#756bb1','#54278f']

def once(text, old, new):
    assert text.count(old)==1, old[:100]
    return text.replace(old,new,1)

SET_PRESET='''async function setPreset(name,options={}){
  name=resolvePreset(name);prepareTheme(name);
  const ticket=++presetSerial,box=document.getElementById('viewLoading');
  if(typeof normaliseEnvironmentChoice==='function')normaliseEnvironmentChoice(name);
  requestedPreset=name;viewReady=false;
  box.style.display='none';
  const loadingTimer=setTimeout(()=>{if(ticket===presetSerial){box.textContent='Loading view…';box.style.display='block';}},180);
  document.getElementById('contextMenu').inert=true;
  try{
    const groups=new Set([...(thematicGroups(name)||PRESET_GROUPS[name]||[]),...(typeof environmentGroups==='function'?environmentGroups(name):[])]);
    if(options.keepContext)for(const c of currentContext)for(const g of CONTEXT_GROUPS[c]||[])groups.add(g);
    if(name==='crossings'&&map.getZoom()>=10)groups.add('minorRoads');
    await Promise.all([...groups].map(ensureGroup).concat(name==='projects'?[ensureProjects()]:[]));
    if(ticket!==presetSerial)return;
    // Keep the old view intact during loading, then replace layers and controls together.
    clearRuralAccessSelection();corridors.prepare(name);sedac.prepare();
    if(!options.keepContext){
      currentContext.clear();
      document.querySelectorAll('#contextMenu input[type="checkbox"]').forEach(input=>input.checked=false);
    }
    map.stop();closeMapOverlays();hideProjectLayer();closeProjectDetails();
    setProjectPanelVisible(name==='projects');
    setEventPanelVisible(name==='acled'&&themeState.acled==='points');
    pEl('projectOverlay').checked=name==='projects'&&(options.keepContext?pEl('projectOverlay').checked:true);
    viewReady=true;applyPresetNow(name);
    if(name==='acled'&&themeState.acled==='points')renderEventResults();
    if(name==='projects')renderProjectMap();
    corridors.ready(name);box.style.display='none';
  }catch(e){if(ticket===presetSerial){viewReady=false;box.textContent='This view could not be loaded. Click the view again to retry.';box.style.display='block';console.error('View failed:',name,e);}}
  finally{clearTimeout(loadingTimer);if(ticket===presetSerial)document.getElementById('contextMenu').inert=false;}
}'''

def patch_page(page, is_map):
    page=page.replace('sedac/sedac-v1.css?v=2026-10-15.sedac.45','sedac/sedac-v2.css?v='+REV)
    if not is_map:
        return page.replace('sedac/analysis-v1.js?v=2026-10-15.sedac.45','sedac/analysis-v2.js?v='+REV)
    page=once(page,'sedac/sedac-v2.js?v=2026-10-15.sedac.46','sedac/sedac-v3.js?v='+REV)
    page=once(page,'corridors/corridor-integration-v10.js?v=2026-10-14.10','corridors/corridor-integration-v11.js?v='+REV)
    a=page.index('function clearRuralAccessViewLayout(){');b=page.index("map.on('click',",a)
    page=page[:a]+page[b:]
    page=page.replace('  clearRuralAccessViewLayout();\n','').replace('  applyRuralAccessViewLayout();\n','')
    a=page.index('async function setPreset(name,options={}){');b=page.index('\nasync function syncRoadDetail()',a)
    page=page[:a]+SET_PRESET+'\n'+page[b:]
    page=page.replace('currentView:()=>currentPreset','currentView:()=>viewReady?currentPreset:null')
    return page

def modules(site):
    js=(BASE/'site/sedac/sedac-v2.js').read_text()
    a=js.index(' function restoreMenu()');b=js.index(' function add(',a)
    js=js[:a]+" function prepare(){clear();document.body.classList.remove('deprivation-view');state.pixel=null;}\n"+js[b:]
    js=once(js,".then(d=>{if(d.format", ".then(async d=>{if(d.format")
    js=once(js,"throw Error('Invalid SEDAC data');data=d;", "throw Error('Invalid SEDAC data');await recolourGRDI(d.grdi);data=d;")
    helper=''' const grdiPalette=['#f2f0f7','#cbc9e2','#9e9ac8','#756bb1','#54278f'];
 async function recolourGRDI(r){
  // Recolour the already-projected display image; native values and geometry stay untouched.
  const img=new Image();img.src=r.image;await img.decode();
  const canvas=document.createElement('canvas');canvas.width=img.naturalWidth;canvas.height=img.naturalHeight;
  const ctx=canvas.getContext('2d');ctx.drawImage(img,0,0);const pixels=ctx.getImageData(0,0,canvas.width,canvas.height),rgba=pixels.data;
  const colours=new Map(r.bands.map((b,i)=>[parseInt(b.colour.slice(1),16),grdiPalette[i].slice(1).match(/../g).map(x=>parseInt(x,16))]));
  for(let i=0;i<rgba.length;i+=4){if(!rgba[i+3])continue;const colour=colours.get((rgba[i]<<16)|(rgba[i+1]<<8)|rgba[i+2]);if(!colour)throw Error('Unexpected GRDI display colour');rgba.set(colour,i);}
  ctx.putImageData(pixels,0,0);r.image=canvas.toDataURL('image/png');r.bands.forEach((b,i)=>b.colour=grdiPalette[i]);
 }
'''
    js=once(js,' function select(box,',helper+' function select(box,')
    a=js.index("  document.body.classList.add('sedac-active');");b=js.index('\n  if(urbanActive(name))',a)
    js=js[:a]+"  document.body.classList.toggle('deprivation-view',metric(name)==='grdi');"+js[b:]
    js=once(js,"   if(kind==='grdi')note(box,'Data cover approximately '+num(r.summary.coverage_share*100,1)+'% of the cluster area. Grey areas have no source value.');", """   if(kind==='grdi'){
    const coverage=document.createElement('div');coverage.className='grdi-coverage';
    coverage.innerHTML='<strong>'+num(r.summary.coverage_share*100,1)+'% of cluster area mapped</strong><div class="grdi-coverage-track" aria-hidden="true"><span style="width:'+r.summary.coverage_share*100+'%"></span></div><small>Grey = no source value. Missing data are not zero.</small>';box.appendChild(coverage);
   }""")
    js=once(js,"  const r=raster(),kind=metric(name);return", """  const r=raster(),kind=metric(name);
  if(kind==='grdi')return '<div class="sedac-key grdi-key"><strong>Relative deprivation index · 0–100</strong><p class="grdi-direction">Lighter = lower · darker = higher</p><div class="grdi-bands">'+r.bands.map((b,i)=>'<div><i style="background:'+b.colour+'"></i><span>'+b.label+'</span><small>'+(i===0?'Lower index':i===r.bands.length-1?'Higher index':'')+'</small></div>').join('')+'</div><p><i style="background:#e5e7eb"></i>No source value</p><p>Display bands, not official poverty categories. The index is not a poverty percentage.</p><p>Inputs: 2010–2020 · approximately 1 km grid.<br>Same scale across all four maps.</p></div>';
  return""")
    css=(BASE/'site/sedac/sedac-v1.css').read_text()
    css+='''\n/* Keep the Map views menu and sidebar rows in place in every thematic view. */
.panel{grid-template-rows:44px minmax(0,286px) minmax(0,1.2fr) minmax(0,1fr) 58px!important}
.panel>.preset-grid{overflow:auto;scrollbar-gutter:stable;grid-auto-rows:minmax(37px,auto)}
.panel>.view-options,.panel>.map-key{min-height:0;overflow:auto;overscroll-behavior:contain}
@media(max-height:700px){.panel{grid-template-rows:38px minmax(90px,36fr) minmax(65px,32fr) minmax(55px,25fr) 42px!important}}
@media(max-width:1024px){.panel{grid-template-rows:40px minmax(90px,37fr) minmax(70px,32fr) minmax(55px,24fr) 38px!important}.panel>.preset-grid{grid-auto-rows:44px;overflow:auto}}
.deprivation-view #map{background:#f3f2f5}.deprivation-view .leaflet-tile-pane{filter:grayscale(1);opacity:.3}
.grdi-coverage{padding:10px 12px;border:1px solid #ddd8e8;border-radius:6px;background:#faf9fc;margin:10px 0;color:#4c3e65}.grdi-coverage strong{font-size:12px}.grdi-coverage small{display:block;font-size:11px;color:#637078;line-height:1.5}.grdi-coverage-track{height:6px;border-radius:3px;background:#e5e7eb;overflow:hidden;margin:8px 0}.grdi-coverage-track span{display:block;height:100%;background:#756bb1}
.grdi-key .grdi-direction{margin:5px 0 10px}.grdi-bands{display:grid;gap:4px}.grdi-bands>div{display:flex;align-items:center;gap:8px;font-size:12px;min-height:20px}.grdi-bands i{width:32px;height:16px;margin:0;flex:none}.grdi-bands small{margin-left:auto;color:#637078;font-size:10px}.deprivation-view .sedac-value{color:#54278f}
'''
    corridor=(ROOT.parent/'map_updates/site/corridors/corridor-integration-v10.js').read_text()
    a=corridor.index('  function syncMapViews(');b=corridor.index('\n  function draw(',a)
    corridor=corridor[:a]+corridor[b:]
    corridor=once(corridor,'clear();syncMapViews(name);','clear();')
    # The shared sidebar CSS fixes row sizes; retain connectivity map styling only.
    corridor=re.sub(r'\.connectivity-view \.panel\{grid-template-rows:[^}]*\}','',corridor)
    corridor=once(corridor,"if(window.innerWidth>1024)locateTrade();",'')
    analysis=(BASE/'site/sedac/analysis-v1.js').read_text()
    analysis=once(analysis,'histogram(r.histogram)',"histogram(r.histogram.map((row,i)=>({...row,colour:"+str(PALETTE)+"[i]})))")
    files={'sedac/sedac-v3.js':js,'sedac/sedac-v2.css':css,'sedac/analysis-v2.js':analysis,'corridors/corridor-integration-v11.js':corridor}
    for path,text in files.items():
        (site/path).parent.mkdir(parents=True,exist_ok=True);(site/path).write_text(text)
    return list(files)
