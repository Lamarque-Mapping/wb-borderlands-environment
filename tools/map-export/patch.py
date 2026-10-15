from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent / 'map_export_finish'
(ROOT / 'working').mkdir(parents=True, exist_ok=True)
(ROOT / 'site/export').mkdir(parents=True, exist_ok=True)
for path in (BASE / 'working').glob('page_map_*.html'):
    page = path.read_text().replace('export/save-view-v2.js?v=2026-10-15.save-view.54', 'export/save-view-v3.js?v=2026-10-15.save-view.55')
    (ROOT / 'working' / path.name).write_text(page)
js = (BASE / 'site/export/save-view-v2.js').read_text()
js = js.replace("backgroundColor:'#fff'});", "backgroundColor:'#fff',style:{position:'static',left:'auto',top:'auto',transform:'none'}});")
js = js.replace("status.appendChild(a);const close=", "status.appendChild(a);const preview=element('a','','Preview');preview.href=url;preview.target='_blank';preview.rel='noopener';preview.style.cssText=a.style.cssText;status.appendChild(preview);const close=")
(ROOT / 'site/export/save-view-v3.js').write_text(js)
package = (BASE / 'package.py').read_text().replace("'map_save_view'", "'map_export_finish'").replace('2026-10-15.save-view.54','2026-10-15.save-view.55').replace('save-view-v2.js','save-view-v3.js')
(ROOT / 'package.py').write_text(package)
