"""Clarify missing climate values and hazard units without changing observations."""
from pathlib import Path
import base64,gzip,hashlib,json,os,re,subprocess
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
ROOT=Path(__file__).resolve().parents[2]
BOOT=ROOT/'boot.json';boot=json.loads(BOOT.read_text());aes=AESGCM(base64.b64decode(boot['public_key']))
def read(meta):
 raw=b''.join((ROOT/p).read_bytes() for p in boot.get('asset_parts',{}).get(meta['path'],[meta['path']]))
 dec=aes.decrypt(base64.b64decode(meta['nonce']),raw,(boot['build']+'|'+meta['id']).encode())
 return gzip.decompress(dec) if meta.get('gzip') else dec
manifest=json.loads(read(boot['manifest']));original=dict(manifest);changed=[]
def put(raw,mime):
 nonce=os.urandom(12);aid=hashlib.sha256(raw+nonce).hexdigest()[:32];path='assets/'+aid+'.bin'
 rawzip=gzip.compress(raw,mtime=0);cipher=aes.encrypt(nonce,rawzip,(boot['build']+'|'+aid).encode());parts=[]
 if len(cipher)>49152:
  for n,i in enumerate(range(0,len(cipher),49152)):
   p=f'assets/{aid}.part{n:03}.bin';(ROOT/p).write_bytes(cipher[i:i+49152]);parts.append(p)
  boot.setdefault('asset_parts',{})[path]=parts
 else:(ROOT/path).write_bytes(cipher)
 meta={'path':path,'id':aid,'nonce':base64.b64encode(nonce).decode(),'gzip':True,'mime':mime,'bytes':len(cipher)}
 assert read(meta)==raw
 return meta

def patch_page(page):
 old='if(name==="climate")rows.push(gradientLegend((DATA.climateHexMetrics||{})[currentClimateMode]));'
 new='if(name==="climate"){rows.push(gradientLegend((DATA.climateHexMetrics||{})[currentClimateMode]));rows.push(legendItem(\'<span class="land-swatch" style="background:#e5e7eb"></span>\',"No valid data"));}'
 assert page.count(old)==1
 page=page.replace(old,new)
 old='row(meta.label,formatMetric(value,meta))';new='row(meta.label,value===null?"No valid data":formatMetric(value,meta))'
 assert page.count(old)==1;page=page.replace(old,new)
 old='if(meta&&meta.unit==="months")return n.toFixed(1)+" months";'
 new=old+'if(meta&&meta.unit==="metres")return (n>0&&n<.01?n.toFixed(4):n.toFixed(2))+" m";'
 assert page.count(old)==1;page=page.replace(old,new)
 page=page.replace('Global Drought Hazard based on SPEI, 25-year return period, aggregated to 10 km hexes.','Global Drought Hazard based on SPEI: modelled months at SPEI ≤ −2.0, 25-year return period, aggregated to 10 km hexes. Grey cells have no valid sampled value.')
 page=page.replace('WRI Aqueduct Floods historical river-inundation hazard, 25-year return period, aggregated to 10 km hexes.','WRI Aqueduct Floods historical river-inundation depth in metres, 25-year return period, aggregated to 10 km hexes. Grey cells have no valid sampled value.')
 return page

checks=[]
for code in ['karamoja','moyale_borana','mandera_triangle','dikhil']:
 key='page/map='+code;page=patch_page(read(manifest[key]).decode())
 js='\n'.join(re.findall(r'<script\b[^>]*>(.*?)</script>',page,re.S))
 test=subprocess.run(['node','--check'],input=js,text=True,capture_output=True)
 assert test.returncode==0,test.stderr
 manifest[key]=put(page.encode(),'text/html');changed.append(key)
 key=code+'/core';core=json.loads(read(manifest[key]));oldcore=json.loads(json.dumps(core))
 for collection in ['climateHexMetrics','hexMetrics']:
  for meta in core.get(collection,{}).values():
   if meta.get('property')=='wb_hex_drought':meta['unit']='months';meta['label']='Mean drought duration — SPEI ≤ −2.0, 25-year return period'
   elif meta.get('property')=='wb_hex_river_flood':meta['unit']='metres';meta['label']='Mean river-flood depth — historical 25-year return period'
 manifest[key]=put(json.dumps(core,separators=(',',':')).encode(),'application/json');changed.append(key)
 checks.append({'cluster':code,'javascript_syntax':'passed','climate_units':['months','metres'],'missing_legend':'No valid data','hex_asset_unchanged':manifest[code+'/hexes']==original[code+'/hexes'],'acled_asset_unchanged':manifest[code+'/acled']==original[code+'/acled']})
assert all(manifest[k]==v for k,v in original.items() if k not in changed)
boot['manifest']=put(json.dumps(manifest,separators=(',',':')).encode(),'application/json')
boot['ui_revision']='2026-11-11.climate-clarity.86';BOOT.write_text(json.dumps(boot,separators=(',',':'))+'\n')
(ROOT/'tools/climate-clarity/validation.json').write_text(json.dumps({'revision':boot['ui_revision'],'changed_assets':changed,'unchanged_data':True,'checks':checks},indent=2)+'\n')
print(json.dumps({'updated_pages':4,'updated_metadata':4,'data_observations_changed':0}))
