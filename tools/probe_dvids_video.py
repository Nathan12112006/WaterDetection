#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess
from pathlib import Path

OUT=Path('dvids_probe'); OUT.mkdir(exist_ok=True)
urls=[
 'https://www.dvidshub.net/video/968344/mount-whitney-conducts-pipe-patching',
 'https://www.dvidshub.net/video/562980/damage-control-wet-trainer',
 'https://www.dvidshub.net/video/564123/sailors-practice-pipe-patching',
]
report=[]
for i,url in enumerate(urls,1):
 rec={'url':url}
 try:
  p=subprocess.run(['yt-dlp','--no-warnings','--dump-single-json',url],capture_output=True,text=True,timeout=120)
  rec['returncode']=p.returncode; rec['stderr']=p.stderr[-4000:]
  if p.returncode==0:
   data=json.loads(p.stdout)
   rec['id']=data.get('id'); rec['title']=data.get('title'); rec['duration']=data.get('duration'); rec['formats']=[{k:f.get(k) for k in ['format_id','ext','width','height','filesize','filesize_approx','url']} for f in (data.get('formats') or [])[-10:]]
   # Download a compact playable version and extract three frames.
   out=OUT/f'video_{i}.mp4'
   q=subprocess.run(['yt-dlp','--no-warnings','-f','worst[ext=mp4]/worst','-o',str(out),url],capture_output=True,text=True,timeout=240)
   rec['download_rc']=q.returncode; rec['download_stderr']=q.stderr[-2000:]
   if out.exists():
    rec['download_bytes']=out.stat().st_size
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-i',str(out),'-vf','fps=1/15,scale=960:-2','-frames:v','6',str(OUT/f'video_{i}_%02d.jpg')],timeout=120)
  else: rec['json_head']=p.stdout[:2000]
 except Exception as e: rec['error']=repr(e)
 report.append(rec)
(OUT/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps(report,indent=2,ensure_ascii=False))
