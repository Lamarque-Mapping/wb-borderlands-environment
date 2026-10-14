"""Build rural-access analysis and matching source notes from audited exports.

Inputs: decrypted baseline page/analysis and page/map=<code> HTML, boot.json
and manifest.json from commit 927b510, plus the audited full-geometry exports.
Example: python build_analysis.py --input cache --data audited_exports --output staged
Outputs remain staged until separately published. Does not upload or alter refs.
"""
import argparse,base64,gzip,hashlib,json,os,re,shutil
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
ROOT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--input',type=Path,required=True)
parser.add_argument('--data',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
SOURCE=args.input.resolve()
OUT=args.output.resolve()
WORK=OUT.parent/'working'
ASSETS=ROOT if (ROOT/'rural-access-v1.js').exists() else ROOT.parent.parent/'analysis'
CODES={'moyale_borana':'Moyale–Borana','mandera_triangle':'Mandera Triangle','karamoja':'Karamoja','dikhil':'Dikhil'}
REVISION='2026-10-14.rural-analysis.40'
NOTE='''The analysis page ranks all 58 supplied source units, of which 57 have valid percentages. Group summaries equal 100 × summed rural population within 2 km divided by summed rural population across valid selected units; no unweighted averaging, area-overlap weighting or selection-tag weighting is used. These are summaries of whole source-unit selections, including territory outside the cluster boundaries, not access estimates for clipped clusters. WorldPop 2020 source denominators are used, separately from the WorldPop 2025 population charts. West Pokot “unknown 8” has a zero rural-population denominator and remains no data; other original unknown names are retained.'''
for p in (OUT,WORK,OUT/'assets',OUT/'analysis',OUT/'tools/rural-access'):
 p.mkdir(parents=True,exist_ok=True)
rows=[]
for code in CODES:
 data=json.loads((args.data/f'{code}_ruralAccess.json').read_text())
 for f in data['ruralAccessUnits']['features']:
  p=f['properties'];rows.append(dict(cluster=code,id=p['source_record_id'],name=p['NAME_2'],region=p['NAME_1'],country=p['country_side'] or p['NAME_0'],source_country=p['NAME_0'],access_pct=p['rai_pct'],rural_population=p['Pop_A2_R'],within_2km=p['Pop_A2_R2K'],status=p['data_status'],selection_tag=p['supplied_coverage_label']))
assert len(rows)==58 and len({r['id'] for r in rows})==58
assert sum(r['access_pct'] is not None for r in rows)==57
for r in rows:
 if r['access_pct'] is None:assert r['id']=='sedac2023:21174' and r['rural_population']==0
 else:assert abs(r['access_pct']-100*r['within_2km']/r['rural_population'])<1e-5
data=dict(format='wb-rural-access-analysis-v1',clusters=[dict(code=k,name=v) for k,v in CODES.items()],rows=rows)
(WORK/'rural_access_analysis.json').write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'),allow_nan=False))
current=(SOURCE/'page_map_mandera_triangle.html').read_text()
pattern=r'<tr><td>Rural road access · source admin 2 units</td>.*?</tr>'
oldrow=re.search(pattern,current).group()
newrow=oldrow.replace('<tr>','<tr class="rai-source-row">',1).replace('</td></tr>',' '+NOTE+'</td></tr>')
page=(SOURCE/'analysis.html').read_text()
assert 'id="rural-access"' not in page, 'Use the documented pre-analysis baseline to avoid duplicate sections.'
scope=re.search(r'<div class="scope-bar".*?<p id="scopeNote" class="scope-note"></p>\n',page,re.S).group()
page=page.replace(scope,'',1)
maplink=re.search(r'<a id="openMap".*?</a>',page).group()
page=page.replace(maplink,'',1)
section=(ROOT/'analysis_section.html').read_text()
page=page.replace('</style></head>','</style><link rel="stylesheet" href="analysis/rural-access-v1.css?v='+REVISION+'"></head>',1)
page=page.replace('<a href="#violence">Violence</a>','<a href="#rural-access">Rural access</a><a href="#violence">Violence</a>',1)
page=page.replace('<a href="#portfolio">Projects</a>','<a href="#portfolio">Projects</a><a href="#data-sources">Sources &amp; limitations</a>',1)
for old,new in [('06 /','07 /'),('05 /','06 /'),('04 /','05 /'),('03 /','04 /'),('02 /','03 /'),('01 /','02 /')]:page=page.replace(old,new)
page=page.replace('<section id="violence"',section+'\n<div class="rai-geography-label"><span>Geography for the remaining charts</span>'+maplink+'</div>\n'+scope+'<section id="violence"',1)
table=re.search(r'<table class="wb-sources-table">.*?</table>',current,re.S).group().replace('class="wb-sources-table"','class="analysis-sources-table"').replace(oldrow,newrow)
sources='<section id="data-sources" class="analysis-card"><div class="analysis-head"><div><p class="section-kicker">08 / Sources</p><h2>Data sources and limitations</h2></div></div><p class="rai-intro">Sources used across the maps and analysis. Rural road access uses whole SEDAC source units; the other population, landscape and healthcare charts use the stated study-area boundaries.</p><details class="method-note"><summary>Open source and licence table</summary><div class="analysis-sources-scroll" tabindex="0" role="region" aria-label="Data sources and limitations table">'+table+'</div></details><p class="chart-foot">Source dates, definitions and geographical units differ. Road proximity, road-network connectivity and modelled healthcare travel time measure different aspects of access. Their percentages should not be treated as interchangeable or as evidence of a causal relationship.</p></section>\n'
page=page.replace('<footer class="page-foot">',sources+'<footer class="page-foot">',1)
page=page.replace('</main><script>','</main><script src="analysis/rural-access-v1.js?v='+REVISION+'"></script><script>',1)
(WORK/'analysis.html').write_text(page)
for code in CODES:
 p=(SOURCE/f'page_map_{code}.html').read_text();assert p.count(oldrow)==1
 p=p.replace(oldrow,newrow)
 marker="await setPreset(startView==='ruralAccess'?'access':['connectivity','fews','projects'].includes(startView)?startView:'clean');"
 assert p.count(marker)==1
 p=p.replace(marker,marker+"\nif(startView==='ruralAccess'){const unit=new URLSearchParams(parent.location.search).get('unit');if(unit&&ruralAccessFeatures().some(f=>ruralAccessId(f.properties)===unit)){selectRuralAccessUnit(unit);locateRuralAccessUnit();}}")
 (WORK/f'page_map_{code}.html').write_text(p)
boot=json.loads((SOURCE/'boot.json').read_text());original=json.loads((SOURCE/'manifest.json').read_text());manifest=dict(original);parts=dict(boot.get('asset_parts',{}));aes=AESGCM(base64.b64decode(boot['public_key']));changes=[]
def asset(raw,mime):
 nonce=os.urandom(12);identifier=hashlib.sha256(raw+b'\0'+nonce).hexdigest()[:32];path='assets/'+identifier+'.bin';encrypted=aes.encrypt(nonce,gzip.compress(raw,mtime=0),(boot['build']+'|'+identifier).encode());assert gzip.decompress(aes.decrypt(nonce,encrypted,(boot['build']+'|'+identifier).encode()))==raw
 if len(encrypted)>49152:
  chunks=[]
  for n,offset in enumerate(range(0,len(encrypted),49152)):
   dest=f'assets/{identifier}.part{n:03d}.bin';(OUT/dest).write_bytes(encrypted[offset:offset+49152]);changes.append(dest);chunks.append(dest)
  parts[path]=chunks
 else:(OUT/path).write_bytes(encrypted);changes.append(path)
 return dict(path=path,id=identifier,nonce=base64.b64encode(nonce).decode(),gzip=True,mime=mime,bytes=len(encrypted))
manifest['analysis/ruralAccess']=asset((WORK/'rural_access_analysis.json').read_bytes(),'application/json')
manifest['page/analysis']=asset((WORK/'analysis.html').read_bytes(),'text/html')
for code in CODES:manifest['page/map='+code]=asset((WORK/f'page_map_{code}.html').read_bytes(),'text/html')
expected={'page/analysis'}|{'page/map='+c for c in CODES}
assert {k for k in original if original[k]!=manifest[k]}==expected
boot['manifest']=asset(json.dumps(manifest,separators=(',',':')).encode(),'application/json');boot['asset_parts']=parts;boot['ui_revision']=REVISION
(OUT/'boot.json').write_text(json.dumps(boot,separators=(',',':'))+'\n');changes.append('boot.json')
for src,dest in [('rural-access-v1.js','analysis/rural-access-v1.js'),('rural-access-v1.css','analysis/rural-access-v1.css')]:
 shutil.copyfile(ASSETS/src,OUT/dest);changes.append(dest)
for src in ['analysis_section.html','build_analysis.py']:
 dest='tools/rural-access/'+src;shutil.copyfile(ROOT/src,OUT/dest);changes.append(dest)
validation={'status':'passed','records':58,'valid_values':57,'missing_values':1,'changed_manifest_entries':sorted(expected),'added_manifest_entries':['analysis/ruralAccess'],'source_fields_preserved':True,'source_geometries_unchanged':True,'revision':REVISION}
dest='tools/rural-access/validation/analysis_package_2026-10-14.json';(OUT/dest).parent.mkdir(exist_ok=True);(OUT/dest).write_text(json.dumps(validation,indent=2)+'\n');changes.append(dest)
(OUT.parent/'changes.json').write_text(json.dumps(changes,indent=2)+'\n');(WORK/'manifest.json').write_text(json.dumps(manifest))
print(json.dumps({'files':len(changes),'bytes':sum((OUT/p).stat().st_size for p in changes),'validation':validation},indent=2))
