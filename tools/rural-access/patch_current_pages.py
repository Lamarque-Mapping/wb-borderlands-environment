"""Patch current decrypted pages deterministically; never writes GitHub or assets.

Input pages are the pinned current snapshots in rai_current/map_cache. Output
pages are separate files in rai_live/working. RAI geometry is supplied as its
own WBVault asset and is never joined to the OCHA district renderer.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import subprocess

CODES = ('moyale_borana', 'mandera_triangle', 'karamoja', 'dikhil')
MARKER = '// Rural road access: SEDAC source units, independent of OCHA geometry.'

CSS = r'''
/* Rural road access keeps source-unit selection in the existing sidebar. */
.rural-access-view .panel{grid-template-rows:minmax(40px,auto) auto minmax(0,1fr) minmax(0,.48fr) 58px}
.rural-map-view-switch>summary{padding:9px 0;font:600 12px/1.4 var(--ui-font);cursor:pointer;color:#244e46;border-bottom:1px solid #d8dfe1}
.rural-map-view-switch .preset-grid{max-height:min(220px,28vh);overflow:auto;padding:8px 0;gap:6px}
.rural-access-controls{font-size:12px;line-height:1.5;margin-top:10px;color:#233a45}
.rural-access-controls>p{margin:6px 0 10px;color:#53656c}
.rural-access-controls label{display:block;font-size:12px;font-weight:600;margin:8px 0}
.rural-access-controls select{display:block;width:100%;min-width:0;box-sizing:border-box;border:1px solid #cbd7d0;border-radius:6px;background:white;color:#233a45;min-height:40px;padding:8px;margin-top:5px;font:400 13px/1.4 var(--ui-font)}
.rural-access-controls button{font:400 12px/1.4 var(--ui-font);min-height:36px;padding:7px 10px;border:1px solid #bccfc5;border-radius:6px;background:#fff;color:#244e46;cursor:pointer}
.rural-access-selection{margin:10px 0;padding:11px 12px;border:1px solid #d6e1dd;border-left:3px solid #244e46;border-radius:6px;background:#f5f9f4;overflow-wrap:anywhere}
.rural-access-selection[hidden]{display:none!important}
.rural-access-selection header{display:flex;align-items:flex-start;justify-content:space-between;gap:8px}
.rural-access-selection header p{font-size:10.5px;line-height:1.4;color:#53656c;margin:0}
.rural-access-selection header button{min-width:32px;min-height:32px;border:0;background:transparent;font-size:22px;line-height:1;padding:0}
.rural-access-selection h3{font-size:17px;line-height:1.3;margin:5px 0 3px;font-weight:650;color:#233a45}
.rural-access-selection .rural-access-area{font-size:11px;margin:0 0 10px;color:#53656c}
.rural-access-value{font-size:29px;font-weight:650;line-height:1.15;color:#244e46;margin:5px 0}
.rural-access-value.rural-access-missing{font-size:21px;color:#53656c}
.rural-access-stat-label{font-size:12px;line-height:1.45;margin:3px 0 10px}
.rural-access-selection table{width:100%;border-collapse:collapse;font-size:11px;line-height:1.5;margin:10px 0}
.rural-access-selection th{font-weight:400;text-align:left;padding:4px 5px 4px 0;vertical-align:top;color:#53656c}
.rural-access-selection td{text-align:right;padding:4px 0;vertical-align:top;color:#233a45;font-variant-numeric:tabular-nums}
.rural-access-selection details{font-size:11px;margin-top:10px}.rural-access-selection summary{cursor:pointer;min-height:28px;line-height:28px}
.rural-access-method{margin-top:10px;font-size:11px;line-height:1.55;color:#53656c}.rural-access-method summary{cursor:pointer;min-height:30px;line-height:30px}.rural-access-method p{margin:6px 0}
.rural-access-controls :is(select,button,summary):focus-visible{outline:2px solid #176f88;outline-offset:2px}
.rural-access-path:focus-visible{outline:none;stroke:#142e43;stroke-width:3px}
.rural-access-key .rural-access-swatch{width:16px;height:12px;border:1px solid #92a393;flex:0 0 auto;border-radius:2px}
.rural-access-key .legend-classes{grid-template-columns:1fr 1fr}.rural-access-key .metric-title{margin-top:0}.rural-access-key p{font-size:11px;line-height:1.5;color:#53656c;margin:7px 0}
@media(max-width:1024px){.rural-access-view .panel{grid-template-rows:40px auto minmax(0,1fr) minmax(0,.43fr) 38px}.rural-map-view-switch>summary{padding:13px 0}.rural-map-view-switch .preset-grid{max-height:min(190px,25vh)}.rural-access-controls select{font-size:16px;min-height:44px}.rural-access-controls button{min-height:44px}.rural-access-selection header button{min-width:44px;min-height:44px}.rural-access-value{font-size:30px}.rural-access-method summary,.rural-access-selection summary{min-height:44px;line-height:44px}}
@media(max-height:600px){.rural-access-view .panel{grid-template-rows:minmax(32px,auto) auto minmax(0,1fr) minmax(0,.4fr) 34px;gap:6px}.rural-map-view-switch .preset-grid{max-height:min(140px,22vh)}}
'''

JS = r'''
// Rural road access: SEDAC source units, independent of OCHA geometry.
const ruralAccessState={selectedId:null,sourceMetadata:null};
const ruralAccessBands=[
  {upper:20,label:'0–<20%',colour:'#ffffcc'},
  {upper:40,label:'20–<40%',colour:'#c2e699'},
  {upper:60,label:'40–<60%',colour:'#78c679'},
  {upper:80,label:'60–<80%',colour:'#31a354'},
  {upper:101,label:'80–100%',colour:'#006837'}
];
function ruralAccessActive(){return currentPreset==='access'&&themeState.access==='ruralAccess';}
function ruralAccessValue(properties){const value=properties?.rai_pct;return typeof value==='number'&&Number.isFinite(value)&&value>=0&&value<=100?value:null;}
function ruralAccessNumber(value,digits=0){return typeof value==='number'&&Number.isFinite(value)?value.toLocaleString(undefined,{maximumFractionDigits:digits}):'Not available';}
function ruralAccessName(properties){return String(properties?.NAME_2||'Unnamed source unit');}
function ruralAccessId(properties){return String(properties?.source_record_id||('sedac2023:'+properties?.__wb_source_fid));}
function ruralAccessFeatures(){return DATA.ruralAccessUnits?.features||[];}
function ruralAccessStyle(feature){
  const p=feature.properties||{},value=ruralAccessValue(p),selected=ruralAccessId(p)===ruralAccessState.selectedId;
  return {color:selected?'#142e43':'#647966',weight:selected?2.7:.75,opacity:selected?1:.85,fillColor:value==null?'#cbd5e1':ruralAccessBands.find(b=>value<b.upper).colour,fillOpacity:.84};
}
function ruralAccessLayer(){
  return L.geoJSON(DATA.ruralAccessUnits||emptyFc(),{pane:'ruralAccessPane',renderer:svgRenderer('ruralAccessPane'),bubblingMouseEvents:false,style:ruralAccessStyle,onEachFeature:(feature,layer)=>{
    const p=feature.properties||{},value=ruralAccessValue(p),id=ruralAccessId(p);
    const label='SEDAC source unit '+ruralAccessName(p)+', '+(p.NAME_0||'country unspecified')+', '+(value==null?'rural access not available':ruralAccessNumber(value,1)+'% rural road access');
    layer.on('click',event=>{if(event.originalEvent)L.DomEvent.stopPropagation(event.originalEvent);selectRuralAccessUnit(id,document.activeElement===layer.getElement());});
    layer.on('add',()=>{
      const path=layer.getElement();if(!path)return;
      path.classList.add('rural-access-path');path.setAttribute('role','button');path.setAttribute('tabindex','0');path.setAttribute('aria-label',label);path.setAttribute('aria-pressed',String(id===ruralAccessState.selectedId));
      path.onkeydown=event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();event.stopPropagation();selectRuralAccessUnit(id,true);}else if(event.key==='Escape'){event.preventDefault();clearRuralAccessSelection();}};
    });
  }});
}
function syncRuralAccessHighlight(){
  active.ruralAccess?.eachLayer(layer=>{layer.setStyle(ruralAccessStyle(layer.feature));layer.getElement()?.setAttribute('aria-pressed',String(ruralAccessId(layer.feature.properties)===ruralAccessState.selectedId));});
}
function clearRuralAccessSelection(){
  ruralAccessState.selectedId=null;syncRuralAccessHighlight();
  const selector=document.getElementById('ruralAccessUnit');if(selector)selector.value='';
  const selection=document.getElementById('ruralAccessSelection');if(selection){selection.replaceChildren();selection.hidden=true;}
}
function selectedRuralAccessFeature(){return ruralAccessFeatures().find(feature=>ruralAccessId(feature.properties)===ruralAccessState.selectedId);}
function selectRuralAccessUnit(id,focusDetails=false){
  if(!ruralAccessActive())return;
  const feature=ruralAccessFeatures().find(candidate=>ruralAccessId(candidate.properties)===String(id));
  if(!feature){clearRuralAccessSelection();return;}
  ruralAccessState.selectedId=String(id);syncRuralAccessHighlight();renderRuralAccessSelection();
  const selector=document.getElementById('ruralAccessUnit');if(selector)selector.value=String(id);
  if(window.innerWidth<=1024){document.querySelector('.panel').classList.add('mobile-open');document.getElementById('projectPanel').classList.remove('mobile-open');document.getElementById('eventPanel').classList.remove('mobile-open');updateMobileNavigation();}
  const detail=document.getElementById('ruralAccessSelection'),view=document.querySelector('.view-options');
  if(detail&&view){const delta=detail.getBoundingClientRect().top-view.getBoundingClientRect().top;if(delta<0||delta>view.clientHeight-65)view.scrollTop+=delta-8;}
  if(focusDetails&&window.innerWidth<=1024)document.getElementById('ruralAccessClear')?.focus({preventScroll:true});
}
function locateRuralAccessUnit(){
  let selected=null;active.ruralAccess?.eachLayer(layer=>{if(ruralAccessId(layer.feature.properties)===ruralAccessState.selectedId)selected=layer;});
  if(!selected||!selected.getBounds().isValid())return;
  const mobile=window.innerWidth<=1024;if(mobile)document.getElementById('mobileMap').click();
  map.fitBounds(selected.getBounds(),{paddingTopLeft:[30,30],paddingBottomRight:mobile?[30,90]:[380,40],maxZoom:11,animate:false});
  if(mobile)document.getElementById('mobileMap').focus({preventScroll:true});
}
function renderRuralAccessSelection(){
  const box=document.getElementById('ruralAccessSelection'),feature=selectedRuralAccessFeature();if(!box)return;
  if(!feature){box.hidden=true;box.replaceChildren();return;}
  const p=feature.properties||{},value=ruralAccessValue(p),area=[p.NAME_1,p.NAME_0].filter(Boolean).join(' · ');
  const noData=value==null?'<p class="theme-note">The source has no valid rural-population denominator for this unit; its access percentage is undefined.</p>':'';
  const side=p.country_side&&p.country_side!==p.NAME_0?row('Supplied country side',p.country_side):'';
  box.innerHTML='<header><p>SEDAC source unit · GADM v3.6</p><button id="ruralAccessClear" type="button" aria-label="Clear selected source unit" title="Clear selection">×</button></header><h3>'+esc(ruralAccessName(p))+'</h3><p class="rural-access-area">'+esc(area)+'</p><div class="rural-access-value'+(value==null?' rural-access-missing':'')+'">'+(value==null?'Not available':ruralAccessNumber(value,1)+'%')+'</div><p class="rural-access-stat-label">of rural population within 2 km of an all-season road</p>'+noData+'<table>'+row('Rural population · 2020',ruralAccessNumber(p.Pop_A2_R))+row('Rural population within 2 km',ruralAccessNumber(p.Pop_A2_R2K))+row('Beyond 2 km',value==null?'Not available':ruralAccessNumber(p.beyond_pct,1)+'%')+'</table><p class="theme-note">Value applies to the whole SEDAC source unit, including any area outside this cluster.</p><button id="ruralAccessLocate" type="button">Zoom to source unit</button><details><summary>Source record details</summary><table>'+row('Source record ID',ruralAccessId(p))+row('Source country',p.NAME_0)+row('Source region',p.NAME_1)+side+row('Supplied selection tag',p.supplied_coverage_label)+row('Release',p.source_release||'2023')+'</table></details>';
  box.hidden=false;
  document.getElementById('ruralAccessClear').onclick=()=>{clearRuralAccessSelection();document.getElementById('ruralAccessUnit')?.focus({preventScroll:true});};
  document.getElementById('ruralAccessLocate').onclick=locateRuralAccessUnit;
}
function renderRuralAccessControls(box){
  const controls=document.createElement('div');controls.className='rural-access-controls';
  controls.innerHTML='<p>Share of rural population within 2 km of an all-season road. Select a shaded source unit or choose one below.</p><label for="ruralAccessUnit">Source unit<select id="ruralAccessUnit"><option value="">Select a source unit…</option></select></label><section id="ruralAccessSelection" class="rural-access-selection" role="region" aria-label="Selected rural access source unit" aria-live="polite" aria-atomic="true" hidden></section><details class="rural-access-method"><summary>Method and data</summary><p>CIESIN / NASA SEDAC · SDG 9.1.1 Rural Access Index, 2023 release. The percentage uses rural population as its denominator.</p><p>WorldPop 2020 population; GHSL 2015 urban/rural classification; OpenStreetMap roads dated 31 March 2022; GADM v3.6 source boundaries. All-season status is inferred from OSM road tags; 2 km measures geographic proximity. Current road passability and travel times are not measured.</p><p>Shading follows the original source units. These can differ from the OCHA administrative reference boundaries. Names supplied as unknown remain unchanged. Missing values are grey.</p><p><a href="https://doi.org/10.7927/fcre-m572" target="_blank" rel="noopener noreferrer">Source dataset and documentation</a></p></details>';
  box.appendChild(controls);
  const selector=document.getElementById('ruralAccessUnit');
  const sorted=[...ruralAccessFeatures()].sort((a,b)=>[a.properties.NAME_0,a.properties.NAME_1,ruralAccessName(a.properties)].join('|').localeCompare([b.properties.NAME_0,b.properties.NAME_1,ruralAccessName(b.properties)].join('|'),undefined,{numeric:true}));
  for(const feature of sorted){const p=feature.properties||{},option=document.createElement('option');option.value=ruralAccessId(p);option.textContent=ruralAccessName(p)+' · '+[p.NAME_1,p.country_side||p.NAME_0].filter(Boolean).join(' · ');selector.appendChild(option);}
  selector.value=ruralAccessState.selectedId||'';selector.onchange=()=>selectRuralAccessUnit(selector.value);renderRuralAccessSelection();
}
function ruralAccessLegend(){
  return '<section class="rural-access-key"><div class="metric-title">Rural population within 2 km of an all-season road</div><div class="legend-classes">'+ruralAccessBands.map(b=>legendItem('<span class="rural-access-swatch" style="background:'+b.colour+'"></span>',b.label)).join('')+legendItem('<span class="rural-access-swatch" style="background:#cbd5e1"></span>','No data')+'</div><p>Same percentage scale in all four clusters.</p><p>SEDAC source admin 2 units · GADM v3.6. Figures refer to the full source polygons.</p></section>';
}
function clearRuralAccessViewLayout(){
  const wrapper=document.querySelector('.rural-map-view-switch');if(wrapper){wrapper.before(wrapper.querySelector('.preset-grid'));wrapper.remove();}
  document.body.classList.remove('rural-access-view');
}
function applyRuralAccessViewLayout(){
  if(!ruralAccessActive())return;
  document.body.classList.add('rural-access-view');
  const presets=document.querySelector('.panel>.preset-grid');if(!presets)return;
  const wrapper=document.createElement('details');wrapper.className='rural-map-view-switch';wrapper.innerHTML='<summary>Map views · Travel time / access</summary>';presets.before(wrapper);wrapper.appendChild(presets);
}
map.on('click',()=>{if(ruralAccessActive()&&ruralAccessState.selectedId)clearRuralAccessSelection();});
'''

LOAD = r'''
    if(group==='ruralAccess'){
      const document=await parent.WBVault.json(DATA.code+'/ruralAccess');
      if(document.format!=='wb-rural-access-v1'||document.code!==DATA.code||document.ruralAccessUnits?.type!=='FeatureCollection'||!Array.isArray(document.ruralAccessUnits.features))throw new Error('Invalid rural-access source data');
      const ids=new Set();for(const feature of document.ruralAccessUnits.features){const p=feature.properties||{},id=ruralAccessId(p);if(ids.has(id)||p.__wb_source_fid==null)throw new Error('Invalid rural-access source record identity');ids.add(id);if(p.rai_pct!=null&&ruralAccessValue(p)==null)throw new Error('Invalid rural-access percentage');}
      DATA.ruralAccessUnits=document.ruralAccessUnits;ruralAccessState.sourceMetadata=document.source_metadata||{};return;
    }
'''

SOURCE_ROW = '''          <tr><td>Rural road access · source admin 2 units</td><td>Center for International Earth Science Information Network (CIESIN), Columbia University / NASA SEDAC, SDG Indicator 9.1.1 Rural Access Index (RAI), 2023 release. <a href="https://doi.org/10.7927/fcre-m572" target="_blank" rel="noopener noreferrer">Dataset DOI and documentation</a>.</td><td>Retain CIESIN / NASA SEDAC attribution; see the source dataset use terms.</td><td>Share of rural population living within 2 km of roads classified as likely all-season using OSM tags, weighted by rural population. Inputs: WorldPop 2020 population, GHSL 2015 urban/rural classification, OpenStreetMap roads as at 31 March 2022, and GADM v3.6 source administrative units. The map displays the full original source polygons and source record IDs; they can differ from the OCHA administrative references. Values are not assigned to current districts by matching names or polygon overlap. Supplied unknown names remain unchanged; undefined rural-population denominators are no data, not zero. A release date does not establish current road conditions or journey times.</td></tr>
'''

def one(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise ValueError(f'{label}: expected one source fragment, found {count}')
    return text.replace(old, new, 1)

def patch(text: str) -> str:
    if MARKER in text:
        raise ValueError('Input is already patched; use the unchanged current-page snapshot')
    text = one(text, '</style></head>', CSS + '\n</style></head>', 'RAI styles')
    text = one(text, '["hexPane",600],["adminPane",650]', '["hexPane",600],["ruralAccessPane",610],["adminPane",650]', 'source pane')
    text = one(text, 'const defs={\n', JS + '\nconst defs={\n  ruralAccess:()=>ruralAccessLayer(),\n', 'source renderer')
    text = one(text, 'function applyPresetNow(name){\n', 'function applyPresetNow(name){\n  clearRuralAccessViewLayout();\n', 'view layout cleanup')
    text = one(text, '  if(name==="access")add(analysisActive()?"analysisHex":"accessHex");', '  if(name==="access")add(ruralAccessActive()?"ruralAccess":analysisActive()?"analysisHex":"accessHex");', 'source draw choice')
    text = one(text, 'document.getElementById("accessControls").style.display=name==="access"&&!analysisActive()?"block":"none";', 'document.getElementById("accessControls").style.display=name==="access"&&themeState.access===\'travel\'?"block":"none";', 'hide travel controls')
    text = one(text, '  corridors.draw(name);\n  refreshLegend(name);', '  corridors.draw(name);\n  applyRuralAccessViewLayout();\n  refreshLegend(name);', 'rural view layout')
    text = one(text, '  if(name==="access"&&!analysisActive())rows.push(gradientLegend((DATA.accessHexMetrics||{})[currentAccessMode]));', '  if(name==="access"&&themeState.access===\'travel\')rows.push(gradientLegend((DATA.accessHexMetrics||{})[currentAccessMode]));\n  if(ruralAccessActive())rows.push(ruralAccessLegend());', 'source legend')
    text = one(text, '  if(name==="access"&&!analysisActive())source+=\' Malaria Atlas Project accessibility to healthcare (2019) and accessibility to cities (2015), aggregated to 10 km hexes. Values are modelled minutes.\';', '  if(name==="access"&&themeState.access===\'travel\')source+=\' Malaria Atlas Project accessibility to healthcare (2019) and accessibility to cities (2015), aggregated to 10 km hexes. Values are modelled minutes.\';\n  if(ruralAccessActive())source+=\' Rural access shading: CIESIN / NASA SEDAC, SDG 9.1.1, 2023 release; WorldPop 2020, GHSL 2015, OSM 31 March 2022 and GADM v3.6.\';', 'source legend attribution')
    text = one(text, 'if(currentPreset==="access"){remove("accessHex");add("accessHex");refreshLegend("access")}', 'if(currentPreset==="access"&&themeState.access===\'travel\'){remove("accessHex");add("accessHex");refreshLegend("access")}', 'travel callback guard')
    text = one(text, " access:[['travel','Mean travel times'],['coverage','Population access to healthcare']],", " access:[['travel','Mean travel times'],['coverage','Population access to healthcare'],['ruralAccess','Rural road access']],", 'access choice')
    text = one(text, 'function thematicGroups(name){\n', "function thematicGroups(name){\n if(name==='access'&&themeState.access==='ruralAccess')return ['ruralAccess'];\n", 'source-only lazy groups')
    text = one(text, ' box.appendChild(buttons);\n if(group===\'acled\'&&themeState.acled!==\'points\'){', ' box.appendChild(buttons);\n if(group===\'access\'&&themeState.access===\'ruralAccess\')renderRuralAccessControls(box);\n if(group===\'acled\'&&themeState.acled!==\'points\'){', 'source controls')
    text = one(text, "    const asset=(DATA.lazyGroups||{})[group];if(!asset)return;", LOAD + "    const asset=(DATA.lazyGroups||{})[group];if(!asset)return;", 'source asset loader')
    text = one(text, "  name=resolvePreset(name);prepareTheme(name);", "  name=resolvePreset(name);prepareTheme(name);\n  clearRuralAccessSelection();clearRuralAccessViewLayout();", 'selection lifecycle cleanup')
    text = one(text, 'if(!Object.keys(DATA.accessHexMetrics||{}).length){const b=document.querySelector(\'[data-preset="access"]\');if(b)b.disabled=true}', '// Rural-access assets are available even if travel-time hex metrics are absent.\nif(!Object.keys(DATA.accessHexMetrics||{}).length&&!'+"['moyale_borana','mandera_triangle','karamoja','dikhil']"+'.includes(DATA.code)){const b=document.querySelector(\'[data-preset="access"]\');if(b)b.disabled=true}', 'access availability')
    text = one(text, "await setPreset(['connectivity','fews','projects'].includes(startView)?startView:'clean');", "if(startView==='ruralAccess')themeState.access='ruralAccess';\nawait setPreset(startView==='ruralAccess'?'access':['connectivity','fews','projects'].includes(startView)?startView:'clean');", 'explicit RAI deep link')
    text = one(text, '          <tr><td>Travel time to healthcare</td>', SOURCE_ROW + '          <tr><td>Travel time to healthcare</td>', 'source documentation row')
    text = one(text, 'City/town nodes and city/town/village nodes are separate; thresholds are 2, 5 and 10 km with a 15 km halo.', 'The 10 km grid is a chosen starting scale for exploratory comparison, not an operational catchment standard. City/town nodes and city/town/village nodes are separate; local-path thresholds are 2, 5 and 10 km with a 15 km halo.', 'connectivity grid wording')
    text = one(text, 'BGS Africa Groundwater Atlas; WPdx. Data are processed and visualised for analytical use.', 'BGS Africa Groundwater Atlas; WPdx; CIESIN / NASA SEDAC. Data are processed and visualised for analytical use.', 'source credit list')
    return text

def syntax_check(path: pathlib.Path) -> list[dict]:
    text = path.read_text(encoding='utf-8')
    scripts = re.findall(r'<script\b[^>]*>([\s\S]*?)</script>', text, re.I)
    output=[]
    for index, script in enumerate(scripts):
        if not script.strip():
            continue
        file=path.with_name(path.stem+f'_script_{index}.js')
        file.write_text(script,encoding='utf-8')
        subprocess.run(['node','--check',str(file)],check=True,capture_output=True,text=True)
        output.append({'inline_script_index':index,'bytes':len(script.encode()),'node_syntax':'pass'})
    return output

def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=pathlib.Path,default=pathlib.Path(__file__).parent.parent/'rai_current'/'map_cache')
    parser.add_argument('--output',type=pathlib.Path,default=pathlib.Path(__file__).parent/'working')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    report={'base_head':'7b8ba4c422fbbd310a62e81cde9c8cfa26b781a9','patch_version':'2026-10-14.rural-access.1','data_contract':'wb-rural-access-v1','pages':{},'limitations':['Syntax and static lifecycle checks do not replace live browser verification. Geometry and attributes belong to independent source assets; this patch never modifies or joins them.']}
    for code in CODES:
        filename=f'page_map_{code}.html';source=args.source/filename;out=args.output/filename
        raw=source.read_bytes();result=patch(raw.decode('utf-8'));out.write_text(result,encoding='utf-8')
        checks=syntax_check(out)
        assert "access:'travel'" in result
        assert result.count(MARKER)==1
        assert "bubblingMouseEvents:false,style:ruralAccessStyle" in result
        assert "if(name==='access'&&themeState.access==='ruralAccess')return ['ruralAccess'];" in result
        assert 'ruralAccess:()=>ruralAccessLayer()' in result
        report['pages'][code]={'source_sha256':hashlib.sha256(raw).hexdigest(),'output_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'source_bytes':len(raw),'output_bytes':out.stat().st_size,'inline_scripts':checks,'travel_default':'retained','geometry_policy':'standalone SEDAC source polygons; no current-admin join','source_selector':'all source units in current-cluster asset; independent of screen-visible geometry','selection_cleanup':'blank map click, clear X, or setPreset lifecycle','mobile':'existing Views close X + auto-open source details after map selection','common_palette':'five fixed YlGn bands; null grey'}
    (args.output.parent/'page_patch_validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    main()
