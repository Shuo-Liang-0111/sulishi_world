"""Compare original survey and I3S heights at fixed LV95 points; no geometry edits."""
import json, struct
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
base=json.loads((ROOT/'derived/G1_geo_base.json').read_text())
terrain=next(o for o in base['objects'] if o['kind']=='terrain_reference')
origin=np.array([2683775,1246700,400])
tv=np.array(terrain['vertices'])+origin
tf=np.array(terrain['faces'])
manifest=json.loads((ROOT/'sources/mesh/local_GEOZ_3DMesh_2_1/manifest.json').read_text())

def hits(tris,p):
    a=tris[:,0,:2]; b=tris[:,1,:2]-a; c=tris[:,2,:2]-a; v=p-a
    d=b[:,0]*c[:,1]-b[:,1]*c[:,0]
    valid=np.abs(d)>1e-8
    d=np.where(valid,d,1)
    u=(v[:,0]*c[:,1]-v[:,1]*c[:,0])/d
    w=(b[:,0]*v[:,1]-b[:,1]*v[:,0])/d
    mask=valid&(u>=-1e-5)&(w>=-1e-5)&(u+w<=1.00001)
    h=tris[:,0,2]+u*(tris[:,1,2]-tris[:,0,2])+w*(tris[:,2,2]-tris[:,0,2])
    return h[mask].tolist()

points={'plaza_camera':[2683644,1246685],'bellevue_camera':[2683562,1246806],
        'station_camera':[2683784,1246740],'pavilion_roof':[2683575,1246838],
        'pavilion_south_apron':[2683577,1246817],'pavilion_east_apron':[2683597,1246840],
        'plaza_north':[2683660,1246775],'lake_edge':[2683540,1246640]}
out={}
for name,point in points.items():
    p=np.array(point); photo=[]
    for item in manifest['items']:
        m=item['mbs']
        if np.linalg.norm(p-np.array(m[:2]))>m[3]: continue
        raw=Path(item['geometry']).read_bytes(); nv=struct.unpack_from('<I',raw)[0]
        v=np.frombuffer(raw,dtype='<f4',count=nv*3,offset=8).reshape(-1,3)+np.array(m[:3])
        for h in hits(v.reshape(-1,3,3),p):photo.append({'z_ln02':h,'node':item['node']})
    out[name]={'lv95':point,'terrain_z':hits(tv[tf],p),
               'photo_surfaces':sorted(photo,key=lambda a:a['z_ln02'])}
(ROOT/'evidence/G1_004r2/surface_alignment.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
