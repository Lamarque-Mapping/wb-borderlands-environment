from html.parser import HTMLParser
from pathlib import Path
import json,re,subprocess
root=Path(__file__).resolve().parent
class Node:
 def __init__(self,tag='',attrs=()):self.tag=tag;self.attrs=dict(attrs);self.children=[]
 def walk(self):
  yield self
  for c in self.children:
   if isinstance(c,Node):yield from c.walk()
 def text(self):return ''.join(c.text() if isinstance(c,Node) else c for c in self.children)
class Parser(HTMLParser):
 def __init__(self):super().__init__();self.root=Node();self.stack=[self.root]
 def handle_starttag(self,tag,attrs):
  n=Node(tag,attrs);self.stack[-1].children.append(n)
  if tag not in ['area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr']:self.stack.append(n)
 def handle_endtag(self,tag):
  for i in range(len(self.stack)-1,0,-1):
   if self.stack[i].tag==tag:self.stack=self.stack[:i];return
 def handle_data(self,data):self.stack[-1].children.append(data)
p=Parser();html=(root/'analysis.html').read_text();p.feed(html);nodes=list(p.root.walk());spec={}
ids=[n.attrs['id'] for n in nodes if 'id' in n.attrs];assert len(ids)==len(set(ids))
sections=[n for n in nodes if n.tag=='section'];expected=['population','urban-settlements','settlement','landcover','deprivation','rural-access','healthcare','violence','historical-heat','portfolio','data-sources'];assert [n.attrs['id'] for n in sections]==expected
nav=next(n for n in nodes if n.tag=='nav' and n.attrs.get('class')=='section-nav');assert [n.attrs['href'][1:] for n in nav.walk() if n.tag=='a']==expected
for n in nodes:
 if 'id' not in n.attrs:continue
 spec[n.attrs['id']]={'tag':n.tag,'value':n.attrs.get('value',''),'text':n.text(),'options':[{'value':o.attrs.get('value',''),'text':o.text()} for o in n.walk() if o.tag=='option'],'buttons':[{'value':b.attrs['data-value'],'text':b.text(),'pressed':b.attrs.get('aria-pressed')} for b in n.walk() if b.tag=='button' and 'data-value' in b.attrs]}
sources=sections[-1];spec['source_rows']=[[c.text().strip() for c in row.children if isinstance(c,Node) and c.tag=='td'] for row in sources.walk() if row.tag=='tr' and any(isinstance(c,Node) and c.tag=='td' for c in row.children)]
(root/'dom-spec.json').write_text(json.dumps(spec))
for i,n in enumerate(n for n in nodes if n.tag=='script'):
 if not n.attrs.get('src'):
  f=root/f'inline-{i}.js';f.write_text(n.text());subprocess.run(['node','--check',str(f)],check=True)
assert len([i for i in ids if i.endswith('ExportCSV')])==11
assert len([i for i in ids if i.endswith('ExportPNG')])==10
print(json.dumps({'order':expected,'unique_ids':len(ids),'data_exports':11,'chart_exports':10,'source_rows':len(spec['source_rows'])}))
