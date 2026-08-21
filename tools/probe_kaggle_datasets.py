#!/usr/bin/env python3
from __future__ import annotations
import io, json, os, zipfile, hashlib
from pathlib import Path
import requests
from PIL import Image, ImageOps, ImageDraw, ImageFont

OUT=Path('kaggle_probe'); OUT.mkdir(exist_ok=True)
DATASETS={
 'industrial_hazards':'vigneshnachu/industrial-hazards-detection',
 'water_pipes':'tareqalhmiedat/water-pipes-dataset',
 'flooding_images':'hhrclemson/flooding-image-dataset',
}
headers={'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36'}
report={}
for name,slug in DATASETS.items():
 url=f'https://www.kaggle.com/api/v1/datasets/download/{slug}'
 rec={'slug':slug,'url':url}
 try:
  r=requests.get(url,headers=headers,timeout=120,allow_redirects=True)
  rec.update({'status':r.status_code,'final_url':r.url,'content_type':r.headers.get('content-type',''),'bytes':len(r.content),'sha256':hashlib.sha256(r.content).hexdigest()})
  if r.status_code==200 and r.content[:2]==b'PK':
   zpath=OUT/f'{name}.zip'; zpath.write_bytes(r.content)
   with zipfile.ZipFile(io.BytesIO(r.content)) as z:
    infos=z.infolist(); names=[i.filename for i in infos]
    exts={'.jpg','.jpeg','.png','.webp','.bmp'}
    imgs=[i for i in infos if Path(i.filename).suffix.lower() in exts and not i.is_dir()]
    rec['file_count']=len(infos); rec['image_count']=len(imgs); rec['sample_names']=names[:200]
    # Build a 30-image contact sheet from evenly spaced valid images.
    chosen=[]
    if imgs:
     step=max(1,len(imgs)//30)
     for info in imgs[::step]:
      if len(chosen)>=30: break
      try:
       im=Image.open(io.BytesIO(z.read(info))).convert('RGB')
       if min(im.size)<100: continue
       chosen.append((info.filename,im.copy()))
      except Exception: pass
    if chosen:
     cols=5; rows=(len(chosen)+cols-1)//cols; cw=320; ch=245; ih=205
     sheet=Image.new('RGB',(cols*cw,rows*ch),'white'); d=ImageDraw.Draw(sheet); font=ImageFont.load_default()
     for idx,(fn,im) in enumerate(chosen):
      rr,cc=divmod(idx,cols); im.thumbnail((cw-8,ih-8),Image.Resampling.LANCZOS)
      sheet.paste(im,(cc*cw+(cw-im.width)//2,rr*ch+(ih-im.height)//2))
      d.text((cc*cw+4,rr*ch+ih+1),f'{idx+1:02d} {fn[-55:]}',fill='black',font=font)
     sheet.save(OUT/f'{name}_contact.jpg',quality=88)
  else:
   rec['head']=r.text[:1000]
 except Exception as e: rec['error']=repr(e)
 report[name]=rec
 print(name,{k:rec.get(k) for k in ['status','bytes','file_count','image_count','error']})
(OUT/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
