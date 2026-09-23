"""Fetch bounded terrain triangles with spatial subdivision if service caps a tile."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'sources'/'terrain';OUT.mkdir(parents=True,exist_ok=True)
URL='https://www.ogd.stadt-zuerich.ch/wfs/geoportal/Digitales_Terrainmodell__TIN_'
LIMIT=20000

def tile(bounds, name, depth=0):
    path=OUT/(name+'.geojson')
    params={'service':'WFS','version':'1.1.0','request':'GetFeature','typeName':'lod0_gelaende',
            'bbox':','.join(map(str,bounds))+',EPSG:2056','srsName':'EPSG:2056',
            'outputFormat':'application/vnd.geo+json','maxFeatures':LIMIT}
    if path.exists(): data=path.read_bytes()
    else:
        for attempt in range(3):
            try:
                r=requests.get(URL,params=params,timeout=(12,90));r.raise_for_status()
                data=r.content
                j=json.loads(data)
                if j.get('type')!='FeatureCollection':raise ValueError('Invalid terrain response')
                path.write_bytes(data);break
            except Exception:
                if attempt==2:raise
    j=json.loads(data);n=len(j.get('features',[]))
    if n>=LIMIT:
        if depth>=4:raise ValueError('Terrain cap unresolved at '+name)
        x0,y0,x1,y1=bounds;xm=(x0+x1)/2;ym=(y0+y1)/2
        return sum([tile(b,name+'_'+str(i),depth+1) for i,b in enumerate(
            [(x0,y0,xm,ym),(xm,y0,x1,ym),(x0,ym,xm,y1),(xm,ym,x1,y1)])],[])
    rec={'file':str(path),'bbox_epsg2056':bounds,'features':n,'bytes':len(data),
         'sha256':hashlib.sha256(data).hexdigest(),
         'source_url':requests.Request('GET',URL,params=params).prepare().url,
         'utc':datetime.now(timezone.utc).isoformat(),'at_limit':False}
    print(json.dumps({'tile':name,'features':n,'bytes':len(data)}),flush=True)
    return [rec]

if __name__=='__main__':
    # Context includes complete proposed G1 and neighboring contact surfaces.
    jobs=[([x,y,x+100,y+100],f'{x}_{y}')
          for x in range(2683400,2684200,100) for y in range(1246300,1247200,100)]
    with ThreadPoolExecutor(max_workers=3) as pool:
        results=list(pool.map(lambda args:tile(*args),jobs))
    leaves=sum(results,[])
    (OUT/'index.json').write_text(json.dumps({'tiles':leaves,
      'note':'Tiles have boundary duplicates. Deduplicate by official objectid before meshing; TIN is not entrance-level survey.'},indent=2),encoding='utf-8')
    print(json.dumps({'complete_tiles':len(leaves),'bytes':sum(t['bytes'] for t in leaves)}))
