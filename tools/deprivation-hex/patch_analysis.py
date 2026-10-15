from pathlib import Path
import re
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent/'source_balance';REV='2026-10-15.grdi-hex.50'
page=(ROOT/'working/analysis.html').read_text()
a=page.index('<div class="rai-geography-label">');b=page.index('<section id="violence"',a)
scope=page[a:b].replace('Geography for the remaining charts','Comparison geography')
scope=scope.replace('<p id="scopeNote"', '<p class="scope-note">These controls apply to violence, population, land cover, settlement change, healthcare and projects. Rural access, urban settlements, deprivation and heat have their own selectors.</p>\n<p id="scopeNote"')
page=page[:a]+page[b:]
page=page.replace('<div id="analysisApp" inert>','<div id="analysisApp" inert>\n'+scope,1)
methods={
 'towns':'GUPPD v1 (2024) supplies circa-2015 source settlement footprints and names, with modelled GHSL R2023 population for 2020. Settlements are selected by source representative points inside a cluster; populations refer to the whole original footprint, which can extend beyond it. These are not municipal boundaries or current town census totals.',
 'grdi':'GRDI v1 (2022) uses inputs from 2010–2020. These means and distributions include valid source pixels only, weighted by approximate cell area; the coverage figure is the share of cluster area represented by those pixels. They are not population-weighted estimates. Missing building-footprint coverage is not evidence of no population or no deprivation. The map also offers 10 km hex summaries with per-hex coverage.',
 'heat':'GEHE supplies annual counts for 1983–2016. The historical mean requires all 34 years at each pixel. Area averages use fixed source-pixel locations and spherical grid-cell areas; edge inclusion follows pixel centres. They are approximate geographic summaries, not population-weighted exposure estimates. WBGT incorporates humidity and is not ordinary air temperature.'
}
settings=[('towns','urban-settlements','urbanAnalysis','Urban settlements and population','GUPPD · 2020 population','urban'),('grdi','deprivation','deprivationAnalysis','Relative deprivation','GRDI · inputs 2010–2020','deprivation'),('heat','historical-heat','heatAnalysis','Historical humid heat','GEHE · 1983–2016','heat')]
sections=[]
for mode,id,prefix,title,badge,view in settings:
 heat=('<label>WBGT threshold<select id="'+prefix+'Threshold"><option value="28">Above 28°C WBGT</option><option value="30">Above 30°C WBGT</option><option value="32">Above 32°C WBGT</option></select></label>') if mode=='heat' else ''
 sections.append(f'''<section id="{id}" class="analysis-card" aria-labelledby="{prefix}Heading">
 <div class="analysis-head"><div><p class="section-kicker">00 / {title}</p><h2 id="{prefix}Heading">{title}</h2></div><span class="source-badge">{badge}</span></div>
 <p id="{prefix}Loading" role="status">Loading {title.lower()}…</p>
 <div id="{prefix}Content" hidden>
  <div class="control-bar sedac-analysis-toolbar"><label>Cluster<select id="{prefix}Cluster"></select></label>{heat}<button type="button" id="{prefix}Download" class="sedac-download">Download displayed data · CSV</button><a id="{prefix}Map" target="_top" href="?view={view}#map=karamoja">Open this map ↗</a></div>
  <div id="{prefix}Body"></div>
 </div>
 <details class="method-note"><summary>Source, geography and calculation</summary><p>{methods[mode]}</p><p>Source dates, licences and limitations are listed in the table below.</p></details>
</section>''')
page,n=re.subn(r'<section id="sedac-context".*?</section>','\n'.join(sections),page,flags=re.S);assert n==1
order=[('rural-access','Rural access'),('violence','Violence'),('population','Population'),('deprivation','Deprivation'),('landcover','Land cover'),('historical-heat','Historical heat'),('settlement','Settlement change'),('urban-settlements','Urban settlements'),('healthcare','Healthcare'),('portfolio','Projects'),('data-sources','Sources &amp; limitations')]
blocks=[]
for number,(id,label) in enumerate(order,1):
 m=re.search(r'<section id="'+id+r'".*?</section>',page,re.S);assert m,id
 block=m.group();block=re.sub(r'(<p class="section-kicker">)\d+ /',lambda m:m.group(1)+f'{number:02} /',block,count=1)
 blocks.append(block);page=page[:m.start()]+page[m.end():]
nav='<nav class="section-nav" aria-label="Analysis sections">'+''.join('<a href="#'+id+'">'+label+'</a>' for id,label in order)+'</nav>'
page,n=re.subn(r'<nav class="section-nav".*?</nav>',nav+'\n'+'\n'.join(blocks),page,count=1,flags=re.S);assert n==1
page=page.replace('sedac/analysis-v2.js?v=2026-10-15.views.49','sedac/analysis-v3.js?v='+REV)
(ROOT/'working/analysis.html').write_text(page)
old=(BASE/'site/sedac/analysis-v2.js').read_text()
functions=old[old.index('function link('):old.index('async function init()')]
functions=functions.replace("$('sedacAnalysisHeat').hidden=mode!=='heat';",'')
functions=re.sub(r"document.querySelectorAll\('\[data-sedac-analysis\]'\).forEach\(b=>b.setAttribute\('aria-pressed',String\(b.dataset.sedacAnalysis===mode\)\)\);",'',functions)
helpers=old[old.index('const $='):old.index("let data,mode=")]
helpers=helpers.replace('document.getElementById(id)',"document.getElementById(id.replace('sedacAnalysis',prefix))")
js="""(async function(){
'use strict';
const sections=[['towns','urbanAnalysis'],['grdi','deprivationAnalysis'],['heat','heatAnalysis']];
try{
 const data=await parent.WBVault.json('analysis/sedac');
 if(data.format!=='wb-sedac-summary-v1')throw Error('Invalid SEDAC summary');
 for(const [mode,prefix] of sections)mount(mode,prefix);
 function mount(mode,prefix){
"""+helpers+"let code='karamoja',threshold='28';\n"+functions+"""
 $('sedacAnalysisCluster').innerHTML=data.clusters.map(c=>'<option value="'+c.code+'">'+esc(c.label)+'</option>').join('');
 $('sedacAnalysisCluster').value=code;
 $('sedacAnalysisCluster').onchange=()=>{code=$('sedacAnalysisCluster').value;render();};
 if(mode==='heat')$('sedacAnalysisThreshold').onchange=()=>{threshold=$('sedacAnalysisThreshold').value;render();};
 $('sedacAnalysisDownload').onclick=download;render();
 $('sedacAnalysisLoading').hidden=true;$('sedacAnalysisContent').hidden=false;
 }
}catch(e){for(const [,prefix] of sections){const loading=document.getElementById(prefix+'Loading');if(loading)loading.textContent='This analysis could not load. Reopen Analysis to retry.';}console.error(e);}
})();
"""
(ROOT/'site/sedac/analysis-v3.js').write_text(js)
ids=re.findall(r'\bid="([^"]+)"',page);assert len(ids)==len(set(ids))
assert page.index('id="clusterSelect"')<page.index('id="rural-access"')
assert 'sedac-context' not in page and 'data-sedac-analysis' not in page
print('Three independent sections; geography controls at the top; unique element IDs.')
