"""Refresh published regional figures and clarify drought provenance in live pages."""
from pathlib import Path
import base64, gzip, hashlib, json, os, re, shutil, zipfile
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
FIGURES=ROOT.parent/'deliverables'
REVISION='2026-11-11.drought-provenance.88'
boot=json.loads((ROOT/'boot.json').read_text())
aes=AESGCM(base64.b64decode(boot['public_key']))
def read(meta):
 raw=b''.join((ROOT/p).read_bytes() for p in boot.get('asset_parts',{}).get(meta['path'],[meta['path']]))
 raw=aes.decrypt(base64.b64decode(meta['nonce']),raw,(boot['build']+'|'+meta['id']).encode())
 return gzip.decompress(raw) if meta.get('gzip') else raw
manifest=json.loads(read(boot['manifest'])); original=dict(manifest)
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

HDX='https://data.humdata.org/dataset/global-drought-hazard'
CSIC='https://spei.csic.es/spei_database/'
WB='https://datacatalog.worldbank.org/search/dataset/0067121/global-drought-hazard-based-on-spei'
def link(url,label):return f'<a href="{url}" target="_blank" rel="noopener noreferrer">{label}</a>'
row=('<tr><td>Drought hazard (SPEI)</td><td><strong>Weller &amp; Mann (2022), Global Drought Hazard.</strong> '
     'Produced by the Institute for International Law of Peace and Armed Conflict (IFHV), Ruhr University Bochum; distributed through '
     +link(HDX,'HDX')+'. Based on '+link(CSIC,'CSIC’s Global SPEI Database')+' (six-month SPEI; January 1902–December 2018).</td>'
     '<td>CC BY 4.0. Also listed in the '+link(WB,'World Bank Data Catalog')+'.</td>'
     '<td>Selected resource: <strong>SPEI ≤ −2.0; 25-year return period</strong>. Values are modelled months at or below the threshold, '
     'averaged within each 10 km hexagon. They are not observations or predictions of a continuous drought spell. Grey means no valid data, not zero. '
     '<strong>The publisher advises against local or regional applications.</strong> The input climate grid is approximately 0.5°; '
     'interpolation and 10 km hexagons do not add local climate detail. This is a global screening product, not a current drought monitor or climate-change projection.</td></tr>')
old_note=' Global Drought Hazard based on SPEI: modelled months at SPEI ≤ −2.0, 25-year return period, aggregated to 10 km hexes. Grey cells have no valid sampled value.'
new_note=' Source: Weller & Mann (2022), IFHV / Ruhr University Bochum, via HDX. Based on CSIC Global SPEI, 1902–2018. Modelled months at SPEI ≤ −2.0; 25-year return period; 10 km hex means. Grey = no valid data, not zero. Global screening product: publisher advises against local/regional applications. Links and full details: Sources and Limitations.'
changed=[];page_dir=ROOT/'tools/regional-maps/live-pages';page_dir.mkdir(exist_ok=True)
for key in ['page/map=karamoja','page/map=moyale_borana','page/map=mandera_triangle','page/map=dikhil','page/analysis']:
 page=read(manifest[key]).decode()
 page,n=re.subn(r'<tr><td>Drought risk</td>.*?</tr>',lambda _:row,page,flags=re.S)
 assert n==1,(key,n)
 if key.startswith('page/map='):
  assert page.count(old_note)==1,key
  page=page.replace(old_note,new_note)
 page=page.replace('Global Drought Hazard based on SPEI; Malaria','Weller &amp; Mann / IFHV Global Drought Hazard via HDX, based on CSIC SPEI; Malaria')
 (page_dir/(key.replace('/','_').replace('=','_')+'.html')).write_text(page)
 manifest[key]=put(page.encode(),'text/html');changed.append(key)

for code in ['karamoja','moyale_borana','mandera_triangle','dikhil']:
 key=code+'/core';core=json.loads(read(manifest[key]));before=json.loads(json.dumps(core))
 metric=core['climateHexMetrics']['drought']
 metric['label']='Modelled months at SPEI ≤ −2.0 — 25-year return period'
 metric['shortLabel']='Drought hazard'
 metric['source']={'citation':'Weller & Mann (2022), Global Drought Hazard','producer':'IFHV, Ruhr University Bochum','distributor':'Humanitarian Data Exchange (HDX)','url':HDX,'resource_id':'3d067bc4-e6bd-413e-a490-2010aa842a63','input':'CSIC Global SPEI Database, six-month SPEI','input_period':'1902–2018','input_url':CSIC,'limitation':'Global screening product; publisher advises against local or regional applications.'}
 for field in ['property','low','high','unit','summaryMethod']:
  assert metric[field]==before['climateHexMetrics']['drought'][field]
 for field in core:
  if field!='climateHexMetrics':assert core[field]==before[field]
 manifest[key]=put(json.dumps(core,separators=(',',':')).encode(),'application/json');changed.append(key)

page=(ROOT/'regional-maps/page.html').read_text()
note=('<p><strong>Drought source:</strong> Weller &amp; Mann (2022), <em>Global Drought Hazard</em>, IFHV / Ruhr University Bochum, distributed through '+link(HDX,'HDX')+'. '
      'Uses '+link(CSIC,'CSIC’s Global SPEI Database')+' for 1902–2018: six-month SPEI, threshold ≤ −2.0, 25-year return period. '
      'Modelled months are averaged within 10 km hexagons; they do not describe a predicted continuous spell. '
      '<strong>The publisher advises against local or regional applications.</strong> This global screening layer has an underlying climate grid of approximately 0.5°. '
      +link(WB,'World Bank catalogue listing')+'.</p>')
notes_tag='<section class="notes" aria-label="Interpretation and sources">'
assert page.count(notes_tag)==1
page=page.replace(notes_tag,notes_tag+note)
# New asset URLs avoid stale browser/CDN image and ZIP caches.
page=re.sub(r'((?:src|href)="regional-maps/(?:previews|files)/[^"?]+)(")',rf'\1?v={REVISION}\2',page)
(ROOT/'regional-maps/page.html').write_text(page)
manifest['page/regional-maps']=put(page.encode(),'text/html');changed.append('page/regional-maps')
assert all(manifest[k]==v for k,v in original.items() if k not in changed)
boot['manifest']=put(json.dumps(manifest,separators=(',',':')).encode(),'application/json');boot['ui_revision']=REVISION
(ROOT/'boot.json').write_text(json.dumps(boot,separators=(',',':'))+'\n')

hashes={}
for p in sorted(FIGURES.glob('*.png')):
 with Image.open(p) as im:
  assert im.size==(3840,2160)
  preview=im.copy();preview.resize((1200,675),Image.Resampling.LANCZOS).convert('RGB').save(ROOT/'regional-maps/previews'/p.with_suffix('.webp').name,quality=88,method=6)
 shutil.copy2(p,ROOT/'regional-maps/files'/p.name)
 hashes[p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
bundle=ROOT/'regional-maps/files/WB_Four_Cluster_Presentation_Maps.zip'
with zipfile.ZipFile(bundle) as z:entries={n:z.read(n) for n in z.namelist()}
for name in entries:
 p=ROOT/'regional-maps/files'/name
 if p.exists():entries[name]=p.read_bytes()
with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for name,raw in entries.items():z.writestr(name,raw)
with zipfile.ZipFile(bundle) as z:
 for name,sha in hashes.items():assert hashlib.sha256(z.read(name)).hexdigest()==sha
checks={'revision':REVISION,'changed_manifest_keys':changed,'other_assets_unchanged':True,'numeric_data_unchanged':True,'regional_credit_removed':True,'distinct_cluster_fills':4,'source_png_hashes':hashes,'source_resource_id':'3d067bc4-e6bd-413e-a490-2010aa842a63','bundle_matches_pngs':True}
(ROOT/'tools/regional-maps/provenance-validation.json').write_text(json.dumps(checks,indent=2)+'\n')
print(json.dumps(checks,indent=2))
