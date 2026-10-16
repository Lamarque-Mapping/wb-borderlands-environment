from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import base64,gzip,hashlib,json,os,shutil,subprocess

ROOT=Path(__file__).resolve().parent;SITE=ROOT/'site'
boot=json.loads((ROOT/'boot.json').read_text());original=json.loads((ROOT/'manifest.json').read_text());manifest=dict(original)
aes=AESGCM(base64.b64decode(boot['public_key']));changes=[]
(SITE/'assets').mkdir(exist_ok=True)
def asset(raw,mime):
 nonce=os.urandom(12);aid=hashlib.sha256(raw+nonce).hexdigest()[:32];path='assets/'+aid+'.bin';aad=(boot['build']+'|'+aid).encode();encrypted=aes.encrypt(nonce,gzip.compress(raw,mtime=0),aad)
 assert len(encrypted)<49152
 (SITE/path).write_bytes(encrypted);changes.append(path)
 assert gzip.decompress(aes.decrypt(nonce,encrypted,aad))==raw
 return dict(path=path,id=aid,nonce=base64.b64encode(nonce).decode(),gzip=True,mime=mime,bytes=len(encrypted))
manifest['page/analysis']=asset((ROOT/'analysis.html').read_bytes(),'text/html')
assert all(manifest[k]==v for k,v in original.items() if k!='page/analysis')
boot['manifest']=asset(json.dumps(manifest,separators=(',',':')).encode(),'application/json');boot['ui_revision']='2026-10-16.analysis.57'
(SITE/'boot.json').write_text(json.dumps(boot,separators=(',',':'))+'\n');changes.append('boot.json')
for file in ['analysis/exports-v1.js','analysis/exports-v1.css','analysis/rural-access-v2.js','sedac/analysis-v4.js']:
 if file.endswith('.js'):subprocess.run(['node','--check',str(SITE/file)],check=True)
 changes.append(file)
out=SITE/'tools/analysis-update';out.mkdir(parents=True,exist_ok=True)
for file in ['patch.py','core-exports.js','package.py','check_structure.py','check_exports.cjs','validation.json','README.md']:
 shutil.copyfile(ROOT/file,out/file);changes.append('tools/analysis-update/'+file)
queue=[]
for path in changes:
 raw=(SITE/path).read_bytes();queue.append(dict(path=path,content=base64.b64encode(raw).decode(),sha=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest(),bytes=len(raw)))
(ROOT/'queue.json').write_text(json.dumps(queue));print(json.dumps({'files':len(queue),'bytes':sum(r['bytes'] for r in queue),'revision':boot['ui_revision'],'unchanged':'all data assets and all map pages'}))
