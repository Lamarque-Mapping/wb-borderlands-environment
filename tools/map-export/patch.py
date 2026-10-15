from pathlib import Path
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent/'rai_border_ui';WORK=ROOT/'working'
WORK.mkdir(parents=True,exist_ok=True)
def replace(text,old,new):
 assert text.count(old)==1,(old[:100],text.count(old));return text.replace(old,new)
for code in ['mandera_triangle','moyale_borana','karamoja','dikhil']:
 page=(BASE/'working'/f'page_map_{code}.html').read_text()
 page=replace(page,'</script></head>','</script><link rel="stylesheet" href="export/save-view-v1.css?v=2026-10-15.save-view.53"><script src="export/save-view-v1.js?v=2026-10-15.save-view.53"></script></head>')
 page=replace(page,'<button id="wbOpenSourcesButton" type="button">Data sources &amp; limitations</button></div>','<button id="wbOpenSourcesButton" type="button">Data sources &amp; limitations</button><button id="wbSaveView" type="button" title="Download a high-resolution framed PNG of the current map, with legend and source credits">Save view</button></div>')
 page=replace(page,"if(startView==='urban'){const id=", "window.setupWBMapExport({map,DATA,isReady:()=>viewReady});\nif(startView==='urban'){const id=")
 (WORK/f'page_map_{code}.html').write_text(page)
print('Added Save view to all four map pages.')
