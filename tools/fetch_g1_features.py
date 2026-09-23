"""Bounded WFS source acquisition. Larger context envelope is not the G1 boundary."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
import requests

ROOT = Path(__file__).resolve().parents[1]
BBOX = [2683420, 1246300, 2684200, 1247110]
SETS = [
 ('geo_bauten___dachmodell', 'bauten_dachmodell_3d'),
 ('geo_fuss__und_velowegnetz', 'tbl_routennetz'),
 ('geo_brunnen', 'wvz_brunnen'),
 ('geo_bauminventar', 'bauminventar'),
 ('geo_kunstbauteninventar', 'view_kuba_flaechen'),
 ('geo_kunstbauteninventar', 'view_kuba_linien'),
 ('geo_digitales_terrainmodell__tin_', 'lod0_gelaende'),
]

def fetch(pair, probe):
    package, kind = pair
    cat=json.loads((ROOT/'sources'/'catalogue'/(package+'-summary.json')).read_text(encoding='utf-8'))
    u=next(r['url'] for r in cat['resources'] if r['format'].upper()=='WFS')
    parts=urlsplit(u); endpoint=urlunsplit((parts.scheme,parts.netloc,parts.path,'',''))
    params={'service':'WFS','version':'1.1.0','request':'GetFeature','typeName':kind,
            'bbox':','.join(map(str,BBOX))+',EPSG:2056', 'srsName':'EPSG:2056',
            'outputFormat':'application/vnd.geo+json','maxFeatures':2 if probe else 20000}
    folder=ROOT/'sources'/('feature-probes' if probe else 'features')
    folder.mkdir(parents=True,exist_ok=True)
    path=folder/(kind+'.geojson')
    try:
        if path.exists():
            data=path.read_bytes();url=requests.Request('GET',endpoint,params=params).prepare().url
        else:
            with requests.get(endpoint,params=params,timeout=(12,100),stream=True) as r:
                r.raise_for_status();url=r.url
                chunks=[];n=0
                for b in r.iter_content(65536):
                    n+=len(b)
                    if n>(12_000_000 if probe else 160_000_000):
                        raise ValueError('Source response exceeded bounded acquisition budget')
                    chunks.append(b)
            data=b''.join(chunks)
            if not data.lstrip().startswith(b'{'):
                (folder/(kind+'-error.xml')).write_bytes(data)
                raise ValueError(data.decode('utf-8',errors='replace')[:350])
            j=json.loads(data)
            if j.get('type')!='FeatureCollection':raise ValueError('Not a GeoJSON FeatureCollection')
            path.write_bytes(data)
        j=json.loads(data)
        f=j.get('features',[])
        rec={'source_url':url,'utc':datetime.now(timezone.utc).isoformat(),'bbox_epsg2056':BBOX,
             'role':'source acquisition context, not construction boundary','feature_count':len(f),
             'probe_only':probe,'crs':j.get('crs'),'bytes':len(data),
             'sha256':hashlib.sha256(data).hexdigest(),
             'types':sorted(set(str(x.get('geometry',{}).get('type')) for x in f)),
             'first_properties':f[0].get('properties') if f else None}
        (folder/(kind+'-receipt.json')).write_text(json.dumps(rec,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'layer':kind,'count':len(f),'bytes':len(data),
                          'types':rec['types'],'probe':probe},ensure_ascii=False),flush=True)
        if not probe and len(f)>=20000: raise ValueError('Possible server cap; pagination required')
    except Exception as e:
        print(json.dumps({'layer':kind,'error':str(e)},ensure_ascii=False),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--probe',action='store_true')
    p.add_argument('--skip-terrain',action='store_true');args=p.parse_args()
    chosen=[s for s in SETS if not args.skip_terrain or s[1]!='lod0_gelaende']
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(lambda x:fetch(x,args.probe),chosen))
