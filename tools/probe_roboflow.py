#!/usr/bin/env python3
from __future__ import annotations
import json,re,urllib.parse,os,sys
from pathlib import Path
import requests
from bs4 import BeautifulSoup

OUT=Path('roboflow_probe'); OUT.mkdir(exist_ok=True)
PAGES={
 'pipe':'https://universe.roboflow.com/new-workspace-0bgj4/pipe-leak-yp6il',
 'pipe_browse':'https://universe.roboflow.com/new-workspace-0bgj4/pipe-leak-yp6il/browse',
 'acc':'https://universe.roboflow.com/water-leakage-detection/water-leakage',
 'acc_browse':'https://universe.roboflow.com/water-leakage-detection/water-leakage/browse',
}
S=requests.Session(); S.headers.update({'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36','Accept-Language':'en-US,en;q=0.9'})
report={}
all_scripts=[]
for name,url in PAGES.items():
 try:
  r=S.get(url,timeout=30); rec={'status':r.status_code,'len':len(r.content),'url':r.url,'content_type':r.headers.get('content-type','')}
  (OUT/f'{name}.html').write_bytes(r.content)
  text=r.text
  rec['source_urls']=sorted(set(re.findall(r'https://source\.roboflow\.com/[^"\'<>\\ ]+',text)))[:100]
  rec['api_urls']=sorted(set(re.findall(r'https?://[^"\'<>\\ ]*(?:api|browse|dataset|project)[^"\'<>\\ ]*',text)))[:200]
  soup=BeautifulSoup(text,'html.parser')
  scripts=[]
  for tag in soup.find_all('script'):
   src=tag.get('src')
   if src:
    full=urllib.parse.urljoin(r.url,src); scripts.append(full); all_scripts.append(full)
  rec['scripts']=scripts
  nd=soup.find('script',id='__NEXT_DATA__')
  if nd and nd.string:
   (OUT/f'{name}_next_data.json').write_text(nd.string,encoding='utf-8')
   rec['next_data_len']=len(nd.string)
  rec['next_push_count']=text.count('self.__next_f.push')
  report[name]=rec
 except Exception as e: report[name]={'error':repr(e)}

# Download JS chunks and grep informative strings. Limit total to 80 MB.
js_records=[]; total=0
for i,url in enumerate(dict.fromkeys(all_scripts)):
 if total>80_000_000: break
 try:
  r=S.get(url,timeout=30)
  total+=len(r.content)
  p=OUT/f'chunk_{i:03d}.js'; p.write_bytes(r.content)
  t=r.text
  hits=[]
  for pat in ['source.roboflow.com','/browse','api.roboflow','dataset','projectId','workspaceSlug','images?','pagination','cursor','universe']:
   pos=0
   while True:
    j=t.find(pat,pos)
    if j<0: break
    hits.append({'pattern':pat,'snippet':t[max(0,j-250):j+500]})
    pos=j+len(pat)
    if sum(1 for x in hits if x['pattern']==pat)>=8: break
  if hits: js_records.append({'url':url,'status':r.status_code,'len':len(r.content),'hits':hits})
 except Exception as e: js_records.append({'url':url,'error':repr(e)})
report['js_records']=js_records

# Probe likely endpoints and record response status/first text.
workspace='new-workspace-0bgj4'; project='pipe-leak-yp6il'
acc_ws='water-leakage-detection'; acc_proj='water-leakage'
likely=[]
for ws,pr in [(workspace,project),(acc_ws,acc_proj)]:
 likely += [
  f'https://api.roboflow.com/{ws}/{pr}',
  f'https://api.roboflow.com/{ws}/{pr}?api_key=',
  f'https://api.roboflow.com/universe/{ws}/{pr}',
  f'https://universe.roboflow.com/api/{ws}/{pr}',
  f'https://universe.roboflow.com/api/{ws}/{pr}/images',
  f'https://universe.roboflow.com/api/projects/{ws}/{pr}',
  f'https://universe.roboflow.com/{ws}/{pr}/browse?page=2',
 ]
probes=[]
for url in likely:
 try:
  r=S.get(url,timeout=20)
  probes.append({'url':url,'status':r.status_code,'content_type':r.headers.get('content-type',''),'len':len(r.content),'head':r.text[:2000]})
 except Exception as e: probes.append({'url':url,'error':repr(e)})
report['probes']=probes
(OUT/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps({k:({kk:v.get(kk) for kk in ['status','len','source_urls','scripts','next_data_len','next_push_count']} if isinstance(v,dict) else v) for k,v in report.items() if k!='js_records'},indent=2,ensure_ascii=False))
