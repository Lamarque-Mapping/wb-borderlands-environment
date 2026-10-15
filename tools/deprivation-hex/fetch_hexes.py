import json,urllib.request,base64,gzip,time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
root=Path(__file__).resolve().parent
boot=json.loads(Path('source_balance/site/boot.json').read_text());manifest=json.loads(Path('source_balance/working/manifest.json').read_text());aes=AESGCM(base64.b64decode(boot['public_key']))
base='https://hughlamarque-dev.github.io/wb-borderlands-environment/'
codes=['mandera_triangle','moyale_borana','karamoja','dikhil']
def fetch(path):
 return urllib.request.urlopen(base+path,timeout=60).read()
paths=[]
for c in codes:
 desc=manifest[c+'/hexes'];paths+=boot.get('asset_parts',{}).get(desc['path'],[desc['path']])
with ThreadPoolExecutor(max_workers=16) as pool:raw=dict(zip(paths,pool.map(fetch,paths)))
for c in codes:
 desc=manifest[c+'/hexes'];data=b''.join(raw[p] for p in boot.get('asset_parts',{}).get(desc['path'],[desc['path']]))
 plain=gzip.decompress(aes.decrypt(base64.b64decode(desc['nonce']),data,(boot['build']+'|'+desc['id']).encode()))
 (root/'input'/f'{c}_hexes.json').write_bytes(plain)
 d=json.loads(plain);print(c,len(d['hexGrid']['features']),list(d['hexGrid']['features'][0]['properties'])[:10])
