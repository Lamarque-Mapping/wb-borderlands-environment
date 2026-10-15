from pathlib import Path
import base64, gzip, hashlib, json, os, re, shutil, subprocess
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent / 'map_export_finish'
SITE = ROOT / 'site'
WORK = ROOT / 'working'
boot = json.loads((BASE / 'site/boot.json').read_text())
original = json.loads((BASE / 'working/manifest.json').read_text())
manifest = dict(original)
aes = AESGCM(base64.b64decode(boot['public_key']))
changes = []
(SITE / 'assets').mkdir(exist_ok=True)

def asset(raw, mime):
    nonce = os.urandom(12)
    aid = hashlib.sha256(raw + nonce).hexdigest()[:32]
    path = 'assets/' + aid + '.bin'
    aad = (boot['build'] + '|' + aid).encode()
    encrypted = aes.encrypt(nonce, gzip.compress(raw, mtime=0), aad)
    parts = []
    if len(encrypted) > 49152:
        for n, i in enumerate(range(0, len(encrypted), 49152)):
            p = f'assets/{aid}.part{n:03}.bin'
            (SITE / p).write_bytes(encrypted[i:i + 49152])
            parts.append(p)
            changes.append(p)
        boot['asset_parts'][path] = parts
    else:
        (SITE / path).write_bytes(encrypted)
        changes.append(path)
    assert gzip.decompress(aes.decrypt(nonce, b''.join((SITE/p).read_bytes() for p in parts or [path]), aad)) == raw
    return dict(path=path, id=aid, nonce=base64.b64encode(nonce).decode(), gzip=True, mime=mime, bytes=len(encrypted))

codes = ['mandera_triangle', 'moyale_borana', 'karamoja', 'dikhil']
for code in codes:
    filename = f'page_map_{code}.html'
    page = (WORK / filename).read_text()
    for i, script in enumerate(re.findall(r'<script\b[^>]*>(.*?)</script>', page, re.S)):
        if not script.strip():
            continue
        p = WORK / f'{filename}-{i}.js'
        p.write_text(script)
        subprocess.run(['node', '--check', str(p)], check=True, capture_output=True)
    assert page.count("['deprivation','Deprivation · raster'],['deprivationHex','Deprivation · hexagons']") == 1
    manifest['page/map=' + code] = asset(page.encode(), 'text/html')

assert all(manifest[k] == v for k, v in original.items() if not k.startswith('page/map='))
boot['manifest'] = asset(json.dumps(manifest, separators=(',', ':')).encode(), 'application/json')
boot['ui_revision'] = '2026-10-15.save-view.55'
(SITE / 'boot.json').write_text(json.dumps(boot, separators=(',', ':')) + '\n')
(WORK / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
changes += ['boot.json', 'export/save-view-v3.js']
subprocess.run(['node', '--check', str(SITE / 'export/save-view-v3.js')], check=True, capture_output=True)
out = SITE / 'tools/map-export'
out.mkdir(parents=True, exist_ok=True)
for filename in ['patch.py', 'package.py']:
    shutil.copyfile(ROOT / filename, out / filename)
    changes.append('tools/map-export/' + filename)

queue = []
for path in changes:
    raw = (SITE / path).read_bytes()
    queue.append(dict(path=path, bytes=len(raw), sha=hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()))
(ROOT / 'queue.json').write_text(json.dumps(queue))
print(json.dumps(dict(files=len(queue), revision=boot['ui_revision'], data_assets_unchanged=True, analysis_page_unchanged=True)))
