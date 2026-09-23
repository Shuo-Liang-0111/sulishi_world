"""Acquire original public I3S geometry with explicit coverage and cache receipts.

No image enhancement; bounds are a source context envelope, not a completion claim.
"""
import concurrent.futures
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import struct
import time
import requests

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'sources'/'mesh'
WEBSCENE=Path('F:/MyWorld/research/goal-construction/zurich-source/webscene-data.json')
BBOX=[2683420,1246300,2684200,1247110]
ORIGIN=[2683775,1246700,400]
OUT.mkdir(parents=True,exist_ok=True)

def fetch(url,path):
    if path.exists():return path.read_bytes()
    path.parent.mkdir(parents=True,exist_ok=True)
    for attempt in range(3):
        try:
            r=requests.get(url,timeout=(12,40));r.raise_for_status()
            path.write_bytes(r.content)
            return r.content
        except Exception:
            if attempt==2:raise
            time.sleep(1+attempt)

def intersects(mbs):
    x,y,z,r=mbs
    dx=max(BBOX[0]-x,0,x-BBOX[2]);dy=max(BBOX[1]-y,0,y-BBOX[3])
    return dx*dx+dy*dy<=r*r

def layer_metadata(layer):
    url=layer['url'];name=url.split('/services/Hosted/')[1].split('/')[0]
    data=json.loads(fetch(url+'?f=pjson',OUT/name/'layer.json'))
    e=data.get('fullExtent',{})
    if not all(k in e for k in ['xmin','ymin','xmax','ymax']):
        raise ValueError('No usable fullExtent: '+name)
    selected=not(e['xmin']>BBOX[2] or e['xmax']<BBOX[0] or e['ymin']>BBOX[3] or e['ymax']<BBOX[1])
    return {'name':name,'url':url,'fullExtent':e,'intersects_context':selected}

def acquire(layer):
    base=layer['url'];folder=OUT/layer['name'];known={}
    is_old=layer['name']=='local_GEOZ_3DMesh_2_1'
    caches=[Path('F:/MyWorld/research/city-reassessment-20260921')/n/'nodes'
            for n in ['zurich-bellevue','zurich-central']]
    def node(i):
        target=folder/'nodes'/(str(i)+'.json')
        if is_old and not target.exists():
            for c in caches:
                p=c/(str(i)+'.json')
                if p.exists():
                    target.parent.mkdir(parents=True,exist_ok=True)
                    target.write_bytes(p.read_bytes());break
        return json.loads(fetch(base+'/nodes/'+str(i),target))
    front=['root'];seen=set();leaves=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        while front:
            todo=[i for i in front if i not in seen];seen.update(todo)
            if len(seen)>25000:raise RuntimeError('Node traversal exceeded diagnostic limit; inspect before continuing')
            ns=list(pool.map(node,todo));front=[]
            for n in ns:
                if not intersects(n['mbs']):continue
                if n.get('children'):
                    front.extend(c['id'] for c in n['children'] if intersects(c['mbs']))
                elif n.get('geometryData'):leaves.append(n)
            print(json.dumps({'layer':layer['name'],'visited':len(seen),'leaves':len(leaves),'next':len(front)}),flush=True)
        (folder/'selection.json').write_text(json.dumps(leaves),encoding='utf-8')
        def asset(n):
            i=n['id'];d=folder/'assets';d.mkdir(exist_ok=True)
            for ext,endpoint in [('bin','geometries'),('jpg','textures')]:
                target=d/(i+'.'+ext)
                if is_old and not target.exists():
                    for c in caches:
                        p=c.parent/'obj'/(i+'.'+ext)
                        if p.exists():target.write_bytes(p.read_bytes());break
                data=fetch(base+f'/nodes/{i}/{endpoint}/0',target)
            raw=(d/(i+'.bin')).read_bytes();tex=(d/(i+'.jpg')).read_bytes()
            nv,nf=struct.unpack_from('<II',raw)
            if nv%3 or len(raw)<8+nv*20:raise ValueError('Unexpected I3S schema: '+i)
            return {'node':i,'mbs':n['mbs'],'vertices':nv,'triangles':nv//3,
                    'geometry':str(d/(i+'.bin')),'texture':str(d/(i+'.jpg')),
                    'geometry_sha256':hashlib.sha256(raw).hexdigest(),
                    'texture_sha256':hashlib.sha256(tex).hexdigest(),
                    'bytes':len(raw)+len(tex)}
        items=list(pool.map(asset,leaves))
    manifest={**layer,'utc':datetime.now(timezone.utc).isoformat(),'bbox_epsg2056':BBOX,
              'origin_epsg2056_ln02':ORIGIN,'node_count':len(seen),'leaf_count':len(items),
              'triangles':sum(i['triangles'] for i in items),'bytes':sum(i['bytes'] for i in items),
              'source_visual_quality':'unmodified photogrammetry; not accepted close-range geometry',
              'selection_note':'All intersecting bounding spheres traversed to leaves; edges may exceed context envelope.',
              'items':items}
    (folder/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in manifest.items() if k not in ['items','fullExtent']}),flush=True)
    return str(folder/'manifest.json')

if __name__=='__main__':
    layers=[l for l in json.loads(WEBSCENE.read_text(encoding='utf-8'))['operationalLayers']
            if l.get('layerType')=='IntegratedMeshLayer']
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        records=list(pool.map(layer_metadata,layers))
    (OUT/'coverage.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
    print(json.dumps({'intersecting_services':[r['name'] for r in records if r['intersects_context']]}),flush=True)
    manifests=[acquire(r) for r in records if r['intersects_context']]
    (OUT/'index.json').write_text(json.dumps({'manifests':manifests,'bbox_epsg2056':BBOX,
                                            'origin_epsg2056_ln02':ORIGIN},indent=2),encoding='utf-8')
