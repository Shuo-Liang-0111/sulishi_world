"""Recreate AV36232 context from already cached official feature layers.

An existing input is compared semantically and preserved byte-for-byte because
saved native checkpoints record its original SHA256.
"""
from pathlib import Path
import hashlib,json
from shapely.geometry import shape

R=Path(__file__).resolve().parents[1];D=R/'derived/bellevue/bridgehead_bank'
D.mkdir(parents=True,exist_ok=True)
paths=[R/'sources/features'/name for name in
       ['av_bo_boflaeche_a.geojson','av_ei_flaechenelement_a.geojson','bauminventar.geojson']]
layers=[json.loads(p.read_text(encoding='utf-8'))['features'] for p in paths]
source=next(f for f in layers[0] if f['id']=='av_bo_boflaeche_a.36232')
foot=shape(source['geometry'])
context=dict(source=source,
    adjacent_structures=[f for f in layers[1] if f.get('geometry') and shape(f['geometry']).intersects(foot)],
    trees=[f for f in layers[2] if f.get('geometry') and shape(f['geometry']).distance(foot)<8],
    origin=[2683775,1246700,400])
path=D/'context.json'
if path.exists():
    assert json.loads(path.read_text(encoding='utf-8'))==context,'Existing context differs: inspect before replacing'
else:path.write_text(json.dumps(context,ensure_ascii=False,indent=2),encoding='utf-8')
report=dict(source=source['id'],structures=len(context['adjacent_structures']),
    nearby_inventory_trees=len(context['trees']),source_area_m2=foot.area,
    source_sha256={p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
    context_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),network_requests=0)
(D/'context_provenance.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
