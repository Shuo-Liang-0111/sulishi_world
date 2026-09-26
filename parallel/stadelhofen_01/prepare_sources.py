"""Inspect cached official data, cache one missing primary reference, write only here."""
from pathlib import Path
import sys, json, hashlib, datetime
ROOT = Path('H:/MyWorld/ZurichWorld')
OUT = ROOT/'parallel/stadelhofen_01'
sys.path.insert(0,str(ROOT/'tools'))
from workspace_paths import read_path
import numpy as np
from shapely.geometry import shape, box

for name in ['sources','derived','evidence','runtime','native']:
    (OUT/name).mkdir(exist_ok=True)
scope = box(2683800,1246700,2683950,1246880)
report={}
for layer in ['av_geb_gebaeudeadresse_t','av_bo_boflaeche_a','av_ei_flaechenelement_a','av_ei_linienelement']:
    path=read_path('sources/features/'+layer+'.geojson')
    data=json.loads(path.read_text(encoding='utf-8'))
    selected=[f for f in data['features'] if f['geometry'] and shape(f['geometry']).intersects(scope)]
    (OUT/'derived'/f'{layer}_local.geojson').write_text(json.dumps(dict(type='FeatureCollection',features=selected)),encoding='utf-8')
    report[layer]=[dict(id=f['id'],properties=f['properties'],bounds=shape(f['geometry']).bounds) for f in selected]
    print(layer,len(selected))
g=json.loads(read_path('derived/G1_geo_base.json').read_text())
selected=[]
for o in g['objects']:
    if o['kind']=='terrain_reference':continue
    v=np.array(o['vertices'])
    if not len(v):continue
    lo=v.min(axis=0);hi=v.max(axis=0)
    if hi[0]<25 or lo[0]>175 or hi[1]<0 or lo[1]>180:continue
    selected.append(o)
print('geo-base-buildings',json.dumps([dict(id=o['id'],bounds=[np.min(o['vertices'],axis=0).tolist(),np.max(o['vertices'],axis=0).tolist()]) for o in selected]))
(OUT/'derived/official_local_buildings.json').write_text(json.dumps(dict(origin=g['origin'],objects=selected)))
(OUT/'derived/source_inventory.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')

print('Run cache_reference.py with bundled Python for PDF extraction.')
