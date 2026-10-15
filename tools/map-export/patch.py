from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent / 'map_export_frame'
(ROOT / 'working').mkdir(parents=True, exist_ok=True)
(ROOT / 'site/export').mkdir(parents=True, exist_ok=True)
for path in (BASE / 'working').glob('page_map_*.html'):
    page = path.read_text().replace('export/save-view-v3.js?v=2026-10-15.save-view.55', 'export/save-view-v4.js?v=2026-10-15.save-view.56')
    (ROOT / 'working' / path.name).write_text(page)
js = (BASE / 'site/export/save-view-v3.js').read_text()
# Permanent labels (including FEWS trade locations) are part of the visible map.
js = js.replace("&&!node.classList?.contains('leaflet-tooltip-pane')", '')
(ROOT / 'site/export/save-view-v4.js').write_text(js)
package = (BASE / 'package.py').read_text().replace("'map_export_finish'", "'map_export_frame'").replace('2026-10-15.save-view.55','2026-10-15.save-view.56').replace('save-view-v3.js','save-view-v4.js')
(ROOT / 'package.py').write_text(package)
