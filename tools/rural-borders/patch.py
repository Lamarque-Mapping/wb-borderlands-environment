from pathlib import Path
ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent/'deprivation_tabs'
WORK=ROOT/'working'
SITE=ROOT/'site'
WORK.mkdir(parents=True,exist_ok=True)
(SITE/'sedac').mkdir(parents=True,exist_ok=True)

def replace(text,old,new,count=1):
    assert text.count(old)==count,(old[:100],text.count(old))
    return text.replace(old,new)

revision='2026-10-15.rural-borders.52'
for code in ['mandera_triangle','moyale_borana','karamoja','dikhil']:
    page=(BASE/'working'/f'page_map_{code}.html').read_text()
    page=replace(page,"const ruralAccessState={selectedId:null,sourceMetadata:null};","const ruralAccessState={selectedId:null,sourceMetadata:null,countryLines:null};")
    page=replace(page,"{pane:'ruralAccessPane',renderer:","{pane:'ruralAccessPane',smoothFactor:0,renderer:")
    page=replace(page,"  ruralAccess:()=>ruralAccessLayer(),", "  ruralAccess:()=>ruralAccessLayer(),\n  ruralCountryBorders:()=>geo(ruralAccessState.countryLines||(ruralAccessState.countryLines=window.wbRuralCountryLines(DATA.ruralAccessUnits||emptyFc())),{interactive:false,color:'#314b3d',weight:2.2,opacity:.95,smoothFactor:0,className:'rural-country-border'},'Country division','SEDAC source country division','boundaryPane'),")
    page=replace(page,'function base(){Object.keys(active).filter(k=>!["borders","cluster","countryLabels"].includes(k)).forEach(remove);add("borders");add("cluster");add("countryLabels")}',"function base(){const keys=ruralAccessActive()?['ruralCountryBorders','countryLabels']:['borders','cluster','countryLabels'];Object.keys(active).filter(k=>!keys.includes(k)).forEach(remove);keys.forEach(add);}")
    page=replace(page,"const rows=[legendItem('<span class=\"swatch-line\"></span>','International borders'),legendItem('<span class=\"swatch-line\"></span>','Borderland Analysis boundary'),", "const rows=[...(ruralAccessActive()?[legendItem('<span class=\"swatch-line\" style=\"border-color:#314b3d\"></span>','Country divisions · SEDAC source')]:[legendItem('<span class=\"swatch-line\"></span>','International borders'),legendItem('<span class=\"swatch-line\"></span>','Borderland Analysis boundary')]),")
    page=replace(page,"let source='Administrative boundaries and borders: OCHA Common Operational Datasets (COD-AB), via HDX.';", "let source=ruralAccessActive()?'Country divisions follow the shared edges of the SEDAC source units (GADM v3.6).':'Administrative boundaries and borders: OCHA Common Operational Datasets (COD-AB), via HDX.';")
    page=replace(page,"Shading follows the original source units. These can differ from the OCHA administrative reference boundaries.","Shading and country divisions follow the same original SEDAC source units. The separate OCHA reference borders and cluster outline are hidden in this view.")
    page=replace(page,"['clean','projects','population','towns','services','crossings','builtup','admin','infrastructure']","['clean','projects','towns','services','crossings','builtup','admin','infrastructure']")
    page=replace(page,'sedac/sedac-v5.js?v=2026-10-15.deprivation-tabs.51',f'sedac/sedac-v6.js?v={revision}')
    page=replace(page,'</script></head>',f'</script><script src="analysis/rural-country-lines-v1.js?v={revision}"></script></head>')
    page=replace(page,'they can differ from the OCHA administrative references.','they can differ from the OCHA administrative references. In rural access, country divisions follow exact shared edges between source units in different countries; the separate OCHA borders and cluster outline are hidden to avoid offset lines.')
    (WORK/f'page_map_{code}.html').write_text(page)

module=(BASE/'site/sedac/sedac-v5.js').read_text()
module=replace(module,"   note(box,kind==='grdi'?'Relative deprivation index, 0–100. Higher values indicate more deprivation. Inputs: 2010–2020.':", "   if(kind==='grdi'){const period=note(box,'');period.innerHTML='<strong>2022 release · inputs 2010–2020</strong>';}\n   note(box,kind==='grdi'?'Relative deprivation index, 0–100. Higher values indicate more deprivation.':")
module=replace(module,'<br>Inputs: 2010–2020 · same scale across all four maps.','<br>GRDI v1 · 2022 release · inputs 2010–2020.<br>Same scale across all four maps.')
(SITE/'sedac/sedac-v6.js').write_text(module)

analysis=(ROOT.parent/'deprivation_hex/working/analysis.html').read_text()
analysis=replace(analysis,'GRDI · inputs 2010–2020','GRDI v1 · 2022 release · inputs 2010–2020')
analysis=replace(analysis,'they can differ from the OCHA administrative references.','they can differ from the OCHA administrative references. In rural access, country divisions follow exact shared edges between source units in different countries; the separate OCHA borders and cluster outline are hidden to avoid offset lines.')
(WORK/'analysis.html').write_text(analysis)
print('Prepared aligned rural-access borders, stable Population buttons, and explicit GRDI dates.')
