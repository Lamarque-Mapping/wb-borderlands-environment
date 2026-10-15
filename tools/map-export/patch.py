from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent / 'map_save_view'
(ROOT / 'working').mkdir(parents=True, exist_ok=True)
(ROOT / 'site/export').mkdir(parents=True, exist_ok=True)
for path in (BASE / 'working').glob('page_map_*.html'):
    page = path.read_text().replace('export/save-view-v1.js?v=2026-10-15.save-view.53', 'export/save-view-v2.js?v=2026-10-15.save-view.54')
    (ROOT / 'working' / path.name).write_text(page)
js = (BASE / 'site/export/save-view-v1.js').read_text()
js = js.replace("a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);", "a.click();a.textContent='Download PNG';a.style.cssText='display:inline-block;margin-left:14px;color:#244e46;font-weight:600';")
js = js.replace("status.textContent='Map downloaded · '+output.width.toLocaleString()+' × '+output.height.toLocaleString()+' pixels';setTimeout(()=>status.remove(),8000);", "status.textContent='Map ready · '+output.width.toLocaleString()+' × '+output.height.toLocaleString()+' pixels';status.appendChild(a);const close=element('button','','Close');close.type='button';close.onclick=()=>status.remove();status.appendChild(close);setTimeout(()=>{status.remove();URL.revokeObjectURL(url);},120000);")
(ROOT / 'site/export/save-view-v2.js').write_text(js)
package = (BASE / 'package.py').read_text().replace("'rai_border_ui'", "'map_save_view'").replace('2026-10-15.save-view.53','2026-10-15.save-view.54').replace('save-view-v1.js','save-view-v2.js')
package = package.replace(", 'export/save-view-v1.css', 'vendor/html-to-image.js', 'vendor/html-to-image-LICENSE', 'vendor/html-to-image-version.json'", '')
(ROOT / 'package.py').write_text(package)
