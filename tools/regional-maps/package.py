"""Add the regional map collection to the existing public portal."""
from pathlib import Path
import base64,gzip,hashlib,json,os,re,subprocess
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
ROOT=Path(__file__).resolve().parents[2]
boot=json.loads((ROOT/'boot.json').read_text());aes=AESGCM(base64.b64decode(boot['public_key']))
def read(meta):
 raw=b''.join((ROOT/p).read_bytes() for p in boot.get('asset_parts',{}).get(meta['path'],[meta['path']]))
 raw=aes.decrypt(base64.b64decode(meta['nonce']),raw,(boot['build']+'|'+meta['id']).encode())
 return gzip.decompress(raw) if meta.get('gzip') else raw
manifest=json.loads(read(boot['manifest']));original=dict(manifest)
def put(raw,mime):
 nonce=os.urandom(12);aid=hashlib.sha256(raw+nonce).hexdigest()[:32];path='assets/'+aid+'.bin'
 cipher=aes.encrypt(nonce,gzip.compress(raw,mtime=0),(boot['build']+'|'+aid).encode());parts=[]
 if len(cipher)>49152:
  for n,i in enumerate(range(0,len(cipher),49152)):
   p=f'assets/{aid}.part{n:03}.bin';(ROOT/p).write_bytes(cipher[i:i+49152]);parts.append(p)
  boot.setdefault('asset_parts',{})[path]=parts
 else:(ROOT/path).write_bytes(cipher)
 result={'path':path,'id':aid,'nonce':base64.b64encode(nonce).decode(),'gzip':True,'mime':mime,'bytes':len(cipher)}
 assert read(result)==raw
 return result
home=read(manifest['page/home']).decode()
assert 'data-route="regional-maps"' not in home
arrow='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M4 12h15M13 5l7 7-7 7"/></svg>'
regional='<a href="#regional-maps" data-route="regional-maps" target="_top" class="gallery-analysis gallery-regional"><span class="analysis-copy"><strong>Regional maps</strong><small>All four clusters · ACLED event concentrations · Drought and flood hazards · Presentation downloads</small></span>'+arrow+'</a>'
home=home.replace('</main>',regional+'</main>',1)
home=home.replace('<p class="eyebrow">Regional maps</p>','<p class="eyebrow">Four priority clusters</p>',1)
old=re.search(r'<a class="text-link" href="#analysis".*?</a>',home,re.S)
assert old
nav='<nav class="home-nav" aria-label="Explore views"><a class="text-link" href="#regional-maps" data-route="regional-maps" target="_top">Regional maps '+arrow+'</a>'+old.group(0).replace('Explore analysis','Analysis')+'</nav>'
home=home[:old.start()]+nav+home[old.end():]
css='''.gallery-regional{margin-top:16px;background:#e5ece3}.gallery-regional:hover{background:#d8e4d5}.home-nav{margin-left:auto;display:flex;align-items:center;gap:28px}.home-nav .text-link{gap:10px}@media(max-width:760px){.home-nav{gap:20px}.home-nav .text-link{margin-left:0}.gallery-top .site-header{height:auto;min-height:80px;padding-top:18px;padding-bottom:18px;flex-wrap:wrap}}@media(max-width:560px){.home-nav{width:100%;justify-content:space-between}.home-nav .text-link{min-height:36px;font-size:14px}.gallery-top .site-header{gap:12px}}
'''
home=home.replace('</style>',css+'</style>',1)
page=(ROOT/'regional-maps/page.html').read_text()
# All requested links are local and available before updating the route manifest.
for path in re.findall(r'(?:href|src)="(regional-maps/[^"#]+)"',page):
 assert (ROOT/path).is_file(),path
manifest['page/home']=put(home.encode(),'text/html')
manifest['page/regional-maps']=put(page.encode(),'text/html')
assert all(manifest[k]==v for k,v in original.items() if k!='page/home')
boot['routes']=['home','regional-maps','analysis','map=moyale_borana','map=mandera_triangle','map=karamoja','map=dikhil']
boot['manifest']=put(json.dumps(manifest,separators=(',',':')).encode(),'application/json')
boot['ui_revision']='2026-11-11.regional-maps.87'
(ROOT/'boot.json').write_text(json.dumps(boot,separators=(',',':'))+'\n')
# Store readable layout source for future maintenance; runtime still uses verified assets.
(ROOT/'tools/regional-maps/home.html').write_text(home)
shell=(ROOT/'shell.js').read_text()
old="const allowed=boot.routes||['home','analysis','map=moyale_borana','map=mandera_triangle','map=karamoja','map=dikhil'];"
assert shell.count(old)==1;shell=shell.replace(old,"const allowed=boot.routes||['home','regional-maps','analysis','map=moyale_borana','map=mandera_triangle','map=karamoja','map=dikhil'];")
old="name==='analysis'?'analysis':'maps'";assert shell.count(old)==1;shell=shell.replace(old,"name==='analysis'?'analysis':name==='regional-maps'?'regional maps':'maps'")
old="'map=dikhil':'Dikhil',analysis:'Analysis'};";assert shell.count(old)==1;shell=shell.replace(old,"'map=dikhil':'Dikhil',analysis:'Analysis','regional-maps':'Regional maps'};")
(ROOT/'shell.js').write_text(shell)
index=(ROOT/'index.html').read_text();index=re.sub(r'shell\.js\?v=[^"\s]+','shell.js?v=2026-11-11.regional-maps.87',index)
(ROOT/'index.html').write_text(index)
subprocess.run(['node','--check',str(ROOT/'shell.js')],check=True,capture_output=True)
checks={'revision':boot['ui_revision'],'route':'regional-maps','map_files':5,'home_links':home.count('data-route="regional-maps"'),'download_links_resolve':True,'existing_map_and_analysis_assets_unchanged':all(manifest[k]==v for k,v in original.items() if k!='page/home'),'source_png_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'regional-maps/files').glob('*.png')}}
(ROOT/'tools/regional-maps/validation.json').write_text(json.dumps(checks,indent=2)+'\n')
print(json.dumps(checks))
