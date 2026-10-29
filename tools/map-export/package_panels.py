"""Package only updated map documents and export code for GitHub Pages."""
import base64, gzip, hashlib, json, os, pathlib, subprocess
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
ROOT=pathlib.Path(__file__).resolve().parents[2]
WORK=ROOT/'.work'
REV='2026-10-29.panel-export.83'
boot=json.loads(subprocess.check_output(['git','show','HEAD:boot.json'],cwd=ROOT))
manifest=json.loads((WORK/'manifest.json').read_text())
original=dict(manifest)
aes=AESGCM(base64.b64decode(boot['public_key']))
changed=[]
def asset(raw,mime):
 aid=hashlib.sha256(raw).hexdigest()[:32]
 nonce=os.urandom(12); aad=(boot['build']+'|'+aid).encode()
 encrypted=aes.encrypt(nonce,gzip.compress(raw,mtime=0),aad)
 path='assets/'+aid+'.bin'; parts=[]
 for i in range(0,len(encrypted),49152):
  name=f'assets/{aid}.part{i//49152:03}.bin' if len(encrypted)>49152 else path
  (ROOT/name).write_bytes(encrypted[i:i+49152]);parts.append(name);changed.append(name)
 if len(parts)>1:boot['asset_parts'][path]=parts
 assert gzip.decompress(aes.decrypt(nonce,b''.join((ROOT/n).read_bytes() for n in parts),aad))==raw
 return dict(path=path,id=aid,nonce=base64.b64encode(nonce).decode(),gzip=True,mime=mime,bytes=len(encrypted))
for code in ['karamoja','dikhil','moyale_borana','mandera_triangle']:
 p=WORK/(code+'.html');manifest['page/map='+code]=asset(p.read_bytes(),'text/html')
assert all(manifest[k]==v for k,v in original.items() if not k.startswith('page/map='))
boot['manifest']=asset(json.dumps(manifest,separators=(',',':')).encode(),'application/json')
boot['ui_revision']=REV
(ROOT/'boot.json').write_text(json.dumps(boot,separators=(',',':'))+'\n')
changed+=['boot.json','export/save-view-v8.js','export/save-view-v6.css','export/legend-download-v1.js','sedac/sedac-v8.js','tools/map-export/upgrade_panels.py','tools/map-export/package_panels.py','tools/map-export/panel-export-ui.js']
(WORK/'publish.json').write_text(json.dumps(sorted(set(changed)),indent=2))
print(json.dumps({'revision':REV,'files':len(changed),'analytical_assets_unchanged':True}))
