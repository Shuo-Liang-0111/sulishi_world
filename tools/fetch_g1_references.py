from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'sources'/'references';OUT.mkdir(parents=True,exist_ok=True)
BBOX=[2683420,1246300,2684200,1247110]
items=[
 ('stadelhofen-plan-2025-12.pdf','https://cdnsource.sbb.ch/content/dam/infrastruktur/trafimage/bahnhofplaene/plan-zuerich-stadelhofen-a4.pdf.sbbdownload.pdf',None,
  'SBB station plan 12/2025; spatial reference, not a redistributable texture'),
 ('swissimage-context.jpg','https://wms.geo.admin.ch/',
  {'service':'WMS','request':'GetMap','version':'1.3.0','layers':'ch.swisstopo.swissimage',
   'styles':'','crs':'EPSG:2056','bbox':','.join(map(str,BBOX)),
   'width':2340,'height':2430,'format':'image/jpeg'},
  'swisstopo SWISSIMAGE WMS; acquisition year not inferred from request date; survey reference'),
 ('brunnenguide-kreis-1.pdf','https://www.stadt-zuerich.ch/content/dam/web/de/umwelt-energie/wasser/dokumente/brunnenguides/brunnenguide-kreis-1.pdf',None,
  'Official fountain guide; individual years and current operating states need reconciliation')
]
receipts=[]
for name,url,params,note in items:
    path=OUT/name
    try:
        if not path.exists():
            r=requests.get(url,params=params,timeout=(12,80));r.raise_for_status()
            if not r.content.startswith((b'%PDF',b'\xff\xd8')):raise ValueError(r.text[:200])
            path.write_bytes(r.content);finalurl=r.url
        else:finalurl=requests.Request('GET',url,params=params).prepare().url
        data=path.read_bytes()
        receipts.append({'file':str(path),'url':finalurl,'bytes':len(data),
                         'sha256':hashlib.sha256(data).hexdigest(),
                         'utc':datetime.now(timezone.utc).isoformat(),'note':note,
                         'bbox_epsg2056':BBOX if params else None})
        print(json.dumps({'file':name,'bytes':len(data)}),flush=True)
    except Exception as e:
        receipts.append({'file':name,'url':url,'error':str(e)})
        print(json.dumps({'file':name,'error':str(e)}),flush=True)
(OUT/'receipts.json').write_text(json.dumps(receipts,indent=2),encoding='utf-8')
