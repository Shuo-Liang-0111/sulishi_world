"""Read cached higher road candidates omitted by the old409.2m cutoff.

This does not download data or assume horizontal surfaces are automatically
ground. Atlas review and robust outlier exclusion precede grade preparation.
"""
from pathlib import Path
import argparse,hashlib,json,struct
import numpy as np
from shapely.geometry import Point,box,shape

args=argparse.ArgumentParser();args.add_argument('--check',action='store_true');args=args.parse_args()
R=Path(__file__).resolve().parents[1];D=R/'derived/bellevue/bridge_grade';D.mkdir(exist_ok=True)
region=box(2683474,1246800,2683537,1246870)
av={f['id']:shape(f['geometry']) for f in json.loads((R/'sources/features/av_bo_boflaeche_a.geojson').read_text())['features']}
road=av['av_bo_boflaeche_a.549'];interior=road.buffer(-.15)
manifest=json.loads((R/'sources/mesh/local_GEOZ_3DMesh_2_1/manifest.json').read_text())
rows=[];used=[]
for item in manifest['items']:
    m=np.array(item['mbs'])
    if Point(m[:2]).distance(region)>m[3]:continue
    raw=Path(item['geometry']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==item['geometry_sha256'],item['node']
    nv=struct.unpack_from('<I',raw)[0]
    t=np.frombuffer(raw,dtype='<f4',count=nv*3,offset=8).reshape(-1,3,3)+m[:3]
    c=t.mean(1);n=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);length=np.linalg.norm(n,axis=1)
    for i in np.flatnonzero((c[:,2]>408)&(c[:,2]<410.5)&(abs(n[:,2])>.96*length)&(length>.5)):
        point=Point(c[i,:2])
        if region.covers(point) and interior.covers(point):
            rows.append(dict(node=str(item['node']),face=int(i),xyz=c[i].tolist(),triangle=t[i].tolist(),area_m2=float(length[i]/2)))
    used.append(dict(node=str(item['node']),geometry_sha256=item['geometry_sha256'],texture_sha256=item['texture_sha256']))
payload=json.dumps(rows,indent=2);out=D/'raw_source_candidates.json'
if args.check:assert out.read_text(encoding='utf-8')==payload,'Cached preparation differs'
else:out.write_text(payload,encoding='utf-8')
print(json.dumps(dict(check_only=args.check,candidates=len(rows),source_nodes=len(used),sha256=hashlib.sha256(out.read_bytes()).hexdigest())))
