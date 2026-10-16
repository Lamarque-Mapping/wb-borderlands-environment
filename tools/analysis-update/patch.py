from pathlib import Path
import re

ROOT=Path(__file__).resolve().parent
BASE=ROOT/'baseline'
SITE=ROOT/'site'
page=(BASE/'analysis.html').read_text()
order=['population','urban-settlements','settlement','landcover','deprivation','rural-access','healthcare','violence','historical-heat','portfolio','data-sources']
sections={m.group(1):m.group(0) for m in re.finditer(r'<section id="([^"]+)".*?</section>',page,re.S)}
assert set(sections)==set(order)
old_ids={'rural-access':'raiDownload','urban-settlements':'urbanAnalysisDownload','deprivation':'deprivationAnalysisDownload','historical-heat':'heatAnalysisDownload'}
labels={'population':'Population','urban-settlements':'Urban settlements','settlement':'Settlement change','landcover':'Land cover','deprivation':'Deprivation','rural-access':'Rural access','healthcare':'Healthcare','violence':'Violence','historical-heat':'Historical heat','portfolio':'Projects','data-sources':'Sources &amp; limitations'}
for number,id in enumerate(order,1):
    block=re.sub(r'(class="section-kicker">)\d+ /',rf'\g<1>{number:02d} /',sections[id],count=1)
    if id in old_ids:
        block,n=re.subn(r'<button\b[^>]*\bid="'+old_ids[id]+r'"[^>]*>.*?</button>','',block,count=1,flags=re.S)
        assert n==1
    title=labels[id].replace('&amp;','&')
    buttons=f'<div class="analysis-exports" role="group" aria-label="Export {title}"><button type="button" id="{id}ExportCSV" class="analysis-export" disabled>Export data · CSV</button>'
    if id!='data-sources': buttons+=f'<button type="button" id="{id}ExportPNG" class="analysis-export" data-export-chart="{id}" disabled>Export chart · PNG</button>'
    buttons+=f'<span id="{id}ExportStatus" class="analysis-export-status" role="status" aria-live="polite"></span></div>'
    # Insert immediately below each section's heading, before its local controls.
    head=re.search(r'<div class="analysis-head">.*?</h2></div>(?:<span.*?</span>)?</div>',block,re.S)
    assert head, id
    block=block[:head.end()]+buttons+block[head.end():]
    sections[id]=block
start=page.index('<section ');end=page.rindex('</section>')+len('</section>')
page=page[:start]+'\n'.join(sections[id] for id in order)+page[end:]
page=re.sub(r'<nav class="section-nav".*?</nav>','<nav class="section-nav" aria-label="Analysis sections">'+''.join(f'<a href="#{id}">{labels[id]}</a>' for id in order)+'</nav>',page,count=1,flags=re.S)
page=page.replace('These controls apply to violence, population, land cover, settlement change, healthcare and projects.','These controls apply to population, settlement change, land cover, healthcare, violence and projects.')
page=page.replace('</head>','<link rel="stylesheet" href="analysis/exports-v1.css?v=2026-10-16.analysis.57"></head>',1)
page=page.replace('<script src="sedac/analysis-v3.js?v=2026-10-15.grdi-hex.50"></script>','<script src="analysis/exports-v1.js?v=2026-10-16.analysis.57"></script><script src="sedac/analysis-v4.js?v=2026-10-16.analysis.57"></script>')
page=page.replace('analysis/rural-access-v1.js?v=2026-10-14.rural-analysis.40','analysis/rural-access-v2.js?v=2026-10-16.analysis.57')
page=page.replace('function renderPopulation(){',(ROOT/'core-exports.js').read_text()+'\nfunction renderPopulation(){',1)
page=page.replace(" $('populationSummary').textContent=", " populationExport(rows);\n $('populationSummary').textContent=",1)
page=page.replace(" $('landChart').innerHTML=", " landExport(rows);\n $('landChart').innerHTML=",1)
page=page.replace(" $('builtChart').innerHTML=", " builtExport(rows);\n $('builtChart').innerHTML=",1)
page=page.replace(" $('healthAxis').textContent=", " healthExport(rows);\n $('healthAxis').textContent=",1)
page=page.replace(" if(!u){$('acledChart')", " if(!u){violenceExport(null,cover,[]);$('acledChart')",1)
page=page.replace(" const a=u.acled||{},series=a.monthly||[];", " const a=u.acled||{},series=a.monthly||[];\n violenceExport(u,cover,series);",1)
page=page.replace(" $('portfolioScope').textContent=", " projectsExport(families,rows,display);\n $('portfolioScope').textContent=",1)
(ROOT/'analysis.html').write_text(page)

js=(BASE/'sedac/analysis-v3.js').read_text()
start=js.index('function download(){');end=js.index("\n\n $('sedacAnalysisCluster')",start)
js=js[:start]+'''function download(){
 const c=data.clusters.find(c=>c.code===code);let fields,rows;
 if(mode==='towns'){
  fields=['cluster','source_id','name','country','source_class','population_2020','source_footprint_km2','source','footprint_reference','notes'];
  rows=c.towns.map(t=>[c.label,t.id,t.name,t.country,t.type,t.population_2020,t.area_sqkm,'SEDAC GUPPD v1 (2024); GHSL R2023 population','circa 2015','Whole source footprint selected by representative point inside cluster; not municipal census totals']);
 }else if(mode==='grdi'){
  fields=['record_type','cluster','index_band','share_of_valid_mapped_area','cluster_area_coverage_share','area_mean_index','source','input_years','weighting'];
  rows=[...data.clusters.map(k=>['cluster_summary',k.label,'','',k.grdi.coverage_share,k.grdi.area_mean,'SEDAC GRDI v1 (2022)','2010-2020','Approximate cell area; not population']),...c.grdi.histogram.map(r=>['selected_distribution',c.label,r.label,r.area_share,c.grdi.coverage_share,c.grdi.area_mean,'SEDAC GRDI v1 (2022)','2010-2020','Approximate cell area; not population'])];
 }else{
  fields=['record_type','cluster','year','wbgt_threshold_c','area_weighted_mean_days','cluster_area_coverage_share','source','period','weighting'];
  rows=[...data.clusters.map(k=>['cluster_summary',k.label,'',Number(threshold),k.heat[threshold].area_mean,k.heat[threshold].coverage_share,'SEDAC GEHE (2023)','1983-2016','Same valid pixels; approximate cell area; not population']),...c.heat[threshold].annual.map(r=>['selected_annual_series',c.label,r.year,Number(threshold),r.area_mean_days,c.heat[threshold].coverage_share,'SEDAC GEHE (2023)','1983-2016','Same valid pixels; approximate cell area; not population'])];
 }
 window.WBAnalysisExport.saveCSV(sectionId,fields,rows,code+'_sedac_'+mode+(mode==='heat'?'_'+threshold:'')+'.csv');
}
''' +js[end:]
js=js.replace("let code='karamoja',threshold='28';", "let code='karamoja',threshold='28';\nconst sectionId=mode==='towns'?'urban-settlements':mode==='grdi'?'deprivation':'historical-heat';")
js=js.replace("$('sedacAnalysisDownload').onclick=download;render();", "window.WBAnalysisExport.register(sectionId,download);render();")
(SITE/'sedac').mkdir(exist_ok=True)
(SITE/'sedac/analysis-v4.js').write_text(js)

js=(BASE/'analysis/rural-access-v1.js').read_text()
js=js.replace("$('raiDownload').disabled=!selected.length;", "$('rural-accessExportCSV').disabled=!selected.length;")
start=js.index(" $('raiDownload').onclick=");end=js.index("\n render();$('raiControls')",start)
js=js[:start]+''' window.WBAnalysisExport.register('rural-access',()=>{
 const selected=ordered(rows(),$('raiSort').value),fields=['record_type','cluster','source_id','source_name','region','country','access_pct','rural_population','within_2km','beyond_2km','valid_source_units','missing_source_units','status','boundary_basis','population_year','road_date','release','source'];
 const common=['GADM v3.6 full source units; not clipped cluster estimates',2020,'2022-03-31',2023,'CIESIN / NASA SEDAC Rural Access Index'];
 const exported=[...data.clusters.map(c=>{const s=summary(data.rows.filter(r=>r.cluster===c.code));return ['cluster_summary',c.name,'','','','',s.weighted,s.rural,s.within,s.rural-s.within,s.valid,s.missing,'Valid units only; country filter does not apply to overview',...common];}),...selected.map(r=>['selected_source_unit',r.cluster,r.id,r.name,r.region,r.country,r.access_pct,r.rural_population,r.within_2km,valid(r)?r.rural_population-r.within_2km:null,'','',r.status,...common])];
 window.WBAnalysisExport.saveCSV('rural-access',fields,exported,'rural-access-'+cluster+(country?'-'+country.toLowerCase().replace(/[^a-z0-9]+/g,'-'):'')+'.csv');
 });''' +js[end:]
(SITE/'analysis/rural-access-v2.js').write_text(js)
print('Reordered 10 analyses; added consistent chart and data exports, plus sources CSV.')
