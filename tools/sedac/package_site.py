"""Package the audited SEDAC update without modifying other site assets."""
import base64
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ROOT = Path(__file__).resolve().parent
SITE = ROOT / 'site'
CODES = ['mandera_triangle', 'moyale_borana', 'karamoja', 'dikhil']
REVISION = '2026-10-15.sedac.45'
BASE_HEAD = '7b6f221c2960e1ad9217be8733212104bf6e1a59'
dump = lambda obj: json.dumps(obj, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()
boot = json.loads((ROOT.parent/'rural_access_default/site/boot.json').read_text())
old_boot = json.loads(json.dumps(boot))
baseline = json.loads((ROOT.parent/'rural_access_default/working/manifest.json').read_text())
manifest = dict(baseline)
aes = AESGCM(base64.b64decode(boot['public_key']))
(SITE/'assets').mkdir(exist_ok=True)
changes = ['sedac/sedac-v1.css', 'sedac/sedac-v1.js', 'sedac/analysis-v1.js']
checks = []

def asset(raw, mime, name):
    nonce = os.urandom(12)
    identifier = hashlib.sha256(raw + b'\0' + nonce).hexdigest()[:32]
    path = 'assets/' + identifier + '.bin'
    aad = (boot['build'] + '|' + identifier).encode()
    encrypted = aes.encrypt(nonce, gzip.compress(raw, mtime=0), aad)
    parts = []
    if len(encrypted) > 48*1024:
        for number, offset in enumerate(range(0, len(encrypted), 48*1024)):
            part = f'assets/{identifier}.part{number:03}.bin'
            (SITE/part).write_bytes(encrypted[offset:offset+48*1024])
            changes.append(part)
            parts.append(part)
        boot['asset_parts'][path] = parts
    else:
        (SITE/path).write_bytes(encrypted)
        changes.append(path)
    reconstructed = b''.join((SITE/p).read_bytes() for p in parts or [path])
    assert gzip.decompress(aes.decrypt(nonce, reconstructed, aad)) == raw
    checks.append({'asset': name, 'sha256': hashlib.sha256(raw).hexdigest(),
                   'bytes': len(raw), 'encrypted_bytes': len(encrypted),
                   'parts': len(parts) or 1, 'roundtrip_identical': True})
    return {'path': path, 'id': identifier, 'nonce': base64.b64encode(nonce).decode(),
            'gzip': True, 'mime': mime, 'bytes': len(encrypted)}

for code in CODES:
    for name, path, mime in [
        (code+'/sedac', ROOT/'data'/f'{code}_sedac.json', 'application/json'),
        ('page/map='+code, ROOT/'working'/f'page_map_{code}.html', 'text/html')
    ]:
        manifest[name] = asset(path.read_bytes(), mime, name)
for name, path, mime in [
    ('analysis/sedac', ROOT/'data/summary.json', 'application/json'),
    ('page/analysis', ROOT/'working/analysis.html', 'text/html')
]:
    manifest[name] = asset(path.read_bytes(), mime, name)
expected_changed = {'page/map='+code for code in CODES} | {'page/analysis'}
assert {k for k in baseline if baseline[k] != manifest[k]} == expected_changed
assert set(manifest)-set(baseline) == {c+'/sedac' for c in CODES} | {'analysis/sedac'}
boot['manifest'] = asset(dump(manifest), 'application/json', 'manifest')
boot['ui_revision'] = REVISION
assert {k:v for k,v in boot.items() if k not in ('manifest','asset_parts','ui_revision')} == {
    k:v for k,v in old_boot.items() if k not in ('manifest','asset_parts','ui_revision')}
(SITE/'boot.json').write_bytes(dump(boot)+b'\n')
changes.append('boot.json')
(ROOT/'working/new_manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
validation = {'status':'passed', 'baseline_commit':BASE_HEAD, 'revision':REVISION,
              'updated_pages':sorted(expected_changed), 'other_manifest_entries_unchanged':True,
              'existing_access_configuration_unchanged':True, 'assets':checks}
(ROOT/'package_validation.json').write_text(json.dumps(validation, indent=2)+'\n')
for name in ['build_data.py','patch_site.py','package_site.py','audit.json',
             'baseline_validation.json','package_validation.json','sources.html',
             'analysis_section.html','README.md']:
    target = SITE/'tools/sedac'/name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT/name, target)
    changes.append(target.relative_to(SITE).as_posix())
assert all((SITE/p).is_file() for p in changes)
(ROOT/'changes.json').write_text(json.dumps(changes, indent=2)+'\n')
print(json.dumps({'status':'passed','files':len(changes),'bytes':sum((SITE/p).stat().st_size for p in changes),'assets':checks}, indent=2))
