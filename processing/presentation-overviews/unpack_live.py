from pathlib import Path
import json,gzip,base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
R=Path('live_repo');O=Path('work/live');O.mkdir(exist_ok=True)
b=json.loads((R/'boot.json').read_text()); aes=AESGCM(base64.b64decode(b['public_key']))
def unpack(x):
 raw=b''.join((R/p).read_bytes() for p in b.get('asset_parts',{}).get(x['path'],[x['path']]))
 raw=aes.decrypt(base64.b64decode(x['nonce']),raw,(b['build']+'|'+x['id']).encode())
 return gzip.decompress(raw) if x.get('gzip') else raw
m=json.loads(unpack(b['manifest']));(O/'manifest.json').write_text(json.dumps(m,indent=2))
print('assets',len(m))
for k,v in m.items():
 if any(k.startswith(c+'/') for c in ['moyale_borana','mandera_triangle','karamoja','dikhil']) and k.split('/')[-1] in ['core','acled','hexes'] or k.startswith('page/map=') or k in ['page/home']:
  out=O/(k.replace('/','_').replace('=','_')+('.html' if v['mime']=='text/html' else '.json'))
  raw=unpack(v);out.write_bytes(raw)
  print(k,len(raw),out)
print('other',[(k,v.get('bytes')) for k,v in m.items() if not any(k.startswith(c+'/') for c in ['moyale_borana','mandera_triangle','karamoja','dikhil'])][:30])
