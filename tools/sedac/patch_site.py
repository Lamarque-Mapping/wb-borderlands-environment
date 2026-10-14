from pathlib import Path
import re
import subprocess
ROOT = Path(__file__).resolve().parent
WORK = ROOT/'working'
WORK.mkdir(exist_ok=True)
REV='2026-10-15.sedac.45'

def one(s,old,new):
    assert s.count(old)==1, (old[:100],s.count(old))
    return s.replace(old,new,1)

source_rows=(ROOT/'sources.html').read_text()
source_summary='''<section class="sedac-source-summary"><h3>NASA SEDAC · Urban settlements, deprivation and historical heat</h3><p><strong>GUPPD:</strong> circa-2015 settlement footprints with modelled 2020 populations. <strong>GRDI:</strong> relative deprivation on a 0–100 scale, with inputs from 2010–2020 and substantial source coverage gaps. <strong>GEHE:</strong> historical humid-heat days, 1983–2016.</p><p>Find urban footprints in <strong>Corridors &amp; infrastructure → Towns &amp; transport → Town source</strong>; deprivation in <strong>Population</strong>; and historical heat in <strong>Environment</strong>. Definitions, licences and limitations are listed in the table below.</p></section>'''

for code in ['mandera_triangle','moyale_borana','karamoja','dikhil']:
    page=(ROOT.parent/'rural_access_default/working'/('page_map_'+code+'.html')).read_text()
    page=one(page,'</head>','<link rel="stylesheet" href="sedac/sedac-v1.css?v='+REV+'"><script src="sedac/sedac-v1.js?v='+REV+'"></script></head>')
    page=one(page,"climate:'Drought & flood risk'","climate:'Drought & flood risk',heat:'Historical humid heat'")
    page=one(page,"['raster','Population surface']","['raster','Population surface'],['deprivation','Relative deprivation · SEDAC']")
    page=one(page," if(name==='population')return themeState.population==='raster'?['raster_population']:['hexes'];", " if(name==='population')return themeState.population==='deprivation'?['sedac']:themeState.population==='raster'?['raster_population']:['hexes'];")
    page=one(page,'box.appendChild(buttons);corridors.controls(name,box);return;', 'box.appendChild(buttons);corridors.controls(name,box);sedac.controls(name,box);return;')
    page=one(page," if(group==='access'&&themeState.access==='ruralAccess')renderRuralAccessControls(box);", " sedac.controls(name,box);\n if(group==='access'&&themeState.access==='ruralAccess')renderRuralAccessControls(box);")
    page=one(page,"crossings:['roads','crossings','towns']", "crossings:['roads','crossings','towns','sedac'],heat:['sedac']")
    page=one(page,"async function ensureGroup(group){\n  if(await corridors.load(group))return;", "async function ensureGroup(group){\n  if(await sedac.load(group))return;\n  if(await corridors.load(group))return;")
    page=one(page,"  requestedPreset=name;viewReady=false;corridors.prepare(name);", "  requestedPreset=name;viewReady=false;corridors.prepare(name);sedac.prepare();")
    page=one(page,'  if(name==="population")add(themeState.population==="raster"?"population":"themeHex");', '  if(name==="population"&&themeState.population!=="deprivation")add(themeState.population==="raster"?"population":"themeHex");')
    page=one(page,'  if(name==="crossings"){addRoadNetwork();addCrossings();add("towns")}', '  if(name==="crossings"){addRoadNetwork();addCrossings();if(!sedac.urbanActive(name))add("towns")}')
    page=one(page,'  if(currentContext.has("towns"))add("towns");', '  if(currentContext.has("towns")&&!sedac.urbanActive())add("towns");')
    page=one(page,'  applyRuralAccessViewLayout();\n  refreshLegend(name);','  applyRuralAccessViewLayout();\n  sedac.draw(name);\n  refreshLegend(name);')
    page=one(page,'  if(name==="towns"||name==="crossings"||name==="infrastructure"){', '  if(name==="towns"||(name==="crossings"&&!sedac.urbanActive(name))||name==="infrastructure"){')
    page=one(page,'if(currentContext.has("towns"))rows.push(', 'if(currentContext.has("towns")&&!sedac.urbanActive())rows.push(')
    page=one(page,"  const coverageNote=sourceCoverageNote(name);", "  const sedacKey=sedac.legend(name);if(sedacKey)rows.unshift(sedacKey);\n  const coverageNote=sourceCoverageNote(name);")
    page=one(page,"map.on('zoomend',syncRoadDetail);", "const sedac=window.createWBSEDAC({DATA,map,svgRenderer,setPreset,currentView:()=>currentPreset,populationMode:()=>themeState.population,showSidebar:()=>{if(window.innerWidth<=1024&&!document.querySelector('.panel').classList.contains('mobile-open'))document.getElementById('mobileLayers').click();}});\nmap.on('zoomend',syncRoadDetail);")
    page=one(page,"if(startView==='ruralAccess')themeState.access='ruralAccess';", "if(startView==='ruralAccess')themeState.access='ruralAccess';\nif(startView==='deprivation')themeState.population='deprivation';\nif(startView==='urban')sedac.state.townSource='sedac';\nif(startView==='heat'){const t=new URLSearchParams(parent.location.search).get('heatThreshold');if(['28','30','32'].includes(t))sedac.state.threshold=t;}")
    page=one(page,"await setPreset(startView==='ruralAccess'?'access':['connectivity','fews','projects'].includes(startView)?startView:'clean');", "await setPreset(startView==='ruralAccess'?'access':startView==='deprivation'?'population':startView==='urban'?'crossings':['connectivity','fews','projects','heat'].includes(startView)?startView:'clean');\nif(startView==='urban'){const id=new URLSearchParams(parent.location.search).get('settlement');if(id)sedac.selectTown(id,true);}")
    page=one(page,'        <tbody>', '        <tbody>\n'+source_rows)
    # Explain the new datasets near the top of the existing sources panel as well as in its table.
    page=one(page,'<section class="rai-source-summary"', source_summary+'<section class="rai-source-summary"')
    path=WORK/('page_map_'+code+'.html');path.write_text(page)
    scripts=re.findall(r'<script(?:\s[^>]*)?>(.*?)</script>',page,re.S)
    for i,script in enumerate(scripts):
        if script.strip():
            temp=WORK/(code+'_inline_'+str(i)+'.js');temp.write_text(script);subprocess.run(['node','--check',str(temp)],check=True)

analysis=(ROOT.parent/'map_updates/working/analysis.html').read_text()
analysis=one(analysis,'</head>','<link rel="stylesheet" href="sedac/sedac-v1.css?v='+REV+'"></head>')
analysis=one(analysis,'<a href="#data-sources">Sources &amp; limitations</a>', '<a href="#sedac-context">SEDAC context</a><a href="#data-sources">Sources &amp; limitations</a>')
analysis=one(analysis,'<section id="data-sources"', (ROOT/'analysis_section.html').read_text()+'\n<section id="data-sources"')
analysis=one(analysis,'08 / Sources','09 / Sources')
analysis=one(analysis,'        <tbody>', '        <tbody>\n'+source_rows)
analysis=one(analysis,'<section class="rai-source-summary"',source_summary+'<section class="rai-source-summary"')
analysis=one(analysis,'</div></main><script', '</div></main><script src="sedac/analysis-v1.js?v='+REV+'"></script><script')
(WORK/'analysis.html').write_text(analysis)
for i,s in enumerate(re.findall(r'<script(?:\s[^>]*)?>(.*?)</script>',analysis,re.S)):
    if s.strip():
        p=WORK/('analysis_inline_'+str(i)+'.js');p.write_text(s);subprocess.run(['node','--check',str(p)],check=True)
for p in (ROOT/'site/sedac').glob('*.js'):subprocess.run(['node','--check',str(p)],check=True)
print('Patched four maps and analysis; all JavaScript parses.')
