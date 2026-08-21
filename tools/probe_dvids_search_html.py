#!/usr/bin/env python3
from pathlib import Path
import json, urllib.parse, requests
from bs4 import BeautifulSoup

OUT=Path('dvids_search_probe'); OUT.mkdir(exist_ok=True)
queries=['pipe patching','damage control wet trainer','flooding casualty','leaking pipe water','dripping water pipe']
headers={'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36','Accept-Language':'en-US,en;q=0.9'}
report={}
for q in queries:
    url='https://www.dvidshub.net/search?'+urllib.parse.urlencode({'q':q})
    r=requests.get(url,headers=headers,timeout=30)
    slug=q.replace(' ','_')
    (OUT/f'{slug}.html').write_bytes(r.content)
    soup=BeautifulSoup(r.text,'html.parser')
    links=[]
    for a in soup.find_all('a',href=True):
        href=urllib.parse.urljoin(r.url,a['href'])
        if '/video/' in href or '/image/' in href:
            links.append({'text':' '.join(a.get_text(' ',strip=True).split())[:200],'href':href})
    forms=[]
    for f in soup.find_all('form'):
        forms.append({'action':urllib.parse.urljoin(r.url,f.get('action') or ''),'method':f.get('method'),'inputs':[{'name':i.get('name'),'value':i.get('value'),'type':i.get('type')} for i in f.find_all('input')]})
    pag=[]
    for a in soup.find_all('a',href=True):
        href=urllib.parse.urljoin(r.url,a['href'])
        text=' '.join(a.get_text(' ',strip=True).split())
        if 'page=' in href or text.lower() in {'next','previous','1','2','3','4','5'}:
            pag.append({'text':text,'href':href})
    report[q]={'status':r.status_code,'url':r.url,'bytes':len(r.content),'media_links':links[:500],'media_link_count':len(links),'forms':forms,'pagination':pag[:100]}
(OUT/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps({q:{'status':v['status'],'bytes':v['bytes'],'media_link_count':v['media_link_count'],'pagination':v['pagination'][:10]} for q,v in report.items()},indent=2))
