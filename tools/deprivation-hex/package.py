from pathlib import Path
import json,base64,gzip,hashlib,os,re,shutil,subprocess
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent/'source_balance';SITE=ROOT/'site';WORK=ROOT/'working'
boot=json.loads((BASE/'site/boot.json').read_text());old=json.loads((BASE/'working/manifest.json').read_text());manifest=dict(old);aes=AESGCM(base64.b64decode(boot['public_key']));changes=[]
(SITE/'assets').mkdir(exist_ok=True)
def asset(raw,mime):
 nonce=os.urandom(12);aid=hashlib.sha256(raw+nonce).hexdigest()[:32];path='assets/'+aid+'.bin';aad=(boot['build']+'|'+aid).encode();encrypted=aes.encrypt(nonce,gzip.compress(raw,mtime=0),aad);parts=[]
 if len(encrypted)>49152:
  for n,i in enumerate(range(0,len(encrypted),49152)):
   p=f'assets/{aid}.part{n:03}.bin';(SITE/p).write_bytes(encrypted[i:i+49152]);parts.append(p);changes.append(p)
  boot['asset_parts'][path]=parts
 else:(SITE/path).write_bytes(encrypted);changes.append(path)
 assert gzip.decompress(aes.decrypt(nonce,b''.join((SITE/p).read_bytes() for p in parts or [path]),aad))==raw
 return dict(path=path,id=aid,nonce=base64.b64encode(nonce).decode(),gzip=True,mime=mime,bytes=len(encrypted))
codes=['mandera_triangle','moyale_borana','karamoja','dikhil']
for code in codes:
 manifest[code+'/grdiHex']=asset((ROOT/'data'/f'{code}_grdi_hex.json').read_bytes(),'application/json')
for filename,key in [(f'page_map_{c}.html','page/map='+c) for c in codes]+[('analysis.html','page/analysis')]:
 page=(WORK/filename).read_text()
 for i,script in enumerate(re.findall(r'<script\b[^>]*>(.*?)</script>',page,re.S)):
  if not script.strip():continue
  p=WORK/f'{filename}-{i}.js';p.write_text(script);subprocess.run(['node','--check',str(p)],check=True,capture_output=True)
 assert page.count('Hex means are weighted by the exact area of overlap')==1
 assert not re.search('<(?:tr|section)[^>]*class="(?:rai|sedac)-source',page)
 manifest[key]=asset(page.encode(),'text/html')
assert all(manifest[k]==v for k,v in old.items() if not k.startswith('page/'))
boot['manifest']=asset(json.dumps(manifest,separators=(',',':')).encode(),'application/json');boot['ui_revision']='2026-10-15.grdi-hex.50'
(SITE/'boot.json').write_text(json.dumps(boot,separators=(',',':'))+'\n');changes.append('boot.json');(WORK/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
changes += ['sedac/sedac-v4.js','sedac/analysis-v3.js'];subprocess.run(['node','--check',str(SITE/'sedac/sedac-v4.js')],check=True,capture_output=True)
out=SITE/'tools/deprivation-hex';out.mkdir(parents=True,exist_ok=True)
for path in ['build_data.py','patch_site.py','package.py','fetch_hexes.py','patch_analysis.py']:
 shutil.copyfile(ROOT/path,out/path);changes.append('tools/deprivation-hex/'+path)
validation=json.loads((ROOT/'data/validation.json').read_text())
for row in validation['maps']:
 a=json.loads((ROOT.parent/'sedac_integration/data'/f"{row['code']}_sedac.json").read_text())['grdi']['summary']
 row['source_mean_comparison_error']=abs(row['area_mean']-a['area_mean']);row['coverage_comparison_error']=abs(row['mapped_area_share']-a['coverage_share'])
 assert row['source_mean_comparison_error']<.01 and row['coverage_comparison_error']<.001
validation['notes']=['Comparisons to native whole-pixel summaries differ slightly because hexes clip pixels at the cluster edge and use EPSG:6933 areas.','Source geometry is retained in the display. Invalid polygon rings are repaired for area calculation only.','No original data asset was changed. All five source tables retain equal row styling.']
(out/'validation.json').write_text(json.dumps(validation,indent=2)+'\n');changes.append('tools/deprivation-hex/validation.json')
queue=[]
for path in changes:
 raw=(SITE/path).read_bytes();queue.append({'path':path,'bytes':len(raw),'sha':hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()})
(ROOT/'queue.json').write_text(json.dumps(queue));print(json.dumps({'files':len(queue),'revision':boot['ui_revision'],'original_data_assets_unchanged':True,'maps':4}))
