"""Give every source the same presentation, preserving the existing source notes."""
from pathlib import Path
import base64, gzip, hashlib, html, json, os, re
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from patch_ui import patch_page, modules, REV

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent/'sedac_integration'
SITE = ROOT/'site'
WORK = ROOT/'working'
SITE.mkdir(exist_ok=True)
WORK.mkdir(exist_ok=True)
(SITE/'assets').mkdir(exist_ok=True)
boot = json.loads((BASE/'fix_site/boot.json').read_text())
old_manifest = json.loads((BASE/'working/final_manifest.json').read_text())
manifest = dict(old_manifest)
aes = AESGCM(base64.b64decode(boot['public_key']))
changes = []
checks = []
codes = ['mandera_triangle', 'moyale_borana', 'karamoja', 'dikhil']

def table_rows(page):
    start = page.index('<div id="wbSourcesContent">') if '<div id="wbSourcesContent">' in page else page.index('<section id="data-sources"')
    a = page.index('<tbody>', start)
    b = page.index('</tbody>', a)
    rows = re.findall(r'<tr\b[^>]*>.*?</tr>', page[a:b], re.S)
    return a, b, rows

base_map = (BASE/'working/page_map_karamoja.html').read_text()
project_notes = re.search(r'<h3>Development projects</h3>(.*?)<h3>Source and licence summary</h3>', base_map, re.S).group(1)
project_notes = project_notes.replace('Filtered CSVs can be downloaded after unlocking the site.', 'Filtered exports are available in the project directory.')
project_row = '<tr><td>Development projects · IATI</td><td>International Aid Transparency Initiative (IATI) publisher records, retrieved through d-portal.</td><td>Consult the original publisher’s use terms and retain source attribution for each record.</td><td>'+project_notes+'</td></tr>'

def asset(raw, mime):
    nonce = os.urandom(12)
    aid = hashlib.sha256(raw+nonce).hexdigest()[:32]
    path = 'assets/'+aid+'.bin'
    aad = (boot['build']+'|'+aid).encode()
    encrypted = aes.encrypt(nonce, gzip.compress(raw, mtime=0), aad)
    parts = []
    if len(encrypted) > 49152:
        for n, offset in enumerate(range(0, len(encrypted), 49152)):
            part = f'assets/{aid}.part{n:03}.bin'
            (SITE/part).write_bytes(encrypted[offset:offset+49152])
            parts.append(part); changes.append(part)
        boot['asset_parts'][path] = parts
    else:
        (SITE/path).write_bytes(encrypted); changes.append(path)
    rebuilt = b''.join((SITE/p).read_bytes() for p in parts or [path])
    assert gzip.decompress(aes.decrypt(nonce, rebuilt, aad)) == raw
    return dict(path=path, id=aid, nonce=base64.b64encode(nonce).decode(), gzip=True, mime=mime, bytes=len(encrypted))

all_themes = []
for filename, key in [(f'page_map_{c}.html','page/map='+c) for c in codes]+[('analysis.html','page/analysis')]:
    old = (BASE/'working'/filename).read_text()
    page = old
    for cls in ['sedac-source-summary', 'rai-source-summary']:
        page, n = re.subn(r'<section class="'+cls+r'"[^>]*>.*?</section>', '', page, flags=re.S)
        assert n == 1
    page = re.sub(r'<h3>Development projects</h3>.*?(?=<h3>Source and licence summary</h3>)', '', page, flags=re.S)
    page = page.replace('Sources used across the maps and analysis. Rural road access uses whole SEDAC source units; the other population, landscape and healthcare charts use the stated study-area boundaries.', 'Sources used across the maps and analysis, with their dates, geographical scope, use terms and limitations.')
    if filename == 'analysis.html':
        page = page.replace('<details class="method-note"><summary>Open source and licence table</summary>', '<details class="method-note" open><summary>Source and licence table</summary>')
    a, b, rows = table_rows(page)
    _, _, original_rows = table_rows(old)
    plain = lambda row: re.sub(r'<tr\b[^>]*>', '<tr>', row, count=1)
    rows = [plain(row) for row in rows]
    assert sorted(rows) == sorted(plain(row) for row in original_rows)
    rows.append(project_row)
    theme = lambda row: html.unescape(re.sub('<[^>]+>', '', re.search(r'<td>(.*?)</td>', row, re.S).group(1)))
    rows.sort(key=lambda row: theme(row).casefold())
    page = page[:a]+'<tbody>\n'+'\n'.join(rows)+'\n'+page[b:]
    assert len(rows)==29 and len({theme(row) for row in rows})==29
    assert all(len(re.findall('<td>', row))==4 for row in rows)
    # This is a presentation change: scripts and all existing table cells stay intact.
    assert re.findall(r'<script\b[^>]*>.*?</script>',page,re.S)==re.findall(r'<script\b[^>]*>.*?</script>',old,re.S)
    assert not re.search(r'<(?:tr|section)[^>]*class="(?:rai|sedac)-source',page)
    page = patch_page(page, filename != "analysis.html")
    (WORK/filename).write_text(page)
    manifest[key] = asset(page.encode(), 'text/html')
    checks.append({'page':key,'source_rows':29,'original_28_rows_preserved':True,'source_cleanup_preserves_scripts':True,'stable_menu_and_deferred_view_swap':filename!='analysis.html','no_featured_source_callouts_or_row_styles':True})
    all_themes.append([theme(row) for row in rows])
assert all(themes == all_themes[0] for themes in all_themes)
changed = {k for k in old_manifest if old_manifest[k]!=manifest[k]}
assert changed == {'page/map='+c for c in codes}|{'page/analysis'}
boot['manifest'] = asset(json.dumps(manifest,separators=(',',':')).encode(),'application/json')
boot['ui_revision'] = REV
(SITE/'boot.json').write_text(json.dumps(boot,separators=(',',':'))+'\n')
changes.append('boot.json')
(WORK/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
out = SITE/'tools/source-presentation'
out.mkdir(parents=True,exist_ok=True)
(out/'build.py').write_bytes(Path(__file__).read_bytes())
validation = {'baseline_commit':'23467d53014689f87c3c1e84ff75297df8bd31a1','revision':boot['ui_revision'],'checks':checks,'themes':all_themes[0],'data_assets_unchanged':True}
(out/'validation.json').write_text(json.dumps(validation,indent=2)+'\n')
(out/'patch_ui.py').write_bytes((ROOT/'patch_ui.py').read_bytes())
changes += ['tools/source-presentation/build.py','tools/source-presentation/patch_ui.py','tools/source-presentation/validation.json']
changes += modules(SITE)
queue=[]
for path in changes:
    raw=(SITE/path).read_bytes()
    queue.append({'path':path,'sha':hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()})
(ROOT/'queue.json').write_text(json.dumps(queue))
print(json.dumps({'files':len(queue),'pages':len(checks),'source_rows_per_page':29,'data_assets_unchanged':True}))
