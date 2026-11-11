"""Publish regenerated regional figures without changing the interactive map data."""
from pathlib import Path
import base64, gzip, hashlib, json, os, re, shutil, zipfile
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
FIGURES=ROOT.parent/'deliverables'
REVISION='2026-11-11.public-footers.90'
hashes={}
for p in sorted(FIGURES.glob('*.png')):
 with Image.open(p) as im:
  assert im.size==(3840,2160)
  im.resize((1200,675),Image.Resampling.LANCZOS).convert('RGB').save(ROOT/'regional-maps/previews'/p.with_suffix('.webp').name,quality=88,method=6)
 shutil.copy2(p,ROOT/'regional-maps/files'/p.name)
 hashes[p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
assert len(hashes)==5
bundle=ROOT/'regional-maps/files/WB_Four_Cluster_Presentation_Maps.zip'
with zipfile.ZipFile(bundle) as z:entries={n:z.read(n) for n in z.namelist()}
unchanged={n:hashlib.sha256(raw).hexdigest() for n,raw in entries.items() if n not in hashes}
for name in hashes:entries[name]=(ROOT/'regional-maps/files'/name).read_bytes()
with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for name,raw in entries.items():z.writestr(name,raw)
with zipfile.ZipFile(bundle) as z:
 for name,sha in {**hashes,**unchanged}.items():assert hashlib.sha256(z.read(name)).hexdigest()==sha

boot=json.loads((ROOT/'boot.json').read_text());aes=AESGCM(base64.b64decode(boot['public_key']))
def read(meta):
 raw=b''.join((ROOT/p).read_bytes() for p in boot.get('asset_parts',{}).get(meta['path'],[meta['path']]))
 raw=aes.decrypt(base64.b64decode(meta['nonce']),raw,(boot['build']+'|'+meta['id']).encode())
 return gzip.decompress(raw) if meta.get('gzip') else raw
manifest=json.loads(read(boot['manifest']));original=dict(manifest)
def put(raw,mime):
 nonce=os.urandom(12);aid=hashlib.sha256(raw+nonce).hexdigest()[:32];path='assets/'+aid+'.bin'
 cipher=aes.encrypt(nonce,gzip.compress(raw,mtime=0),(boot['build']+'|'+aid).encode())
 assert len(cipher)<49152
 (ROOT/path).write_bytes(cipher)
 result={'path':path,'id':aid,'nonce':base64.b64encode(nonce).decode(),'gzip':True,'mime':mime,'bytes':len(cipher)}
 assert read(result)==raw
 return result
page=(ROOT/'regional-maps/page.html').read_text()
page=re.sub(r'((?:src|href)="regional-maps/(?:previews|files)/[^"?]+)(?:\?[^" ]*)?(\")',rf'\1?v={REVISION}\2',page)
(ROOT/'regional-maps/page.html').write_text(page)
manifest['page/regional-maps']=put(page.encode(),'text/html')
assert all(manifest[k]==v for k,v in original.items() if k!='page/regional-maps')
boot['manifest']=put(json.dumps(manifest,separators=(',',':')).encode(),'application/json')
boot['ui_revision']=REVISION
(ROOT/'boot.json').write_text(json.dumps(boot,separators=(',',':'))+'\n')
checks={'revision':REVISION,'map_files':5,'source_png_hashes':hashes,'bundle_matches_pngs':True,'other_manifest_assets_unchanged':True,'data_and_audits_unchanged':True}
(ROOT/'tools/regional-maps/public-footer-validation.json').write_text(json.dumps(checks,indent=2)+'\n')
print(json.dumps(checks,indent=2))
